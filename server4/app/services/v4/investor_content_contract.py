"""Deterministic investor-grade content contract for V4 slide output.

This guard is intentionally non-generative. It never creates metrics,
customers, team credentials, market sizes, or citations. It cleans visible
copy, records claim provenance, and turns missing investor-critical facts into
explicit user-input requirements instead of fake deck content.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

from app.services.v4.investor_proof_guard import (
    extract_topic_label,
    normalize_structured_blocks,
)


_TEMPLATE_LEAKAGE_INDUSTRIES = (
    "FinTech",
    "Financial Services",
    "InsurTech",
    "HealthTech",
    "Healthcare",
    "EdTech",
    "SaaS",
    "E-commerce",
    "Real Estate",
)

_PLACEHOLDER_RE = re.compile(
    r"\b("
    r"needs?\s+(?:evidence|inputs?|founder\s+data|pricing\s+inputs?|team\s+data)|"
    r"missing\s+(?:data|evidence|context|inputs?)|"
    r"placeholder|tbd|to\s+be\s+defined|coming\s+soon|"
    r"insert\s+(?:data|metric|logo|content)|"
    r"data\s+(?:needed|required)|"
    r"ask\s+founder|founder\s+input"
    r")\b",
    re.IGNORECASE,
)

# Malformed-template-substitution detector. Catches the cases where the
# LLM emits a literal templating placeholder or an empty interpolation
# (e.g. "Seed for -Month Runway" when runway_months wasn't substituted,
# "Raising $X million", "Close Invoices In {time}", "For [amount] / mo").
# These slip past _PLACEHOLDER_RE because they look like prose.
_MALFORMED_TEMPLATE_RE = re.compile(
    r"(?:"
    # leftover Python-style braces or square brackets around a token
    r"\{[a-z_][\w\.]*\}|"
    r"\[[a-z_][\w\.]*\]|"
    # leftover "$X" / "$Y" placeholder patterns in a headline
    r"\$\s*[XYZNK]\b|"
    # "for -Month Runway", "for - month", "for - Year"
    r"\bfor\s+-+\s*(?:month|months|year|years|day|days|week|weeks)\b|"
    # "in -" / "by -" patterns ("Close in -seconds", "Ship by -2024")
    r"\b(?:in|by|over|across)\s+-+\s*[a-z]+\b|"
    # double-hyphen anywhere ("Seed for -- Runway")
    r"\s--\s|"
    # negative-quantity-without-context ("Raise -$ ", "Hire - engineers")
    r"-\s*\$\s|"
    # known token names that the writer sometimes echoes verbatim
    r"\b(?:company_name|topic_label|round_type|runway_months|raise_amount|use_of_funds_breakdown|amount)\b"
    r")",
    re.IGNORECASE,
)

_META_COMMENTARY_RE = re.compile(
    r"\b("
    r"should\s+(?:map|come|include|show|explain|be|use)|"
    r"must\s+(?:be\s+supplied|come\s+from|include)|"
    r"define\s+the\s+|"
    r"keep\s+this\s+slide|"
    r"roadmap\s+claims?\s+should|"
    r"pricing\s+should|"
    r"buyer,\s*deployment|"
    r"claims?\s+remain\s+qualitative|"
    # Internal pipeline directives that previously leaked into visible
    # copy (subhead/body/bullets) and speaker_notes. None of these are
    # investor-readable phrases — they were planner / regen instructions
    # that the writer echoed back without filtering. Examples seen in
    # production: "USER REVISION REQUEST: Keep these original …",
    # "Cover problem statement for this pitch", "Technical scope covers
    # installer-led and Tier-2.", "Keep these original user/project
    # terms represented in visible slide copy".
    r"user\s+revision\s+request\b|"
    r"keep\s+these\s+original\s+(?:user|project)\s+terms|"
    r"represented\s+in\s+visible\s+slide\s+copy|"
    r"\bcover\s+\w[\w\s]*?\bfor\s+this\s+pitch\b|"
    r"^\s*technical\s+scope\s+covers\b|"
    r"\.\s*technical\s+scope\s+covers\b"
    r")",
    re.IGNORECASE,
)

_UNSUPPORTED_METRIC_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\$?\d+(?:\.\d+)?\s?(?:%|x|m|bn|b|k|ms|sec|seconds|users|customers|arr|mrr)?)",
    re.IGNORECASE,
)

_VISUAL_INTENT_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("architecture", "system", "workflow", "how_it_works", "process", "integration"), "diagram"),
    (("competition", "competitive", "moat", "differentiation"), "comparison"),
    (("pricing", "business_model", "revenue", "financial", "unit_economics"), "table"),
    (("market", "buyer", "gtm", "go_to_market"), "table"),
    (("traction", "proof", "milestone", "pilot"), "table"),
    (("team", "founder"), "team"),
    (("product", "demo", "solution"), "diagram"),
)


def apply_investor_content_contract(
    slides: list[Any],
    *,
    request_text: str,
    purpose: str | None = None,
    mode: str = "standard",
    structured_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply visible-copy and proof guardrails to a generated deck."""
    if not slides:
        return {"changed": 0, "requires_user_input": 0, "assumptions": 0}

    topic_label = extract_topic_label(request_text)
    context = structured_context if isinstance(structured_context, Mapping) else {}
    evidence_text = _evidence_text(request_text, context)
    stage = _extract_stage(request_text, purpose, context)
    is_ai_deck = bool(re.search(r"\b(ai|agentic|llm|machine learning|ml)\b", evidence_text, re.I))

    changed = 0
    needs_input = 0
    assumptions = 0

    for slide in slides:
        before = _slide_signature(slide)
        normalize_structured_blocks(slide)
        _ensure_raw(slide)
        slide.raw["investor_narrative_contract"] = {
            "stage": stage,
            "mode": mode,
            "ai_startup_bar": is_ai_deck,
            "rules": _stage_rules(stage, is_ai_deck),
        }

        _clean_slide_visible_copy(slide, topic_label, evidence_text)
        _apply_missing_data_policy(slide, topic_label, evidence_text, context)
        _ensure_visual_intelligence(slide, topic_label, request_text, context)

        claim_report = _classify_claims(slide, evidence_text)
        slide.raw["claim_contract"] = claim_report
        assumptions += sum(1 for claim in claim_report["claims"] if claim["status"] == "assumption")
        if getattr(slide, "requires_user_input", False):
            needs_input += 1
        if _slide_signature(slide) != before:
            changed += 1

    return {"changed": changed, "requires_user_input": needs_input, "assumptions": assumptions}


