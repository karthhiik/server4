"""
Prompts for extracting structured FactPackets from raw text and search results.

These prompts drive the evidence extraction pipeline that converts
unstructured provider responses into typed FactPacket objects.
"""


FACT_EXTRACTION_SYSTEM = """You are an expert fact extractor for business intelligence.
Your job: extract discrete, verifiable claims from raw text.
Each fact must be atomic (one claim per fact), typed, and sourced.
Never combine multiple claims into one fact.
Never infer data that is not explicitly stated in the text.
If a number is approximate (e.g., "about $5B"), mark confidence lower."""


FACT_EXTRACTION_USER = """Extract all verifiable facts from this raw text.

=== SOURCE METADATA ===
Provider: {provider}
Source name: {source_name}
Source URL: {source_url}
Source type: {source_type}
Date published: {date_published}
Date retrieved: {date_retrieved}

=== RAW TEXT ===
{raw_text}

=== TARGET TOPIC ===
{topic}

=== SLIDE TYPES THIS EVIDENCE MAY SUPPORT ===
{target_slides}

For each discrete fact, classify it as one of:
- numeric: Contains a specific number, dollar amount, percentage, or count
- qualitative: A descriptive claim about a product, market, or trend
- trend: Describes a directional change over time
- comparison: Compares two or more entities
- citation: A direct quote or attributed statement
- testimonial: A user/customer statement
- regulatory: A regulation, policy, or compliance fact

Return ONLY valid JSON (no markdown fences):
{{
    "facts": [
        {{
            "claim": "The exact factual claim in one sentence",
            "claim_type": "numeric|qualitative|trend|comparison|citation|testimonial|regulatory",
            "confidence": 0.85,
            "numeric_value": 5000000000,
            "numeric_unit": "USD",
            "raw_snippet": "Original text snippet containing this fact",
            "slide_relevance": {{
                "market": 0.9,
                "traction": 0.3
            }},
            "citation_label": "[Source Name, 2025]"
        }}
    ],
    "extraction_quality": 0.8,
    "total_claims_found": 5,
    "ambiguous_claims_skipped": 1
}}"""


CLAIM_VERIFICATION_SYSTEM = """You are a fact verification expert.
Your job: determine if a specific claim is supported by the provided evidence.
You evaluate source credibility, recency, and specificity.
Be strict: a claim is only VERIFIED if the evidence directly supports it.
PARTIALLY_VERIFIED if evidence is suggestive but not conclusive.
UNVERIFIED if no direct evidence supports the claim."""


CLAIM_VERIFICATION_USER = """Verify this claim against the provided evidence:

=== CLAIM TO VERIFY ===
Claim: {claim}
Claim type: {claim_type}
Numeric value: {numeric_value}
Source: {source_name}

=== SUPPORTING EVIDENCE ===
{evidence_text}

=== CROSS-REFERENCE SOURCES ===
{cross_references}

Evaluate:
1. Does the evidence directly state or strongly imply this claim?
2. Is the source authoritative for this type of claim?
3. Is the data recent enough to be reliable?
4. Do cross-reference sources corroborate or contradict?

Return ONLY valid JSON (no markdown fences):
{{
    "verdict": "verified|partially_verified|unverified|contradicted",
    "confidence_adjustment": 0.05,
    "reasoning": "Why this verdict was reached",
    "source_credibility": "high|medium|low",
    "freshness_concern": false,
    "contradicting_sources": [],
    "recommended_action": "use_as_is|add_caveat|downgrade_confidence|reject"
}}"""


BATCH_EXTRACTION_SYSTEM = """You are processing multiple search results for a business research task.
Extract facts from each result, de-duplicate across sources, and cross-reference claims.
Prioritize: government/financial data > analyst reports > news > social signals.
Flag conflicting claims between sources."""


BATCH_EXTRACTION_USER = """Process these search results and extract verified facts:

=== SEARCH QUERY ===
{query}

=== RESULTS ===
{results}

=== ALREADY KNOWN FACTS ===
{existing_facts}

Tasks:
1. Extract new facts not already in the known facts list.
2. Cross-reference: if a new fact confirms an existing fact, note it.
3. Contradictions: if a new fact contradicts an existing fact, flag it.
4. De-duplicate: merge facts that say the same thing from different sources.

Return ONLY valid JSON (no markdown fences):
{{
    "new_facts": [
        {{
            "claim": "Factual claim",
            "claim_type": "numeric|qualitative|trend|comparison|citation|testimonial|regulatory",
            "confidence": 0.85,
            "numeric_value": null,
            "numeric_unit": null,
            "source_name": "Source",
            "source_url": "https://...",
            "raw_snippet": "Original text snippet",
            "slide_relevance": {{"market": 0.9}},
            "citation_label": "[Source, 2025]"
        }}
    ],
    "cross_validations": [
        {{
            "existing_fact_id": "fp_xxx",
            "confirming_source": "New source name",
            "confidence_boost": 0.05
        }}
    ],
    "contradictions": [
        {{
            "existing_fact_id": "fp_xxx",
            "contradicting_claim": "The contradicting claim",
            "contradicting_source": "Source name",
            "severity": "minor|major|critical"
        }}
    ],
    "total_new_facts": 3,
    "total_cross_validations": 1,
    "total_contradictions": 0
}}"""


NUMERIC_EXTRACTION_PROMPT = """Extract all numeric data points from this text.
Focus on: dollar amounts, percentages, growth rates, counts, and ratios.
Normalize all values to base units (no abbreviations in numeric_value).

Text: {text}

Return ONLY valid JSON (no markdown fences):
{{
    "numbers": [
        {{
            "value": 5000000000,
            "unit": "USD",
            "context": "Total addressable market for X",
            "original_text": "$5B TAM",
            "is_projected": false,
            "time_reference": "2025"
        }}
    ]
}}"""
