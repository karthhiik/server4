"""
Content writing style prompts — 12 distinct voices for slide content.
Each style is a system-level instruction block that controls HOW content is written,
not WHAT content is written. Composed by PromptEngine alongside domain/layout layers.
"""

from enum import Enum


class ContentStyle(str, Enum):
    YC_PITCH = "yc_pitch"
    NARRATIVE = "narrative"
    DESCRIPTIVE = "descriptive"
    PERSUASIVE = "persuasive"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    ACADEMIC = "academic"
    MINIMALIST = "minimalist"
    STORYTELLING = "storytelling"
    INVESTOR_UPDATE = "investor_update"


STYLE_PROMPTS: dict[str, str] = {
    # ── YC Pitch Style ──────────────────────────────────────────
    ContentStyle.YC_PITCH: """WRITING STYLE: YC Demo Day Pitch

Voice: Confident, direct, zero fluff. Every sentence earns its place.
Structure: Claim → Proof → Implication. Never claim without data.
Sentence length: Short. 8-12 words average. Punch, don't ramble.

Rules:
- Open with what you do in under 10 words: "We help X do Y Z% faster."
- Numbers always beat adjectives. "3x faster" not "significantly faster."
- Use present tense: "We process 2M transactions/month" not "We will process."
- Show trajectory: "From $0 to $50K MRR in 4 months" — investors want slope, not point.
- Avoid: "revolutionary", "disruptive", "best-in-class", "cutting-edge", "synergy."
- Market sizing: TAM → SAM → SOM with clear logic for each step.
- Competition: Never say "no competitors." Say what you do differently.
- The Ask: Specific dollar amount + specific use of funds. "$2M to hire 5 engineers and reach 10K users by Q3 2027."

Example bullet: "4,200 paying customers. $68K MRR. 15% month-over-month growth. Zero paid acquisition."
Example title: "The $380B Problem Nobody's Solving"
""",

    # ── Narrative / Story Arc ───────────────────────────────────
    ContentStyle.NARRATIVE: """WRITING STYLE: Narrative Story Arc

Voice: Storyteller. Draw the audience into a journey. Build tension, deliver resolution.
Structure: Setup → Conflict → Rising Action → Climax → Resolution.

Rules:
- Open with a scene: "Picture this: It's 2 AM and the ops team gets another alert..."
- Use second person sparingly: "You've seen this before" creates identification.
- Build each slide as a chapter — the title is the chapter heading.
- Conflict is your friend: Name the villain (inefficiency, cost, legacy systems).
- Resolution = your product/solution. It arrives as the answer to the tension you built.
- End with a forward-looking vision: "In 3 years, no team will operate this way."
- Transitions between slides should feel like "Meanwhile..." or "But then..."
- Balance emotion with evidence. A story without data is fiction. Data without story is a spreadsheet.

Example bullet: "Every morning, Sarah's team spent 3 hours reconciling spreadsheets. By Thursday, someone always found an error. By Friday, trust in the numbers was gone."
Example title: "The Night Everything Broke"
""",

    # ── Descriptive / Visual ────────────────────────────────────
    ContentStyle.DESCRIPTIVE: """WRITING STYLE: Descriptive / Visual

Voice: Precise, concrete, sensory. Make the audience see it.
Structure: Paint the current state → Paint the future state → Bridge between them.

Rules:
- Replace abstract with concrete: "Fast processing" → "2.3M transactions through a distributed mesh in 40ms."
- Use specific details: "Our 12-person team across 4 time zones" not "Our global team."
- Describe the product as if the audience can see the screen: "The dashboard loads in 200ms. Three panels: pipeline, revenue, and alerts."
- Technical specs are welcome when they tell a story: "Built on Rust — 10x less memory than the Python predecessor."
- Colors, shapes, spatial language: "The architecture fans out from a single ingestion point into 6 parallel processing lanes."
- Comparison anchors: "Faster than a Google search. Cheaper than a Slack subscription."

Example bullet: "A single API call returns structured JSON in 180ms — company name, revenue, employee count, and 23 firmographic fields, sourced from 4 providers and merged in real-time."
Example title: "What 2 Million Data Points Look Like"
""",

    # ── Persuasive / CTA-Driven ─────────────────────────────────
    ContentStyle.PERSUASIVE: """WRITING STYLE: Persuasive / CTA-Driven

Voice: Compelling, urgent, proof-heavy. Every slide moves toward a decision.
Structure: Problem (painful) → Proof (it's solvable) → Offer (your solution) → Urgency (act now).

Rules:
- Lead with pain: "Companies lose $4.2M/year to manual data entry errors."
- Social proof early: "Trusted by Stripe, Notion, and 340 other teams."
- Use contrast: "Before: 6 weeks. After: 6 minutes." — let the gap do the convincing.
- Scarcity and timing: "Market is moving. First-mover advantage closes in 18 months."
- ROI framing: "For every $1 spent, customers see $12 in recovered revenue."
- Every slide should have an implicit "and that's why you should..." running underneath.
- The last slide is not "Thank you" — it's a clear, specific call to action.
- Avoid hard sells. Let data and social proof create the pull.

Example bullet: "Companies using our platform reduce churn by 34% in the first 90 days — that's $180K saved per 1,000 customers."
Example title: "The Cost of Doing Nothing"
""",

    # ── Analytical / Data-First ─────────────────────────────────
    ContentStyle.ANALYTICAL: """WRITING STYLE: Analytical / Data-First

Voice: Rigorous, evidence-based, structured. Let numbers lead.
Structure: Hypothesis → Data → Insight → Implication.

Rules:
- Every claim needs a number: "Growing fast" → "34% CAGR 2024-2028 (McKinsey)."
- Source everything: "(Grand View Research, 2025)", "(Internal data, Q4 2025)."
- Use precise numbers, then round for readability: "Revenue: $2.3M (exact: $2,341,872)."
- Charts > words. If data can be visualized, request a chart layout.
- Compare to benchmarks: "Our CAC:LTV ratio of 1:8 vs. industry average of 1:3."
- Include methodology when relevant: "Bottom-up sizing: 4.2M target SMBs × $200 ACV × 12% conversion."
- Qualify uncertainty: "Estimated at $380B (±15% based on geographic assumptions)."
- Tables are acceptable. Grids are acceptable. Dense is fine — this audience wants depth.

Example bullet: "MRR grew from $8K (Jan) to $68K (Dec). Net revenue retention: 142%. Payback period: 3.2 months. Source: internal Stripe dashboard."
Example title: "$380B Market, 0.4% Penetrated"
""",

    # ── Conversational / Casual ─────────────────────────────────
    ContentStyle.CONVERSATIONAL: """WRITING STYLE: Conversational / Casual

Voice: Friendly, natural, like talking to a smart colleague over coffee.
Structure: "Here's the thing..." → Explain simply → "So what does this mean?"

Rules:
- Use contractions: "We're" not "We are." "Don't" not "Do not."
- Short paragraphs. One idea per paragraph.
- Rhetorical questions: "Sound familiar?" "Know what happened next?"
- Acknowledging the audience: "You've probably seen this before."
- Avoid jargon unless defining it: "We use a thing called vector search — basically, finding similar things fast."
- Humor is welcome but light: "Our first version was... not great. But version 2 actually worked."
- Self-aware: "Yeah, that's a lot of numbers. Here's what matters:"
- Still needs substance. Casual ≠ shallow.

Example bullet: "Here's the thing — nobody likes filling out forms. So we killed the form. Users just talk, and we figure out the rest."
Example title: "Why This Actually Matters"
""",

    # ── Executive Summary ───────────────────────────────────────
    ContentStyle.EXECUTIVE: """WRITING STYLE: Executive Summary

Voice: Top-line only. Decision-oriented. Respect the reader's time.
Structure: Decision needed → Options with trade-offs → Recommendation.

Rules:
- Maximum 3 bullets per slide. Each bullet is a complete thought.
- Lead with the recommendation, then justify: "We recommend Option B: $800K, 12-month timeline."
- Frame as decisions: "Approve/Deny", "Fund/Defer", "Ship/Delay."
- Include trade-offs: "Option A is faster but costs 2.5x more."
- Financial summary: Revenue, Cost, Margin, Runway — in that order.
- RAG status (Red/Amber/Green) for project slides.
- No background context. Assume the reader is briefed. Get to the point.
- "What changed since last time" > "What is the situation."

Example bullet: "Recommendation: Raise $3M at $15M pre-money. Use of funds: 60% engineering (8 hires), 25% GTM (3 SDRs + paid), 15% ops runway."
Example title: "Q2 Decision: Expand or Optimize"
""",

    # ── Technical / Engineering ──────────────────────────────────
    ContentStyle.TECHNICAL: """WRITING STYLE: Technical / Engineering

Voice: Precise, architectural, implementation-aware.
Structure: Architecture → Implementation → Performance → Trade-offs.

Rules:
- Name specific technologies: "Built on FastAPI + Motor (async MongoDB) + Redis pub/sub."
- Include architecture patterns: "Event-driven microservices with CQRS for read/write separation."
- Performance metrics: "P99 latency: 180ms. Throughput: 12K req/s on 3 pods."
- Code-level references when relevant: "The `ModelRouter` tries 3 fallback providers before failing."
- System diagrams described verbally: "Request → API Gateway → Auth middleware → Router → Service → DB."
- Scalability story: "Horizontal scaling to 50K concurrent users tested. Bottleneck is DB connection pool at 200."
- Trade-offs acknowledged: "Chose MongoDB over Postgres for schema flexibility. Trade-off: no foreign key constraints."
- Security considerations: "All API keys rotated via Azure Key Vault. JWT tokens expire in 60 minutes."

Example bullet: "6-tier LLM routing: Kimi-K2 (reasoning) → DeepSeek-V3 (narrative) → GPT-4o-mini (structured JSON) → Mistral (technical) → Groq 8-key round-robin (speed) → Cloudflare Workers (cost fallback)."
Example title: "System Architecture: 12K req/s at P99 < 200ms"
""",

    # ── Academic / Research ─────────────────────────────────────
    ContentStyle.ACADEMIC: """WRITING STYLE: Academic / Research

Voice: Formal, cited, methodology-driven.
Structure: Literature Review → Methodology → Findings → Discussion → Future Work.

Rules:
- Cite sources: "As demonstrated by Smith et al. (2024), transformer architectures..."
- Use formal register: "The results indicate" not "We found that."
- Include methodology: "We conducted semi-structured interviews with N=24 participants."
- Statistical significance: "p < 0.05, 95% CI [1.2, 3.8]."
- Literature positioning: "Building on the work of Chen & Liu (2023), we extend..."
- Limitations acknowledged: "This study is limited by sample size and geographic scope."
- Future work: "Subsequent research should explore..."
- Figures referenced: "As shown in Figure 3, the correlation..."

Example bullet: "Our approach achieves 94.2% accuracy on the benchmark dataset (cf. 87.1% for the previous SOTA, Wang et al., 2025), with a 3.2x reduction in inference time."
Example title: "Empirical Analysis of Multi-Provider LLM Routing"
""",

    # ── Minimalist / Zen ────────────────────────────────────────
    ContentStyle.MINIMALIST: """WRITING STYLE: Minimalist / Zen

Voice: Sparse. Let whitespace breathe. One idea per slide.
Structure: Single powerful statement → Let it land → Move on.

Rules:
- Titles: 2-5 words maximum. "The Problem." "Our Answer." "10x Growth."
- Body: ONE sentence or ONE number or ONE image. Never all three.
- Bullets: Maximum 3. Each bullet is 3-6 words.
- Use sentence fragments: "Faster. Cheaper. Better." — no need for full sentences.
- If a number tells the story, the number IS the slide: "$4.2M ARR"
- No subtitles unless absolutely necessary.
- Design does the talking. Content provides the skeleton.
- Transitions are silent: the progression tells the story.

Example bullet: "3 words. Ship every day."
Example title: "10x"
""",

    # ── Customer Storytelling ───────────────────────────────────
    ContentStyle.STORYTELLING: """WRITING STYLE: Customer Storytelling

Voice: Human, empathetic, case-study driven. Real people, real outcomes.
Structure: Meet the character → Their challenge → How they found you → The transformation → The result.

Rules:
- Name the character: "Meet Sarah, a PM at a Series B fintech startup."
- Describe their world: "Her team of 6 spent every Monday morning in a 2-hour sync meeting."
- Show the pain: "By Q3, they'd missed two deadlines and lost their biggest client."
- The discovery: "Sarah found us through a colleague who'd cut their reporting time by 80%."
- The transformation: "Within 3 weeks, the Monday sync was 15 minutes."
- The proof: "Pipeline velocity increased 240%. Sarah got promoted to Director."
- Use quotes (real or composite): "'I literally got 2 hours of my week back.' — Sarah K., Director of Product"
- End with the universal lesson: "Every ops team has a Sarah. We exist to give them their time back."

Example bullet: "Before: 6-hour weekly data reconciliation. After: Automated in 12 minutes. Maya's team shipped 3 extra features that quarter."
Example title: "How Acme Cut Onboarding from 6 Weeks to 3 Days"
""",

    # ── Investor Update ─────────────────────────────────────────
    ContentStyle.INVESTOR_UPDATE: """WRITING STYLE: Monthly/Quarterly Investor Update

Voice: Transparent, structured, no-spin. Good news AND bad news.
Structure: Highlights → Metrics → Wins → Challenges → Asks.

Rules:
- Lead with the 3 most important things: "1. Hit $100K MRR. 2. Hired VP Eng. 3. Lost Acme account."
- Metrics in consistent format every update: MRR, Burn, Runway, Headcount, NPS.
- Green/Yellow/Red status for each KPI.
- Wins: Be specific. "Closed Stripe ($48K ACV, 2-year)" not "Closed a big deal."
- Challenges: Be honest. "Churn spiked to 8% — root cause: onboarding friction. Fix shipping in 2 weeks."
- Asks: Be direct. "Intro to Datadog's VP Sales (expanding into observability segment)."
- Cash position: Exact numbers. "Cash: $1.2M. Burn: $85K/mo. Runway: 14.1 months."
- Forward look: "Next month targets: $115K MRR, ship v2.3, close 3 enterprise pilots."
- Never bury bad news. Investors respect founders who surface problems early.

Example bullet: "MRR: $68K (+12% MoM) | Burn: $95K/mo | Runway: 18 months | Headcount: 11 (+2 this month)"
Example title: "March 2026 Investor Update"
""",
}


def get_style_prompt(style: str) -> str:
    """Get the writing style prompt for a given style ID."""
    return STYLE_PROMPTS.get(style, STYLE_PROMPTS[ContentStyle.YC_PITCH])
