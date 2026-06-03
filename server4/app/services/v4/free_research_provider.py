"""
Free Research Provider - Zero-cost research APIs for Docker deployment.

Uses Wikipedia, DuckDuckGo, and other free APIs to provide research data
without requiring paid API keys. Designed to work in Azure Docker containers.

Integration points:
- research_collector.py: Add as fallback provider
- fact_verifier.py: Use for fact verification
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class FreeCitation:
    """Citation from free research sources."""
    title: str
    url: str
    snippet: str
    source: str  # "wikipedia", "duckduckgo", "wikidata"
    source_authority: float = 0.5
    published_at: Optional[str] = None


@dataclass
class FreeResearchResult:
    """Result from free research APIs."""
    query: str
    citations: List[FreeCitation] = field(default_factory=list)
    summary: str = ""
    facts: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    sources_used: List[str] = field(default_factory=list)


class FreeResearchProvider:
    """
    Provides research using free APIs that work without API keys.
    
    Sources:
    - Wikipedia API (free, no key required)
    - DuckDuckGo Instant Answer API (free, no key required)
    - Wikidata API (free, no key required)
    
    Designed for Docker deployment where paid APIs may be rate-limited.
    """
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/html, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def research(
        self,
        query: str,
        max_results: int = 8,
        include_wikipedia: bool = True,
        include_duckduckgo: bool = True,
    ) -> FreeResearchResult:
        """
        Perform research using free APIs.
        
        Args:
            query: Research query
            max_results: Maximum citations to return
            include_wikipedia: Include Wikipedia results
            include_duckduckgo: Include DuckDuckGo results
            
        Returns:
            FreeResearchResult with citations and summary
        """
        start = datetime.now(timezone.utc)
        citations: List[FreeCitation] = []
        sources_used: List[str] = []
        
        tasks = []
        if include_wikipedia:
            tasks.append(self._search_wikipedia(query))
        if include_duckduckgo:
            tasks.append(self._search_duckduckgo(query))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("free_research_error", error=str(result))
                    continue
                
                if isinstance(result, list):
                    for cit in result:
                        if isinstance(cit, FreeCitation):
                            citations.append(cit)
                            if cit.source not in sources_used:
                                sources_used.append(cit.source)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_citations = []
        for cit in citations:
            if cit.url not in seen_urls:
                seen_urls.add(cit.url)
                unique_citations.append(cit)
        
        # Do not fabricate citations with an LLM. A sparse research packet is
        # safer than plausible-looking sources that were never fetched.
        if len(unique_citations) < 2:
            logger.info("free_research_sparse_results", query=query, n_existing=len(unique_citations))
        
        # Limit results
        unique_citations = unique_citations[:max_results]
        
        # Generate summary from snippets
        summary = self._generate_summary(query, unique_citations)
        
        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        
        return FreeResearchResult(
            query=query,
            citations=unique_citations,
            summary=summary,
            duration_ms=duration_ms,
            sources_used=sources_used,
        )
    
    async def _search_wikipedia(self, query: str) -> List[FreeCitation]:
        """
        Search Wikipedia API for relevant articles.
        
        Uses Wikipedia's REST API for page summaries (free, no key required).
        """
        client = await self._get_client()
        citations: List[FreeCitation] = []
        
        try:
            # Try Wikimedia REST API for page summary
            # Extract key terms from query
            terms = query.replace("insurance", "").replace("for", "").replace("the", "").strip()
            terms = terms.replace(" ", "_")[:50]
            
            # Wikimedia REST API - more reliable than MediaWiki API
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(terms)}"
            
            response = await client.get(summary_url)
            if response.status_code == 200:
                data = response.json()
                title = data.get("title", "")
                extract = data.get("extract", "")
                url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                
                if title and extract:
                    citations.append(FreeCitation(
                        title=title,
                        url=url or f"https://en.wikipedia.org/wiki/{quote(title)}",
                        snippet=extract[:500],
                        source="wikipedia",
                        source_authority=0.9,
                    ))
                    logger.debug("wikipedia_rest_success", query=query, title=title)
                    return citations
            
            # Fallback: Try related search terms
            related_terms = query.split()[:3]  # First 3 words
            for term in related_terms:
                if len(term) > 3:
                    try:
                        r = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(term)}")
                        if r.status_code == 200:
                            data = r.json()
                            title = data.get("title", "")
                            extract = data.get("extract", "")
                            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                            if title and extract:
                                citations.append(FreeCitation(
                                    title=title,
                                    url=url or f"https://en.wikipedia.org/wiki/{quote(title)}",
                                    snippet=extract[:500],
                                    source="wikipedia",
                                    source_authority=0.85,
                                ))
                    except Exception:
                        pass
            
            logger.debug("wikipedia_search_success", query=query, results=len(citations))
            
        except Exception as e:
            logger.warning("wikipedia_search_error", query=query, error=str(e))
        
        return citations
    
    async def _get_wikipedia_extract(self, client: httpx.AsyncClient, title: str) -> str:
        """Fetch article extract from Wikipedia."""
        try:
            encoded_title = quote(title)
            url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=true&explaintext=true&titles={encoded_title}&format=json"
            
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                extract = page.get("extract", "")
                if extract:
                    return extract[:500]
            
        except Exception:
            pass
        
        return ""
    
    async def _search_duckduckgo(self, query: str) -> List[FreeCitation]:
        """
        Search DuckDuckGo Instant Answer API.
        
        Free API that provides instant answers without requiring a key.
        Returns 202 with empty body when no instant answer exists — this is
        NOT an error, just means DDG doesn't have a direct answer.
        """
        client = await self._get_client()
        citations: List[FreeCitation] = []
        
        try:
            encoded_query = quote(query)
            # DuckDuckGo Instant Answer API — t=h_ ensures proper JSON response
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1&t=h_"
            
            response = await client.get(url)
            # DDG returns 202 when no instant answer — not an error
            if response.status_code not in (200, 202):
                logger.debug("duckduckgo_unexpected_status", query=query, status=response.status_code)
                return citations
            
            # Guard against empty/non-JSON responses
            text = response.text.strip()
            if not text or text.startswith("<"):
                logger.debug("duckduckgo_non_json_response", query=query)
                return citations
            
            try:
                data = response.json()
            except Exception:
                logger.debug("duckduckgo_json_parse_error", query=query)
                return citations
            
            # Abstract (main answer from Wikipedia or other sources)
            abstract = data.get("Abstract", "")
            abstract_url = data.get("AbstractURL", "")
            abstract_source = data.get("AbstractSource", "")
            
            if abstract and abstract_url:
                citations.append(FreeCitation(
                    title=f"{abstract_source} - {query}",
                    url=abstract_url,
                    snippet=abstract[:500],
                    source="duckduckgo",
                    source_authority=0.7,
                ))
            
            # Related topics
            related_topics = data.get("RelatedTopics", [])
            for topic in related_topics[:5]:
                if isinstance(topic, dict):
                    text = topic.get("Text", "")
                    first_url = topic.get("FirstURL", "")
                    if text and first_url:
                        citations.append(FreeCitation(
                            title=text[:100] if len(text) > 100 else text,
                            url=first_url,
                            snippet=text[:500],
                            source="duckduckgo",
                            source_authority=0.6,
                        ))
            
            # Results (web links)
            results = data.get("Results", [])
            for result in results[:3]:
                if isinstance(result, dict):
                    result_url = result.get("FirstURL", "")
                    text = result.get("Text", "")
                    if result_url and text:
                        citations.append(FreeCitation(
                            title=text[:100],
                            url=result_url,
                            snippet=text[:500],
                            source="duckduckgo",
                            source_authority=0.5,
                        ))
            
            if citations:
                logger.debug("duckduckgo_search_success", query=query, results=len(citations))
            else:
                logger.debug("duckduckgo_no_results", query=query)
            
        except Exception as e:
            logger.debug("duckduckgo_search_error", query=query, error=str(e)[:100])
        
        return citations
    
    def _generate_summary(self, query: str, citations: List[FreeCitation]) -> str:
        """Generate a summary from the collected citations."""
        if not citations:
            return f"No research results found for: {query}"
        
        # Combine snippets into a summary
        snippets = [c.snippet for c in citations if c.snippet]
        if not snippets:
            return f"Found {len(citations)} sources for: {query}"
        
        # Simple concatenation with cleanup
        combined = " ".join(snippets[:3])
        # Remove duplicate phrases
        combined = re.sub(r'\s+', ' ', combined)
        
        return combined[:500] if len(combined) > 500 else combined


# Singleton instance for reuse
_free_research_provider: Optional[FreeResearchProvider] = None


def get_free_research_provider() -> FreeResearchProvider:
    """Get or create singleton FreeResearchProvider."""
    global _free_research_provider
    if _free_research_provider is None:
        _free_research_provider = FreeResearchProvider()
    return _free_research_provider


async def free_research(
    query: str,
    max_results: int = 8,
) -> FreeResearchResult:
    """
    Convenience function for free research.
    
    Args:
        query: Research query
        max_results: Maximum citations to return
        
    Returns:
        FreeResearchResult with citations
    """
    provider = get_free_research_provider()
    return await provider.research(query, max_results=max_results)
