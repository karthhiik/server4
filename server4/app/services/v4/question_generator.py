"""
Conversational Question Generator — Standard Mode Only.

Generates ≤8 user-friendly, founder-oriented questions based on missing
startup pillars in the user's prompt. Designed to run in <1s using Groq.

This service only fires for standard mode when the InputAnalyzer detects
an `input_richness_score` below the configurable threshold (default 0.7).

Mechanism:
  1. InputAnalyzer identifies `missing_context` fields (traction, team, etc.)
  2. This generator maps each missing field to a natural chat question.
  3. Questions are emitted as an `awaiting_input` event via the existing
     interactive_prompt infrastructure (Redis polling).
  4. User answers enrich the original prompt before research/skeleton/writer.

Premium mode is completely untouched by this service.
"""

from __future__ import annotations

from typing import Any, Optional

import structlog

from app.models.generation_input_v4 import InputAnalysisResult

logger = structlog.get_logger(__name__)

# ── Richness threshold ──────────────────────────────────────────────
# If the InputAnalyzer rates the prompt at or above this score, skip
# questions entirely and proceed straight to generation (Gamma approach).
DEFAULT_RICHNESS_THRESHOLD = 0.7

# ── Maximum questions ───────────────────────────────────────────────
MAX_QUESTIONS = 8


# ── Question bank ───────────────────────────────────────────────────
# Maps missing_context field names (from InputAnalyzer) to user-friendly
# chat questions. Inspired by PitchBob.io's conversational flow.
QUESTION_BANK: dict[str, dict[str, Any]] = {
    "company_name": {
        "text": "What's your company or project name?",
        "placeholder": "e.g., Acme AI",
        "importance": "critical",
        "order": 1,
    },
    "traction": {
        "text": "What traction do you have so far? (Revenue, users, customers, partnerships — anything that shows momentum)",
        "placeholder": "e.g., $50K MRR, 200 paying customers, 15% MoM growth",
        "importance": "critical",
        "order": 2,
    },
    "fundraising": {
        "text": "How much are you raising and what round is this?",
        "placeholder": "e.g., $2M Seed round, closing Q3 2026",
        "importance": "critical",
        "order": 3,
    },
    "financials": {
        "text": "Share any key financial metrics you have. (ARR, MRR, burn rate, runway, etc.)",
        "placeholder": "e.g., $1.2M ARR, $80K MRR, 18 months runway",
        "importance": "critical",
        "order": 4,
    },
    "team": {
        "text": "Who are the founders? What's their relevant background?",
        "placeholder": "e.g., Jane Doe (CEO, ex-Google PM), John Smith (CTO, MIT CS)",
        "importance": "recommended",
        "order": 5,
    },
    "market": {
        "text": "What's the market opportunity? Any sizing data? (TAM, SAM, SOM)",
        "placeholder": "e.g., $50B TAM, $5B SAM in enterprise hiring",
        "importance": "recommended",
        "order": 6,
    },
    "competitors": {
        "text": "Who are your main competitors? What's your unfair advantage?",
        "placeholder": "e.g., We compete with Lever and Greenhouse, but our AI cuts time-to-hire by 60%",
        "importance": "optional",
        "order": 7,
    },
    "business_model": {
        "text": "How does your business make money? (Pricing model, unit economics)",
        "placeholder": "e.g., SaaS subscription, $499/mo per seat, 85% gross margin",
        "importance": "optional",
        "order": 8,
    },
}

# Priority order for importance levels
_IMPORTANCE_ORDER = {"critical": 0, "recommended": 1, "optional": 2}


class ConversationalQuestionGenerator:
    """Generates ≤8 user-friendly pitch-deck questions from InputAnalysisResult.

    Usage in the pipeline::

        gen = ConversationalQuestionGenerator()
        questions = gen.generate(analysis)  # list[dict] or []
        if questions:
            # pause pipeline, ask user via WS, then enrich prompt
    """

    def __init__(
        self,
        richness_threshold: float = DEFAULT_RICHNESS_THRESHOLD,
        max_questions: int = MAX_QUESTIONS,
    ) -> None:
        self.richness_threshold = richness_threshold
        self.max_questions = max_questions

    def generate(self, analysis: InputAnalysisResult) -> list[dict[str, Any]]:
        """Return a list of question dicts, or empty list if prompt is rich enough.

        Each dict:
          - id:          str  — field key (e.g. "traction")
          - text:        str  — the question to display
          - placeholder: str  — input placeholder hint
          - importance:  str  — "critical" | "recommended" | "optional"
          - required:    bool — True for critical questions
        """
        if analysis.input_richness_score >= self.richness_threshold:
            logger.info(
                "question_generator_skipped",
                reason="input_rich_enough",
                score=analysis.input_richness_score,
                threshold=self.richness_threshold,
            )
            return []

        # Collect questions for every missing field that has a bank entry
        missing_fields = {mc.field for mc in analysis.missing_context}
        candidates: list[dict[str, Any]] = []

        for mc in analysis.missing_context:
            bank_entry = QUESTION_BANK.get(mc.field)
            if not bank_entry:
                continue
            candidates.append({
                "id": mc.field,
                "text": bank_entry["text"],
                "placeholder": bank_entry.get("placeholder", ""),
                "importance": mc.importance,
                "required": mc.importance == "critical",
                "order": bank_entry.get("order", 99),
            })

        # Sort: critical first, then recommended, then optional — stable by order
        candidates.sort(key=lambda q: (_IMPORTANCE_ORDER.get(q["importance"], 2), q["order"]))

        questions = candidates[: self.max_questions]

        logger.info(
            "question_generator_result",
            n_missing=len(missing_fields),
            n_questions=len(questions),
            richness=analysis.input_richness_score,
            threshold=self.richness_threshold,
        )
        return questions


def build_qa_schema(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an interactive_prompt-compatible schema from generated questions.

    The schema is emitted as the ``schema`` field of an ``awaiting_input``
    event so the frontend knows how to render the conversational Q&A UI.
    """
    return {
        "title": "A few quick questions to build your pitch deck",
        "description": (
            "Answer what you can — skip anything you're unsure about. "
            "The more context you provide, the better your deck will be."
        ),
        "kind": "conversational_qa",
        "fields": [
            {
                "name": q["id"],
                "type": "text",
                "label": q["text"],
                "placeholder": q.get("placeholder", ""),
                "required": q.get("required", False),
                "importance": q["importance"],
            }
            for q in questions
        ],
    }


def enrich_prompt_with_answers(
    original_prompt: str,
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
) -> str:
    """Append user answers to the original prompt as structured context.

    This produces an enriched prompt string that the downstream research
    collector and skeleton planner can consume as if the user had originally
    typed a very detailed prompt.
    """
    answer_parts: list[str] = []
    for q in questions:
        qid = q["id"]
        answer_text = str(answers.get(qid) or answers.get("payload", {}).get(qid, "")).strip()
        if not answer_text:
            continue
        # Map field ID to a natural label for the enriched prompt
        label_map = {
            "company_name": "Company",
            "traction": "Traction",
            "fundraising": "Fundraising",
            "financials": "Financials",
            "team": "Team",
            "market": "Market",
            "competitors": "Competitors",
            "business_model": "Business Model",
        }
        label = label_map.get(qid, qid.replace("_", " ").title())
        answer_parts.append(f"{label}: {answer_text}")

    if not answer_parts:
        return original_prompt

    enriched = (
        f"{original_prompt}\n\n"
        f"--- Additional Context (from founder Q&A) ---\n"
        f"{chr(10).join(answer_parts)}"
    )
    return enriched
