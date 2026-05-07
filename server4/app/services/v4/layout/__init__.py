"""Deterministic layout intelligence for V4 slide compilation."""

from app.services.v4.layout.intent_engine import (
    LayoutCandidate,
    LayoutFeatures,
    extract_features,
    select_layout,
)
from app.services.v4.layout.library import LAYOUT_LIBRARY, LayoutSpec

__all__ = [
    "LAYOUT_LIBRARY",
    "LayoutCandidate",
    "LayoutFeatures",
    "LayoutSpec",
    "extract_features",
    "select_layout",
]