def _ensure_raw(slide: Any) -> None:
    if not isinstance(getattr(slide, "raw", None), dict):
        slide.raw = {}


# Verb / action tokens that disambiguate "this is a sentence with a
# claim" from "this is a noun-phrase label". The list intentionally
# stays small — common verbs that appear in pitch deck prose plus
# auxiliary forms. Real bullets ("Direct marketing to homeowners with
# new roofs and high electric bills") trip the regex via "to"+verb or
# the past participle ("validated", "delivered", "earned"); label
# bullets ("Limited Access To Resources") have only "to" with no verb
# afterward and get dropped.
_BULLET_VERB_RE = re.compile(
    r"\b("
    r"is|are|was|were|be|been|being|"
    r"has|have|had|"
    r"do|does|did|"
    r"can|could|would|should|will|may|might|"
    r"\w+(?:s|es|ed|ing)"  # generic verbal endings — "delivers", "matches", "delivered", "scaling"
    r")\b",
    re.IGNORECASE,
)

# Words that look verbal but are usually nouns/adjectives in pitch
# decks. Subtract these from the verb match so "Limited Access To
# Resources" (where "Limited" + "Resources" both end in -ed/-s) doesn't
# falsely pass. Conservative — small list to avoid false negatives.
_BULLET_VERB_BLOCKLIST = frozenset({
    "limited", "trusted", "validated", "qualified", "founded",
    "is", "are",  # too weak to count alone
})


def _bullet_meets_quality_floor(text: str) -> bool:
    """Return True if a bullet has the minimum signal a pitch deck
    bullet should carry: ≥5 words AND at least one real action verb
    (not just an adjective ending in -ed). This filters out the
    "Limited Access To Resources" / "Difficulty Finding Customers"
    failure mode while keeping legitimate short bullets like
    "Sales team scaled from 4 to 12 in 90 days"."""
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if len(words) < 5:
        return False
    has_action_verb = False
    for w in words:
        token = re.sub(r"[^a-zA-Z]", "", w).lower()
        if not token or token in _BULLET_VERB_BLOCKLIST:
            continue
        if _BULLET_VERB_RE.fullmatch(token):
            has_action_verb = True
            break
    return has_action_verb


