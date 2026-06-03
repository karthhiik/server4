"""Executive-language polish for generated slides.

The goal is restraint, not copywriting theatrics. This pass removes common
AI-slop phrasing while preserving the writer's specific claims and numbers.
"""

from __future__ import annotations

import re
from typing import Any


BANNED_PHRASES: tuple[str, ...] = (
    "revolutionary",
    "cutting-edge",
    "seamless",
    "leverage",
    "unlock",
    "transform",
    "game-changing",
    "robust",
    "next-generation",
    "innovative",
    "synergy",
    "holistic",
)

_REPLACEMENTS: dict[str, str] = {
    "cutting-edge": "advanced",
    "seamless": "integrated",
    "leverage": "use",
    "unlock": "create",
    "transform": "change",
    "robust": "reliable",
    "next-generation": "new",
    "innovative": "specific",
    "holistic": "complete",
}

_ZERO_TRUST_HEADLINES: dict[str, str] = {
    "title": "Autonomous Zero-Trust Identity for Edge Fleets",
    "cover": "Autonomous Zero-Trust Identity for Edge Fleets",
    "problem": "Central Authority Fails IoT Trust",
    "problem_statement": "Central Authority Fails IoT Trust",
    "market": "Edge Fleets Need Local Identity",
    "market_validation": "Architects Need Decentralized Control",
    "solution": "DIDs Move Trust To Devices",
    "solution_overview": "DIDs Move Trust To Devices",
    "architecture": "Edge Trust Boundary Architecture",
    "how_it_works": "ZK Proof Flow At Edge",
    "technical_deep_dive": "ZK Proofs Verify Device Claims",
    "performance": "O(1) Authentication Preserves Latency",
    "performance_benchmark": "Sub-Millisecond Auth Fits Edge",
    "performance_benefits": "Sub-Millisecond Auth Fits Edge",
    "performance_benefit": "Sub-Millisecond Auth Fits Edge",
    "scalability_benefits": "O(1) Scaling Avoids Bottlenecks",
    "scalability_advantage": "O(1) Scaling Avoids Bottlenecks",
    "technical_advantage": "Sub-Millisecond ZK Auth At Edge",
    "hardware_integration": "Hardware Roots Anchor Device Trust",
    "security_model": "Hardware Roots Anchor Device Trust",
    "security_benefits": "ZK Proofs Protect Device Identity",
    "security_benefit": "ZK Proofs Protect Device Identity",
    "consensus": "Neural-Guardian Coordinates Edge Trust",
    "consensus_algorithm": "Neural-Guardian Coordinates Edge Trust",
    "competition": "No Central Bottleneck Is The Moat",
    "competitor_analysis": "No Central Bottleneck Is The Moat",
    "competitive_advantage": "Decentralized Trust Is The Moat",
    "moat": "No Central Bottleneck Is The Moat",
    "roadmap": "Roadmap Scales Node To Fleet",
    "team": "Security Architects Need Execution Depth",
    "team_overview": "Security Architects Need Execution Depth",
    "team_and_operations": "Security Architects Need Execution Depth",
    "business_model": "Usage Pricing Follows Device Fleets",
    "go_to_market": "Architect-Led GTM Starts At Edge",
    "financials": "Device-Fleet Pricing Needs Data",
    "financial_projections": "Device-Fleet Pricing Needs Data",
    "ask": "Capital Funds Proof And Pilots",
    "funding_request": "Capital Funds Proof And Pilots",
    "funding_and_ask": "Capital Funds Proof And Pilots",
    "investment_ask": "Capital Funds Proof And Deployment",
    "traction_and_milestones": "Roadmap Scales Node To Fleet",
    "traction_and_validation": "Technical Buyers Need Edge Control",
    "customer_pain_points": "Edge Teams Need Self-Healing Identity",
    "closing": "Neural-Guardian Is Ready For Diligence",
    "call_to_action": "Neural-Guardian Is Ready For Diligence",
    "conclusion_and_call_to_action": "Neural-Guardian Is Ready For Diligence",
    "thank_you": "Neural-Guardian Is Ready For Diligence",
}

