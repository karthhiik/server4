"""
ProductHunt API integration for product launch traction data.
Uses the ProductHunt GraphQL API v2.
"""

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class ProductHuntEngine:
    """Fetches product launch data from ProductHunt GraphQL API."""

    GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

    @staticmethod
    def _headers() -> dict:
        return {
            "Authorization": f"Bearer {settings.PRODUCTHUNT_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    async def _graphql_query(query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against ProductHunt API."""
        if not settings.PRODUCTHUNT_API_KEY:
            raise ConnectionError("ProductHunt not configured")

        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                ProductHuntEngine.GRAPHQL_URL,
                json=payload,
                headers=ProductHuntEngine._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
            raise ValueError(f"ProductHunt GraphQL error: {error_msg}")

        return data.get("data", {})

    @staticmethod
    async def search_products(query: str, max_results: int = 5) -> list[dict]:
        """Search for products on ProductHunt.

        Uses GraphQL API with Bearer token auth.
        Returns: [{name, tagline, votes_count, url, topics, created_at}]
        """
        gql = """
        query SearchProducts($query: String!, $first: Int!) {
            posts(order: VOTES, search: $query, first: $first) {
                edges {
                    node {
                        id
                        name
                        tagline
                        votesCount
                        url
                        website
                        createdAt
                        topics(first: 5) {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = await ProductHuntEngine._graphql_query(
                gql, {"query": query, "first": min(max_results, 20)}
            )

            posts = data.get("posts", {}).get("edges", [])
            results = []
            for edge in posts:
                node = edge.get("node", {})
                topics = [
                    t["node"]["name"]
                    for t in node.get("topics", {}).get("edges", [])
                ]
                results.append({
                    "name": node.get("name", ""),
                    "tagline": node.get("tagline", ""),
                    "votes_count": node.get("votesCount", 0),
                    "url": node.get("url", ""),
                    "website": node.get("website", ""),
                    "topics": topics,
                    "created_at": node.get("createdAt", ""),
                    "provider": "producthunt",
                })
            return results
        except Exception as e:
            logger.warning("producthunt_search_failed", query=query[:50], error=str(e))
            return []

    @staticmethod
    async def get_product_details(slug: str) -> dict:
        """Get detailed product info by slug.

        Returns: name, tagline, description, votes, makers, topics, media.
        """
        gql = """
        query GetProduct($slug: String!) {
            post(slug: $slug) {
                id
                name
                tagline
                description
                votesCount
                commentsCount
                url
                website
                createdAt
                makers {
                    name
                    username
                }
                topics(first: 10) {
                    edges {
                        node {
                            name
                        }
                    }
                }
                media {
                    type
                    url
                }
            }
        }
        """
        try:
            data = await ProductHuntEngine._graphql_query(gql, {"slug": slug})

            post = data.get("post")
            if not post:
                return {"slug": slug, "error": "Product not found", "provider": "producthunt"}

            topics = [
                t["node"]["name"]
                for t in post.get("topics", {}).get("edges", [])
            ]
            makers = [
                {"name": m.get("name", ""), "username": m.get("username", "")}
                for m in post.get("makers", [])
            ]
            media = [
                {"type": m.get("type", ""), "url": m.get("url", "")}
                for m in post.get("media", [])
            ]

            return {
                "name": post.get("name", ""),
                "tagline": post.get("tagline", ""),
                "description": (post.get("description") or "")[:500],
                "votes_count": post.get("votesCount", 0),
                "comments_count": post.get("commentsCount", 0),
                "url": post.get("url", ""),
                "website": post.get("website", ""),
                "created_at": post.get("createdAt", ""),
                "makers": makers,
                "topics": topics,
                "media": media[:3],
                "provider": "producthunt",
            }
        except Exception as e:
            logger.warning("producthunt_details_failed", slug=slug, error=str(e))
            return {"slug": slug, "error": str(e), "provider": "producthunt"}

    @staticmethod
    async def get_trending(max_results: int = 10) -> list[dict]:
        """Get today's trending products.

        Fetches the newest products sorted by votes (highest first).
        """
        gql = """
        query TrendingProducts($first: Int!) {
            posts(order: VOTES, first: $first) {
                edges {
                    node {
                        id
                        name
                        tagline
                        votesCount
                        url
                        website
                        createdAt
                        topics(first: 3) {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = await ProductHuntEngine._graphql_query(
                gql, {"first": min(max_results, 20)}
            )

            posts = data.get("posts", {}).get("edges", [])
            results = []
            for edge in posts:
                node = edge.get("node", {})
                topics = [
                    t["node"]["name"]
                    for t in node.get("topics", {}).get("edges", [])
                ]
                results.append({
                    "name": node.get("name", ""),
                    "tagline": node.get("tagline", ""),
                    "votes_count": node.get("votesCount", 0),
                    "url": node.get("url", ""),
                    "website": node.get("website", ""),
                    "topics": topics,
                    "created_at": node.get("createdAt", ""),
                    "provider": "producthunt",
                })
            return results
        except Exception as e:
            logger.warning("producthunt_trending_failed", error=str(e))
            return []
