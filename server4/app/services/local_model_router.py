"""
Local Model Router — Routes zero-cost tasks to HuggingFace local models.

Uses TinyLlama, Flan-T5, Phi-2 for classification, entity extraction,
and claim typing tasks. Falls back to keyword/regex approaches if local
models or torch are unavailable.

Reads USE_TINYLLAMA, USE_FLAN_T5, USE_PHI2, MODEL_DEVICE from env.
"""

import asyncio
import logging
import re
from functools import lru_cache
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Safe imports — graceful degradation if torch/transformers missing ─

_HAS_TORCH = False
_HAS_TRANSFORMERS = False
_HAS_SENTENCE_TRANSFORMERS = False

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    logger.info("torch not installed — local models disabled, using fallbacks")

try:
    import transformers  # noqa: F401
    _HAS_TRANSFORMERS = True
except ImportError:
    logger.info("transformers not installed — local models disabled, using fallbacks")

try:
    from sentence_transformers import SentenceTransformer  # noqa: F401
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    logger.info("sentence-transformers not installed — embedding fallback active")


# ── Regex patterns for fallback classification ───────────────────

_DECK_TYPE_PATTERNS: dict[str, list[str]] = {
    "investor_pitch": [
        "investor", "pitch", "fundrais", "series", "seed", "venture",
        "valuation", "cap table", "term sheet", "raise",
    ],
    "sales_deck": [
        "sales", "customer", "prospect", "demo", "pricing", "roi",
        "case study", "testimonial", "onboarding",
    ],
    "internal_strategy": [
        "strategy", "roadmap", "okr", "kpi", "quarterly", "internal",
        "board meeting", "executive summary",
    ],
    "product_launch": [
        "launch", "product", "feature", "release", "beta", "announcement",
        "go-to-market", "gtm",
    ],
    "educational": [
        "tutorial", "training", "workshop", "course", "learn",
        "education", "lecture", "teach",
    ],
}

_AUDIENCE_PATTERNS: dict[str, list[str]] = {
    "investors": [
        "investor", "vc", "venture", "angel", "fund", "lp", "gp",
        "raise", "series", "seed", "pre-seed",
    ],
    "customers": [
        "customer", "client", "prospect", "buyer", "user", "enterprise",
    ],
    "internal": [
        "team", "internal", "board", "executive", "management", "employee",
    ],
    "general": [
        "public", "audience", "conference", "summit", "keynote",
    ],
}

_SECTOR_PATTERNS: dict[str, list[str]] = {
    "fintech": ["fintech", "banking", "payment", "insurance", "lending", "neobank"],
    "healthtech": ["health", "medical", "biotech", "pharma", "clinical", "patient"],
    "saas": ["saas", "software", "platform", "cloud", "subscription", "b2b"],
    "ai_ml": ["ai", "machine learning", "deep learning", "nlp", "llm", "neural"],
    "ecommerce": ["ecommerce", "e-commerce", "retail", "marketplace", "shopping"],
    "edtech": ["education", "edtech", "learning", "school", "university", "course"],
    "cleantech": ["clean", "energy", "solar", "wind", "sustainability", "carbon"],
    "cybersecurity": ["security", "cyber", "encryption", "privacy", "compliance"],
    "logistics": ["logistics", "supply chain", "shipping", "freight", "warehouse"],
    "proptech": ["real estate", "proptech", "property", "housing", "rental"],
}

_CLAIM_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("numeric", [
        r"\$[\d,.]+", r"[\d,.]+\s*%", r"[\d,.]+\s*(million|billion|trillion|M|B|T)",
        r"\d+x\b", r"[\d,.]+\s*(users|customers|revenue|ARR|MRR)",
    ]),
    ("trend", [
        r"(growing|declining|increasing|decreasing|rising|falling)",
        r"(year.over.year|YoY|MoM|QoQ)", r"(CAGR|growth rate)",
        r"(trend|momentum|trajectory|acceleration)",
    ]),
    ("comparison", [
        r"(compared to|versus|vs\.?|outperform|better than|worse than)",
        r"(relative to|in contrast|unlike|similar to)",
        r"(more than|less than|higher|lower|faster|slower)",
    ]),
    ("citation", [
        r"(according to|cited by|published in|reported by)",
        r"(study|research|paper|journal|survey|report)",
        r"(et al\.?|doi:|arxiv|isbn)",
    ]),
    ("testimonial", [
        r'(".*")', r"(said|stated|noted|commented|remarked)",
        r"(testimonial|review|endorsement|quote)",
    ]),
    ("regulatory", [
        r"(regulation|compliance|law|act|statute|directive)",
        r"(FDA|SEC|GDPR|HIPAA|SOC|ISO|PCI)",
        r"(approved|certified|licensed|registered)",
    ]),
    ("qualitative", []),  # Default fallback
]