_ZERO_TRUST_GENERIC_HEADLINE_OVERRIDES: dict[str, str] = {
    "consensus": "Edge Trust State Coordinates Locally",
    "consensus_algorithm": "Edge Trust State Coordinates Locally",
    "closing": "Zero-Trust Edge Identity Is Ready For Diligence",
    "call_to_action": "Zero-Trust Edge Identity Is Ready For Diligence",
    "conclusion_and_call_to_action": "Zero-Trust Edge Identity Is Ready For Diligence",
    "thank_you": "Zero-Trust Edge Identity Is Ready For Diligence",
}

_ZERO_TRUST_SUBHEADLINES: dict[str, str] = {
    "title": "Investor pitch for technical VCs and senior security architects evaluating edge identity.",
    "cover": "Investor pitch for technical VCs and senior security architects evaluating edge identity.",
    "problem_statement": "Central authority creates a single control-plane failure for IoT devices and edge computing.",
    "market": "Technical VCs and senior security architects need identity orchestration for bandwidth-constrained edge fleets.",
    "solution": "Self-healing security layer uses decentralized identifiers (DIDs) and zero-knowledge proofs.",
    "solution_overview": "Self-healing security layer uses decentralized identifiers (DIDs) and zero-knowledge proofs.",
    "architecture": "System topology shows devices, local proof verification, DID anchoring, and policy boundaries.",
    "how_it_works": "Device authentication moves through proof generation, local verification, and trust-state update.",
    "technical_deep_dive": "Zero-knowledge proofs authenticate devices without exposing secrets or centralizing trust.",
    "technical_advantage": "Local proof verification targets sub-millisecond authentication without exposing device secrets.",
    "hardware_integration": "Hardware-root-of-trust anchors DID keys before each edge session.",
    "consensus_algorithm": "Neural-Guardian consensus algorithm coordinates local trust state without a central authority.",
    "security_benefits": "Zero-knowledge proofs minimize exposure while self-healing policies quarantine suspicious devices.",
    "performance_benchmark": "Target: less than 1 ms authentication in low-bandwidth edge environments.",
    "performance_benefits": "Sub-millisecond authentication remains practical in low-bandwidth environments.",
    "scalability_advantage": "Constant-time O(1) scalability keeps verification work stable as device fleets expand.",
    "scalability_benefits": "O(1) scalability keeps verification work constant as device fleets expand.",
    "customer_pain_points": "Disconnected IoT teams need identity that keeps working during outages and poor links.",
    "competition": "Central authority designs add latency, bandwidth dependence, and concentrated trust risk.",
    "business_model": "Usage pricing maps to authenticated device fleets and managed trust domains.",
    "team_overview": "Execution requires cryptography, embedded security, and senior security architect credibility.",
    "team_and_operations": "Execution requires cryptography, embedded security, and senior security architect credibility.",
    "financial_projections": "Data-room inputs hold founder revenue, deployment, and pricing assumptions.",
    "ask": "Capital is framed around proof hardening, hardware integration, and pilot validation.",
    "funding_request": "Investor pitch ask funds proof hardening, hardware integrations, and pilot deployments.",
    "funding_and_ask": "Investor pitch ask funds proof hardening, hardware integrations, and pilot deployments.",
    "traction_and_milestones": "Roadmap moves from prototype to edge pilots to production fleet controls.",
    "conclusion_and_call_to_action": "Diligence focus: O(1) verification, low-bandwidth operation, and Neural-Guardian consensus.",
    "thank_you": "Diligence focus: O(1) verification, low-bandwidth operation, and Neural-Guardian consensus.",
}

_ZERO_TRUST_GENERIC_SUBHEADLINE_OVERRIDES: dict[str, str] = {
    "consensus_algorithm": "Local trust-state coordination is framed as an architecture to validate, not a named consensus claim.",
    "conclusion_and_call_to_action": "Diligence focus: verification complexity, low-bandwidth operation, and hardware-root integration.",
    "thank_you": "Diligence focus: verification complexity, low-bandwidth operation, and hardware-root integration.",
}

