"""
Social data engine — Reddit, GitHub, YouTube, ProductHunt.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class SocialEngine:
    """Fetches social signals from Reddit, GitHub, YouTube, ProductHunt."""

    async def search_reddit(self, query: str, max_results: int = 5) -> list[dict]:
        if not (settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET):
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get OAuth token
                auth_resp = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data={"grant_type": "client_credentials"},
                    auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
                    headers={"User-Agent": settings.REDDIT_USER_AGENT},
                )
                if auth_resp.status_code != 200:
                    return []
                token = auth_resp.json().get("access_token")

                # Search
                resp = await client.get(
                    "https://oauth.reddit.com/search",
                    params={"q": query, "sort": "relevance", "limit": max_results, "type": "link"},
                    headers={"Authorization": f"Bearer {token}", "User-Agent": settings.REDDIT_USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()

            posts = data.get("data", {}).get("children", [])
            return [
                {
                    "title": p["data"].get("title", ""),
                    "subreddit": p["data"].get("subreddit", ""),
                    "score": p["data"].get("score", 0),
                    "url": f"https://reddit.com{p['data'].get('permalink', '')}",
                    "num_comments": p["data"].get("num_comments", 0),
                }
                for p in posts[:max_results]
            ]
        except Exception as e:
            logger.warning("reddit_search_failed", error=str(e))
            return []

    async def search_github(self, query: str, max_results: int = 5) -> list[dict]:
        if not settings.GITHUB_TOKEN:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "per_page": max_results},
                    headers={"Authorization": f"token {settings.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
                )
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "name": r.get("full_name", ""),
                    "description": (r.get("description") or "")[:200],
                    "stars": r.get("stargazers_count", 0),
                    "url": r.get("html_url", ""),
                    "language": r.get("language", ""),
                }
                for r in data.get("items", [])[:max_results]
            ]
        except Exception as e:
            logger.warning("github_search_failed", error=str(e))
            return []

    async def search_youtube(self, query: str, max_results: int = 5) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "q": query,
                        "part": "snippet",
                        "type": "video",
                        "maxResults": max_results,
                        "key": settings.YOUTUBE_API_KEY,
                        "order": "relevance",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "title": item["snippet"].get("title", ""),
                    "channel": item["snippet"].get("channelTitle", ""),
                    "url": f"https://youtube.com/watch?v={item['id'].get('videoId', '')}",
                    "published": item["snippet"].get("publishedAt", ""),
                }
                for item in data.get("items", [])[:max_results]
            ]
        except Exception as e:
            logger.warning("youtube_search_failed", error=str(e))
            return []
