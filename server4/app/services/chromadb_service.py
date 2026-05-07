"""
ChromaDB Service — Vector database for presentation embeddings and RAG retrieval.

Provides persistent storage for:
- Presentation content embeddings (search similar decks)
- Slide skill examples (few-shot retrieval for the Code agent)
- Research data embeddings (Researcher agent RAG)
"""

from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Lazy import — chromadb is heavy
_chroma_client = None
_presentations_collection = None
_skills_collection = None
_research_collection = None


def _get_client():
    """Return a singleton PersistentClient, creating it on first call."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path="./data/chromadb")
        logger.info("chromadb_client_initialized", path="./data/chromadb")
    return _chroma_client


def _get_collection(name: str):
    """Get or create a ChromaDB collection by name."""
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


class ChromaService:
    """Vector database operations for the V7 slide system.

    Collections:
        presentations — full deck content for similarity search
        slide_skills  — Code Agent skill examples for few-shot DSL generation
        research_data — Researcher Agent RAG documents
    """

    def __init__(self) -> None:
        self._presentations = _get_collection("presentations")
        self._skills = _get_collection("slide_skills")
        self._research = _get_collection("research_data")
        logger.info("chromadb_service_ready")

    # ── presentations ─────────────────────────────────────────

    async def add_presentation(
        self,
        id: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Index a presentation's text content for similarity search."""
        meta = metadata or {}
        # ChromaDB is sync; run in executor to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._presentations.upsert(
                ids=[id],
                documents=[text],
                metadatas=[meta],
            ),
        )
        logger.debug("chromadb_presentation_indexed", id=id)

    async def search_similar(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Find presentations similar to the query text."""
        import asyncio
        loop = asyncio.get_running_loop()
        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        results = await loop.run_in_executor(
            None,
            lambda: self._presentations.query(**kwargs),
        )
        return self._format_results(results)

    async def delete_presentation(self, id: str) -> None:
        """Remove a presentation from the index."""
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: self._presentations.delete(ids=[id]),
        )
        logger.debug("chromadb_presentation_deleted", id=id)

    # ── slide skills ──────────────────────────────────────────

    async def add_skill_example(
        self,
        skill_name: str,
        version: int,
        example_dsl: str,
        quality_score: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Store a high-quality DSL example for few-shot Code Agent retrieval."""
        doc_id = f"{skill_name}_v{version}_{quality_score}"
        meta = {
            "skill_name": skill_name,
            "version": version,
            "quality_score": quality_score,
            **(metadata or {}),
        }
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._skills.upsert(
                ids=[doc_id],
                documents=[example_dsl],
                metadatas=[meta],
            ),
        )
        logger.debug("chromadb_skill_indexed", skill=skill_name, version=version)

    async def search_skill_examples(
        self,
        query: str,
        skill_name: Optional[str] = None,
        min_quality: int = 0,
        n_results: int = 3,
    ) -> list[dict[str, Any]]:
        """Retrieve similar DSL examples for few-shot prompting."""
        import asyncio
        loop = asyncio.get_running_loop()
        where_filter: Optional[dict[str, Any]] = None
        conditions: list[dict[str, Any]] = []
        if skill_name:
            conditions.append({"skill_name": {"$eq": skill_name}})
        if min_quality > 0:
            conditions.append({"quality_score": {"$gte": min_quality}})
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where_filter:
            kwargs["where"] = where_filter
        results = await loop.run_in_executor(
            None, lambda: self._skills.query(**kwargs),
        )
        return self._format_results(results)

    # ── research data ─────────────────────────────────────────

    async def add_research_document(
        self,
        id: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Index a research document for Researcher Agent RAG."""
        meta = metadata or {}
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._research.upsert(
                ids=[id],
                documents=[text],
                metadatas=[meta],
            ),
        )
        logger.debug("chromadb_research_indexed", id=id)

    async def search_research(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """RAG retrieval for research context."""
        import asyncio
        loop = asyncio.get_running_loop()
        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        results = await loop.run_in_executor(
            None, lambda: self._research.query(**kwargs),
        )
        return self._format_results(results)

    # ── helpers ────────────────────────────────────────────────

    @staticmethod
    def _format_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalise ChromaDB query results into a flat list of dicts."""
        items: list[dict[str, Any]] = []
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for i, doc_id in enumerate(ids):
            items.append({
                "id": doc_id,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": distances[i] if i < len(distances) else None,
            })
        return items

    async def collection_count(self, collection: str = "presentations") -> int:
        """Return the number of documents in a collection."""
        import asyncio
        loop = asyncio.get_running_loop()
        coll_map = {
            "presentations": self._presentations,
            "slide_skills": self._skills,
            "research_data": self._research,
        }
        coll = coll_map.get(collection)
        if coll is None:
            raise ValueError(f"Unknown collection: {collection}")
        count: int = await loop.run_in_executor(None, coll.count)
        return count
