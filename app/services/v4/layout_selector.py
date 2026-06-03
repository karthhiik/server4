"""
Content-aware layout selector for Barise v4 presentation backend.

Intelligently assigns layout types based on content and intent.
CRITICAL: Never assigns process_flow to vague content.
"""

import re
import uuid
from typing import List, Optional

from app.models.v4 import (
    BodyBlock,
    ChartBlock,
    FlowNode,
    MediaBlock,
    MetricBlock,
    SlideContent,
    TextBlock,
)


# ============================================================================
# DETECTION HELPERS
# ============================================================================


def _count_metrics(blocks: Optional[List[BodyBlock]]) -> int:
    """Count MetricBlock instances in body_blocks."""
    if not blocks:
        return 0
    return sum(1 for block in blocks if isinstance(block, MetricBlock))


def _has_chart(blocks: Optional[List[BodyBlock]]) -> bool:
    """Check if any block is ChartBlock."""
    if not blocks:
        return False
    return any(isinstance(block, ChartBlock) for block in blocks)


def _has_media(blocks: Optional[List[BodyBlock]]) -> bool:
    """Check if any block is MediaBlock."""
    if not blocks:
        return False
    return any(isinstance(block, MediaBlock) for block in blocks)


def _count_blocks(blocks: Optional[List[BodyBlock]]) -> int:
    """Count total body blocks."""
    return len(blocks) if blocks else 0


def _total_chars(blocks: Optional[List[BodyBlock]]) -> int:
    """Sum character count across all blocks."""
    if not blocks:
        return 0

    total = 0
    for block in blocks:
        if isinstance(block, TextBlock):
            if block.headline:
                total += len(block.headline)
            total += len(block.text)
        elif isinstance(block, MetricBlock):
            total += len(block.value) + len(block.label)
            if block.delta:
                total += len(block.delta)
        elif isinstance(block, ChartBlock):
            total += len(str(block.data))
        elif isinstance(block, MediaBlock):
            if block.caption:
                total += len(block.caption)
    return total


def _has_step_keywords(text: str) -> bool:
    """Detect step/process keywords in text."""
    pattern = r"\b(step|phase|stage|input|output|process|workflow|pipeline|sequence|flow|chain)\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def _has_flow_verbs(text: str) -> bool:
    """Detect flow/transformation verbs in text."""
    pattern = r"\b(feeds? into|transforms?|converts?|routes?|authenticates?|verifies?|processes?|generates?|outputs?)\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def _extract_all_text(content: SlideContent) -> str:
    """Extract all text from content for keyword matching."""
    text_parts = []

    if content.headline:
        text_parts.append(content.headline)
    if content.subhead:
        text_parts.append(content.subhead)

    if content.body_blocks:
        for block in content.body_blocks:
            if isinstance(block, TextBlock):
                if block.headline:
                    text_parts.append(block.headline)
                text_parts.append(block.text)
            elif isinstance(block, MetricBlock):
                text_parts.append(block.label)
            elif isinstance(block, QuoteBlock):
                text_parts.append(block.quote)

    return " ".join(text_parts)


# ============================================================================
# LAYOUT SELECTION ENGINE
# ============================================================================


def select_layout(content: SlideContent, intent: str) -> str:
    """
    Content-aware layout selector with priority-based rules.

    Args:
        content: SlideContent with blocks and nodes
        intent: Slide intent (cover, title, problem, solution, etc.)

    Returns:
        layout_type string (hero, stat_hero, split, bento, etc.)
    """
    metric_count = _count_metrics(content.body_blocks)
    block_count = _count_blocks(content.body_blocks)
    total_chars = _total_chars(content.body_blocks)
    has_chart = _has_chart(content.body_blocks)
    has_media = _has_media(content.body_blocks)
    all_text = _extract_all_text(content)
    has_step_keywords = _has_step_keywords(all_text)
    has_flow_verbs = _has_flow_verbs(all_text)
    has_explicit_nodes = content.nodes is not None and len(content.nodes) >= 2

    # PRIORITY 1: Intent-based rules
    if intent in ["title", "cover", "intro"]:
        return "hero"

    # PRIORITY 2: Single metric focus
    if metric_count == 1 and block_count <= 2 and total_chars < 200:
        return "stat_hero"

    # PRIORITY 3: Multiple metrics
    if 2 <= metric_count <= 4 and total_chars < 400:
        return "metrics"

    # PRIORITY 4: Chart
    if has_chart:
        return "chart"

    # PRIORITY 5: Media-first
    if has_media and block_count <= 2:
        return "media_first"

    # PRIORITY 6: Quote/testimonial
    if intent in ["testimonial", "quote", "social_proof"]:
        return "quote"

    # PRIORITY 7: Comparison (problem/solution with exactly 2 blocks)
    if intent in ["problem", "solution", "comparison"] and block_count == 2:
        return "comparison"

    # PRIORITY 8: Process flow (CRITICAL: only if keywords present)
    if intent in ["solution", "process", "how_it_works"] and has_step_keywords and has_flow_verbs:
        if has_explicit_nodes and len(content.nodes) <= 6:
            return "process_flow"
        elif block_count <= 5:
            # Will be converted to nodes in validate_layout_compatibility
            return "process_flow"

    # PRIORITY 9: Timeline
    if intent in ["timeline", "roadmap", "history"] and block_count <= 5:
        return "timeline"

    # PRIORITY 10: Bento grid (3-6 blocks)
    if 3 <= block_count <= 6:
        return "bento"

    # PRIORITY 11: Feature grid (3-6 blocks, concise)
    if 3 <= block_count <= 6 and total_chars < 600:
        return "feature_grid"

    # DEFAULT: Split layout
    return "split"


