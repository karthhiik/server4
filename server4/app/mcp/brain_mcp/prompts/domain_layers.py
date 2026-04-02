"""
Domain expertise layers — deep knowledge about pitch decks, investor psychology,
data presentation, and common mistakes. Composed by PromptEngine.
"""

# ── Pitch Deck Structural Rules ─────────────────────────────
PITCH_DECK_RULES = """PITCH DECK EXPERTISE:

Structural Rules:
- Rule of 10/20/30: ~10 slides, ~20 minutes, 30pt font minimum.
- Every slide answers exactly ONE question. If it answers two, split it.
- First 3 slides decide if the rest gets read. Nail them.
  Slide 1: What do you do? (crystal clear, <10 words)
  Slide 2: Why does this matter? (market pull, not tech push)
  Slide 3: Proof it's working (traction, trajectory, or validation)
- Traction slides MUST show trajectory (graph going up-right), not point-in-time KPIs alone.
- Market slides MUST use TAM → SAM → SOM funnel with clear methodology for each.
- Competition slides MUST NOT say "no competitors." Position on a 2x2 matrix or feature comparison.
- The Ask slide: exact dollar amount, exact use-of-funds breakdown, exact timeline.

Narrative Arc for Pitch Decks:
1. HOOK: One sentence that makes them lean forward.
2. PROBLEM: Why does this hurt? Who feels the pain? How much does it cost?
3. SOLUTION: What do you do about it? (product, not vision)
4. WHY NOW: What changed that makes this possible/necessary today?
5. TRACTION: Prove people want this. Revenue, users, growth rate, retention.
6. BUSINESS MODEL: How do you make money? Unit economics.
7. MARKET: How big can this get? TAM/SAM/SOM with logic.
8. TEAM: Why are YOU the ones to build this? Relevant experience, not bios.
9. THE ASK: What do you need? What will you do with it? What milestones will it unlock?

Investor-Hostile Patterns (avoid):
- Projecting $100M ARR with no bottoms-up logic.
- "If we get just 1% of the market..." — this is a red flag.
- Team slide listing 8 advisors and 2 founders.
- Market slide citing total addressable market without serviceable.
- "We have no competition" — means you haven't looked or the market doesn't exist.
"""

# ── YC Specific Principles ──────────────────────────────────
YC_PRINCIPLES = """YC PITCH PRINCIPLES:

Core YC Philosophy:
- "Make something people want." Prove demand before vision.
- Talk to users. Build product. Grow revenue. Everything else is noise.
- Pitch the trajectory, not the product. VCs invest in slopes, not points.
- Founders > idea. Show why you specifically will win this market.
- The best pitch decks tell the story of an inevitability.

YC Demo Day Format (2 minutes, 8-10 slides):
1. Company name + one-liner (5 seconds)
2. The problem (20 seconds) — make it visceral, not theoretical
3. The solution (20 seconds) — show, don't tell. Screenshot or demo.
4. Traction (30 seconds) — THE most important slide. Graph going up and to the right.
5. Business model (15 seconds) — how you make money, unit economics.
6. Market size (10 seconds) — big enough to matter.
7. Team (10 seconds) — relevant credentials only, not life stories.
8. The ask (10 seconds) — specific amount, specific milestones.

YC Content Rules:
- No buzzwords. "AI-powered" is not a feature. What does it DO?
- Specific > General. "We save ops teams 6 hours/week" > "We improve efficiency."
- Revenue is the strongest signal. If you have it, lead with it.
- If pre-revenue, show engagement: DAU, retention curve, waitlist size.
- Founder-market fit: 1 sentence on why YOU. "I spent 8 years in healthcare ops and built this for teams like my own."
- No slides about your tech stack. Investors don't care about your architecture.
- No slides about your advisory board (unless an advisor is a customer).
"""

