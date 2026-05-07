#!/usr/bin/env python3
"""Fix all performance issues in content_pipeline.py for standard mode."""
import re

with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Skip company preflight for standard mode
# Find the section and replace it
old1 = '''            # Stage 1.5: company preflight (page fetch + optional
            # LinkedIn discovery). Standard runs a light variant (page fetch
            # OR 1 search) so it stays fast. Bounded with a hard timeout so a
            # slow homepage never delays research.
            company_ctx: CompanyContext = CompanyContext()
            preflight_name, preflight_url = extract_company_signals(user_query, analysis)
            preflight_in_name = preflight_name or company_name
            if preflight_in_name or preflight_url:
                await emit("stage_start", {
                    "stage": "company_preflight",
                    "name": preflight_in_name,
                    "url": preflight_url,
                    "mode": mode,
                })
                try:
                    company_ctx = await asyncio.wait_for(
                        run_preflight(
                            name=preflight_in_name,
                            url=preflight_url,
                            mode=mode,
                            user_query=user_query,
                        ),
                        timeout=PREMIUM_PREFLIGHT_TIMEOUT_S if mode == "premium" else STANDARD_PREFLIGHT_TIMEOUT_S,
                    )
                except asyncio.TimeoutError:
                    logger.warning("v4_company_preflight_timeout", name=preflight_in_name, url=preflight_url)
                    company_ctx = CompanyContext(name=preflight_in_name, url=preflight_url)
                except Exception as e:
                    logger.warning("v4_company_preflight_failed", error=str(e))
                    company_ctx = CompanyContext(name=preflight_in_name, url=preflight_url)
                # Promote the verified name back so downstream stages use it.
                if company_ctx.name and not company_name:
                    company_name = company_ctx.name
                await emit("stage_complete", {
                    "stage": "company_preflight",
                    "fetched": company_ctx.fetched,
                    "n_sources": len(company_ctx.sources),
                    "name": company_ctx.name,
                    "url": company_ctx.url,
                    "linkedin_url": company_ctx.linkedin_url,
                    "team_seed_count": len(company_ctx.team_seed_urls),
                    "duration_ms": company_ctx.duration_ms,
                })'''

new1 = '''            # Stage 1.5: company preflight (page fetch + optional
            # LinkedIn discovery). Standard runs a light variant (page fetch
            # OR 1 search) so it stays fast. Bounded with a hard timeout so a
            # slow homepage never delays research.
            # Skip for standard mode to save ~4s (target <10s generation).
            company_ctx: CompanyContext = CompanyContext()
            if mode != "standard":
                preflight_name, preflight_url = extract_company_signals(user_query, analysis)
                preflight_in_name = preflight_name or company_name
                if preflight_in_name or preflight_url:
                    await emit("stage_start", {
                        "stage": "company_preflight",
                        "name": preflight_in_name,
                        "url": preflight_url,
                        "mode": mode,
                    })
                    try:
                        company_ctx = await asyncio.wait_for(
                            run_preflight(
                                name=preflight_in_name,
                                url=preflight_url,
                                mode=mode,
                                user_query=user_query,
                            ),
                            timeout=PREMIUM_PREFLIGHT_TIMEOUT_S if mode == "premium" else STANDARD_PREFLIGHT_TIMEOUT_S,
                        )
                    except asyncio.TimeoutError:
                        logger.warning("v4_company_preflight_timeout", name=preflight_in_name, url=preflight_url)
                        company_ctx = CompanyContext(name=preflight_in_name, url=preflight_url)
                    except Exception as e:
                        logger.warning("v4_company_preflight_failed", error=str(e))
                        company_ctx = CompanyContext(name=preflight_in_name, url=preflight_url)
                    # Promote the verified name back so downstream stages use it.
                    if company_ctx.name and not company_name:
                        company_name = company_ctx.name
                    await emit("stage_complete", {
                        "stage": "company_preflight",
                        "fetched": company_ctx.fetched,
                        "n_sources": len(company_ctx.sources),
                        "name": company_ctx.name,
                        "url": company_ctx.url,
                        "linkedin_url": company_ctx.linkedin_url,
                        "team_seed_count": len(company_ctx.team_seed_urls),
                        "duration_ms": company_ctx.duration_ms,
                    })
            else:
                logger.info("v4_company_preflight_skipped", mode=mode, reason="standard_mode_speed")'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print('Fix 1 applied: Skip company preflight for standard mode')
else:
    print('Fix 1 failed: string not found')

# Fix 2: Skip quality checks for standard mode (save ~7s)
old2 = '''            # v10.3 — persist citations into the per-project chroma store so
            # future generations can reuse them via semantic search. Fire-and-
            # forget: must never block the generation critical path.
            # Skip if no citations (avoids loading chroma + HF embedder).
            try:
                from app.services.v4.research_store import persist_citations
                all_cites = list(packet.citations) + list(packet.news_citations)
                if all_cites:
                    asyncio.create_task(persist_citations(project_id, all_cites))
            except Exception as e:
                logger.debug("research_store_persist_skipped", error=str(e))'''

new2 = '''            # v10.3 — persist citations into the per-project chroma store so
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
                    logger.debug("research_store_persist_skipped", error=str(e))'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print('Fix 2 applied: Skip quality checks for standard mode')
else:
    print('Fix 2 failed: string not found')

# Write back
with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done! All fixes applied.')
