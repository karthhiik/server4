"""Semantic icon mapping for generated slide kits."""

from __future__ import annotations


ICON_SEMANTIC_MAP: dict[str, tuple[str, ...]] = {
    "growth": ("TrendingUp", "BarChart", "Rocket"),
    "security": ("Shield", "Lock", "Key"),
    "automation": ("Workflow", "Bot", "Zap"),
    "team": ("Users", "Network"),
    "cost": ("DollarSign", "Wallet", "Calculator"),
}


def icon_for(text: str) -> str:
    value = (text or "").lower()
    for keyword, icons in ICON_SEMANTIC_MAP.items():
        if keyword in value:
            return icons[0]
    if any(word in value for word in ("risk", "compliance", "trust")):
        return "Shield"
    if any(word in value for word in ("speed", "time", "fast")):
        return "Zap"
    if any(word in value for word in ("customer", "user", "market")):
        return "Users"
    return ""
