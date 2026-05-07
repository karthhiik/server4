"""MongoDB persistence for deck runs, evidence, and generation results."""

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.mcp.brain_mcp.research.models import (
    FactPacket,
    SlideContentContract,
    SlideEvidenceBundle,
)

logger = logging.getLogger(__name__)


class EvidenceStore:
    """MongoDB persistence layer for deck generation results."""

    COLLECTION = "deck_runs"
    EVIDENCE_COLLECTION = "deck_evidence"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collection = db[self.COLLECTION]
        self._evidence = db[self.EVIDENCE_COLLECTION]

    async def save_deck_run(self, deck_id: str, user_id: str, data: dict) -> None:
        """Save or update a deck run."""
        data.update(
            {
                "deck_id": deck_id,
                "user_id": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if "created_at" not in data:
            data["created_at"] = datetime.now(timezone.utc).isoformat()

        await self._collection.update_one(
            {"deck_id": deck_id},
            {"$set": data, "$setOnInsert": {"created_at": data["created_at"]}},
            upsert=True,
        )
        logger.info("Saved deck run %s for user %s", deck_id, user_id)

    async def get_deck_run(self, deck_id: str) -> Optional[dict]:
        """Get a deck run by ID."""
        doc = await self._collection.find_one({"deck_id": deck_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def get_user_runs(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get recent deck runs for a user, newest first."""
        cursor = (
            self._collection.find(
                {"user_id": user_id},
                {
                    "_id": 0,
                    "deck_id": 1,
                    "status": 1,
                    "topic": 1,
                    "style": 1,
                    "budget_mode": 1,
                    "total_slides_generated": 1,
                    "total_time_ms": 1,
                    "created_at": 1,
                    "completed_at": 1,
                    "errors": 1,
                },
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results

    async def update_status(
        self, deck_id: str, status: str, error: Optional[str] = None
    ) -> None:
        """Update deck run status."""
        update: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error is not None:
            update["error"] = error
        if status in ("completed", "failed", "partial"):
            update["completed_at"] = datetime.now(timezone.utc).isoformat()

        await self._collection.update_one(
            {"deck_id": deck_id}, {"$set": update}
        )

    async def save_contracts(
        self, deck_id: str, contracts: list[SlideContentContract]
    ) -> None:
        """Save slide content contracts to the deck run."""
        serialized = [c.to_dict() for c in contracts]
        await self._collection.update_one(
            {"deck_id": deck_id},
            {
                "$set": {
                    "contracts": serialized,
                    "total_slides_generated": len(contracts),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        logger.info(
            "Saved %d contracts for deck %s", len(contracts), deck_id
        )

    async def get_contracts(self, deck_id: str) -> list[dict]:
        """Get slide content contracts for a deck."""
        doc = await self._collection.find_one(
            {"deck_id": deck_id}, {"contracts": 1}
        )
        if not doc:
            return []
        return doc.get("contracts", [])

    async def save_evidence(
        self, deck_id: str, packets: list[FactPacket]
    ) -> None:
        """Save evidence packets in a separate collection for fast retrieval."""
        if not packets:
            return

        docs = []
        for pkt in packets:
            doc = pkt.to_dict()
            doc["deck_id"] = deck_id
            doc["stored_at"] = datetime.now(timezone.utc).isoformat()
            docs.append(doc)

        # Remove old evidence for this deck then insert fresh
        await self._evidence.delete_many({"deck_id": deck_id})
        await self._evidence.insert_many(docs)
        logger.info(
            "Saved %d evidence packets for deck %s", len(docs), deck_id
        )

    async def get_evidence(
        self, deck_id: str, slide_id: Optional[str] = None
    ) -> list[dict]:
        """Get evidence packets, optionally filtered by slide_id."""
        query: dict = {"deck_id": deck_id}
        if slide_id:
            query[f"slide_relevance.{slide_id}"] = {"$exists": True}

        cursor = self._evidence.find(query, {"_id": 0})
        results = []
        async for doc in cursor:
            results.append(doc)
        return results

    async def save_bundle(
        self, deck_id: str, bundle: SlideEvidenceBundle
    ) -> None:
        """Save a slide evidence bundle within the deck run."""
        await self._collection.update_one(
            {"deck_id": deck_id},
            {
                "$push": {
                    "evidence_bundles": bundle.to_dict(),
                }
            },
        )

    async def delete_deck_run(self, deck_id: str) -> bool:
        """Delete a deck run and its evidence."""
        result = await self._collection.delete_one({"deck_id": deck_id})
        await self._evidence.delete_many({"deck_id": deck_id})
        return result.deleted_count > 0
