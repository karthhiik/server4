---
name: llm-content-orchestration
description: "Design and implement how available LLMs and APIs are orchestrated for content generation. Use when: routing tasks to specific models, designing multi-model pipelines (think → draft → refine → critique), engineering prompts for slide content, managing token budgets, building fallback chains, optimizing generation cost and speed, selecting which model handles which generation role, or parallelizing LLM calls for faster generation."
---

# LLM Content Orchestration

## Purpose
This skill covers how the product uses its available LLM models to generate presentation content. The key challenge: multiple models with different strengths must be orchestrated into a fast, cost-effective, high-quality generation pipeline. No hypothetical models — only use what's actually available and configured in the codebase.

## Core Principle: Available Models Only

**NEVER propose using a model that isn't configured in the project.** Before designing any generation pipeline:
1. Check `app/config.py` and `.env.example` for configured API keys and model names
2. Check `app/services/` for existing LLM routing/calling code
3. Check `app/mcp/` for MCP-based model access
4. Only design pipelines using models that are actually available

## Model Routing Strategy

### The Four-Role Pipeline Mapping

Each generation role has different requirements. Map models to roles based on their strengths:

| Role | Requirement | Ideal Model Profile |
|------|------------|-------------------|
| **Strategist** | Complex reasoning, narrative planning, audience analysis | Strong reasoning model, moderate speed acceptable |
| **Researcher** | Content generation, data synthesis, domain knowledge | Large context window, broad knowledge, fast |
| **Composer** | Structured output, layout decisions, JSON generation | Strong instruction following, reliable JSON output |
| **Critic** | Quality assessment, pattern detection, coherence check | Good reasoning, can compare against criteria |

### Routing Principles
- **Thinking models** (reasoning-enhanced) → Strategist and Critic roles (need deep analysis)
- **Fast models** (low latency) → Researcher role for parallel content generation
- **Instruction-following models** → Composer role for structured DSL output
- **Cost-effective models** → Bulk operations, iterations, non-critical passes

### Fallback Chain Design
Every model call must have a fallback:
```
Primary Model → Fallback Model 1 → Fallback Model 2 → Error with partial result
```
Never let a single model failure kill the entire generation. Degrade gracefully:
- If the Strategist model fails → use a simpler model with a more detailed prompt
- If a Researcher call fails → skip that slide's enrichment, use Strategist's outline content
- If the Composer fails → use a default layout for that slide, flag for manual editing

## Prompt Engineering for Slide Content

### Strategist Prompts
The Strategist prompt must produce a structured Deck Blueprint:
- Input: User query, presentation type, audience context
- Output: Ordered list of slide intents with: purpose, key message, content requirements, narrative role
- The prompt must enforce: story arc thinking, audience-awareness, no generic filler

**Key technique**: Give the Strategist examples of BAD deck outlines (generic, no narrative) and GOOD deck outlines (specific, story-driven) in the prompt. Few-shot learning with contrast.

### Researcher Prompts
The Researcher generates content for each slide independently (parallelizable):
- Input: Slide intent from Blueprint, deck context (topic, audience, tone)
- Output: Content blocks — headline, body text, data points, evidence markers
- The prompt must enforce: specificity over generality, numbers over vague claims, <75 words per slide

**Key technique**: Include word count constraints directly in the prompt. Models respect explicit limits better than implicit ones.

### Composer Prompts
The Composer must produce valid DSL output:
- Input: Enriched content blocks, available layout types, previous slide's layout
- Output: Structured JSON matching the slide DSL schema
- The prompt must enforce: valid JSON, layout variety, proper element positioning

**Key technique**: Provide the exact JSON schema in the prompt. Use constrained output / JSON mode when available. Include 2-3 complete examples of valid slide JSON.

### Critic Prompts
The Critic evaluates the complete deck:
- Input: Full deck JSON, quality criteria checklist
- Output: Score (1-10), specific issues with slide numbers, fix instructions
- The prompt must enforce: actionable feedback, not vague ("slide 3 headline is too generic" not "improve quality")

**Key technique**: Give the Critic a rubric with weighted criteria. Narrative flow (25%), content specificity (25%), design variety (20%), text density (15%), coherence (15%).

## Token Budget Management

### Budget Allocation per Deck Generation
Total budget must fit within practical limits. Allocate tokens strategically:

| Stage | Input Tokens | Output Tokens | Notes |
|-------|-------------|---------------|-------|
| Strategist | ~500 (query + system prompt) | ~1000 (blueprint) | Single call |
| Researcher | ~300 per slide × N slides | ~500 per slide × N | Parallel calls |
| Composer | ~800 per slide (content + schema) | ~600 per slide | Parallel calls |
| Critic | ~2000 (full deck) | ~500 (assessment) | Single call |

For a 12-slide deck: ~500 + (300×12) + (800×12) + 2000 = ~15,700 input tokens, ~1000 + (500×12) + (600×12) + 500 = ~14,700 output tokens.

### Token Optimization Techniques
- **Compress system prompts**: Remove examples after the first generation (use cached prompts)
- **Parallelize Researcher + Composer**: Don't wait for all research to finish before composing
- **Batch small slides**: Combine 2-3 simple slides into one Composer call
- **Cache common patterns**: Pitch deck blueprints for standard types can be cached, skipping the Strategist for common queries

## Parallel Generation Architecture

For sub-30s generation, parallelism is essential:

```
[Strategist] ─── produces Blueprint (3-5s)
      │
      ├── [Researcher slide 1] ──┐
      ├── [Researcher slide 2] ──┤
      ├── [Researcher slide 3] ──┼── all parallel (5-10s total)
      ├── ...                    │
      └── [Researcher slide N] ──┘
                                 │
      ├── [Composer slide 1] ────┐
      ├── [Composer slide 2] ────┤
      ├── [Composer slide 3] ────┼── all parallel, start as each Researcher finishes (5-10s total)
      ├── ...                    │
      └── [Composer slide N] ────┘
                                 │
                          [Critic] ─── reviews full deck (3-5s)
```

Researcher and Composer can be pipelined: as soon as slide 1's research is done, the Composer starts on slide 1 while Researcher is still working on slides 2-N.

## Quality Gates

Before delivering generated content to the user, enforce:

1. **No empty slides** — every slide must have at least a headline
2. **No duplicate content** — adjacent slides must not repeat the same message
3. **Word count compliance** — no slide exceeds 100 words of visible text
4. **JSON validity** — all slide data must parse without errors
5. **Layout variety** — no more than 2 identical layouts in any 5-slide window
6. **Narrative coherence** — first slide sets context, last slide has a call to action

## Procedure When Working on LLM Orchestration

1. **Inventory available models** — Read config files to know exactly what's available
2. **Map models to roles** — Assign based on actual model capabilities, not assumptions
3. **Design the prompt chain** — Write prompts for each role with examples
4. **Implement parallel execution** — Use async/await or Celery for parallel model calls
5. **Build fallback chains** — Every call must have a degradation path
6. **Add quality gates** — Validate output before returning to user
7. **Measure latency** — Track time per stage, optimize the bottleneck
8. **Monitor costs** — Log token usage per generation for cost forecasting
