# Slide Content Generation Engine — V7 Sub-Architecture

**Document Status**: Final Architecture Plan  
**Target Output**: Real-World Investor Pitch Decks, Reading/Presentation Modes, 50+ Narrative Styles  
**Integration Point**: Seamlessly feeds into the `PREMIUM_SLIDE_MCP_V7_PLAN.md` renderer  

---

## 1. Executive Summary

This document outlines the **Slide Content Generation Engine**, a standalone intelligence pipeline that sits *before* the V7 Multi-Renderer Layout Engine. Its sole purpose is to act as an elite team of startup founders (CEO, CTO, Market Researcher) who debate, research, and compose perfectly structured, real-time, data-backed slide content using heavily optimized Free-Tier and Subscription API load balancing.

---

## 2. API Quota & Load Balancing Strategy (.env Optimization)

We have a vastly diverse set of API keys. To prevent exhausting free tiers, the engine uses an **Intelligent Waterfall Router**.

### 2.1 The Orchestration & Formatting Layer (Cost: $0)
*   **Model**: **Groq (8 API Keys)**
*   **Strategy**: Groq is lightning-fast but rate-limited per key. The `KeyManager` round-robins across `GROQ_API_KEY1` through `GROQ_API_KEY7`.
*   **Role**: Query generation, formatting raw text into Slide DSL v2 JSON, applying syntax constraints.

### 2.2 The Deep Thinking & Synthesis Layer (Subscription)
*   **Model**: **Azure DeepSeek-V3** & **Azure Kimi-K2**
*   **Role**: Only invoked when complex synthesis is required (e.g., digesting 50 pages of scraped markdown into a 4-bullet TAM slide). 

### 2.3 The Elite RAG & Fallback Layer (Cost: $0)
*   **Model**: **Cloudflare Workers AI** (Qwen, Gemma)
*   **Limit**: ~1000 requests daily.
*   **Role**: Generating embeddings for scraped websites, performing semantic similarity search (RAG) locally before passing context to Groq.

### 2.4 The Deep Research Web Layer (Waterfall Fallbacks)
When the "Market Researcher Agent" needs real-time data:
1.  **Exa.ai / Tavily** (Primary, 1000 free/mo) — Used for finding competitors and TAM metrics.
2.  **Serper.dev / SERPAPI** (3 keys, 7500 total free) — Fallback traditional search.
3.  **Jina.ai / Firecrawl** (Scraping) — Only used on the top 3 URLs returned by search to bypass paywalls and extract clean markdown.
4.  **Domain-Specific**: `ALPHA_VANTAGE`, `FINNHUB`, `FRED_API` are strictly reserved for the "Financial Projections" slides to pull real-time bond rates/stock comps without burning generic search credits.

---

## 3. The CEO / CTO Synthetic Debate Pipeline (Pitch Decks Only)

For core investor pitch decks, generating static content is insufficient. The engine deploys a **Multi-Agent Deliberation MCP**.

1.  **The Pitch Request**: User asks for a "Pitch Deck for an AI-powered supply chain startup."
2.  **The Market Researcher Agent**: Dispatches parallel searches via Groq + Exa.ai to find supply chain inefficiencies and 3 competitor profiles.
3.  **The CTO Agent**: Reviews the technical feasibility. *Prompt context:* "How do we build this? What is our technical moat?"
4.  **The CEO Agent**: *Prompt context:* "Investors only care about TAM and Go-to-Market. Challenge the CTO's technical jargon. Simplify it."
5.  **The Matrix Chat**: The CEO and CTO pass the context back and forth 2 times via the `DeepSeek-V3` model. 
6.  **The Synthesis**: The output is stripped of dialogue and merged into the final 10-slide structure (e.g., Problem, Solution, Traction, Market, Competition).

---

## 4. Elite RAG & Deep Research (Inspired by Lightpanda)

To mimic Lightpanda/OpenAI Deep Research:
*   **Self-Correcting Queries**: If the initial search ("AI supply chain market size") returns generic results, Groq automatically rewrites the query ("Global logistics AI predictive maintenance CAGR 2026 report").
*   **Vector Memory**: We use the `EMBEDDINGS_PATH` locally. Scraped data is embedded via Cloudflare Workers AI.
*   **Information Density Scoring**: Before putting a bullet point on a slide, the RAG model checks if it contains a verifiable metric (%, $, X). If not, the bullet is rejected and re-written.

---

## 5. Domain Intelligence: Reading vs. Presentation Modes

The generated output automatically scales to two parallel structures within the Slide DSL v2:

*   **Presentation Mode (The Deck)**: 
    *   Maximum 15 words per slide.
    *   Heavy rely on visuals/charts.
    *   *Hidden Artifact*: Every slide generates detailed `speaker_notes` using Azure GPT-4o-mini so the founder knows exactly what to say.
*   **Reading Mode (The Memo)**: 
    *   Expands the bullet points into prose.
    *   Includes footnotes and citations linked directly to the `Tavily` or `Exa.ai` source URLs.

---

## 6. The 50+ Narrative Styles Engine

The content must match the aesthetics of the V7 Theme engine. We apply a **Style Injection Map** during the final Groq JSON formatting phase. 

**Categories include:**
*   **The YC Standard**: Data-driven, cold, logical, minimal adjectives.
*   **The Visionary (Steve Jobs)**: Heavy contrast (The Old Way vs. The New Way), emotional resonance.
*   **The Academic/Deep Tech**: Dense proofs, methodology disclosures, high technical fidelity.
*   **The Storyteller**: Uses narrative arcs (Hero's Journey) where the customer is the protagonist.

*(There are 46 more styles mapped to system prompts loaded into the Azure Mistral/Kimi endpoints).*

---

## 7. Streaming & Observability (React Flow UI)

Since deep research takes 15-45 seconds, the UI must keep the user engaged.

*   **Action Stream**: The backend streams SSE (Server-Sent Events) to the frontend.
*   **React Flow Visualizer**: The user sees a real-time node graph.
    *   *Node 1*: "CEO Agent: Critiquing Market Size" -> *Green Check*.
    *   *Node 2*: "Exa.ai: Fetching Competitor Pricing" -> *Spinning*.
    *   *Node 3*: "RAG: Filtering irrelevant data" -> *Filtering animation*.
*   **Slide Hydration**: As soon as Slide 1 (The Problem) passes the CEO/CTO debate, its JSON is streamed directly to the V7 reveal.js/React renderer so the user can see it render immediately while Slide 2 is still being researched.

---

## 8. Integration with V7 Schema

This engine outputs strict JSON that the `PREMIUM_SLIDE_MCP_V7_PLAN.md` routers consume verbatim:

```json
{
  "slide_number": 3,
  "layout_type": "split_data_visual",
  "narrative_style": "yc_standard",
  "presentation_content": {
    "headline": "$1.2T Supply Chain Crisis",
    "bullets": ["30% food waste globally", "Legacy ERPs delay tracking by 48 hrs"]
  },
  "reading_content": {
    "paragraph": "According to the World Bank data retrieved via FRED API in 2026, over 30% of global food shipments..."
  },
  "speaker_notes": "Emphasize the 48-hour delay. This is where our technical moat applies.",
  "data_sources": ["https://worldbank.org/supply-data"]
}
```

This perfectly decouples the **Elite Intelligence** from the **Pptx/Three.js Renderers**.