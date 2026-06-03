"""
V4 Loop Guard — deterministic repetition / stutter / template-stamp detector
for generated decks.

Motivation (from huggingface/ml-intern "Doom Loop Detector" pattern):
    LLMs can settle into a groove where every slide reads the same way —
    same opening verb, same sentence rhythm, near-duplicate bullets, or a
    stuttering phrase ("in order to in order to"). The critic's 5-dim
    rubric catches most of this indirectly, but adjacent-only variety
    penalties miss deck-wide drift. This module looks at the whole deck
    and flags:

        1. Headline duplication (same or ≥80% Jaccard across slides).
        2. Bullet n-gram loops: ≥3 bullets in the deck that share a
           4-gram prefix.
        3. Within-slide stutter: "word word" or "phrase phrase" repeats.
        4. Template-stamping: ≥5 slides using the same layout AND the
           same starter verb across their headlines.
        5. Global intent imbalance: all N slides collapsed to ≤2 intents
           (symptom of a failed planner where the writer auto-repeated).

The module is PURE: no LLM calls, no network, sub-millisecond for 50
slides. It emits a structured report that `critic_engine.py` folds into
its local scoring pass, so deck-wide loops cause a targeted rewrite the
same way a single-slide quality miss does.

Return value is a `LoopGuardReport` that the critic uses two ways:

    * `per_slide_penalty[idx]` — how much to subtract from the slide's
      weighted overall (capped 0..4.0 so no single loop sinks a slide).
    * `per_slide_issues[idx]` — stringified feedback appended to the
      slide's `SlideScore.issues` so the targeted rewrite cycle sees it
      in the `Critic feedback to address:` injection.

This is a HARD quality gate: a loop that survives two rewrite cycles
still lowers the final overall score but will NOT block the deck.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Tunables ────────────────────────────────────────────────────────

# Jaccard threshold above which two headlines count as duplicates.
_HEADLINE_DUP_JACCARD = 0.80

# How many slides must share a 4-gram bullet prefix to flag a loop.
_BULLET_LOOP_MIN_COUNT = 3

# How many slides sharing (layout, starter-verb) counts as a template
# stamp. 5 is intentionally generous: a 10-slide deck with 5 `two-column`
# slides is fine ONLY if they start with different verbs.
_TEMPLATE_STAMP_MIN = 5

# Deck size below which an intent imbalance isn't interesting.
_INTENT_IMBALANCE_MIN_SLIDES = 6


# ── Data structures ────────────────────────────────────────────────

@dataclass
class LoopFinding:
    kind: str                            # "headline_dup" | "bullet_loop" | "stutter" | "template_stamp" | "intent_imbalance"
    slide_indices: list[int]             # every slide this finding implicates
    detail: str                          # short human-readable summary
    severity: float                      # 0..1 scalar used to scale the penalty


@dataclass
class LoopGuardReport:
    findings: list[LoopFinding] = field(default_factory=list)
    per_slide_penalty: dict[int, float] = field(default_factory=dict)
    per_slide_issues: dict[int, list[str]] = field(default_factory=dict)

    @property
    def is_clean(self) -> bool:
        return not self.findings

    @property
    def n_findings(self) -> int:
        return len(self.findings)

    def to_dict(self) -> dict[str, Any]:
        """Emitted via Redis progress events so the UI can surface the
        loops detected."""
        return {
            "n_findings": len(self.findings),
            "findings": [
                {
                    "kind": f.kind,
                    "slide_indices": list(f.slide_indices),
                    "detail": f.detail,
                    "severity": round(f.severity, 2),
                }
                for f in self.findings
            ],
            "per_slide_penalty": {int(k): round(v, 2) for k, v in self.per_slide_penalty.items()},
        }


# ── Small text helpers ─────────────────────────────────────────────

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_STOPWORDS = frozenset(
    "a an the and or of for to in on at by with from as is are was were be been being "
    "this that these those our your their its we you they i it our we’re you’re they’re".split()
)


def _tokenize(text: Optional[str]) -> list[str]:
    if not text:
        return []
    return [w.lower() for w in _WORD_RE.findall(text)]


def _content_tokens(text: Optional[str]) -> list[str]:
    """Tokens minus stopwords — used for Jaccard headline comparison."""
    return [w for w in _tokenize(text) if w not in _STOPWORDS]


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _starter_verb(headline: str) -> Optional[str]:
    """Return the first content word of the headline (lowercase)."""
    toks = _content_tokens(headline)
    return toks[0] if toks else None


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


# ── Individual detectors ───────────────────────────────────────────

def _detect_headline_duplicates(slides: list[Any]) -> list[LoopFinding]:
    """Pairwise Jaccard on content-only tokens. O(N^2) but N ≤ 50 so this
    is a few microseconds."""
    findings: list[LoopFinding] = []
    token_bags = [(s.index, _content_tokens(getattr(s, "headline", ""))) for s in slides]
    flagged: set[frozenset[int]] = set()
    for i, (idx_i, toks_i) in enumerate(token_bags):
        if not toks_i:
            continue
        for idx_j, toks_j in token_bags[i + 1 :]:
            if not toks_j:
                continue
            key = frozenset({idx_i, idx_j})
            if key in flagged:
                continue
            j = _jaccard(toks_i, toks_j)
            if j >= _HEADLINE_DUP_JACCARD:
                flagged.add(key)
                findings.append(LoopFinding(
                    kind="headline_dup",
                    slide_indices=[idx_i, idx_j],
                    detail=f"Slides {idx_i} and {idx_j} share ~{int(j * 100)}% headline tokens",
                    severity=min(1.0, j),
                ))
    return findings


# Intent families — semantically equivalent intents that should NEVER
# produce the same headline (e.g., unique_advantage + usp).
_INTENT_FAMILIES = [
    {"unique_advantage", "usp", "differentiation", "moat"},
    {"market", "market_size", "opportunity", "demand"},
    {"solution", "product", "how_it_works", "platform"},
    {"team", "founders", "leadership", "advisors"},
    {"traction", "milestones", "growth", "progress"},
    {"problem", "pain", "challenge", "gap"},
    {"business_model", "pricing", "revenue", "monetization"},
    {"competition", "competitors", "landscape", "alternatives"},
]


def _intent_family(intent: str) -> frozenset[str]:
    """Return the intent family this intent belongs to, or a singleton."""
    intent_lower = (intent or "").lower()
    for family in _INTENT_FAMILIES:
        if intent_lower in family:
            return frozenset(family)
    return frozenset({intent_lower})


def _detect_intent_family_duplicates(slides: list[Any]) -> list[LoopFinding]:
    """Detect slides in the same intent family with duplicate headlines.

    The planner sometimes creates both 'unique_advantage' and 'usp' slides.
    If the writer produces the same headline for both, the deck looks broken.
    This detector catches intent-level duplication even when the raw headline
    text differs slightly (Jaccard >= 0.70 within a family).
    """
    findings: list[LoopFinding] = []
    flagged: set[frozenset[int]] = set()

    # Group slides by intent family
    family_to_slides: dict[frozenset[str], list[Any]] = defaultdict(list)
    for s in slides:
        family_to_slides[_intent_family(getattr(s, "intent", ""))].append(s)

    for family, family_slides in family_to_slides.items():
        if len(family_slides) < 2:
            continue
        # Pairwise Jaccard within the family
        token_bags = [
            (s.index, _content_tokens(getattr(s, "headline", "")))
            for s in family_slides
        ]
        for i, (idx_i, toks_i) in enumerate(token_bags):
            if not toks_i:
                continue
            for idx_j, toks_j in token_bags[i + 1 :]:
                if not toks_j:
                    continue
                key = frozenset({idx_i, idx_j})
                if key in flagged:
                    continue
                j = _jaccard(toks_i, toks_j)
                # Lower threshold (0.70) for intent-family duplicates because
                # semantically similar intents are more likely to drift.
                if j >= 0.70:
                    flagged.add(key)
                    findings.append(LoopFinding(
                        kind="intent_family_dup",
                        slide_indices=[idx_i, idx_j],
                        detail=(
                            f"Slides {idx_i} and {idx_j} share ~{int(j * 100)}% "
                            f"headline tokens within intent family {sorted(family)[:3]}"
                        ),
                        severity=min(1.0, j + 0.15),  # Higher penalty for intent dups
                    ))
    return findings


def _detect_bullet_loops(slides: list[Any]) -> list[LoopFinding]:
    """A 4-gram bullet prefix that recurs across ≥3 slides is a writer
    loop (classic symptom: "We will leverage AI to..." x 6).
    """
    prefix_to_slides: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for s in slides:
        bullets = getattr(s, "bullets", []) or []
        seen_in_slide: set[tuple[str, ...]] = set()
        for b in bullets:
            toks = _content_tokens(b)
            # Need at least the 4-gram window we're going to compare.
            # Five-token bullets ("will leverage AI automate workflows")
            # still indicate a writer loop when repeated across slides;
            # demanding 7+ tokens missed real loops in short bullets.
            if len(toks) < 4:
                continue
            key = tuple(toks[:4])
            # Count each prefix at most once per slide.
            if key in seen_in_slide:
                continue
            seen_in_slide.add(key)
            prefix_to_slides[key].append(s.index)
    findings: list[LoopFinding] = []
    for prefix, indices in prefix_to_slides.items():
        if len(indices) >= _BULLET_LOOP_MIN_COUNT:
            findings.append(LoopFinding(
                kind="bullet_loop",
                slide_indices=sorted(set(indices)),
                detail=f"{len(indices)} slides start a bullet with '{' '.join(prefix)}'",
                severity=min(1.0, 0.3 + 0.15 * len(indices)),
            ))
    return findings


_STUTTER_RE = re.compile(r"\b(\w+)\s+\1\b", flags=re.IGNORECASE)


def _detect_stutter(slides: list[Any]) -> list[LoopFinding]:
    """Within-slide "word word" stutter — typical artifact of resume-hint
    fallback running off the rails."""
    findings: list[LoopFinding] = []
    for s in slides:
        fields = [
            getattr(s, "headline", "") or "",
            getattr(s, "subheadline", "") or "",
            getattr(s, "body", "") or "",
            " ".join(str(bullet or "") for bullet in (getattr(s, "bullets", []) or [])),
        ]
        text = " ".join(f for f in fields if f)
        matches = _STUTTER_RE.findall(text)
        # Filter out legit repeats we allow ("that that" mid-sentence is
        # rare; "no no" is emphasis). We flag any repeat of a token ≥3
        # chars since longer stutters are almost always bugs.
        real = [m for m in matches if len(m) >= 3]
        if real:
            findings.append(LoopFinding(
                kind="stutter",
                slide_indices=[s.index],
                detail=f"Slide {s.index} stutters on: {', '.join(sorted(set(real))[:3])}",
                severity=min(1.0, 0.4 + 0.15 * len(real)),
            ))
    return findings


def _detect_template_stamp(slides: list[Any]) -> list[LoopFinding]:
    """≥ _TEMPLATE_STAMP_MIN slides that share both `layout` AND the
    starter verb of the headline."""
    if len(slides) < _TEMPLATE_STAMP_MIN:
        return []
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for s in slides:
        layout = (getattr(s, "layout", "") or "").lower()
        verb = _starter_verb(getattr(s, "headline", "") or "")
        if not layout or not verb:
            continue
        groups[(layout, verb)].append(s.index)
    findings: list[LoopFinding] = []
    for (layout, verb), indices in groups.items():
        if len(indices) >= _TEMPLATE_STAMP_MIN:
            findings.append(LoopFinding(
                kind="template_stamp",
                slide_indices=sorted(indices),
                detail=(
                    f"{len(indices)} slides share layout='{layout}' and headline "
                    f"starter '{verb}'"
                ),
                severity=min(1.0, 0.2 + 0.1 * len(indices)),
            ))
    return findings


def _detect_intent_imbalance(slides: list[Any]) -> list[LoopFinding]:
    """If a planner collapsed into ≤2 distinct intents on a ≥6-slide deck,
    the writer loop has gone global."""
    if len(slides) < _INTENT_IMBALANCE_MIN_SLIDES:
        return []
    intents = [((getattr(s, "intent", "") or "").lower() or "unknown") for s in slides]
    counter = Counter(intents)
    distinct = len(counter)
    if distinct <= 2:
        # Flag EVERY slide — it's a deck-wide pathology.
        return [LoopFinding(
            kind="intent_imbalance",
            slide_indices=[s.index for s in slides],
            detail=(
                f"Deck collapses into {distinct} intent(s): "
                + ", ".join(f"{k}×{v}" for k, v in counter.most_common())
            ),
            severity=1.0,
        )]
    return []


# ── Public entry point ────────────────────────────────────────────

def detect_loops(slides: list[Any]) -> LoopGuardReport:
    """Run every detector and return a merged report.

    `slides` is a list of GeneratedSlide (or any object exposing
    `.index`, `.headline`, `.bullets`, `.layout`, `.intent`,
    `.subheadline`, `.body`).
    """
    report = LoopGuardReport()
    if not slides:
        return report

    all_findings: list[LoopFinding] = []
    try:
        all_findings.extend(_detect_headline_duplicates(slides))
        all_findings.extend(_detect_intent_family_duplicates(slides))
        all_findings.extend(_detect_bullet_loops(slides))
        all_findings.extend(_detect_stutter(slides))
        all_findings.extend(_detect_template_stamp(slides))
        all_findings.extend(_detect_intent_imbalance(slides))
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("loop_guard_detection_failed", error=str(e))
        return report

    report.findings = all_findings

    # Fold findings into per-slide penalties and issue strings.
    # Penalty cap = 4.0 per slide (keeps a single slide from zeroing out
    # even if every detector fires).
    for f in all_findings:
        pts = 1.5 * f.severity
        for idx in f.slide_indices:
            report.per_slide_penalty[idx] = min(
                4.0, report.per_slide_penalty.get(idx, 0.0) + pts
            )
            report.per_slide_issues.setdefault(idx, []).append(
                f"loop_{f.kind}: {f.detail}"
            )

    logger.info(
        "v4_loop_guard_scan",
        n_findings=len(all_findings),
        n_slides_flagged=len(report.per_slide_penalty),
        kinds=sorted({f.kind for f in all_findings}),
    )
    return report