def _clean_slide_visible_copy(slide: Any, topic_label: str, evidence_text: str) -> None:
    for field in ("headline", "subheadline", "body", "speaker_notes"):
        cleaned = _clean_visible_text(getattr(slide, field, "") or "", evidence_text)
        # Detect malformed-template-substitution glitches (e.g. "Seed for
        # -Month Runway" when the LLM forgot to substitute runway_months).
        # Replace headline / subheadline outright so we never ship a
        # leaked placeholder; for body / speaker_notes, drop the field.
        if cleaned and _MALFORMED_TEMPLATE_RE.search(cleaned):
            if field == "headline":
                cleaned = _fallback_headline(slide, topic_label)
            else:
                cleaned = ""
        if field == "headline" and not cleaned:
            cleaned = _fallback_headline(slide, topic_label)
        setattr(slide, field, cleaned)

    bullets = []
    seen: set[str] = set()
    for bullet in getattr(slide, "bullets", []) or []:
        cleaned = _clean_visible_text(bullet, evidence_text)
        if not cleaned:
            continue
        # Drop bullets that contain malformed template placeholders.
        if _MALFORMED_TEMPLATE_RE.search(cleaned):
            continue
        # Drop telegraphic noun-phrase bullets. Real pitch decks use
        # full sentences with at least one piece of evidence per
        # bullet. We require ≥5 words AND at least one verb-like token
        # so labels like "Limited Access To Resources" (5 words but
        # no verb — the failure mode founders flagged in user testing)
        # also get dropped. The regex matches common verb endings; it
        # is intentionally conservative to avoid wiping good copy.
        if not _bullet_meets_quality_floor(cleaned):
            continue
        sig = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
        if sig in seen:
            continue
        seen.add(sig)
        bullets.append(cleaned)
        if len(bullets) >= 4:
            break
    slide.bullets = bullets

    # Body / bullets dedup. The writer occasionally puts the first
    # bullet's text in `body` (or vice versa), producing visible
    # duplication on the rendered slide. When body == bullet[0] (or one
    # is a substring of the other) we drop body and keep the bullets.
    body = (getattr(slide, "body", None) or "").strip()
    if body and bullets:
        first_bullet = bullets[0]
        body_norm = re.sub(r"\W+", " ", body.lower()).strip()
        bullet_norm = re.sub(r"\W+", " ", first_bullet.lower()).strip()
        if body_norm and bullet_norm and (body_norm == bullet_norm or body_norm in bullet_norm or bullet_norm in body_norm):
            slide.body = ""

    # Pipe-joined body / multi-claim body. The writer sometimes packs
    # 2-3 claims into a single body string separated by " | " (artifact
    # of training data that paired bullet lists with prose). Render
    # treats body as a single paragraph so the user sees an awkward
    # "A | B | C" line. Split on pipe; if any claim is truncated
    # ("delivered hundreds of …"), drop body entirely so the renderer
    # falls back to bullets. Otherwise keep the longest complete clause.
    body = (getattr(slide, "body", None) or "").strip()
    if body and "|" in body:
        parts = [p.strip(" -") for p in body.split("|") if p.strip(" -")]
        # Filter out fragments that appear truncated mid-thought.
        complete = [p for p in parts if not re.search(r"\b(of|the|a|an|to|with|for|by|in|on|at)\.?\s*$", p, re.IGNORECASE)]
        if not complete:
            slide.body = ""
        elif len(parts) > 1:
            # Multiple claims in one body line is a UX bug regardless of
            # truncation. Promote the body fragments to bullets when
            # there isn't already a bullet list, otherwise drop body.
            if not bullets:
                slide.bullets = complete[:4]
                slide.body = ""
            else:
                slide.body = max(complete, key=lambda s: len(s.split()))

    # StatHero / stat_blocks safety. The writer sometimes packs multiple
    # values into a single stat label using "|" separators (e.g.
    # "Founders combine decades in solar | Co-founder previously scaled
    # GTM"). The renderer truncates that to a single line so the user
    # sees an awkward fragment. Split on pipe and drop multi-claim
    # labels so a single-stat block displays a single coherent claim.
    stat_blocks = getattr(slide, "stat_blocks", None) or []
    if stat_blocks:
        cleaned_stats: list[Any] = []
        for stat in stat_blocks:
            label = ""
            if isinstance(stat, dict):
                label = str(stat.get("label") or "").strip()
            else:
                label = str(getattr(stat, "label", "") or "").strip()
            if "|" in label:
                # Take the first cleanly-terminated clause. If the first
                # clause looks like a sentence fragment (no verb, ends
                # mid-word) prefer the second clause.
                parts = [p.strip(" -") for p in label.split("|") if p.strip(" -")]
                if parts:
                    chosen = max(parts, key=lambda s: len(s.split()))
                    if isinstance(stat, dict):
                        stat = {**stat, "label": chosen}
                    else:
                        try:
                            setattr(stat, "label", chosen)
                        except Exception:  # noqa: BLE001
                            pass
            cleaned_stats.append(stat)
        slide.stat_blocks = cleaned_stats


