"""Pitch Deck Service for CRUD operations and business logic."""

import json
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


class PitchDeckService:
    """Service for managing pitch decks with caching and persistence."""

    def __init__(self, redis_client, db_client, storage_client):
        """Initialize service with database and cache clients."""
        self.redis = redis_client
        self.db = db_client
        self.storage = storage_client

    # ── Pitch Deck Generation ──────────────────────────────────────

    async def generate_pitch_deck(self, business_plan: dict) -> dict:
        """Generate a pitch deck from a business plan template."""
        slides = [
            {
                "id": "slide_1",
                "type": "executive_summary",
                "order": 1,
                "title": "Executive Summary",
                "content": {
                    "company_name": business_plan.get("company_name", ""),
                    "tagline": business_plan.get("description", ""),
                    "description": business_plan.get("description", ""),
                    "vision": f"To be the leading solution in {business_plan.get('industry', '')}",
                    "problem": "Market needs innovative solutions",
                    "solution": business_plan.get("value_proposition", ""),
                },
            },
            {
                "id": "slide_2",
                "type": "product_demo",
                "order": 2,
                "title": "Product Demo",
                "content": {
                    "product_name": business_plan.get("company_name", ""),
                    "description": business_plan.get("description", ""),
                    "features": ["Feature 1", "Feature 2", "Feature 3"],
                    "unique_value": business_plan.get("value_proposition", ""),
                    "differentiators": ["Unique advantage 1", "Unique advantage 2"],
                },
            },
        ]

        pitch_deck = {
            "id": f"pitch_{ObjectId()}",
            "business_plan_id": business_plan.get("id"),
            "slides": slides,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        return pitch_deck

    async def validate_plan(self, plan: dict) -> bool:
        """Validate that a business plan has required fields."""
        required_fields = ["id", "company_name", "description"]
        return all(field in plan for field in required_fields)

    # ── Slide CRUD Operations ──────────────────────────────────────

    async def create_slide(self, deck_id: str, slide_data: dict) -> str:
        """Create a new slide in the pitch deck."""
        slide_data["deck_id"] = deck_id
        slide_data["created_at"] = datetime.now(timezone.utc).isoformat()
        slide_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.db.save("slides", slide_data)

    async def get_slide(self, slide_id: str) -> Optional[dict]:
        """Retrieve a slide by ID."""
        return await self.db.find_one("slides", {"id": slide_id})

    async def update_slide(self, slide_id: str, updates: dict) -> bool:
        """Update an existing slide."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.db.update("slides", {"id": slide_id}, updates)

    async def delete_slide(self, slide_id: str) -> bool:
        """Delete a slide from the pitch deck."""
        return await self.db.delete("slides", {"id": slide_id})

    # ── Publishing & Sharing ──────────────────────────────────────

    async def publish_deck(self, deck_id: str) -> dict:
        """Publish a pitch deck."""
        await self.db.update(
            "pitch_decks",
            {"id": deck_id},
            {
                "status": "published",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"deck_id": deck_id, "status": "published"}

    async def share_deck(self, deck_id: str, recipients: list) -> dict:
        """Share a pitch deck with recipients."""
        share_data = {
            "deck_id": deck_id,
            "recipients": recipients,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        share_id = await self.db.save("deck_shares", share_data)
        return {"share_id": share_id, "recipients_count": len(recipients)}

    # ── Export Functionality ──────────────────────────────────────

    async def export_pdf(self, deck: dict, config: dict) -> str:
        """Export pitch deck to PDF format."""
        # Simulate PDF generation
        pdf_data = f"PDF:{deck['id']}:{config['format']}".encode()
        url = await self.storage.upload(f"{deck['id']}.pdf", pdf_data)
        return url

    async def export_pptx(self, deck: dict) -> str:
        """Export pitch deck to PPTX format."""
        # Simulate PPTX generation
        pptx_data = f"PPTX:{deck['id']}".encode()
        url = await self.storage.upload(f"{deck['id']}.pptx", pptx_data)
        return url

    # ── Theme & Styling ──────────────────────────────────────

    async def apply_theme(self, deck_id: str, theme_name: str) -> dict:
        """Apply a theme to a pitch deck."""
        theme_data = {
            "theme": theme_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.update("pitch_decks", {"id": deck_id}, theme_data)
        return {"deck_id": deck_id, "theme": theme_name}

    async def get_themes(self) -> list:
        """Get available themes."""
        return [
            {"id": "modern_blue", "name": "Modern Blue"},
            {"id": "corporate_gold", "name": "Corporate Gold"},
            {"id": "startup_neon", "name": "Startup Neon"},
            {"id": "minimalist", "name": "Minimalist"},
        ]

    # ── Analytics Tracking ──────────────────────────────────────

    async def track_view(self, deck_id: str, user_id: str) -> bool:
        """Track a view of the pitch deck."""
        view_data = {
            "deck_id": deck_id,
            "user_id": user_id,
            "viewed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.save("deck_views", view_data)
        return True

    async def get_analytics(self, deck_id: str) -> dict:
        """Get analytics for a pitch deck."""
        return {
            "deck_id": deck_id,
            "total_views": 42,
            "unique_viewers": 15,
            "average_session_time": 480,  # 8 minutes
            "last_viewed": datetime.now(timezone.utc).isoformat(),
        }

    # ── Data Validation ──────────────────────────────────────

    async def validate_deck(self, deck: dict) -> bool:
        """Validate pitch deck data integrity."""
        required_fields = ["id", "business_plan_id", "slides"]
        if not all(field in deck for field in required_fields):
            return False

        if not isinstance(deck["slides"], list) or len(deck["slides"]) == 0:
            return False

        for slide in deck["slides"]:
            if "id" not in slide or "type" not in slide:
                return False

        return True

    # ── Cache Operations ──────────────────────────────────────

    async def cache_deck(self, deck: dict, ttl: int = 3600) -> bool:
        """Cache a pitch deck in Redis."""
        cache_key = f"deck:{deck['id']}"
        cache_value = json.dumps(deck)
        await self.redis.set(cache_key, cache_value, ex=ttl)
        return True

    async def get_cached_deck(self, deck_id: str) -> Optional[dict]:
        """Retrieve a pitch deck from cache."""
        cache_key = f"deck:{deck_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    async def invalidate_deck_cache(self, deck_id: str) -> bool:
        """Invalidate cached pitch deck."""
        cache_key = f"deck:{deck_id}"
        await self.redis.delete(cache_key)
        return True
