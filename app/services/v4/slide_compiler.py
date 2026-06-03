"""
Slide compiler for Barise v4 presentation backend.

Compiles raw slide data into production-ready CompiledSlide objects with layout_type
(never kit_jsx) and validated content.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.v4 import CompiledSlide, ResolvedDesignTokens, SlideContent
from app.services.v4.layout_selector import select_layout, validate_layout_compatibility


class SlideCompiler:
    """Compiles slides into final, renderable format."""

    def __init__(self, design_tokens: ResolvedDesignTokens):
        """
        Initialize compiler with design tokens.

        Args:
            design_tokens: ResolvedDesignTokens for the deck
        """
        self.design_tokens = design_tokens

    def compile_slide(
        self,
        slide_index: int,
        intent: str,
        content: SlideContent,
        slide_id: Optional[str] = None,
    ) -> CompiledSlide:
        """
        Compile a single slide into production-ready format.

        Args:
            slide_index: 0-based slide index in deck
            intent: Slide intent (cover, problem, solution, etc.)
            content: SlideContent with headline, blocks, nodes
            slide_id: Optional custom slide ID (generated if None)

        Returns:
            CompiledSlide with layout_type, content, and all metadata
        """
        # Select layout based on content and intent
        layout_type = select_layout(content, intent)

        # Ensure content structure matches layout requirements
        content = validate_layout_compatibility(content, layout_type)

        # Generate slide ID if not provided
        if not slide_id:
            slide_id = f"slide_{slide_index}"

        # Create compiled slide with all fields
        compiled = CompiledSlide(
            slide_id=slide_id,
            slide_no=slide_index + 1,
            layout_type=layout_type,
            intent=intent,
            content=content,
            design_tokens=self.design_tokens,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        return compiled

    def compile_deck(
        self,
        slides_data: List[Dict[str, Any]],
        deck_tokens: ResolvedDesignTokens,
    ) -> List[CompiledSlide]:
        """
        Compile all slides in a deck.

        Args:
            slides_data: List of raw slide dicts with content, intent, optional design_tokens
            deck_tokens: Default ResolvedDesignTokens for the deck

        Returns:
            List of CompiledSlide objects
        """
        compiled_slides = []

        for slide_index, slide_data in enumerate(slides_data):
            # Extract content from slide data
            content_data = slide_data.get("content", {})
            content = SlideContent(**content_data)

            # Extract intent (default to "content" if not specified)
            intent = slide_data.get("intent", "content")

            # Use slide-specific tokens or deck tokens
            tokens = slide_data.get("design_tokens") or deck_tokens
            if isinstance(tokens, dict):
                tokens = ResolvedDesignTokens(**tokens)

            # Compile this slide
            compiler = SlideCompiler(tokens)
            compiled_slide = compiler.compile_slide(
                slide_index=slide_index,
                intent=intent,
                content=content,
                slide_id=slide_data.get("slide_id"),
            )

            compiled_slides.append(compiled_slide)

        return compiled_slides
