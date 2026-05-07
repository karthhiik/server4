"""
ChromaDB Evidence Store — Vector indexing for evidence reuse.

Stores FactPackets as embedded vectors in ChromaDB for:
- Cross-slide evidence retrieval
- Cross-deck evidence reuse (previous deck runs can inform new ones)
- Semantic similarity search for related evidence
"""

import asyncio
import json
import logging
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import (
    ClaimType,
    FactPacket,
    FreshnessClass,
    SlideKind,
    SourceType,
)
from app.services.chromadb_service import ChromaService

logger = logging.getLogger(__name__)

EVIDENCE_COLLECTION = "slide_evidence"


class ChromaDBEvidence:
    """ChromaDB-backed evidence store for semantic search and reuse."""

    def __init__(self, chroma_service: ChromaService) -> None:
        self._chroma = chroma_service
        self._collection_name = EVIDENCE_COLLECTION
        self._collection = self._ensure_collection()

    def _ensure_collection(self) -> Any:
        """Get or create the evidence collection."""
        try:
            from app.services.chromadb_service import _get_collection
            return _get_collection(self._collection_name)
        except Exception:
            logger.warning(
                "evidence_collection_init_deferred",
                collection=self._collection_name,
            )
            return None

    def _get_coll(self) -> Any:
        """Lazy accessor — initialize collection if not yet ready."""
        if self._collection is None:
            self._collection = self._ensure_collection()
        return self._collection

    async def index_fact_packet(self, packet: FactPacket, deck_id: str) -> None:
        """
        Index a FactPacket in ChromaDB for future retrieval.

        Text: claim + source_name
        Metadata: claim_type, source_type, freshness_class, confidence,
                  provider, deck_id, slide relevances
        """
        coll = self._get_coll()
        if coll is None:
            logger.error("evidence_collection_unavailable")
            return

        document = f"{packet.claim} — {packet.source_name}"
        if packet.raw_snippet:
            # Append snippet for richer embeddings, truncate to avoid bloat
            document += f" | {packet.raw_snippet[:500]}"

        # Build metadata — ChromaDB metadata values must be str, int, float, or bool
        metadata: dict[str, Any] = {
            "claim_type": packet.claim_type.value,
            "source_type": packet.source_type.value,
            "freshness_class": packet.freshness_class.value,
            "confidence": packet.confidence,
            "provider": packet.provider,
            "deck_id": deck_id,
            "source_name": packet.source_name,
            "extraction_method": packet.extraction_method,
            "cross_validated": packet.cross_validated,
        }
        if packet.numeric_value is not None:
            metadata["numeric_value"] = packet.numeric_value
        if packet.numeric_unit:
            metadata["numeric_unit"] = packet.numeric_unit
        if packet.date_published:
            metadata["date_published"] = packet.date_published
        if packet.source_url:
            metadata["source_url"] = packet.source_url

        # Encode slide_relevance as flat keys
        for slide_kind, score in packet.slide_relevance.items():
            metadata[f"rel_{slide_kind}"] = score

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: coll.upsert(
                    ids=[packet.id],
                    documents=[document],
                    metadatas=[metadata],
                ),
            )
            logger.debug(
                "evidence_indexed",
                packet_id=packet.id,
                deck_id=deck_id,
                claim_type=packet.claim_type.value,
            )
        except Exception:
            logger.exception(
                "evidence_index_failed",
                packet_id=packet.id,
                deck_id=deck_id,
            )

    async def index_batch(
        self, packets: list[FactPacket], deck_id: str
    ) -> None:
        """Batch index multiple FactPackets."""
        if not packets:
            return

        coll = self._get_coll()
        if coll is None:
            logger.error("evidence_collection_unavailable")
            return

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for packet in packets:
            doc = f"{packet.claim} — {packet.source_name}"
            if packet.raw_snippet:
                doc += f" | {packet.raw_snippet[:500]}"

            meta: dict[str, Any] = {
                "claim_type": packet.claim_type.value,
                "source_type": packet.source_type.value,
                "freshness_class": packet.freshness_class.value,
                "confidence": packet.confidence,
                "provider": packet.provider,
                "deck_id": deck_id,
                "source_name": packet.source_name,
                "extraction_method": packet.extraction_method,
                "cross_validated": packet.cross_validated,
            }
            if packet.numeric_value is not None:
                meta["numeric_value"] = packet.numeric_value
            if packet.numeric_unit:
                meta["numeric_unit"] = packet.numeric_unit
            if packet.date_published:
                meta["date_published"] = packet.date_published
            if packet.source_url:
                meta["source_url"] = packet.source_url
            for sk, score in packet.slide_relevance.items():
                meta[f"rel_{sk}"] = score

            ids.append(packet.id)
            documents.append(doc)
            metadatas.append(meta)

        # ChromaDB batch upsert (sync, run in executor)
        loop = asyncio.get_running_loop()
        # ChromaDB has a batch limit of ~5000; chunk if needed
        batch_size = 500
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            batch_ids = ids[start:end]
            batch_docs = documents[start:end]
            batch_metas = metadatas[start:end]
            try:
                await loop.run_in_executor(
                    None,
                    lambda _i=batch_ids, _d=batch_docs, _m=batch_metas: coll.upsert(
                        ids=_i,
                        documents=_d,
                        metadatas=_m,
                    ),
                )
            except Exception:
                logger.exception(
                    "evidence_batch_index_failed",
                    batch_start=start,
                    batch_size=len(batch_ids),
                    deck_id=deck_id,
                )

        logger.info(
            "evidence_batch_indexed",
            count=len(ids),
            deck_id=deck_id,
        )

    async def search_similar(
        self,
        query: str,
        slide_kind: Optional[SlideKind] = None,
        claim_type: Optional[ClaimType] = None,
        min_confidence: float = 0.5,
        n_results: int = 10,
        exclude_deck_id: Optional[str] = None,
    ) -> list[FactPacket]:
        """
        Search for similar evidence across all indexed decks.
        Supports filtering by slide_kind, claim_type, confidence.
        """
        coll = self._get_coll()
        if coll is None:
            return []

        # Build where filter
        conditions: list[dict[str, Any]] = []
        conditions.append({"confidence": {"$gte": min_confidence}})

        if claim_type is not None:
            conditions.append({"claim_type": {"$eq": claim_type.value}})

        if exclude_deck_id:
            conditions.append({"deck_id": {"$ne": exclude_deck_id}})

        if slide_kind is not None:
            # Filter by slide relevance key existing with non-zero score
            conditions.append({f"rel_{slide_kind.value}": {"$gt": 0.0}})

        where_filter: Optional[dict[str, Any]] = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        loop = asyncio.get_running_loop()
        try:
            kwargs: dict[str, Any] = {
                "query_texts": [query],
                "n_results": n_results,
            }
            if where_filter:
                kwargs["where"] = where_filter

            raw = await loop.run_in_executor(
                None, lambda: coll.query(**kwargs)
            )
        except Exception:
            logger.exception("evidence_search_failed", query=query[:100])
            return []

        return self._results_to_packets(raw)

    async def get_deck_evidence(self, deck_id: str) -> list[FactPacket]:
        """Get all evidence indexed for a specific deck."""
        coll = self._get_coll()
        if coll is None:
            return []

        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(
                None,
                lambda: coll.get(
                    where={"deck_id": {"$eq": deck_id}},
                    include=["documents", "metadatas"],
                ),
            )
        except Exception:
            logger.exception("get_deck_evidence_failed", deck_id=deck_id)
            return []

        return self._get_results_to_packets(raw)

    async def delete_deck_evidence(self, deck_id: str) -> None:
        """Remove all evidence for a deck (cleanup)."""
        coll = self._get_coll()
        if coll is None:
            return

        loop = asyncio.get_running_loop()
        try:
            # ChromaDB delete by where filter
            await loop.run_in_executor(
                None,
                lambda: coll.delete(
                    where={"deck_id": {"$eq": deck_id}},
                ),
            )
            logger.info("deck_evidence_deleted", deck_id=deck_id)
        except Exception:
            logger.exception("delete_deck_evidence_failed", deck_id=deck_id)

    # ── Internal helpers ──────────────────────────────────────

    def _results_to_packets(self, raw: dict[str, Any]) -> list[FactPacket]:
        """Convert ChromaDB query results to FactPackets."""
        packets: list[FactPacket] = []
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]

        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            doc = docs[i] if i < len(docs) else ""

            # Reconstruct claim from document
            claim = doc.split(" — ")[0] if " — " in doc else doc

            # Reconstruct slide_relevance from flat keys
            slide_rel: dict[str, float] = {}
            for key, val in meta.items():
                if key.startswith("rel_") and isinstance(val, (int, float)):
                    slide_rel[key[4:]] = float(val)

            try:
                packet = FactPacket(
                    id=doc_id,
                    claim=claim,
                    claim_type=ClaimType(meta.get("claim_type", "qualitative")),
                    source_url=meta.get("source_url"),
                    source_name=meta.get("source_name", "unknown"),
                    source_type=SourceType(
                        meta.get("source_type", "web_extracted")
                    ),
                    date_published=meta.get("date_published"),
                    date_retrieved=meta.get("date_retrieved", ""),
                    freshness_class=FreshnessClass(
                        meta.get("freshness_class", "undated")
                    ),
                    confidence=float(meta.get("confidence", 0.5)),
                    numeric_value=meta.get("numeric_value"),
                    numeric_unit=meta.get("numeric_unit"),
                    extraction_method=meta.get(
                        "extraction_method", "llm_extracted"
                    ),
                    provider=meta.get("provider", "chromadb_recall"),
                    cross_validated=bool(meta.get("cross_validated", False)),
                    slide_relevance=slide_rel,
                )
                packets.append(packet)
            except (ValueError, KeyError):
                logger.warning(
                    "packet_reconstruction_failed",
                    doc_id=doc_id,
                    exc_info=True,
                )

        return packets

    def _get_results_to_packets(self, raw: dict[str, Any]) -> list[FactPacket]:
        """Convert ChromaDB .get() results to FactPackets."""
        packets: list[FactPacket] = []
        ids = raw.get("ids", [])
        docs = raw.get("documents", [])
        metas = raw.get("metadatas", [])

        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            doc = docs[i] if i < len(docs) else ""

            claim = doc.split(" — ")[0] if " — " in doc else doc

            slide_rel: dict[str, float] = {}
            for key, val in meta.items():
                if key.startswith("rel_") and isinstance(val, (int, float)):
                    slide_rel[key[4:]] = float(val)

            try:
                packet = FactPacket(
                    id=doc_id,
                    claim=claim,
                    claim_type=ClaimType(meta.get("claim_type", "qualitative")),
                    source_url=meta.get("source_url"),
                    source_name=meta.get("source_name", "unknown"),
                    source_type=SourceType(
                        meta.get("source_type", "web_extracted")
                    ),
                    date_published=meta.get("date_published"),
                    date_retrieved=meta.get("date_retrieved", ""),
                    freshness_class=FreshnessClass(
                        meta.get("freshness_class", "undated")
                    ),
                    confidence=float(meta.get("confidence", 0.5)),
                    numeric_value=meta.get("numeric_value"),
                    numeric_unit=meta.get("numeric_unit"),
                    extraction_method=meta.get(
                        "extraction_method", "llm_extracted"
                    ),
                    provider=meta.get("provider", "chromadb_recall"),
                    cross_validated=bool(meta.get("cross_validated", False)),
                    slide_relevance=slide_rel,
                )
                packets.append(packet)
            except (ValueError, KeyError):
                logger.warning(
                    "packet_reconstruction_failed",
                    doc_id=doc_id,
                    exc_info=True,
                )

        return packets