# ── Investor Psychology ─────────────────────────────────────
INVESTOR_PSYCHOLOGY = """INVESTOR PSYCHOLOGY:

How Investors Read Decks:
- VCs review 1,000+ decks per year. Average time on first pass: 3 minutes 44 seconds.
- They decide in the FIRST 3 SLIDES whether to keep reading.
- They look for: team credibility, market size, traction, defensibility.
- They pattern-match against winners they've seen before.
- Red flags cause instant rejection. Green flags earn a meeting.

What Creates Urgency:
- Market timing: "This regulation goes into effect in 2027. Companies need to comply."
- Competitive dynamics: "Two well-funded competitors entered — the window is now."
- Traction inflection: "We're growing 25% month-over-month. Need fuel to keep the slope."

What Builds Credibility:
- Specific numbers with sources beat vague claims every time.
- Admitting what you DON'T know: "We're testing two go-to-market motions."
- Customer logos and names (with permission) beat "100+ customers."
- Showing you've talked to users: "In 40 customer interviews, 92% said..."

What Kills Deals:
- Unrealistic projections with no assumptions shown.
- Cannot articulate why NOW (timing is everything in VC).
- No clear path from current state to next milestone.
- Founder cannot explain unit economics.
- Deck is 30+ slides (lack of editing = lack of judgment).
"""

# ── Data Presentation Rules ─────────────────────────────────
DATA_PRESENTATION_RULES = """DATA PRESENTATION RULES:

Number Formatting:
- Never say "large market." Say "$380B by 2028 (Grand View Research)."
- Never say "fast growing." Say "34% CAGR 2024-2028 (Gartner)."
- Round for readability: "$2.3M" not "$2,341,872." "$4.2B" not "$4,187,000,000."
- Growth metrics: "15% MoM" or "3.2x YoY" — pick one format and be consistent.
- Always include the time dimension: "$50K MRR" → "$50K MRR (as of March 2026)."

Chart Rules:
- Bar charts for comparison across categories.
- Line charts for trends over time. ALWAYS include the time axis.
- Pie charts ONLY for parts-of-a-whole when ≤5 categories.
- Never use 3D charts. Never use dual-axis charts.
- Growth charts: Show the inflection point. Label it. "Product-market fit: Oct 2025."
- Label axes. Include units. Add source attribution below.

Source Attribution:
- Any claim over $1M or over 10% needs a source.
- Format: "(McKinsey, 2025)" or "Source: Internal Stripe Dashboard, March 2026."
- "Internal data" is valid for your own metrics.
- If estimated, say so: "Estimated based on public filings and industry reports."
- Avoid citing sources older than 3 years for market data.

Metric Presentation:
- KPIs in priority order: Revenue → Growth Rate → Retention → Unit Economics → Market Size.
- Always show trajectory, not just current state: "$50K MRR, from $8K six months ago."
- Use comparisons: "3x industry average", "Top 10% of YC W26 batch."
- Include cohort data when possible: "January cohort retains at 85% after 6 months."
"""

# ── Common Mistakes Guard ───────────────────────────────────
COMMON_MISTAKES = """AVOID THESE PITCH DECK MISTAKES:

Words That Signal Weak Thinking (do NOT use):
- "Revolutionary" — every startup says this. Show, don't tell.
- "Disruptive" — earned, not claimed. Let traction speak.
- "Best-in-class" — compared to what? Says nothing.
- "Cutting-edge" — vague. Name the actual technology.
- "Synergy" — corporate jargon. Be specific about the value.
- "Holistic" — means nothing concrete.
- "Leverage" (as verb) — say "use" or describe the specific mechanism.
- "Unique" — everything is unique. What makes it BETTER?
- "World-class" — prove it with a metric.
- "Game-changer" — the audience decides this, not you.

Structural Mistakes:
- Wall of text: If a slide has >50 words of body text, it needs editing.
- Too many bullets: Max 6 per slide. If you have 8, combine or split.
- Missing the ask: Investors need to know exactly what you want and why.
- Burying traction: If you have traction, it's slide 3-4, not slide 8.
- Generic competition slide: "We have no direct competitors" = red flag.
- No use-of-funds: "We need $2M" without explaining where it goes.

Data Mistakes:
- Hockey stick projection with no assumption backing.
- TAM cited without methodology (top-down vs. bottom-up).
- Showing percentage growth without absolute numbers (200% of $100 = $300).
- Cherry-picking metrics: Show NPS but hide churn.
- Mixing time periods: MRR (monthly) next to ARR (annual) without labeling.
"""
