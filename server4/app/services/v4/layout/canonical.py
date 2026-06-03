"""Canonical layout catalog — single source of truth for layout names.

The V4 generator emits 13 canonical layout strings on every slide:
    title-only, two-column, stat-hero, grid-3, chart-focus, image-full,
    quote, comparison, timeline, table, diagram, process, bullet-points

The frontend (``barise-editorial-main/src/lib/server4.ts``) used to maintain
its own ``SERVER4_LAYOUT_ALIASES`` map of 60+ aliases, which silently drifted
every time the backend introduced a new kit variant. This module makes the
backend the authority: ``GET /api/v4/layouts`` returns the catalog, and the
frontend consumes it instead of duplicating the mapping.

Stays aligned with:
- ``app.services.v4.skeleton_planner._CANONICAL_LAYOUTS`` (the writer-side set)
- ``app.routers.v4_editor._ALLOWED_LAYOUTS`` (the editor-side PATCH validator)
- The kit module names in ``lliveupdatedstreaming/sandbox/src/kit/index.ts``

Any drift between this module and the three surfaces above is a real bug.
The accompanying contract test ``tests/test_canonical_layout_catalog.py``
fails CI if the sets diverge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutEntry:
    """One canonical layout the V4 generator emits.

    ``aliases`` lists every legacy / variant string that downstream code
    should normalize to ``id``. Aliases include lowercase kit names and
    legacy shorthand the writer occasionally produced before the canonical
    set was enforced.
    """

    id: str
    description: str
    kit_components: tuple[str, ...]
    aliases: tuple[str, ...]


# Order is the order the catalog is exposed to the API consumer.
# Group by content shape: hero/title slides first, then text, structured
# data, comparisons, processes, and image-bearing layouts.
_CATALOG: tuple[LayoutEntry, ...] = (
    LayoutEntry(
        id="title-only",
        description="Hero / cover / closing slide. One headline plus optional subheadline.",
        kit_components=("TitleHero", "CoverSlide", "CinematicHero", "DuotoneHero"),
        aliases=(
            "title", "title-hero", "title-slide", "cover", "opening", "closing",
            "close", "thank-you", "thanks", "cta", "hero", "thank_you",
            "section", "section-break", "divider",
        ),
    ),
    LayoutEntry(
        id="two-column",
        description="Two-column layout for paired text+text or text+visual.",
        kit_components=("SplitContent", "FeatureGrid", "EditorialImage", "SplitOverlap"),
        aliases=(
            "split", "split-content", "text-with-image", "editorial-image",
            "image-left", "image-right", "two-col", "2-column",
        ),
    ),
    LayoutEntry(
        id="grid-3",
        description="3-6 equal cards (features, team, social proof, logos).",
        kit_components=("FeatureGrid", "BentoGrid", "GlassCard", "TeamGrid",
                        "ValuePropGrid", "TeamMemberStrip", "SocialProof", "LogoMarquee"),
        aliases=(
            "cards", "grid", "three-column", "3-column", "feature-grid", "featuregrid",
            "bento", "bento-grid", "team-grid", "teamgrid",
            "social-proof", "logo-marquee", "value-prop-grid",
        ),
    ),
    LayoutEntry(
        id="stat-hero",
        description="One-to-four big numbers with context labels.",
        kit_components=("StatHero", "FloatingStat", "MetricsDashboard"),
        aliases=(
            "stat", "stats", "stat-grid", "stathero", "metrics", "kpi",
            "metrics-dashboard", "metricsdashboard", "floating-stat", "floatingstat",
        ),
    ),
    LayoutEntry(
        id="chart-focus",
        description="Chart-led slide. Bar / line / pie / area / scatter.",
        kit_components=("ChartBlock",),
        aliases=("chart", "chartblock", "graph", "benchmark", "data-chart"),
    ),
    LayoutEntry(
        id="quote",
        description="Pull-quote / testimonial / customer voice.",
        kit_components=("QuoteBlock", "QuoteHighlight", "TestimonialCard"),
        aliases=(
            "quoteblock", "testimonial", "testimonial-card", "testimonialcard",
            "quote-highlight", "quotehighlight", "pullquote", "pull-quote",
        ),
    ),
    LayoutEntry(
        id="comparison",
        description="Side-by-side comparison: 2-3 columns of paired claims.",
        kit_components=("ComparisonBlock", "ProblemSolution", "BeforeAfter"),
        aliases=(
            "compare", "comparisonblock", "comparisonmatrix", "matrix",
            "versus", "vs", "before-after", "beforeafter",
            "problem-solution", "problemsolution",
        ),
    ),
    LayoutEntry(
        id="timeline",
        description="Sequential events: history, roadmap, funding rounds.",
        kit_components=("TimelineBlock", "Roadmap"),
        aliases=(
            "timelineblock", "roadmap", "milestones", "reel", "history", "journey",
        ),
    ),
    LayoutEntry(
        id="table",
        description="Tabular comparison of 3+ attributes across 3+ entities.",
        kit_components=("DataTable", "PricingTable"),
        aliases=(
            "data-table", "datatable", "pricing", "pricing-table", "pricingtable",
        ),
    ),
    LayoutEntry(
        id="diagram",
        description="System / architecture / network / flywheel diagram.",
        kit_components=("DiagramBlock",),
        aliases=(
            "diagramblock", "architecture", "architecture-map", "system-map",
            "network", "flywheel", "flow", "loop",
        ),
    ),
    LayoutEntry(
        id="process",
        description="Step-by-step process / workflow / how-it-works.",
        kit_components=("ProcessFlow",),
        aliases=(
            "process-flow", "processflow", "workflow", "steps", "how-it-works",
        ),
    ),
    LayoutEntry(
        id="image-full",
        description="Full-bleed background image with text overlay.",
        kit_components=("FullBleedImage", "AppMockup"),
        aliases=(
            "image", "full-bleed", "fullbleedimage", "cinematic", "cinematichero",
            "duotonehero", "appmockup", "app-mockup",
        ),
    ),
    LayoutEntry(
        id="bullet-points",
        description="Text-led slide with 3-6 bullets and optional body.",
        kit_components=("FeatureGrid",),  # bullets render via FeatureGrid in the kit
        aliases=("bullet", "bullets", "text", "list", "bulletpoints"),
    ),
)


# Build the alias map at import time. Every alias normalizes to a canonical id.
# An alias collision (same alias mapping to two different ids) is a real bug,
# so we raise at import time instead of silently dropping a mapping.
def _build_alias_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in _CATALOG:
        # The canonical id maps to itself for round-tripping.
        out[entry.id] = entry.id
        for alias in entry.aliases:
            normalized = alias.lower().replace("_", "-").strip()
            if not normalized:
                continue
            existing = out.get(normalized)
            if existing is not None and existing != entry.id:
                raise RuntimeError(
                    f"layout alias collision: '{alias}' maps to both "
                    f"'{existing}' and '{entry.id}' — fix one of them in canonical.py"
                )
            out[normalized] = entry.id
    return out


ALIAS_MAP: dict[str, str] = _build_alias_map()


def canonical_layout_ids() -> tuple[str, ...]:
    """Return the ordered tuple of canonical layout ids."""
    return tuple(entry.id for entry in _CATALOG)


def all_known_aliases() -> tuple[str, ...]:
    """Return every accepted alias (including canonical ids themselves)."""
    return tuple(sorted(ALIAS_MAP.keys()))


def normalize_layout(layout: str | None, *, fallback: str = "auto") -> str:
    """Normalize an arbitrary layout string to a canonical id.

    Returns ``fallback`` for empty input and the lower-cased, hyphenated
    string when the alias is not known — callers (``slide_compiler``,
    ``v4_editor``, the API endpoint) decide whether to treat unknown
    layouts as ``auto`` or to reject them.
    """
    if not layout:
        return fallback
    normalized = layout.strip().lower().replace("_", "-").replace(" ", "-")
    if not normalized:
        return fallback

    candidates: list[str] = [normalized]
    # Some legacy strings carry a `kit:variant` suffix (e.g.
    # `TitleHero:closing-ask`). Try the whole string, then each part.
    if ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        candidates.extend([prefix, suffix])

    for candidate in candidates:
        mapped = ALIAS_MAP.get(candidate)
        if mapped is not None:
            return mapped
        # Kit-component names are stored in PascalCase in the catalog
        # (``TitleHero``, ``ComparisonBlock``). The normalized form may be
        # ``titlehero`` (collapsed) or ``title-hero`` (hyphenated). Match
        # both without bloating the explicit alias list.
        for entry in _CATALOG:
            for kit in entry.kit_components:
                if candidate in (kit.lower(), _hyphenate_kit(kit)):
                    return entry.id
    return normalized


def _hyphenate_kit(kit: str) -> str:
    """``TitleHero`` → ``title-hero`` for alias lookup."""
    out: list[str] = []
    for i, ch in enumerate(kit):
        if i > 0 and ch.isupper():
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


def catalog_payload() -> dict[str, object]:
    """Build the JSON-serializable payload for ``GET /api/v4/layouts``.

    Wire shape (consumed by ``barise-editorial-main/src/lib/server4.ts``):
        {
            "version": "v4.1",
            "default": "auto",
            "layouts": [
                {
                    "id": "title-only",
                    "description": "...",
                    "kit_components": ["TitleHero", "CoverSlide", ...],
                    "aliases": ["title", "title-hero", ...]
                },
                ...
            ],
            "alias_map": {
                "title": "title-only",
                "cover": "title-only",
                ...
            }
        }
    """
    return {
        "version": "v4.1",
        "default": "auto",
        "layouts": [
            {
                "id": entry.id,
                "description": entry.description,
                "kit_components": list(entry.kit_components),
                "aliases": list(entry.aliases),
            }
            for entry in _CATALOG
        ],
        "alias_map": dict(ALIAS_MAP),
    }


__all__ = [
    "ALIAS_MAP",
    "LayoutEntry",
    "all_known_aliases",
    "canonical_layout_ids",
    "catalog_payload",
    "normalize_layout",
]
