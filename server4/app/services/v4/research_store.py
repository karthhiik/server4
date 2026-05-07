"""
V4 Research Store — Chroma-backed semantic cache for research citations.

Purpose
-------
Research is expensive (external APIs, latency, cost). Once collected, citations
and extracted document chunks should be:
  1. Persisted to disk so re-generations don't hammer providers.
  2. Searchable by semantic similarity (not just exact-query lookup).
  3. Scoped per project so one user's research doesn't leak into another's deck.

Collection naming
-----------------
  `research_{project_id}`    — web/news citations for a project
  `docs_{project_id}`        — uploaded-document chunks for a project

Lazy init: the Chroma client and the BGE embedder both initialise on first use.
If either fails (e.g. chromadb not installed, HF model can't download), the
store degrades to an in-memory stub so the pipeline keeps working.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any, Optional

import structlog

from app.services.v4.embeddings import get_embedder

logger = structlog.get_logger(__name__)


_client = None
_client_lock = asyncio.Lock()


def _disable_chroma_product_telemetry() -> None:
    try:
        import posthog  # type: ignore

        posthog.disabled = True

        def _capture_noop(*args, **kwargs):
            return None

        posthog.capture = _capture_noop
    except Exception:
        return


async def _get_client():
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings as ChromaSettings  # type: ignore
        except ImportError:
            logger.warning("chroma_unavailable")
            return None
        _disable_chroma_product_telemetry()
        try:
            from app.config import settings
            path = Path(getattr(settings, "EMBEDDINGS_PATH", "") or "./.cache/embeddings") / "chroma"
        except Exception:
            path = Path("./.cache/embeddings/chroma")
        
        # Skip Chroma if path doesn't exist (no data persisted yet)
        if not path.exists():
            logger.info("chroma_client_skipped", path=str(path), reason="path_not_found")
            return None
        
        def _build():
            return chromadb.PersistentClient(
                path=str(path),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
            )

        _client = await asyncio.to_thread(_build)
        logger.info("chroma_client_ready", path=str(path))
        return _client


def _safe_collection_name(raw: str) -> str:
    # Chroma requires 3-63 chars, [a-zA-Z0-9._-] only
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in raw)[:48]
    return f"{safe}_{h}"


async def _get_collection(name: str):
    """Get collection if it exists, return None if not (avoids creating empty collections)."""
    client = await _get_client()
    if client is None:
        return None
    safe = _safe_collection_name(name)
    def _get():
        try:
            return client.get_collection(name=safe)
        except Exception:
            # Collection doesn't exist yet - no documents uploaded
            return None
    return await asyncio.to_thread(_get)


# ── Public API ────────────────────────────────────────────────────

async def persist_citations(project_id: str, citations: list[Any]) -> int:
    """Embed + persist research citations for a project.

    `citations` items must expose `.url`, `.title`, `.snippet`, `.source` (Citation dataclass).
    Returns number of items persisted (0 if Chroma unavailable).
    """
    if not citations:
        return 0
    coll = await _get_collection(f"research_{project_id}")
    if coll is None:
        return 0

    texts: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    for c in citations:
        url = getattr(c, "url", "") or ""
        title = getattr(c, "title", "") or ""
        snippet = getattr(c, "snippet", "") or ""
        source = getattr(c, "source", "") or ""
        if not (title or snippet):
            continue
        doc_id = hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()
        texts.append(f"{title}. {snippet}"[:2000])
        metas.append({"url": url[:500], "title": title[:300], "source": source[:30]})
        ids.append(doc_id)
    if not texts:
        return 0

    try:
        embedder = await get_embedder()
        vecs = await embedder.embed_many(texts)
    except Exception as e:
        logger.warning("persist_citations.embed_failed", error=str(e))
        return 0

    def _upsert():
        coll.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=vecs)
    try:
        await asyncio.to_thread(_upsert)
        logger.info("persist_citations.ok", project_id=project_id, n=len(ids))
        return len(ids)
    except Exception as e:
        logger.warning("persist_citations.upsert_failed", error=str(e))
        return 0


async def persist_document_chunks(
    project_id: str,
    doc_id: str,
    chunks: list[str],
    metadata: Optional[dict] = None,
) -> int:
    """Embed + persist chunked uploaded-document text for a project."""
    if not chunks:
        return 0
    coll = await _get_collection(f"docs_{project_id}")
    if coll is None:
        return 0
    base_meta = {"doc_id": doc_id[:120], **(metadata or {})}

    try:
        embedder = await get_embedder()
        vecs = await embedder.embed_many(chunks)
    except Exception as e:
        logger.warning("persist_doc_chunks.embed_failed", error=str(e))
        return 0

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metas = [dict(base_meta, chunk_index=i) for i in range(len(chunks))]

    def _upsert():
        coll.upsert(ids=ids, documents=chunks, metadatas=metas, embeddings=vecs)
    try:
        await asyncio.to_thread(_upsert)
        logger.info("persist_doc_chunks.ok", project_id=project_id, doc_id=doc_id, n=len(ids))
        return len(ids)
    except Exception as e:
        logger.warning("persist_doc_chunks.upsert_failed", error=str(e))
        return 0


async def query_research(project_id: str, query: str, k: int = 10) -> list[dict]:
    """Semantic search over research citations for a project."""
    return await _query(f"research_{project_id}", query, k)


async def query_docs(project_id: str, query: str, k: int = 10) -> list[dict]:
    """Semantic search over uploaded-document chunks for a project."""
    return await _query(f"docs_{project_id}", query, k)


async def _query(collection_name: str, query: str, k: int) -> list[dict]:
    coll = await _get_collection(collection_name)
    if coll is None or not query:
        return []
    try:
        embedder = await get_embedder()
        qvec = await embedder.embed_one(query)
    except Exception as e:
        logger.warning("research_store.query_embed_failed", error=str(e))
        return []

    def _q():
        return coll.query(query_embeddings=[qvec], n_results=min(k, 50))
    try:
        res = await asyncio.to_thread(_q)
    except Exception as e:
        logger.warning("research_store.query_failed", error=str(e))
        return []

    out: list[dict] = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({
            "text": doc,
            "metadata": meta or {},
            "score": float(1.0 - dist) if dist is not None else 0.0,
        })
    return out
