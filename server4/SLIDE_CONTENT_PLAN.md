# Slide Content Generation - Deep Research & RAG Architecture Plan

## Executive Summary
This architecture plan outlines a highly robust, real-time context aggregation ("Deep Research") and generation (RAG) system for Pitch Deck and Presentation slide generation. Recognizing the budget limitations of early-stage startups, this system optimizes API utilization through extensive fallback tiers, asynchronous data fetching across multiple free-tier and shared-pool APIs, and local RAG capabilities. It leverages a structured multi-agent workflow to output highly stylized, narrative-driven presentation content. An interactive React Flow UI provides real-time visualization of the reasoning and generation pipeline.

---

## 1. Intelligence Discovery: API & Resource Audit

Based on the backend configuration (`app/config.py`), the following intelligence APIs are available. The architecture will cycle and multiplex across these to respect free-tier limits.

### LLM Generators (Iterative Fallback)
*   **Tier 0 (Reasoning/Planning):** Azure Kimi-K2-Thinking, Azure Phi-4-Reasoning. (Use for analyzing user queries and architecting the overall presentation narrative).
*   **Tier 1 (Storytelling/Content execution):** Azure DeepSeek-V3.2. (Handles the heavy lifting of narrative structure and styling).
*   **Tier 2 (Fast Structured JSON):** Azure GPT-4o-mini. (Excellent for rapid schema generation and React Flow graph extraction).
*   **Tier 3 (Technical/Analytical):** Azure Mistral-medium. (For data-heavy slides).
*   **Tier 4 (High-Volume Aggregation):** Groq (8 API keys used in a round-robin). (Used for fast summarization of web data with extremely low latency).
*   **Tier 5/6 (Fallbacks):** Cloudflare Workers (GLM, QWEN, GEMMA), HuggingFace, OpenRouter free tier.

**Strategy:** Use Groq for summarizing scraped data (low latency/high rate limit). Use DeepSeek-V3 for the slide crafting. Use Kimi-K2 for the orchestration and outline.

### Deep Research & Market APIs
*   **Web Search:** Serper (x3 keys round-robin) and SerpAPI (x2 keys round-robin). *Free tiers typically allow 100-250 searches/month per key.*
*   **AI-Agents Search:** Tavily (research specific), Exa, Firecrawl, Jina.ai, You.com. *Tavily gives ~1000 free searches. Firecrawl handles scraping and markdown conversion.*
*   **Financial/Economic Data:** Alpha Vantage, Finnhub, Polygon, FRED, Census API, FMP. *Vital for GTM and Financial projections slides. Usually capped at 5-50 calls/min.*
*   **News & Sentiment:** NewsAPI, NewsData, Guardian, World News. *Provides up-to-date market trends.*
*   **Social / Developer Data:** Reddit, GitHub, YouTube, ProductHunt. *Perfect for startup traction and competitive analysis.*

---

## 2. The "Deep Research" RAG Architecture

Inspired by `lightpanda` and other advanced research frameworks, the slide content engine employs an asynchronous, multi-stage fact-finding pipeline before any content is written.

### Stage 1: The Brief Analyzer (Kimi-K2)
*   **Input:** User's text description, company URL, uploaded docs (if any), desired output format (e.g., "YC Pitch Deck", "Series A", "Sales Deck"), and stylistic choice (over 50+ supported, e.g., "Storytelling", "Data-driven", "Visionary").
*   **Action:** Breaks down the slide deck framework (e.g., Problem, Solution, Market Size, Traction). Identifies missing data gaps.

### Stage 2: Distributed Data Scavenging (Deep Research)
*   **Mechanism:** Async parallel fetching.
*   **Market Size/Trends:** Fires search queries via Tavily and Serper to find recent competitor data and market reports.
*   **Financial Proxies:** Uses FMP / Alpha Vantage applied to similar public companies to establish baselines.
*   **Scraping:** Firecrawl extracts markdown from top search results.
*   **Summarization Bypass:** Groq reads the dumped markdown concurrently and condenses it into highly dense fact-payloads to save token context size.

### Stage 3: Local RAG Aggregation (ChromaDB)
*   **Storage:** The summarized facts, user documents, and historical templates are embedded and inserted into local `ChromaDB`.
*   **Retrieval:** When generating the "Solution" slide, the engine queries the ChromaDB for exactly the scraped competitor data and user metrics relevant only to "Solution", preventing hallucination and context-bloat.

### Stage 4: Narrative Synthesis & Slide Crafting (DeepSeek-V3)
*   **Context Injection:** The RAG chunks + stylistic prompts are fed to DeepSeek.
*   **Execution:** DeepSeek outputs structured JSON mapping out Header, Bullet Points, Speaking Notes, and Image Prompts per slide.
*   **Style Engine:** Applies the specific stylistic wrapper chosen (e.g., adjusting tone, vocabulary, and pacing).

---

## 3. Real-Time Streaming & Visualizing the "React Flow"

A modern UI requires transparency, especially when generation takes time.

### Backend Streaming (FastAPI + Server-Sent Events / WebSockets)
As the deep research and generation execute, the backend emits granular event states.

*   `[Search_Start]` -> *Fetching competitors from Serper...*
*   `[Scrape_Complete]` -> *Ingested 4 URLs via Firecrawl.*
*   `[RAG_Embed]` -> *Extracting market size data...*
*   `[Slide_Gen_1]` -> *Drafting Problem Slide...*

### Frontend React Flow Integration
Instead of a simple loading bar, the frontend utilizes `React Flow` to render an interactive Directed Acyclic Graph (DAG) visualizing the agentic workflow.

1.  **Nodes:** Represent agents, APIs, and generated slides.
    *   *Node A (User Input)* -> *Node B (Orchestrator Agent)* -> *(Nodes C, D, E: Web Search, Financial APIs, GitHub)*
    *   *Nodes C,D,E* -> *Node F (Knowledge Graph/ChromaDB)*
    *   *Node F* -> *Node G (Slide Content Engine)*
2.  **Edges:** Animated (using React Flow's `animated: true` edge property) to simulate data flowing across nodes as SSE events arrive.
3.  **Live Updates:** As DeepSeek yields slide content, a new node (e.g., `Slide 1: Problem`) unfurls on the map, displaying a preview of the generated content.
4.  **Style Inspector:** A dedicated control node reflects the chosen style (e.g., "YC Pitch Deck - Storytelling") showing the applied prompt constraints.

---

## 4. Implementation Phasing

*   **Phase A: API Multiplexer Core:** Build the robust round-robin and fallback router for Serper, Groq, and SerpAPI to guarantee search never fails.
*   **Phase B: Async Deep Research Engine:** Implement the Firecrawl/Tavily data scavenger and hook it into the ChromaDB RAG layer.
*   **Phase C: DeepSeek Content Pipeline:** Craft the dense JSON schemas for slide generation and implement the 50+ dynamic style prompts.
*   **Phase D: Streaming & React Flow:** Expose the SSE endpoints in FastAPI and configure the React Flow component in the frontend to consume the event stream.

---
*Optimized for Barise's Visionary Architect operations: Maximizing output quality while operating within optimal free-tier boundaries.*