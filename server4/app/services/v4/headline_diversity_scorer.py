"""
V4 headline-diversity scorer.

Runs *across the deck* (after the per-slide HeadlineQualityGate).
Catches the failure mode where every individual headline passes the
specificity check but the deck as a whole reads as 8 variations of
the same thesis. Real-world investor decks fail diligence when the
problem / solution / market / traction headlines all pattern-match.

Scoring axes
~~~~~~~~~~~~

1. **Generic-template overlap** — headlines that match known weak
   patterns ("Transforming X with AI", "The Future of Y", "Building
   the Best Z") are penalized as a deck even when each individual
   line passed the per-slide gate.

2. **Verb diversity** — strong decks use a wide verb vocabulary across
   slides (Close, Eliminate, Reach, Capture, Compound, Earn, Defend).
   Weak decks reuse the same verb 4+ times ("We deliver X", "We
   deliver Y", "We deliver Z").

3. **Noun-phrase repetition** — penalize repeated leading noun phrases
   (e.g. "Our platform" / "Our product" / "Our team" all starting the
   same way reads as a template stamp).

4. **Bigram overlap** — Jaccard similarity on 2-grams across pairs of
   headlines; high overlap pairs surface as redundant.

The scorer returns a score 0-10 plus the indices that need
regeneration (those with the worst overlap). The writer's quality
loop reads the indices and re-rolls only those headlines.
"""

from __future__ import annotations

import re
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import structlog

logger = structlog.get_logger(__name__)


_GENERIC_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\btransforming\s+\w+\s+with\s+ai\b", re.IGNORECASE),
    re.compile(r"\bthe future of\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bbuilding\s+the\s+(best|next)\s+\w+\b", re.IGNORECASE),
    re.compile(r"\brevolutioniz(e|ing)\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bdisrupting\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bnext[- ]?gen(eration)?\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bworld[- ]?class\b", re.IGNORECASE),
    re.compile(r"\bbest[- ]in[- ]class\b", re.IGNORECASE),
    re.compile(r"\bend[- ]to[- ]end\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bunleash(ing)?\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bone[- ]?stop\s+(shop|solution|platform)\b", re.IGNORECASE),
    re.compile(r"\bgame[- ]?chang(er|ing)\b", re.IGNORECASE),
    re.compile(r"\bunique value proposition\b", re.IGNORECASE),
)

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]+")
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "he", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "to", "was", "we", "with", "our", "us", "you",
    "your", "this", "these", "those", "but", "if", "their", "they",
    "them", "his", "her", "him", "she", "do", "does", "did",
})


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokens(text) if t not in _STOPWORDS and len(t) > 1]


def _bigrams(tokens: list[str]) -> list[tuple[str, str]]:
    return list(zip(tokens, tokens[1:]))


def _leading_noun_phrase(text: str) -> str:
    """Return the first 2 content tokens — captures whether two
    headlines start the same way (e.g. "Our platform delivers X" vs
    "Our platform automates Y" both → "platform delivers"-ish).
    """
    toks = _content_tokens(text)
    return " ".join(toks[:2])


def _first_verb(text: str) -> str:
    """Best-effort: return the first verb-like token. We don't run a
    POS tagger — verbs are typically the second word after a "We" /
    "Our" subject, or the first word in imperative-style headlines.
    """
    toks = _tokens(text)
    if not toks:
        return ""
    if toks[0] in {"we", "our", "the", "a"}:
        return toks[1] if len(toks) > 1 else ""
    return toks[0]


@dataclass
class HeadlineDiversityResult:
    score: float                  # 0..10
    issues: list[str] = field(default_factory=list)
    flagged_indices: list[int] = field(default_factory=list)
    verb_repeats: dict[str, int] = field(default_factory=dict)
    leading_phrase_repeats: dict[str, int] = field(default_factory=dict)
    generic_hits: list[tuple[int, str]] = field(default_factory=list)
    semantic_pairs: list[tuple[int, int, float]] = field(default_factory=list)