# ============================================================================
# CONTENT TRANSFORMATION
# ============================================================================


def blocks_to_nodes(blocks: Optional[List[BodyBlock]]) -> List[FlowNode]:
    """
    Convert body blocks to flow nodes (max 6).

    Args:
        blocks: List of body blocks

    Returns:
        List of FlowNode objects with appropriate statuses
    """
    if not blocks:
        return []

    # Status cycle for variety
    statuses = ["input", "process", "output", "process", "output", "decision"]

    nodes = []
    for i, block in enumerate(blocks[:6]):  # Max 6 nodes
        status = statuses[i % len(statuses)]

        if isinstance(block, TextBlock):
            # Use headline as label if available, else first 40 chars of text
            label = block.headline if block.headline else block.text[:40].strip()
            description = block.text if block.headline else None
        elif isinstance(block, MetricBlock):
            label = block.label
            description = f"{block.value} {block.label}"
        else:
            label = f"Step {i + 1}"
            description = None

        node = FlowNode(
            id=str(uuid.uuid4()),
            label=label,
            description=description,
            status=status,
        )
        nodes.append(node)

    return nodes


def validate_layout_compatibility(
    content: SlideContent, layout_type: str
) -> SlideContent:
    """
    Ensure content structure matches layout requirements.

    Args:
        content: Original SlideContent
        layout_type: Selected layout type

    Returns:
        Modified SlideContent with layout-compatible structure
    """
    # Process flow: convert blocks to nodes if needed
    if layout_type == "process_flow":
        if not content.nodes:
            content.nodes = blocks_to_nodes(content.body_blocks)
            content.body_blocks = None

    # Metrics/stat_hero: ensure at least one metric block
    if layout_type in ["metrics", "stat_hero"]:
        if content.body_blocks is None:
            content.body_blocks = []

        has_metric = any(isinstance(b, MetricBlock) for b in content.body_blocks)
        if not has_metric:
            metric_block = MetricBlock(
                type="metric",
                value="TBD",
                label="Key Metric",
            )
            content.body_blocks.insert(0, metric_block)

    return content


# ============================================================================
# COMPATIBILITY CHECK (informational)
# ============================================================================


def get_layout_info(layout_type: str) -> dict:
    """
    Return layout-specific rendering info.

    Useful for frontend to understand constraints.
    """
    info_map = {
        "hero": {
            "max_blocks": None,
            "requires_nodes": False,
            "typical_intent": "cover, title, intro",
        },
        "stat_hero": {
            "max_blocks": 3,
            "requires_metrics": True,
            "requires_nodes": False,
        },
        "metrics": {
            "max_blocks": 4,
            "requires_metrics": True,
            "requires_nodes": False,
        },
        "chart": {
            "max_blocks": 1,
            "requires_chart": True,
            "requires_nodes": False,
        },
        "process_flow": {
            "max_nodes": 6,
            "requires_nodes": True,
            "requires_blocks": False,
        },
        "timeline": {
            "max_blocks": 5,
            "requires_nodes": False,
        },
        "bento": {
            "min_blocks": 3,
            "max_blocks": 6,
            "requires_nodes": False,
        },
        "feature_grid": {
            "min_blocks": 3,
            "max_blocks": 6,
            "requires_nodes": False,
        },
        "split": {
            "min_blocks": 1,
            "max_blocks": None,
            "requires_nodes": False,
        },
        "quote": {
            "requires_quote": True,
            "requires_nodes": False,
        },
        "comparison": {
            "blocks_required": 2,
            "requires_nodes": False,
        },
        "media_first": {
            "requires_media": True,
            "max_blocks": 2,
            "requires_nodes": False,
        },
    }

    return info_map.get(layout_type, {})
