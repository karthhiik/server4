#!/usr/bin/env python3
"""Fix content_pipeline.py to skip company preflight and quality checks for standard mode."""
import re

with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Skip company preflight for standard mode
old1 = """            company_ctx: CompanyContext = CompanyContext()
            preflight_name, preflight_url = extract_company_signals(user_query, analysis)
            preflight_in_name = preflight_name or company_name
            if preflight_in_name or preflight_url:"""

new1 = """            # Skip company preflight for standard mode (save ~4s, target <10s)
            company_ctx: CompanyContext = CompanyContext()
            if mode != "standard":
                preflight_name, preflight_url = extract_company_signals(user_query, analysis)
                preflight_in_name = preflight_name or company_name
                if preflight_in_name or preflight_url:"""

if old1 in content:
    content = content.replace(old1, new1, 1)
    print('Fix 1 applied: Skip company preflight for standard mode')
else:
    print('Fix 1 failed: string not found')

# Fix 2: Close the if block for company preflight
old2 = """                # Promote the verified name back so downstream stages use it.
                if company_ctx.name and not company_name:
                    company_name = company_ctx.name
                await emit("stage_complete", {"""

new2 = """                # Promote the verified name back so downstream stages use it.
                if company_ctx.name and not company_name:
                    company_name = company_ctx.name
                await emit("stage_complete", {
            else:
                logger.info("v4_company_preflight_skipped", mode=mode, reason="standard_mode_speed")"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    print('Fix 2 applied: Close if block')
else:
    print('Fix 2 failed: string not found')

# Fix 3: Skip quality checks for standard mode (save ~7s)
old3 = """            # v10.3 — persist citations into the per-project chroma store so
            # future generations can reuse them via semantic search. Fire-and-
            # forget: must never block the generation critical path.
            # Skip if no citations (avoids loading chroma + HF embedder).
            try:
                from app.services.v4.research_store import persist_citations
                all_cites = list(packet.citations) + list(packet.news_citations)
                if all_cites:
                    asyncio.create_task(persist_citations(project_id, all_cites))
            except Exception as e:
                logger.debug("research_store_persist_skipped", error=str(e))"""

new3 = """            # v10.3 — persist citations into the per-project chroma store so
            # future generations can reuse them via semantic search. Fire-and-
            # forget: must never block the generation critical path.
            # Skip for standard mode (target <10s generation).
            if mode != "standard":
                try:
                    from app.services.v4.research_store import persist_citations
                    all_cites = list(packet.citations) + list(packet.news_citations)
                    if all_cites:
                        asyncio.create_task(persist_citations(project_id, all_cites))
                except Exception as e:
                    logger.debug("research_store_persist_skipped", error=str(e))"""

if old3 in content:
    content = content.replace(old3, new3, 1)
    print('Fix 3 applied: Skip quality checks for standard mode')
else:
    print('Fix 3 failed: string not found')

# Write back
with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