_ENTITY_COMPANY_PAT = re.compile(
    r"\b([A-Z][a-zA-Z0-9&'-]+(?:\s+[A-Z][a-zA-Z0-9&'-]+)*"
    r"(?:\s+(?:Inc\.?|Corp\.?|Ltd\.?|LLC|Co\.?|PLC|GmbH|S\.A\.?|AG))?)\b"
)
_ENTITY_MARKET_PAT = re.compile(
    r"\b([A-Za-z\s\-]+?)\s+(?:market|industry|sector)\b", re.IGNORECASE
)
_ENTITY_METRIC_PAT = re.compile(
    r"(\$[\d,.]+\s*(?:billion|trillion|million|B|T|M|bn|mn)?|[\d,.]+\s*%)",
)
_ENTITY_TECH_TERMS = {
    "AI", "ML", "NLP", "LLM", "GPT", "blockchain", "SaaS",
    "IoT", "API", "cloud", "5G", "AR", "VR", "deep learning",
    "kubernetes", "serverless", "web3", "DeFi",
}
_ENTITY_STOP = {
    "The", "This", "That", "These", "With", "From", "About",
    "However", "Therefore", "Moreover", "Additionally", "According",
    "Based", "While", "Although", "Since", "Because", "Despite",
}


class LocalModelRouter:
    """Routes zero-cost tasks to local HuggingFace models."""

    TASK_MAP: dict[str, dict[str, str]] = {
        "intent_classification": {"model": "flan-t5", "fallback": "cf-glm"},
        "entity_extraction": {"model": "phi-2", "fallback": "cf-qwen"},
        "claim_typing": {"model": "flan-t5", "fallback": "cf-glm"},
        "embedding": {"model": "all-MiniLM-L6-v2", "fallback": "cf-workers-embedding"},
    }

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._available: dict[str, bool] = {}
        self._device: str = getattr(settings, "MODEL_DEVICE", "cpu")
        self._loading: dict[str, bool] = {}  # prevent concurrent loads
        self._init_models()

    def _init_models(self) -> None:
        """
        Register available local models based on env config.
        Lazy loading — model loaded on first use, not at startup.
        """
        can_load = _HAS_TORCH and _HAS_TRANSFORMERS

        self._available["flan-t5"] = (
            can_load and getattr(settings, "USE_FLAN_T5", False)
        )
        self._available["phi-2"] = (
            can_load and getattr(settings, "USE_PHI2", False)
        )
        self._available["tinyllama"] = (
            can_load and getattr(settings, "USE_TINYLLAMA", False)
        )
        self._available["all-MiniLM-L6-v2"] = _HAS_SENTENCE_TRANSFORMERS

        logger.info(
            "local_model_router_init",
            device=self._device,
            has_torch=_HAS_TORCH,
            has_transformers=_HAS_TRANSFORMERS,
            has_sentence_transformers=_HAS_SENTENCE_TRANSFORMERS,
            available_models={k: v for k, v in self._available.items() if v},
        )

    def _load_model(self, model_name: str) -> Any:
        """Load a model on first use. Thread-safe via flag."""
        if model_name in self._models:
            return self._models[model_name]

        if self._loading.get(model_name):
            return None
        self._loading[model_name] = True

        try:
            if model_name == "flan-t5" and self._available.get("flan-t5"):
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                model_id = "google/flan-t5-small"
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
                model = model.to(self._device)
                model.eval()
                self._models["flan-t5"] = {"model": model, "tokenizer": tokenizer}
                logger.info("flan_t5_loaded", device=self._device)
                return self._models["flan-t5"]

            if model_name == "phi-2" and self._available.get("phi-2"):
                from transformers import AutoModelForCausalLM, AutoTokenizer
                model_id = "microsoft/phi-2"
                tokenizer = AutoTokenizer.from_pretrained(
                    model_id, trust_remote_code=True
                )
                model = AutoModelForCausalLM.from_pretrained(
                    model_id, trust_remote_code=True,
                    torch_dtype=torch.float32,
                )
                model = model.to(self._device)
                model.eval()
                self._models["phi-2"] = {"model": model, "tokenizer": tokenizer}
                logger.info("phi2_loaded", device=self._device)
                return self._models["phi-2"]

            if model_name == "tinyllama" and self._available.get("tinyllama"):
                from transformers import AutoModelForCausalLM, AutoTokenizer
                model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                model = AutoModelForCausalLM.from_pretrained(
                    model_id, torch_dtype=torch.float32
                )
                model = model.to(self._device)
                model.eval()
                self._models["tinyllama"] = {"model": model, "tokenizer": tokenizer}
                logger.info("tinyllama_loaded", device=self._device)
                return self._models["tinyllama"]

            if model_name == "all-MiniLM-L6-v2" and self._available.get(
                "all-MiniLM-L6-v2"
            ):
                from sentence_transformers import SentenceTransformer as ST
                model = ST("all-MiniLM-L6-v2", device=self._device)
                self._models["all-MiniLM-L6-v2"] = model
                logger.info("minilm_loaded", device=self._device)
                return model

        except Exception:
            logger.exception("model_load_failed", model=model_name)
            self._available[model_name] = False
        finally:
            self._loading[model_name] = False

        return None

    # ── Public API ────────────────────────────────────────────

    async def classify_intent(self, text: str) -> dict[str, Any]:
        """
        Classify deck type, audience, sector from text.
        Returns: {deck_type, audience, sector, confidence}
        Uses Flan-T5 for classification with prompt-based approach.
        Falls back to keyword matching if model unavailable.
        """
        if self._available.get("flan-t5"):
            result = await self._flan_t5_classify(text)
            if result:
                return result

        # Fallback: keyword-based classification
        return self._keyword_classify_intent(text)

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract named entities (companies, markets, metrics).
        Uses Phi-2 or falls back to regex/keyword extraction.
        Returns: [{name, type, confidence}]
        """
        if self._available.get("phi-2"):
            result = await self._phi2_extract_entities(text)
            if result:
                return result

        # Fallback: regex-based extraction
        return self._regex_extract_entities(text)

    async def classify_claim(self, claim: str) -> str:
        """
        Classify claim type (numeric, qualitative, trend, etc.).
        Uses Flan-T5, falls back to regex.
        """
        if self._available.get("flan-t5"):
            result = await self._flan_t5_classify_claim(claim)
            if result:
                return result

        # Fallback: regex-based classification
        return self._regex_classify_claim(claim)

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate text embedding for ChromaDB indexing.
        Uses all-MiniLM-L6-v2, falls back to simple hash-based vector.
        Returns: 384-dimensional float vector
        """
        if self._available.get("all-MiniLM-L6-v2"):
            result = await self._minilm_embed(text)
            if result is not None:
                return result

        # Fallback: deterministic pseudo-embedding (for dev/testing only)
        return self._fallback_embedding(text)

    def is_available(self, task: str) -> bool:
        """Check if local model is available for a task."""
        task_info = self.TASK_MAP.get(task)
        if not task_info:
            return False
        return self._available.get(task_info["model"], False)

    # ── Flan-T5 methods ───────────────────────────────────────

    async def _flan_t5_classify(self, text: str) -> Optional[dict[str, Any]]:
        """Use Flan-T5 for intent classification."""
        model_bundle = self._load_model("flan-t5")
        if not model_bundle:
            return None

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None, self._flan_t5_classify_sync, text, model_bundle
            )
            return result
        except Exception:
            logger.exception("flan_t5_classify_failed")
            return None

    def _flan_t5_classify_sync(
        self, text: str, bundle: dict[str, Any]
    ) -> dict[str, Any]:
        """Synchronous Flan-T5 classification."""
        model = bundle["model"]
        tokenizer = bundle["tokenizer"]
        text_truncated = text[:512]

        # Deck type classification
        deck_prompt = (
            f"Classify the following text into one of these presentation types: "
            f"investor_pitch, sales_deck, internal_strategy, product_launch, educational. "
            f"Text: {text_truncated}\nType:"
        )
        deck_type = self._flan_t5_generate(model, tokenizer, deck_prompt).strip().lower()
        deck_type = self._sanitize_category(
            deck_type, list(_DECK_TYPE_PATTERNS.keys()), "investor_pitch"
        )

        # Audience classification
        aud_prompt = (
            f"Who is the target audience for this text: investors, customers, internal, or general? "
            f"Text: {text_truncated}\nAudience:"
        )
        audience = self._flan_t5_generate(model, tokenizer, aud_prompt).strip().lower()
        audience = self._sanitize_category(
            audience, list(_AUDIENCE_PATTERNS.keys()), "general"
        )

        # Sector classification
        sector_prompt = (
            f"What industry sector does this text describe? "
            f"Options: fintech, healthtech, saas, ai_ml, ecommerce, edtech, "
            f"cleantech, cybersecurity, logistics, proptech. "
            f"Text: {text_truncated}\nSector:"
        )
        sector = self._flan_t5_generate(model, tokenizer, sector_prompt).strip().lower()
        sector = self._sanitize_category(
            sector, list(_SECTOR_PATTERNS.keys()), "saas"
        )

        return {
            "deck_type": deck_type,
            "audience": audience,
            "sector": sector,
            "confidence": 0.75,
            "method": "flan-t5",
        }

    def _flan_t5_generate(
        self, model: Any, tokenizer: Any, prompt: str, max_new_tokens: int = 30
    ) -> str:
        """Generate text with Flan-T5."""
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                num_beams=1,
            )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)

    async def _flan_t5_classify_claim(self, claim: str) -> Optional[str]:
        """Use Flan-T5 for claim type classification."""
        model_bundle = self._load_model("flan-t5")
        if not model_bundle:
            return None

        loop = asyncio.get_running_loop()
        try:
            prompt = (
                f"Classify this claim into one type: numeric, qualitative, trend, "
                f"comparison, citation, testimonial, regulatory. "
                f"Claim: {claim[:300]}\nType:"
            )
            result = await loop.run_in_executor(
                None,
                self._flan_t5_generate,
                model_bundle["model"],
                model_bundle["tokenizer"],
                prompt,
                10,
            )
            valid_types = [
                "numeric", "qualitative", "trend", "comparison",
                "citation", "testimonial", "regulatory",
            ]
            cleaned = result.strip().lower()
            if cleaned in valid_types:
                return cleaned
            # Map partial matches
            for vt in valid_types:
                if vt in cleaned:
                    return vt
            return None
        except Exception:
            logger.exception("flan_t5_claim_classify_failed")
            return None

    # ── Phi-2 methods ─────────────────────────────────────────

    async def _phi2_extract_entities(
        self, text: str
    ) -> Optional[list[dict[str, Any]]]:
        """Use Phi-2 for entity extraction."""
        model_bundle = self._load_model("phi-2")
        if not model_bundle:
            return None

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, self._phi2_extract_sync, text, model_bundle
            )
        except Exception:
            logger.exception("phi2_extract_failed")
            return None

    def _phi2_extract_sync(
        self, text: str, bundle: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Synchronous Phi-2 entity extraction."""
        model = bundle["model"]
        tokenizer = bundle["tokenizer"]

        prompt = (
            f"Extract all named entities from this text. "
            f"For each entity, provide: name, type (company/market/metric/technology/person). "
            f"Output as a list.\n\n"
            f"Text: {text[:400]}\n\n"
            f"Entities:\n"
        )
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=False,
                num_beams=1,
                pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        # Parse the output — try line-by-line extraction
        entities: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line in raw.strip().split("\n"):
            line = line.strip().lstrip("-•* ")
            if not line:
                continue
            # Try parsing "Name (type)" or "Name: type" patterns
            name, etype = self._parse_entity_line(line)
            if name and name.lower() not in seen:
                seen.add(name.lower())
                entities.append({
                    "name": name,
                    "type": etype,
                    "confidence": 0.7,
                    "method": "phi-2",
                })
            if len(entities) >= 20:
                break

        return entities if entities else self._regex_extract_entities(text)

    @staticmethod
    def _parse_entity_line(line: str) -> tuple[Optional[str], str]:
        """Parse a line like 'Google (company)' or 'Google: company'."""
        import re as _re
        # Pattern: Name (type)
        m = _re.match(r"(.+?)\s*\((\w+)\)", line)
        if m:
            return m.group(1).strip(), m.group(2).lower()
        # Pattern: Name: type
        m = _re.match(r"(.+?):\s*(\w+)", line)
        if m:
            return m.group(1).strip(), m.group(2).lower()
        # Pattern: Name - type
        m = _re.match(r"(.+?)\s*-\s*(\w+)", line)
        if m and len(m.group(2)) > 2:
            return m.group(1).strip(), m.group(2).lower()
        return None, "unknown"

    # ── MiniLM embedding ──────────────────────────────────────

    async def _minilm_embed(self, text: str) -> Optional[list[float]]:
        """Generate embedding with all-MiniLM-L6-v2."""
        model = self._load_model("all-MiniLM-L6-v2")
        if model is None:
            return None

        loop = asyncio.get_running_loop()
        try:
            embedding = await loop.run_in_executor(
                None, lambda: model.encode(text[:512], normalize_embeddings=True)
            )
            return embedding.tolist()
        except Exception:
            logger.exception("minilm_embed_failed")
            return None

    # ── Fallback methods ──────────────────────────────────────

    def _keyword_classify_intent(self, text: str) -> dict[str, Any]:
        """Keyword-based intent classification (no ML required)."""
        text_lower = text.lower()

        def _score_patterns(patterns: dict[str, list[str]]) -> tuple[str, float]:
            best_cat = ""
            best_score = 0.0
            for category, keywords in patterns.items():
                hits = sum(1 for kw in keywords if kw in text_lower)
                score = hits / max(len(keywords), 1)
                if score > best_score:
                    best_score = score
                    best_cat = category
            return best_cat, best_score

        deck_type, dt_score = _score_patterns(_DECK_TYPE_PATTERNS)
        audience, aud_score = _score_patterns(_AUDIENCE_PATTERNS)
        sector, sec_score = _score_patterns(_SECTOR_PATTERNS)

        # Apply defaults if nothing matched
        if not deck_type or dt_score < 0.05:
            deck_type = "investor_pitch"
        if not audience or aud_score < 0.05:
            audience = "investors"
        if not sector or sec_score < 0.05:
            sector = "saas"

        avg_confidence = (dt_score + aud_score + sec_score) / 3
        return {
            "deck_type": deck_type,
            "audience": audience,
            "sector": sector,
            "confidence": round(min(0.7, avg_confidence + 0.2), 2),
            "method": "keyword_fallback",
        }

    def _regex_extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Regex-based entity extraction (no ML required)."""
        entities: list[dict[str, Any]] = []
        seen: set[str] = set()

        def _add(name: str, etype: str, conf: float = 0.5) -> None:
            key = name.strip().lower()
            if key and key not in seen and len(key) > 1:
                seen.add(key)
                entities.append({
                    "name": name.strip(),
                    "type": etype,
                    "confidence": conf,
                    "method": "regex_fallback",
                })

        # Companies
        for m in _ENTITY_COMPANY_PAT.finditer(text):
            name = m.group(1).strip()
            words = name.split()
            if len(words) >= 2 and words[0] not in _ENTITY_STOP:
                _add(name, "company", 0.5)

        # Markets
        for m in _ENTITY_MARKET_PAT.finditer(text):
            market_name = m.group(1).strip()
            if len(market_name) > 3:
                _add(f"{market_name} market", "market", 0.5)

        # Metrics
        for m in _ENTITY_METRIC_PAT.finditer(text):
            _add(m.group(1), "metric", 0.6)

        # Technology terms
        for term in _ENTITY_TECH_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                _add(term, "technology", 0.6)

        return entities

    def _regex_classify_claim(self, claim: str) -> str:
        """Regex-based claim type classification."""
        for claim_type, patterns in _CLAIM_TYPE_RULES:
            if not patterns:
                continue
            for pat in patterns:
                if re.search(pat, claim, re.IGNORECASE):
                    return claim_type
        return "qualitative"

    @staticmethod
    def _fallback_embedding(text: str, dim: int = 384) -> list[float]:
        """
        Deterministic pseudo-embedding for dev/testing when no model available.
        Uses character-level hashing to produce a stable vector.
        NOT suitable for production semantic search — only for pipeline testing.
        """
        import hashlib
        import struct

        # Hash text in overlapping windows to capture some positional info
        vector = [0.0] * dim
        text_bytes = text.encode("utf-8", errors="replace")
        for i in range(dim):
            chunk = text_bytes[i % len(text_bytes): (i % len(text_bytes)) + 16]
            h = hashlib.md5(chunk + i.to_bytes(4, "little")).digest()  # noqa: S324
            val = struct.unpack("<f", h[:4])[0]
            # Normalize to [-1, 1]
            vector[i] = max(-1.0, min(1.0, val / 1e10))

        # L2 normalize
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    @staticmethod
    def _sanitize_category(
        value: str, valid: list[str], default: str
    ) -> str:
        """Map model output to valid category or default."""
        value = value.strip().lower().replace(" ", "_").replace("-", "_")
        if value in valid:
            return value
        # Partial match
        for v in valid:
            if v in value or value in v:
                return v
        return default