def _clean_visible_text(value: Any, evidence_text: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    text = _remove_template_leakage(text, evidence_text)
    text = _strip_internal_directives(text)
    if _PLACEHOLDER_RE.search(text) or _META_COMMENTARY_RE.search(text):
        return ""
    return text.strip(" -")


# Surgical strip for sentences containing internal pipeline directives
# (e.g. "Foo. Technical scope covers X.", "Bar. USER REVISION REQUEST:
# do this."). When the *entire* remaining text would still match a
# directive, _clean_visible_text falls through to the existing
# wipe-the-field path. When only part of the field is contaminated we
# drop the bad sentence and keep the rest. This is what lets a real
# subhead like "We connect installers to homeowners" survive when the
# regen engine appended "Technical scope covers …" to it.
_INTERNAL_DIRECTIVE_SENTENCE_RE = re.compile(
    r"(?:^|[.!?]\s+)"
    r"[^.!?]*?(?:"
    r"USER\s+REVISION\s+REQUEST"
    r"|Keep\s+these\s+original\s+(?:user|project)\s+terms"
    r"|represented\s+in\s+visible\s+slide\s+copy"
    r"|Technical\s+scope\s+covers"
    r"|Cover\s+\w[\w\s]*?\s+for\s+this\s+pitch"
    r")"
    r"[^.!?]*[.!?]?",
    re.IGNORECASE,
)


def _strip_internal_directives(text: str) -> str:
    if not text:
        return text
    cleaned = _INTERNAL_DIRECTIVE_SENTENCE_RE.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    return cleaned


def _remove_template_leakage(text: str, evidence_text: str) -> str:
    cleaned = text
    for industry in _TEMPLATE_LEAKAGE_INDUSTRIES:
        if industry.lower() in evidence_text:
            continue
        cleaned = re.sub(
            rf"\s+(?:for|in)\s+{re.escape(industry)}\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
    return re.sub(r"\s+", " ", cleaned).strip()


def _fallback_headline(slide: Any, topic_label: str) -> str:
    intent = (getattr(slide, "intent", "") or "").lower()
    if "title" in intent or getattr(slide, "index", 1) == 0:
        return topic_label
    if "problem" in intent:
        return "The Urgent Problem"
    if "solution" in intent or "product" in intent:
        return "A Credible Path To Value"
    if any(k in intent for k in ("architecture", "workflow", "process", "how_it_works")):
        return "How The System Works"
    if "competition" in intent:
        return "Competitive Positioning"
    if "market" in intent:
        return "Buyer Urgency And Market Logic"
    if any(k in intent for k in ("pricing", "business_model", "financial", "revenue")):
        return "Revenue Model Diligence"
    if "team" in intent:
        return "Team Diligence Checklist"
    if any(k in intent for k in ("traction", "milestone", "proof")):
        return "Progress Proof Checklist"
    if any(k in intent for k in ("ask", "funding", "capital")):
        return "Capital Plan And Milestones"
    return topic_label


def _apply_missing_data_policy(
    slide: Any,
    topic_label: str,
    evidence_text: str,
    context: Mapping[str, Any],
) -> None:
    intent = (getattr(slide, "intent", "") or "").lower()
    missing_kind = _missing_kind_for_intent(intent, evidence_text, context)
    if not missing_kind:
        return
    slide.requires_user_input = True
    slide.user_input_kind = missing_kind
    slide.user_input_reason = _missing_reason(missing_kind)
    slide.layout = "table"
    slide.table = _question_table(missing_kind, topic_label)
    slide.bullets = []
    slide.stat_blocks = []
    slide.chart = None
    if _PLACEHOLDER_RE.search(getattr(slide, "headline", "") or ""):
        slide.headline = _fallback_headline(slide, topic_label)


def _missing_kind_for_intent(intent: str, evidence_text: str, context: Mapping[str, Any]) -> str | None:
    if "team" in intent and not _has_context_block(context, "team") and not _has_any(evidence_text, ("founder", "ceo", "cto", "team", "ex-")):
        return "team"
    if any(k in intent for k in ("traction", "proof", "milestone")) and not _has_context_block(context, "traction") and not _has_any(evidence_text, ("pilot", "customer", "user", "arr", "mrr", "revenue", "partnership", "deployment")):
        return "traction"
    if any(k in intent for k in ("financial", "revenue", "business_model", "pricing")) and not _has_context_block(context, "financials") and not _has_any(evidence_text, ("arr", "mrr", "revenue", "gross margin", "pricing", "burn", "runway", "cac", "ltv")):
        return "financials"
    if any(k in intent for k in ("ask", "funding", "capital")) and not _has_context_block(context, "fundraising") and not _has_any(evidence_text, ("raising", "raise", "use of funds", "runway", "seed", "series a", "$")):
        return "fundraising"
    return None


def _missing_reason(kind: str) -> str:
    return {
        "team": "Team slides require founder names, roles, and credibility signals.",
        "traction": "Traction slides require founder-provided usage, customer, pilot, or revenue evidence.",
        "financials": "Financial slides require founder-provided revenue, margin, burn, runway, or pricing inputs.",
        "fundraising": "Ask slides require amount, round, use of funds, and milestone plan.",
    }.get(kind, "This slide requires user-provided proof before export.")


def _question_table(kind: str, topic_label: str) -> dict[str, Any]:
    tables = {
        "team": [
            ["Who leads product, GTM, and technical execution?", "Names, roles, and relevant proof"],
            ["Why is this team credible for this market?", "Founder-market fit and prior domain wins"],
            ["Which advisor or operator fills current gaps?", "Credible coverage for regulated or technical risk"],
        ],
        "traction": [
            ["What proof exists today?", "Customers, pilots, signed LOIs, deployments, or usage"],
            ["What metric is improving?", "Retention, activation, revenue, cycle time, or model performance"],
            ["What is the next validation milestone?", "A dated proof point investors can diligence"],
        ],
        "financials": [
            ["What revenue exists today?", "ARR, MRR, pipeline, or pre-revenue status"],
            ["What unit drives pricing?", "Seat, usage, device, asset, transaction, or policy value"],
            ["What does margin depend on?", "COGS, model cost, service load, and support burden"],
        ],
        "fundraising": [
            ["How much is being raised?", "Round size and instrument"],
            ["What milestones does capital unlock?", "Product, proof, GTM, hiring, or regulatory progress"],
            ["How long is the runway?", "Months of execution and measurable next financing signal"],
        ],
    }
    return {
        "headers": ["Founder Question", "Investor-Ready Answer"],
        "rows": tables.get(kind, [[f"What proof anchors {topic_label}?", "Specific user-provided evidence"]]),
    }


def _ensure_visual_intelligence(
    slide: Any,
    topic_label: str,
    request_text: str,
    context: Mapping[str, Any],
) -> None:
    if _has_structured_block(slide):
        return
    intent = (getattr(slide, "intent", "") or "").lower()
    visual = _visual_kind(intent)
    if visual == "diagram":
        slide.diagram = _diagram_from_slide(slide, topic_label, request_text)
        slide.layout = "diagram"
        slide.bullets = []
    elif visual == "comparison":
        slide.comparison = _comparison_from_context(context)
        slide.layout = "comparison"
        slide.bullets = []
    elif visual == "table":
        slide.table = _proof_table_for_intent(intent, topic_label)
        slide.layout = "table"
        slide.bullets = []
    elif visual == "team":
        team = _team_members_from_context(context)
        if team:
            slide.team_members = team
            slide.layout = "team-grid"


def _visual_kind(intent: str) -> str | None:
    for markers, kind in _VISUAL_INTENT_RULES:
        if any(marker in intent for marker in markers):
            return kind
    return None


def _has_structured_block(slide: Any) -> bool:
    return any(
        bool(getattr(slide, field, None))
        for field in ("stat_blocks", "chart", "table", "timeline", "comparison", "diagram", "quote", "team_members")
    )


def _diagram_from_slide(slide: Any, topic_label: str, request_text: str) -> dict[str, Any]:
    points = _meaningful_points(getattr(slide, "bullets", []) or [])
    if not points:
        points = _meaningful_points(re.split(r"[.;]", getattr(slide, "body", "") or ""))
    if not points:
        points = _meaningful_points(re.split(r"[,;]", request_text))[:3]
    labels = ["Input"] + (points[:3] or [topic_label, "Decision logic", "Proof loop"]) + ["Outcome"]
    nodes = [{"id": f"n{i}", "label": label[:54]} for i, label in enumerate(labels, start=1)]
    edges = [{"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "label": "then"} for i in range(len(nodes) - 1)]
    return {"layout": "flow", "nodes": nodes, "edges": edges, "caption": f"{topic_label} operating flow"}


def _comparison_from_context(context: Mapping[str, Any]) -> dict[str, Any]:
    competitors = context.get("competitors") if isinstance(context, Mapping) else None
    columns: list[dict[str, Any]] = []
    if isinstance(competitors, list):
        for competitor in competitors[:2]:
            if not isinstance(competitor, Mapping):
                continue
            name = str(competitor.get("name") or "Alternative").strip()
            weaknesses = _meaningful_points(competitor.get("weaknesses") or [])
            diff = str(competitor.get("differentiator") or "").strip()
            items = weaknesses[:3] or ([diff] if diff else ["Positioning requires founder proof"])
            columns.append({"title": name, "items": items, "highlight": False})
    columns.append({
        "title": "Our Wedge",
        "items": ["Owned insight", "Operational proof path", "Repeatable differentiation"],
        "highlight": True,
    })
    if len(columns) < 2:
        columns.insert(0, {
            "title": "Current Alternatives",
            "items": ["Manual workflow", "Services-heavy delivery", "Weak data loop"],
            "highlight": False,
        })
    return {"columns": columns[:3]}


def _proof_table_for_intent(intent: str, topic_label: str) -> dict[str, Any]:
    if "market" in intent:
        rows = [
            ["Buyer", "Named ICP and budget owner", "Founder/research source"],
            ["Urgency", "Workflow pain tied to time, cost, or risk", "Founder/source"],
            ["Scale", "TAM/SAM/SOM only when sourced", "External citation"],
        ]
    elif any(k in intent for k in ("pricing", "business_model", "financial", "revenue")):
        rows = [
            ["Pricing unit", "Seat, usage, asset, transaction, or policy value", "Founder answer"],
            ["Revenue quality", "ARR/MRR, pipeline, retention, or pre-revenue status", "Founder answer"],
            ["Margin path", "COGS, model cost, service load, and support burden", "Founder answer"],
        ]
    elif any(k in intent for k in ("traction", "proof", "milestone")):
        rows = [
            ["Usage proof", "Users, deployments, pilots, contracts, or LOIs", "Founder answer"],
            ["Learning loop", "Data or feedback that compounds", "Founder answer"],
            ["Next milestone", "Dated proof event", "Founder answer"],
        ]
    else:
        rows = [
            [topic_label, "Evidence tied to this brief", "Founder/source"],
            ["Investor claim", "Specific operating proof", "Founder/source"],
        ]
    return {"headers": ["Claim Area", "Evidence Standard", "Allowed Source"], "rows": rows}


def _classify_claims(slide: Any, evidence_text: str) -> dict[str, Any]:
    claims = []
    has_citation = bool(getattr(slide, "citations", None))
    for text in _visible_claims(slide):
        if not text:
            continue
        status = "sourced" if has_citation or "http://" in text or "https://" in text else "assumption"
        compact = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if status != "sourced" and compact and len(compact) > 14 and compact[:80] in evidence_text:
            status = "founder_provided"
        if _UNSUPPORTED_METRIC_RE.search(text) and status == "assumption":
            status = "requires_source"
        claims.append({"text": text[:220], "status": status})
    return {
        "claims": claims,
        "all_claims_allowed": all(c["status"] != "requires_source" for c in claims),
        "policy": "sourced_or_founder_provided_or_marked_assumption",
    }


def _visible_claims(slide: Any) -> Iterable[str]:
    yield getattr(slide, "headline", "") or ""
    yield getattr(slide, "subheadline", "") or ""
    yield getattr(slide, "body", "") or ""
    for bullet in getattr(slide, "bullets", []) or []:
        yield str(bullet)
    for block in getattr(slide, "stat_blocks", []) or []:
        if isinstance(block, Mapping):
            yield f"{block.get('value', '')} {block.get('label', '')}".strip()


def _extract_stage(request_text: str, purpose: str | None, context: Mapping[str, Any]) -> str:
    haystack = f"{request_text} {purpose or ''} {json.dumps(context, default=str)}".lower()
    if "series a" in haystack or "series_a" in haystack:
        return "series_a"
    if "pre-seed" in haystack or "pre seed" in haystack or "pre_seed" in haystack:
        return "pre_seed"
    if "seed" in haystack:
        return "seed"
    return "general"


def _stage_rules(stage: str, is_ai_deck: bool) -> list[str]:
    rules = {
        "pre_seed": ["insight", "founder-market fit", "demo", "early proof"],
        "seed": ["usage", "ICP", "retention", "pilots", "pricing"],
        "series_a": ["revenue", "growth", "margins", "pipeline", "repeatable GTM"],
        "general": ["clear problem", "credible solution", "market logic", "team", "proof"],
    }.get(stage, [])
    if is_ai_deck:
        rules += ["proprietary data", "production deployments", "revenue momentum", "gross-margin trajectory", "compounding loops"]
    return rules


def _evidence_text(request_text: str, context: Mapping[str, Any]) -> str:
    return f"{request_text or ''} {json.dumps(context, default=str, ensure_ascii=False)}".lower()


def _has_context_block(context: Mapping[str, Any], key: str) -> bool:
    value = context.get(key)
    if value in (None, "", [], {}):
        return False
    if isinstance(value, Mapping):
        return any(v not in (None, "", [], {}) for v in value.values())
    return True


def _has_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker.lower() in text for marker in markers)


def _meaningful_points(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, Iterable):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_visible_text(item, "")
        if not text:
            continue
        text = re.sub(r"^\s*[-*0-9.)]+\s*", "", text).strip()
        if len(text) < 3:
            continue
        sig = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if sig in seen:
            continue
        seen.add(sig)
        out.append(text)
    return out


def _team_members_from_context(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    team = context.get("team")
    if not isinstance(team, list):
        return []
    members: list[dict[str, Any]] = []
    for member in team:
        if not isinstance(member, Mapping):
            continue
        name = str(member.get("name") or "").strip()
        if not name:
            continue
        members.append({
            "name": name,
            "role": str(member.get("role") or "").strip(),
            "bio": str(member.get("bio") or "").strip(),
            "photo_url": str(member.get("photo_url") or "").strip(),
            "linkedin_url": str(member.get("linkedin_url") or "").strip(),
            "x_url": str(member.get("x_url") or "").strip(),
        })
    return members


def _slide_signature(slide: Any) -> str:
    payload = {
        "headline": getattr(slide, "headline", None),
        "subheadline": getattr(slide, "subheadline", None),
        "body": getattr(slide, "body", None),
        "bullets": getattr(slide, "bullets", None),
        "layout": getattr(slide, "layout", None),
        "table": getattr(slide, "table", None),
        "comparison": getattr(slide, "comparison", None),
        "diagram": getattr(slide, "diagram", None),
        "requires_user_input": getattr(slide, "requires_user_input", None),
    }
    return json.dumps(payload, sort_keys=True, default=str)


# ────────────────────────────────────────────────────────────────────
# Public sanitizer — apply at DTO boundary so already-persisted decks
# (generated before the leak fix shipped) display clean text without
# requiring a regen. Mirrors the cleaning that `_clean_slide_visible_copy`
# does on a fresh GeneratedSlide instance.
# ────────────────────────────────────────────────────────────────────


def sanitize_persisted_slide_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """In-place sanitize a Mongo slide document for outbound rendering.

    Stripping the same internal-directive leaks (Cover X for this pitch,
    USER REVISION REQUEST, Technical scope covers …) at the read path
    means existing decks generated under the old contract surface clean
    copy to the share viewer / studio / PDF screenshot pipeline without
    a database migration.

    Mutates and returns the same dict for caller convenience.
    """
    if not isinstance(doc, dict):
        return doc

    for field in ("headline", "subheadline", "body", "speaker_notes"):
        original = doc.get(field)
        if not isinstance(original, str) or not original.strip():
            continue
        cleaned = _strip_internal_directives(original)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Only overwrite when we actually changed something — otherwise
        # leave the original to preserve formatting of well-written copy.
        if cleaned != original.strip():
            doc[field] = cleaned

    # Drop subhead / body that are noun-phrase labels (no verb) — these
    # are the "Limited Access To Resources" / "Access To Resources And
    # Customers" / "Increasing Environmental Awareness" failure mode
    # the founder flagged. Headline is allowed to be a label-style
    # phrase because it acts as a deck title; body/subhead must read
    # as a sentence with a verb.
    for field in ("subheadline", "body"):
        text = doc.get(field)
        if not isinstance(text, str) or not text.strip():
            continue
        # Allow longer fields that contain at least one period — those
        # are multi-sentence. Single-clause noun phrases under ~10 words
        # without a verb get dropped.
        if "." not in text and not _bullet_meets_quality_floor(text):
            doc[field] = ""

    bullets = doc.get("bullets")
    if isinstance(bullets, list):
        cleaned_bullets: list[str] = []
        seen: set[str] = set()
        for raw in bullets:
            text = re.sub(r"\s+", " ", str(raw or "")).strip()
            if not text:
                continue
            text = _strip_internal_directives(text)
            text = text.strip(" -")
            if not text:
                continue
            if _META_COMMENTARY_RE.search(text):
                continue
            # Same quality floor as fresh-write path — see
            # `_bullet_meets_quality_floor`.
            if not _bullet_meets_quality_floor(text):
                continue
            sig = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
            if sig in seen:
                continue
            seen.add(sig)
            cleaned_bullets.append(text)
        doc["bullets"] = cleaned_bullets

    # Drop body when it duplicates bullet[0].
    body = doc.get("body")
    bullets_now = doc.get("bullets") or []
    if isinstance(body, str) and body and bullets_now:
        body_norm = re.sub(r"\W+", " ", body.lower()).strip()
        first_bullet_norm = re.sub(r"\W+", " ", str(bullets_now[0]).lower()).strip()
        if body_norm and first_bullet_norm and (
            body_norm == first_bullet_norm
            or body_norm in first_bullet_norm
            or first_bullet_norm in body_norm
        ):
            doc["body"] = ""

    # Pipe-joined body cleanup. See _clean_slide_visible_copy for the
    # full reasoning. Already-persisted decks may have bodies like
    # "Generates three bids | Pre-screens installers | Delivered …"
    # — split into bullets when no bullet list exists, otherwise keep
    # the longest complete clause.
    body = doc.get("body")
    if isinstance(body, str) and body and "|" in body:
        parts = [p.strip(" -") for p in body.split("|") if p.strip(" -")]
        complete = [p for p in parts if not re.search(r"\b(of|the|a|an|to|with|for|by|in|on|at)\.?\s*$", p, re.IGNORECASE)]
        if not complete:
            doc["body"] = ""
        elif len(parts) > 1:
            if not doc.get("bullets"):
                doc["bullets"] = complete[:4]
                doc["body"] = ""
            else:
                doc["body"] = max(complete, key=lambda s: len(s.split()))

    # Stat-block label cleanup. "Founders | Co-founder previously …" →
    # take the longer clause so the rendered label is one coherent claim.
    stat_blocks = doc.get("stat_blocks")
    if isinstance(stat_blocks, list):
        for stat in stat_blocks:
            if not isinstance(stat, dict):
                continue
            label = str(stat.get("label") or "")
            if "|" in label:
                parts = [p.strip(" -") for p in label.split("|") if p.strip(" -")]
                if parts:
                    stat["label"] = max(parts, key=lambda s: len(s.split()))

    return doc


__all__ = [
    "apply_investor_content_contract",
    "sanitize_persisted_slide_doc",
]
