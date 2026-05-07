"""
V4 HF Reranker — local bge-reranker-v2-m3 cross-encoder wrapper.

Model: BAAI/bge-reranker-v2-m3
  - License: Apache-2.0 (commercial-safe for SaaS)
  - Size: 568M params (~1.1GB FP32, ~570MB FP16)
  - Source: https://huggingface.co/BAAI/bge-reranker-v2-m3
  - Multilingual; strong on diverse domains.
  - Why this over Jina rerankers: Jina v2 base is cc-by-nc-4.0 (NOT SaaS-safe).

Usage:
    reranker = await get_reranker()
    scores = await reranker.score(query, [passage_a, passage_b, ...])
    top = await reranker.top_k(query, passages, k=8)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

MODEL_ID = "BAAI/bge-reranker-v2-m3"


class HFReranker:
    def __init__(self) -> None:
        self._model = None
        self._lock = asyncio.Lock()
        self._load_failed: Optional[str] = None

    async def _ensure_loaded(self):
        await self._do_load()

    def is_loaded(self) -> bool:
        return self._model is not None

    def load_failed(self) -> Optional[str]:
        return self._load_failed

    async def warm(self, *, timeout_s: float = 60.0) -> bool:
        """Public warm-up. Awaits model load up to `timeout_s`. Returns True if
        loaded, False if it failed or timed out. Never raises."""
        if self._model is not None:
            return True
        if self._load_failed is not None:
            return False
        try:
            await asyncio.wait_for(self._do_load(), timeout=timeout_s)
            return self._model is not None
        except asyncio.TimeoutError:
            logger.warning("hf_reranker.warm_timeout", timeout_s=timeout_s)
            return False
        except Exception as e:  # noqa: BLE001
            logger.warning("hf_reranker.warm_failed", error=str(e)[:200])
            return False

    async def _do_load(self):
        if self._model is not None:
            return
        if self._load_failed is not None:
            raise RuntimeError(f"hf_reranker previously failed to load: {self._load_failed}")
        async with self._lock:
            if self._model is not None:
                return
            if self._load_failed is not None:
                raise RuntimeError(f"hf_reranker previously failed to load: {self._load_failed}")
            try:
                from sentence_transformers import CrossEncoder  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "sentence-transformers not installed; "
                    "add `sentence-transformers>=2.7.0` to requirements.txt"
                ) from e
            cache_dir = self._cache_dir()
            hf_token = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN")
            device = os.environ.get("MODEL_DEVICE", "cpu")
            logger.info("hf_reranker.loading", model=MODEL_ID, device=device)

            def _load():
                kwargs: dict[str, Any] = {"device": device, "cache_folder": str(cache_dir)}
                if hf_token:
                    # Newer sentence-transformers uses `token=`; older used `use_auth_token=`.
                    # Try newer arg first and fall back silently.
                    try:
                        return CrossEncoder(MODEL_ID, token=hf_token, **kwargs)
                    except TypeError:
                        return CrossEncoder(MODEL_ID, use_auth_token=hf_token, **kwargs)
                return CrossEncoder(MODEL_ID, **kwargs)

            try:
                self._model = await asyncio.to_thread(_load)
                logger.info("hf_reranker.loaded", model=MODEL_ID)
            except Exception as e:  # noqa: BLE001
                self._load_failed = f"{type(e).__name__}: {str(e)[:160]}"
                logger.warning("hf_reranker.load_failed", error=self._load_failed)
                raise

    @staticmethod
    def _cache_dir() -> Path:
        try:
            from app.config import settings
            d = Path(getattr(settings, "EMBEDDINGS_PATH", "") or "./.cache/embeddings")
        except Exception:
            d = Path("./.cache/embeddings")
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def score(self, query: str, passages: list[str], *, batch_size: int = 16) -> list[float]:
        """Return one relevance score per passage."""
        if not query or not passages:
            return [0.0 for _ in passages]
        await self._ensure_loaded()
        pairs = [(query, p if p and p.strip() else " ") for p in passages]

        def _predict():
            return self._model.predict(  # type: ignore[union-attr]
                pairs, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True
            )

        arr = await asyncio.to_thread(_predict)
        return [float(x) for x in arr.tolist()]

    async def top_k(self, query: str, passages: list[str], k: int = 8) -> list[tuple[int, float]]:
        """Return [(original_index, score)] sorted desc by score, truncated to k."""
        scores = await self.score(query, passages)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:k]


_reranker: Optional[HFReranker] = None
_init_lock = asyncio.Lock()


async def get_reranker() -> HFReranker:
    global _reranker
    if _reranker is not None:
        return _reranker
    async with _init_lock:
        if _reranker is None:
            _reranker = HFReranker()
        return _reranker