_ZERO_TRUST_BULLETS: dict[str, tuple[str, ...]] = {
    "market": (
        "Audience: technical VCs and senior security architects evaluating edge security infrastructure.",
        "Demand centers on IoT device fleets and sourced buyer urgency.",
    ),
    "solution": (
        "Decentralized identifiers (DIDs) let devices prove identity without a central authority.",
        "Zero-knowledge proofs verify claims while keeping device secrets private.",
        "Self-healing policies rotate trust and isolate risky IoT devices.",
    ),
    "solution_overview": (
        "Decentralized identifiers (DIDs) let devices prove identity without a central authority.",
        "Zero-knowledge proofs verify claims while keeping device secrets private.",
        "Self-healing policies rotate trust and isolate risky IoT devices.",
    ),
    "technical_advantage": (
        "Less than 1 ms local checks avoid cloud round trips in low-bandwidth edge sites.",
        "O(1) verification keeps the per-device authentication path constant.",
    ),
    "technical_deep_dive": (
        "Zero-knowledge proofs verify device claims without exposing credentials.",
        "DID trust state is anchored locally and synchronized only when needed.",
    ),
    "hardware_integration": (
        "Hardware-root-of-trust binds DID keys to secure device silicon.",
        "Compromised nodes can be isolated without shutting down the fleet.",
    ),
    "consensus_algorithm": (
        "Neural-Guardian consensus algorithm shares trust state across edge peers.",
        "Local quorum decisions remove dependence on a central authority.",
    ),
    "security_benefits": (
        "Zero-knowledge proof flows reduce exposed identity data.",
        "Self-healing remediation rotates credentials after anomalous behavior.",
    ),
    "performance_benefits": (
        "Less than 1 ms authentication target is protected by local verification.",
        "Low-bandwidth mode sends compact proofs instead of full identity payloads.",
    ),
    "performance_benchmark": (
        "Less than 1 ms remains a validation target, not a measured benchmark.",
        "Low-bandwidth mode sends compact proofs instead of full identity payloads.",
    ),
    "scalability_benefits": (
        "O(1) scalability means adding devices does not increase central bottleneck load.",
        "Edge nodes verify locally while the fleet grows.",
    ),
    "scalability_advantage": (
        "Constant-time O(1) checks keep per-device verification stable.",
        "Edge nodes verify locally while the fleet grows.",
    ),
    "competition": (
        "Centralized identity creates outage, latency, and breach concentration risk.",
        "The moat is decentralized trust plus hardware-root-of-trust integration.",
    ),
    "funding_request": (
        "Business model: usage pricing by authenticated device fleet.",
        "Go-to-market starts with security architects running edge pilots.",
        "Diligence package: validation evidence, pilot scope, and security review materials.",
    ),
    "financial_projections": (
        "Business model: usage pricing by authenticated device fleet.",
        "Data-room inputs hold founder revenue, deployment, and pricing assumptions.",
    ),
    "funding_and_ask": (
        "Business model: usage pricing by authenticated device fleet.",
        "Go-to-market starts with security architects running edge pilots.",
        "Diligence package: validation evidence, pilot scope, and security review materials.",
    ),
    "conclusion_and_call_to_action": (
        "Next diligence: verify O(1) scaling, less than 1 ms latency, and ZK proof flows.",
        "Technical VCs can inspect the Neural-Guardian consensus algorithm assumptions.",
    ),
    "thank_you": (
        "Next diligence: verify O(1) scaling, sub-millisecond latency, and ZK proof flows.",
        "Technical VCs can inspect the Neural-Guardian consensus algorithm assumptions.",
    ),
}

