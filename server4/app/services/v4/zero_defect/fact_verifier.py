"""
Fact Verifier - Verifies factual claims using web search
Uses research APIs to verify claims against external sources

Updated 2026-05-11: Added scrape.do, Jina, and DuckDuckGo as free-tier fallbacks.
Fixed LLM response handling (use .content attribute instead of raw object).
Added key pool support for round-robin API key rotation with fallback.
"""

import json
import httpx
import structlog
from typing import List, Dict, Any, Optional
from app.services.v4.zero_defect.models import Fact
from app.config import settings
from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.key_pool import get_pool

logger = structlog.get_logger(__name__)


class FactVerifier:
    """Verifies factual claims using web search APIs with intelligent fallback chain."""
    
    def __init__(self):
        # Ordered by reliability, speed, and key pool availability.
        # APIs with active keys in .env are enabled; others are commented.
        # Fallback order: fastest/key-pooled first → free APIs last.
        self.search_apis = []
        if settings.tinyfish_keys:
            self.search_apis.append("tinyfish")
        if settings.serper_keys:
            self.search_apis.append("serper")
        if settings.tavily_keys:
            self.search_apis.append("tavily")
        if settings.exa_keys:
            self.search_apis.append("exa")
        if settings.you_com_keys:
            self.search_apis.append("you_com")
        if settings.jina_keys:
            self.search_apis.append("jina")
        if settings.firecrawl_keys:
            self.search_apis.append("firecrawl")
        if settings.SCRAPE_DO_API_KEY:
            self.search_apis.append("scrape_do")
        # Always include free fallback
        self.search_apis.append("duckduckgo")
        
        self.current_api_index = 0
        self._model_router: Optional[ModelRouter] = None
    
    @property
    def model_router(self) -> ModelRouter:
        """Lazy-initialize model router to avoid circular imports."""
        if self._model_router is None:
            self._model_router = ModelRouter.get_instance()
        return self._model_router
    
    async def _analyze_with_llm(self, claim: str, search_results: list, sources: list) -> Dict[str, Any]:
        """Use LLM to analyze search results and determine verification."""
        system_prompt = """You are a fact verification expert. Analyze search results to determine if a claim is verified.

Return JSON with:
- verified: true/false if claim is supported by sources
- confidence: 0.0-1.0 confidence score
- explanation: brief explanation of verification"""

        user_prompt = f"""Claim to verify: {claim}

Search results:
{json.dumps(search_results[:5], indent=2)}

Return JSON only."""

        try:
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # FIX: response is LLMResponse object, access .content attribute
            content = response.content if hasattr(response, 'content') else str(response)
            result = json.loads(content)
            
            return {
                "verified": result.get("verified", False),
                "confidence": float(result.get("confidence", 0.0)),
                "sources": sources,
                "explanation": result.get("explanation", "")
            }
        except Exception as e:
            print(f"Error analyzing with LLM: {e}")
            return {
                "verified": False,
                "confidence": 0.0,
                "sources": sources,
                "explanation": f"LLM analysis failed: {str(e)}"
            }
    
    async def verify(self, fact: Fact) -> Fact:
        """
        Verify a single factual claim using web search with intelligent fallback.
        
        Only the FIRST failing API is logged at warning level.
        Subsequent failures are logged at debug to avoid log spam.
        
        Args:
            fact: Fact object to verify
            
        Returns:
            Updated Fact with verification results
        """
        # Validate claim before sending to any API
        if not fact.claim or not fact.claim.strip() or len(fact.claim.strip()) < 5:
            fact.verified = False
            fact.confidence = 0.0
            fact.flagged = False  # Not enough content to verify
            return fact
        
        # Try each search API until one succeeds
        first_failure_logged = False
        for i in range(len(self.search_apis)):
            api_name = self.search_apis[(self.current_api_index + i) % len(self.search_apis)]
            
            try:
                verification_result = await self._verify_with_api(fact, api_name)
                if verification_result:
                    fact.verified = verification_result["verified"]
                    fact.confidence = verification_result["confidence"]
                    fact.sources = verification_result["sources"]
                    
                    if fact.confidence < 0.8:
                        fact.flagged = True
                    
                    return fact
            except Exception as e:
                if not first_failure_logged:
                    logger.warning(f"fact_verify_api_failed_first", api=api_name, error=str(e)[:100])
                    first_failure_logged = True
                else:
                    logger.debug(f"fact_verify_api_failed", api=api_name, error=str(e)[:80])
                continue
        
        # If all APIs fail, mark as unverified but don't block pipeline
        logger.info("fact_verify_all_apis_failed", claim=fact.claim[:60])
        fact.verified = False
        fact.confidence = 0.0
        fact.flagged = True
        return fact
    
    async def verify_batch(self, facts: List[Fact]) -> List[Fact]:
        """
        Verify multiple facts in parallel
        
        Args:
            facts: List of Fact objects to verify
            
        Returns:
            List of updated Fact objects
        """
        import asyncio
        
        tasks = [self.verify(fact) for fact in facts]
        verified_facts = await asyncio.gather(*tasks)
        
        return verified_facts
    
    async def _verify_with_api(self, fact: Fact, api_name: str) -> Dict[str, Any]:
        """
        Verify fact using specific search API
        
        Args:
            fact: Fact object to verify
            api_name: Name of search API to use
            
        Returns:
            Dictionary with verification results
        """
        if api_name == "tinyfish":
            return await self._verify_with_tinyfish(fact)
        elif api_name == "you_com":
            return await self._verify_with_you_com(fact)
        elif api_name == "duckduckgo":
            return await self._verify_with_duckduckgo(fact)
        elif api_name == "jina":
            return await self._verify_with_jina(fact)
        elif api_name == "scrape_do":
            return await self._verify_with_scrape_do(fact)
        elif api_name == "serper":
            return await self._verify_with_serper(fact)
        elif api_name == "exa":
            return await self._verify_with_exa(fact)
        elif api_name == "tavily":
            return await self._verify_with_tavily(fact)
        elif api_name == "firecrawl":
            return await self._verify_with_firecrawl(fact)
        else:
            raise ValueError(f"Unknown API: {api_name}")
    
    async def _verify_with_tinyfish(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using TinyFish AI search API with key pool rotation.
        
        TinyFish API docs: GET https://api.search.tinyfish.ai?query=... with X-API-Key header.
        500 requests/month per key (free tier). 5 keys pooled for 2500 total/month.
        """
        from urllib.parse import quote
        
        pool = get_pool("tinyfish", settings.tinyfish_keys)
        if pool.empty:
            raise ValueError("No TinyFish API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available TinyFish API key")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"https://api.search.tinyfish.ai?query={quote(fact.claim)}&language=en",
                    headers={
                        "X-API-Key": key,
                        "Accept": "application/json",
                        "User-Agent": "BariseFactVerifier/1.0"
                    }
                )
                
                if response.status_code == 429:
                    await pool.report_failure(key, 429)
                    raise Exception("TinyFish API rate limited (429)")
                if response.status_code in (401, 403):
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"TinyFish API auth error: {response.status_code}")
                if response.status_code != 200:
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"TinyFish API error: {response.status_code}")
                
                await pool.report_success(key)
                data = response.json()
                
                results = data.get("results", []) if isinstance(data, dict) else []
                if not results:
                    return {
                        "verified": False,
                        "confidence": 0.0,
                        "sources": []
                    }
                
                sources = [r.get("url", "") for r in results[:5] if r.get("url")]
                formatted_results = [
                    {
                        "title": r.get("title", ""),
                        "snippet": (r.get("snippet") or r.get("description") or "")[:500],
                        "url": r.get("url", "")
                    }
                    for r in results[:5]
                ]
                return await self._analyze_with_llm(fact.claim, formatted_results, sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_you_com(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using You.com SDK with key pool rotation"""
        pool = get_pool("you_com", settings.you_com_keys)
        if pool.empty:
            raise ValueError("No You.com API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available You.com API key")
        
        try:
            from youdotcom import You
            
            # Use SDK - the correct method is you.search.unified()
            you = You(api_key_auth=key)
            # Call search.unified() method
            response = you.search.unified(query=fact.claim, count=5)
            
            await pool.report_success(key)
            
            # Handle response structure from SDK - match research_collector approach
            if not response:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Access results - the SDK returns a dict or object
            web_results = []
            if isinstance(response, dict):
                results = response.get("results", {})
                web_results = results.get("web", []) if isinstance(results, dict) else []
            elif hasattr(response, '__dict__'):
                # If it's an object, try to convert to dict
                response_dict = response.__dict__
                results = response_dict.get("results", {}) if isinstance(response_dict, dict) else {}
                web_results = results.get("web", []) if isinstance(results, dict) else []
            
            if not web_results:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "sources": []
                }
            
            sources = [r.get("url", "") for r in web_results[:5] if isinstance(r, dict) and r.get("url")]
            # Format results for LLM analysis
            formatted_results = []
            for r in web_results[:5]:
                if isinstance(r, dict):
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("description", r.get("snippet", ""))[:500],
                        "url": r.get("url", "")
                    })
            return await self._analyze_with_llm(fact.claim, formatted_results, sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_duckduckgo(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using DuckDuckGo Instant Answer API (completely free, no API key needed)"""
        from urllib.parse import quote
        
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # DuckDuckGo Instant Answer API — add t=h_ param and proper headers
            response = await client.get(
                f"https://api.duckduckgo.com/?q={quote(fact.claim)}&format=json&no_html=1&skip_disambig=1&t=h_",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "BariseFactVerifier/1.0"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"DuckDuckGo API error: {response.status_code}")
            
            # DDG sometimes returns JS/JSONP even with format=json; guard against empty body
            text = response.text.strip()
            if not text or text.startswith("<"):
                raise Exception("DuckDuckGo returned non-JSON response")
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                # Try to extract JSON from JSONP wrapper if present
                text = text.lstrip("callback(")  # type: ignore
                text = text.rstrip(");")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise Exception("DuckDuckGo returned unparseable JSON")
            
            # Extract relevant information
            results = []
            sources = []
            
            # Abstract from Wikipedia/other sources
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", ""),
                    "snippet": data.get("Abstract", ""),
                    "url": data.get("AbstractURL", "")
                })
                if data.get("AbstractURL"):
                    sources.append(data.get("AbstractURL"))
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
                    if topic.get("FirstURL"):
                        sources.append(topic.get("FirstURL"))
            
            if not results:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "sources": []
                }
            
            return await self._analyze_with_llm(fact.claim, results, sources)
    
    async def _verify_with_jina(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using Jina Reader search with key pool rotation"""
        pool = get_pool("jina", settings.jina_keys)
        if pool.empty:
            raise ValueError("No Jina API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available Jina API key")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"https://s.jina.ai/{fact.claim}",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Accept": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"Jina API error: {response.status_code}")
                
                await pool.report_success(key)
                data = response.json()
                results = data.get("data", []) if isinstance(data, dict) else []
                
                if not results:
                    return {
                        "verified": False,
                        "confidence": 0.0,
                        "sources": []
                    }
                
                sources = [r.get("url", "") for r in results[:5] if r.get("url")]
                return await self._analyze_with_llm(fact.claim, results[:5], sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_scrape_do(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using scrape.do (free tier available)"""
        if not settings.SCRAPE_DO_API_KEY:
            raise ValueError("No scrape.do API key available")
        
        from urllib.parse import quote
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # scrape.do search endpoint
            response = await client.get(
                f"https://api.scrape.do?token={settings.SCRAPE_DO_API_KEY}&url={quote(fact.claim)}"
            )
            
            if response.status_code != 200:
                raise Exception(f"scrape.do API error: {response.status_code}")
            
            data = response.json()
            
            # scrape.do returns scraped content, use it for verification
            content = data.get("content", "") or data.get("body", "")
            
            if not content:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Use LLM to analyze scraped content
            return await self._analyze_with_llm(
                fact.claim, 
                [{"snippet": content[:2000]}], 
                [data.get("url", "scraped_content")]
            )
    
    async def _verify_with_serper(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using Serper API with key pool rotation"""
        pool = get_pool("serper", settings.serper_keys)
        if pool.empty:
            raise ValueError("No Serper API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available Serper API key")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    json={
                        "q": fact.claim,
                        "num": 5
                    },
                    headers={
                        "X-API-KEY": key,
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"Serper API error: {response.status_code}")
                
                await pool.report_success(key)
                data = response.json()
                
                if not data.get("organic"):
                    return {
                        "verified": False,
                        "confidence": 0.0,
                        "sources": []
                    }
                
                sources = [r.get("link", "") for r in data.get("organic", [])[:5]]
                return await self._analyze_with_llm(fact.claim, data.get("organic", [])[:5], sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_exa(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using Exa API with key pool rotation"""
        pool = get_pool("exa", settings.exa_keys)
        if pool.empty:
            raise ValueError("No Exa API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available Exa API key")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.exa.ai/search",
                    json={
                        "query": fact.claim,
                        "numResults": 5,
                        "useAutoprompt": True
                    },
                    headers={
                        "x-api-key": key,
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"Exa API error: {response.status_code}")
                
                await pool.report_success(key)
                data = response.json()
                
                if not data.get("results"):
                    return {
                        "verified": False,
                        "confidence": 0.0,
                        "sources": []
                    }
                
                sources = [r.get("url", "") for r in data.get("results", [])]
                return await self._analyze_with_llm(fact.claim, data.get("results", [])[:5], sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_tavily(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using Tavily SDK with key pool rotation"""
        # Validate claim
        if not fact.claim or not fact.claim.strip():
            return {
                "verified": False,
                "confidence": 0.0,
                "sources": []
            }
        
        pool = get_pool("tavily", settings.tavily_keys)
        if pool.empty:
            raise ValueError("No Tavily API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available Tavily API key")
        
        try:
            from tavily import AsyncTavilyClient
            
            # Use async SDK
            tavily_client = AsyncTavilyClient(api_key=key)
            response = await tavily_client.search(
                query=fact.claim.strip(),
                search_depth="basic",
                max_results=5
            )
            
            await pool.report_success(key)
            
            if not response.get("results"):
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "sources": []
                }
            
            sources = [r.get("url", "") for r in response.get("results", [])]
            formatted_results = [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:500],
                    "url": r.get("url", "")
                }
                for r in response.get("results", [])[:5]
            ]
            return await self._analyze_with_llm(fact.claim, formatted_results, sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
    
    async def _verify_with_firecrawl(self, fact: Fact) -> Dict[str, Any]:
        """Verify fact using Firecrawl API with key pool rotation"""
        pool = get_pool("firecrawl", settings.firecrawl_keys)
        if pool.empty:
            raise ValueError("No Firecrawl API keys available")
        
        key = await pool.acquire()
        if not key:
            raise ValueError("No available Firecrawl API key")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.firecrawl.dev/v1/search",
                    json={
                        "query": fact.claim,
                        "limit": 5
                    },
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    await pool.report_failure(key, response.status_code)
                    raise Exception(f"Firecrawl API error: {response.status_code}")
                
                await pool.report_success(key)
                data = response.json()
                
                if not data.get("data"):
                    return {
                        "verified": False,
                        "confidence": 0.0,
                        "sources": []
                    }
                
                sources = [r.get("metadata", {}).get("sourceURL", "") for r in data.get("data", [])]
                return await self._analyze_with_llm(fact.claim, data.get("data", [])[:5], sources)
        except Exception as e:
            await pool.report_failure(key, 0)
            raise e
