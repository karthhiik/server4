"""License-Governed Asset Registry for V5.5.

Tracks icon/image assets with license metadata. Supports free-tier providers:
- Lucide (MIT, 1500+)
- Tabler (MIT, 4000+)
- Iconify free sets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AssetRegistryEntry:
    asset_id: str           # e.g. "lucide:chart-up"
    provider: str           # e.g. "lucide"
    kind: str             # "icon" | "image" | "logo"
    license_type: str       # "MIT" | "CC-BY" | "proprietary"
    attribution_required: bool = False
    allowed_surfaces: list[str] = field(default_factory=lambda: ["editor", "present", "export"])
    static_svg: Optional[str] = None
    animated_lottie: Optional[str] = None
    url: Optional[str] = None

    def to_doc(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "provider": self.provider,
            "kind": self.kind,
            "license_type": self.license_type,
            "attribution_required": self.attribution_required,
            "allowed_surfaces": self.allowed_surfaces,
            "static_svg": self.static_svg,
            "animated_lottie": self.animated_lottie,
            "url": self.url,
        }


class AssetRegistry:
    """In-memory + MongoDB-backed asset registry."""

    FREE_ICON_PROVIDERS = {
        "lucide": {"license": "MIT", "attribution": False},
        "tabler": {"license": "MIT", "attribution": False},
        "heroicons": {"license": "MIT", "attribution": False},
        "mdi-light": {"license": "Apache-2.0", "attribution": False},
    }

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._cache: dict[str, AssetRegistryEntry] = {}

    def register(self, entry: AssetRegistryEntry) -> None:
        self._cache[entry.asset_id] = entry

    def lookup(self, asset_id: str) -> AssetRegistryEntry | None:
        """Lookup by asset_id. <10ms target."""
        return self._cache.get(asset_id)

    def is_allowed(self, asset_id: str, surface: str) -> bool:
        """Check if asset is licensed for a given surface (editor/present/export)."""
        entry = self.lookup(asset_id)
        if not entry:
            return False
        return surface in entry.allowed_surfaces

    def resolve_icon(self, iconify_id: str) -> AssetRegistryEntry:
        """Resolve an Iconify-style icon ID to a registry entry."""
        if ":" in iconify_id:
            provider, name = iconify_id.split(":", 1)
        else:
            provider, name = "lucide", iconify_id

        meta = self.FREE_ICON_PROVIDERS.get(provider, {"license": "unknown", "attribution": True})
        return AssetRegistryEntry(
            asset_id=f"{provider}:{name}",
            provider=provider,
            kind="icon",
            license_type=meta["license"],
            attribution_required=meta["attribution"],
            allowed_surfaces=["editor", "present", "export"],
        )

    def bulk_register_free_icons(self) -> int:
        """Pre-register known free icon providers. Returns count."""
        count = 0
        # Lucide common icons
        for name in ["target", "trending-up", "users", "zap", "shield", "chart-bar",
                     "lightbulb", "rocket", "globe", "clock", "check-circle", "x-circle",
                     "arrow-right", "chevron-right", "star", "heart", "lock"]:
            self.register(self.resolve_icon(f"lucide:{name}"))
            count += 1
        return count