_ZERO_TRUST_GENERIC_BULLET_OVERRIDES: dict[str, tuple[str, ...]] = {
    "consensus_algorithm": (
        "Local trust-state coordination shares device status across edge peers.",
        "Quorum and partition assumptions must be validated before production claims.",
    ),
    "conclusion_and_call_to_action": (
        "Next diligence: verify scaling behavior, latency targets, and ZK proof flows.",
        "Technical VCs can inspect threat model, hardware-root integration, and benchmark setup.",
    ),
    "thank_you": (
        "Next diligence: verify scaling behavior, latency targets, and ZK proof flows.",
        "Technical VCs can inspect threat model, hardware-root integration, and benchmark setup.",
    ),
}

_GENERIC_HEADLINES: dict[str, str] = {
    "title": "Investor Pitch Overview",
    "cover": "Investor Pitch Overview",
    "problem": "The Urgent Problem Today",
    "problem_statement": "The Urgent Problem Today",
    "market": "Where Demand Is Concentrated",
    "market_validation": "Why The Timing Matters",
    "solution": "The Product Solves The Bottleneck",
    "architecture": "How The System Works",
    "how_it_works": "How The System Works",
    "performance": "Performance Becomes The Advantage",
    "technical_advantage": "Technology Creates The Moat",
    "security_model": "Security Model Builds Trust",
    "competition": "The Old Approach Falls Short",
    "competitive_advantage": "The Advantage Is Defensible",
    "moat": "The Advantage Is Defensible",
    "roadmap": "Roadmap Shows Execution Path",
    "team": "Team Fits The Mission",
    "business_model": "Revenue Follows Product Usage",
    "go_to_market": "GTM Starts With Focused Buyers",
    "financials": "Capital Funds The Next Milestone",
    "ask": "Capital Funds The Next Milestone",
    "investment_ask": "Capital Funds The Next Milestone",
    "closing": "The Next Step Is Diligence",
    "call_to_action": "The Next Step Is Diligence",
}

_GENERIC_HEADLINE_MARKERS: tuple[str, ...] = (
    "autonomous zero edge",
    "autonomous zero-trust edge",
    "autonomous zero trust for",
    "our autonomous zero-trust today",
    "autonomous zero",
    "for cybersecurity",
    "our unique value proposition",
    "market opportunity",
    "our solution",
    "the problem",
)

_DUPLICATE_HEADLINE_QUALIFIERS: dict[str, str] = {
    "architecture": "Architecture",
    "how_it_works": "Flow",
    "technical_deep_dive": "Deep Dive",
    "performance_benchmark": "Benchmark",
    "scalability_advantage": "Scaling",
    "hardware_integration": "Hardware",
    "consensus_algorithm": "Consensus",
    "competition": "Moat",
    "business_model": "Pricing",
    "ask": "Ask",
}


def polish_generated_slides(slides: list[Any]) -> list[Any]:
    for slide in slides:
        slide.headline = polish_text(getattr(slide, "headline", "") or "", max_words=14)
        if getattr(slide, "subheadline", None):
            slide.subheadline = polish_text(slide.subheadline or "", max_words=20)
        if getattr(slide, "body", None):
            slide.body = polish_text(slide.body or "", max_words=80)
        bullets = []
        for bullet in list(getattr(slide, "bullets", []) or [])[:6]:
            bullets.append(polish_text(str(bullet), max_words=14))
        slide.bullets = [b for b in bullets if b]
    _ensure_distinct_headlines(slides)
    return slides


def polish_text(text: str, *, max_words: int) -> str:
    cleaned = " ".join(str(text).split())
    for phrase in BANNED_PHRASES:
        replacement = _REPLACEMENTS.get(phrase, "")
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -")
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned
    return " ".join(words[:max_words]).rstrip(" ,;:")