def score_deck_diversity(
    slides: Iterable[Any],
    *,
    embedding_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> HeadlineDiversityResult:
    """Score headline diversity across a deck.

    Args:
      slides: iterable of objects with ``.headline`` and ``.index``
        attributes (GeneratedSlide / compiled-slide source). Slides
        without a headline are silently skipped.

    Returns:
      HeadlineDiversityResult with a 0..10 score and the flagged
      slide indices that should regenerate.
    """
    slide_list = [s for s in slides if getattr(s, "headline", None)]
    if not slide_list:
        return HeadlineDiversityResult(score=10.0)

    n = len(slide_list)
    issues: list[str] = []
    flagged: set[int] = set()
    score = 10.0

    # 1. Generic-template hits.
    generic_hits: list[tuple[int, str]] = []
    for slide in slide_list:
        h = str(slide.headline or "")
        for pattern in _GENERIC_PATTERNS:
            if pattern.search(h):
                idx = int(getattr(slide, "index", 0) or 0)
                generic_hits.append((idx, pattern.pattern))
                flagged.add(idx)
                break
    if generic_hits:
        issues.append(f"{len(generic_hits)} headlines match known generic templates")
        score -= min(3.0, 0.6 * len(generic_hits))

    # 2. Verb diversity — same first verb on 3+ slides is a stamp.
    verb_counter: Counter[str] = Counter()
    verb_to_indices: dict[str, list[int]] = {}
    for slide in slide_list:
        verb = _first_verb(slide.headline)
        if not verb or verb in _STOPWORDS:
            continue
        verb_counter[verb] += 1
        idx = int(getattr(slide, "index", 0) or 0)
        verb_to_indices.setdefault(verb, []).append(idx)
    verb_repeats = {v: c for v, c in verb_counter.items() if c >= 3}
    if verb_repeats:
        for v, c in verb_repeats.items():
            issues.append(f"verb {v!r} appears at the start of {c} headlines")
            for idx in verb_to_indices.get(v, [])[1:]:  # keep one, regen the rest
                flagged.add(idx)
        score -= min(2.5, 0.5 * sum(verb_repeats.values()))

    # 3. Leading noun-phrase repetition — same first 3 content tokens.
    phrase_counter: Counter[str] = Counter()
    phrase_to_indices: dict[str, list[int]] = {}
    for slide in slide_list:
        phrase = _leading_noun_phrase(slide.headline)
        if not phrase:
            continue
        phrase_counter[phrase] += 1
        idx = int(getattr(slide, "index", 0) or 0)
        phrase_to_indices.setdefault(phrase, []).append(idx)
    leading_phrase_repeats = {p: c for p, c in phrase_counter.items() if c >= 2}
    if leading_phrase_repeats:
        # Only penalize if a phrase repeats 3+ times — 2 is normal cohesion.
        heavy = {p: c for p, c in leading_phrase_repeats.items() if c >= 3}
        if heavy:
            for p, c in heavy.items():
                issues.append(f"leading phrase {p!r} repeats across {c} headlines")
                for idx in phrase_to_indices.get(p, [])[1:]:
                    flagged.add(idx)
            score -= min(2.0, 0.5 * sum(heavy.values()))

    # 4. Bigram Jaccard overlap — pairwise. High overlap on 2+ pairs
    # is a signal the headlines are paraphrases of each other.
    bigram_sets: list[set[tuple[str, str]]] = [
        set(_bigrams(_content_tokens(s.headline))) for s in slide_list
    ]
    high_overlap_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bigram_sets[i], bigram_sets[j]
            if not a or not b:
                continue
            intersect = len(a & b)
            union = len(a | b)
            if union == 0:
                continue
            jaccard = intersect / union
            if jaccard >= 0.4:
                high_overlap_pairs += 1
                idx_b = int(getattr(slide_list[j], "index", 0) or 0)
                flagged.add(idx_b)
    if high_overlap_pairs:
        issues.append(f"{high_overlap_pairs} headline pairs share >=40% bigrams")
        score -= min(2.5, 0.5 * high_overlap_pairs)

    # 5. Semantic cosine overlap. Production can pass a MiniLM embedding
    # function; tests and constrained local runs fall back to deterministic
    # lexical vectors so this scorer never downloads a model implicitly.
    semantic_pairs: list[tuple[int, int, float]] = []
    vectors = _headline_vectors([str(s.headline or "") for s in slide_list], embedding_fn)
    for i in range(n):
        for j in range(i + 1, n):
            sim = _cosine(vectors[i], vectors[j])
            if sim > 0.85:
                idx_i = int(getattr(slide_list[i], "index", 0) or 0)
                idx_j = int(getattr(slide_list[j], "index", 0) or 0)
                semantic_pairs.append((idx_i, idx_j, round(sim, 3)))
                flagged.add(idx_j)
    if semantic_pairs:
        issues.append(f"{len(semantic_pairs)} headline pairs exceed 0.85 semantic cosine similarity")
        score -= min(3.0, 0.7 * len(semantic_pairs))

    score = max(0.0, round(score, 2))
    return HeadlineDiversityResult(
        score=score,
        issues=issues,
        flagged_indices=sorted(flagged),
        verb_repeats=verb_repeats,
        leading_phrase_repeats=leading_phrase_repeats,
        generic_hits=generic_hits,
        semantic_pairs=semantic_pairs,
    )


_SYNONYM_CANONICAL = {
    "automates": "automate",
    "automating": "automate",
    "automation": "automate",
    "reduces": "reduce",
    "reduced": "reduce",
    "cuts": "reduce",
    "slashes": "reduce",
    "lowers": "reduce",
    "cost": "cost",
    "costs": "cost",
    "spend": "cost",
    "expenses": "cost",
    "invoice": "invoice",
    "invoices": "invoice",
    "billing": "invoice",
    "approval": "approval",
    "approvals": "approval",
    "finance": "finance",
    "financial": "finance",
    "teams": "team",
    "team": "team",
    "platform": "workflow",
    "automation": "workflow",
    "workflow": "workflow",
    "workflows": "workflow",
    "system": "workflow",
    "systems": "workflow",
}


def _headline_vectors(
    headlines: list[str],
    embedding_fn: Callable[[list[str]], list[list[float]]] | None,
) -> list[list[float]]:
    if embedding_fn is not None:
        try:
            vectors = embedding_fn(headlines)
            if len(vectors) == len(headlines) and all(isinstance(v, list) for v in vectors):
                return vectors
        except Exception as exc:  # noqa: BLE001
            logger.warning("headline_embedding_fn_failed", error=str(exc)[:160])
    return [_lexical_semantic_vector(headline) for headline in headlines]


def _lexical_semantic_vector(headline: str) -> list[float]:
    tokens = [
        _SYNONYM_CANONICAL.get(token, token)
        for token in _content_tokens(headline)
    ]
    dims = [0.0] * 128
    for token in tokens:
        bucket = int(hashlib.sha1(token.encode("utf-8")).hexdigest()[:8], 16) % len(dims)
        dims[bucket] += 1.0
    return dims


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    mag_a = sum(a[i] * a[i] for i in range(n)) ** 0.5
    mag_b = sum(b[i] * b[i] for i in range(n)) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


__all__ = ["score_deck_diversity", "HeadlineDiversityResult"]