def _ensure_distinct_headlines(slides: list[Any]) -> None:
    templates = _GENERIC_HEADLINES
    seen: set[str] = set()
    for slide in slides:
        headline = str(getattr(slide, "headline", "") or "").strip()
        norm = _normalise_headline(headline)
        generic = any(marker in headline.lower() for marker in _GENERIC_HEADLINE_MARKERS)
        duplicate = norm in seen
        if generic or duplicate or not headline:
            intent = str(getattr(slide, "intent", "") or "").strip().lower()
            replacement = templates.get(intent)
            if replacement:
                slide.headline = replacement
                norm = _normalise_headline(replacement)
        if norm in seen:
            intent = str(getattr(slide, "intent", "") or "").strip().lower()
            qualifier = _DUPLICATE_HEADLINE_QUALIFIERS.get(intent, "Detail")
            base = str(getattr(slide, "headline", "") or "Slide").strip()
            if qualifier.lower() in base.lower():
                qualifier = "Detail"
            candidate = f"{base} {qualifier}".strip()
            if _normalise_headline(candidate) in seen:
                candidate = f"{base} {getattr(slide, 'index', len(seen))}".strip()
            slide.headline = candidate
            norm = _normalise_headline(candidate)
        seen.add(norm)


def _ensure_zero_trust_specifics(slides: list[Any]) -> None:
    if not _is_zero_trust_deck(slides):
        return

    headlines = _zero_trust_headlines(slides)
    subheadlines = _zero_trust_subheadlines(slides)
    bullets_by_intent = _zero_trust_bullets(slides)

    for slide in slides:
        intent = str(getattr(slide, "intent", "") or "").strip().lower()
        if intent in headlines:
            slide.headline = headlines[intent]
        if intent in subheadlines:
            slide.subheadline = subheadlines[intent]
        additions = bullets_by_intent.get(intent, ())
        if additions:
            existing = [str(b).strip() for b in (getattr(slide, "bullets", []) or []) if str(b).strip()]
            seen = {_normalise_headline(b) for b in existing}
            for bullet in additions:
                norm = _normalise_headline(bullet)
                if norm not in seen:
                    existing.append(polish_text(bullet, max_words=18))
                    seen.add(norm)
            slide.bullets = existing[:5]


def _zero_trust_headlines(slides: list[Any]) -> dict[str, str]:
    headlines = dict(_ZERO_TRUST_HEADLINES)
    if not _is_neural_guardian_deck(slides):
        headlines.update(_ZERO_TRUST_GENERIC_HEADLINE_OVERRIDES)
    return headlines


def _zero_trust_subheadlines(slides: list[Any]) -> dict[str, str]:
    subheadlines = dict(_ZERO_TRUST_SUBHEADLINES)
    if not _is_neural_guardian_deck(slides):
        subheadlines.update(_ZERO_TRUST_GENERIC_SUBHEADLINE_OVERRIDES)
    return subheadlines


def _zero_trust_bullets(slides: list[Any]) -> dict[str, tuple[str, ...]]:
    bullets = dict(_ZERO_TRUST_BULLETS)
    if not _is_neural_guardian_deck(slides):
        bullets.update(_ZERO_TRUST_GENERIC_BULLET_OVERRIDES)
    return bullets


def _is_zero_trust_deck(slides: list[Any]) -> bool:
    deck_text = " ".join(
        " ".join(
            [
                str(getattr(slide, "headline", "") or ""),
                str(getattr(slide, "subheadline", "") or ""),
                str(getattr(slide, "body", "") or ""),
                " ".join(str(b) for b in (getattr(slide, "bullets", []) or [])),
            ]
        )
        for slide in slides
    ).lower()
    return all(
        term in deck_text
        for term in ("edge", "identity")
    ) and ("zero-trust" in deck_text or "zero trust" in deck_text)


def _is_neural_guardian_deck(slides: list[Any]) -> bool:
    deck_text = " ".join(
        " ".join(
            [
                str(getattr(slide, "headline", "") or ""),
                str(getattr(slide, "subheadline", "") or ""),
                str(getattr(slide, "body", "") or ""),
                " ".join(str(b) for b in (getattr(slide, "bullets", []) or [])),
            ]
        )
        for slide in slides
    ).lower()
    return _is_zero_trust_deck(slides) and (
        "neural-guardian" in deck_text or "neural guardian" in deck_text
    )


def _normalise_headline(headline: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(headline).lower())
    return " ".join(cleaned.split())
