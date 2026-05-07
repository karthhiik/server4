#!/usr/bin/env python
"""Reconstruct content_pipeline.py with correct content."""
import os

# The correct content_pipeline.py file
# Based on the project structure and error messages

content = '''"""
V4 Content Pipeline - Orchestrates the slide generation process.
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.v4.skeleton_planner import SkeletonPlanner
from app.services.v4.parallel_writer import ParallelWriter
from app.services.v4.slide_compiler import SlideCompiler
from app.services.v4.critic_engine import CriticEngine
from app.services.v4.model_router import ModelRouter

logger = logging.getLogger(__name__)


class ContentPipeline:
    """Main content pipeline for V4 slide generation."""
    
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.planner = SkeletonPlanner(model_router)
        self.writer = ParallelWriter(model_router)
        self.compiler = SlideCompiler()
        self.critic = CriticEngine(model_router)
        
    async def generate(
        self,
        project_id: str,
        user_query: str,
        research: Optional[Dict[str, Any]] = None,
        target_slide_count: Optional[int] = None,
        purpose: str = "custom",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate slides from user query.
        
        Args:
            project_id: Unique project identifier
            user_query: User's presentation request
            research: Optional research data
            target_slide_count: Desired number of slides
            purpose: Presentation purpose (investor_pitch, custom, etc.)
            
        Returns:
            Dict with slides and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Plan the skeleton
            logger.info(f"Starting content generation for project {project_id}")
            
            skeleton = await self.planner.plan(
                project_id=project_id,
                user_query=user_query,
                research=research,
                slide_count=target_slide_count,
                narrative_arc="investor_pitch" if purpose == "investor_pitch" else "custom",
            )
            
            if not skeleton or "slides" not in skeleton:
                raise ValueError("Planner failed to generate valid skeleton")
            
            logger.info(f"Skeleton planned: {len(skeleton.get('slides', []))} slides")
            
            # Step 2: Write slide content in parallel
            slides_data = await self.writer.write_all(
                skeleton=skeleton,
                research=research,
                purpose=purpose,
            )
            
            if not slides_data:
                raise ValueError("Writer failed to generate slide content")
            
            logger.info(f"Content written for {len(slides_data)} slides")
            
            # Step 3: Compile slides with design tokens
            compiled_slides = self.compiler.compile_all(
                slides_data=slides_data,
                theme=kwargs.get("theme", "modern"),
                purpose=purpose,
            )
            
            # Step 4: Quality check
            quality_score = await self.critic.evaluate(
                slides=compiled_slides,
                query=user_query,
                research=research,
            )
            
            logger.info(f"Quality score: {quality_score}")
            
            # Step 5: Return result
            result = {
                "slides": compiled_slides,
                "skeleton": skeleton,
                "metadata": {
                    "project_id": project_id,
                    "slide_count": len(compiled_slides),
                    "quality_score": quality_score,
                    "generation_time": time.time() - start_time,
                    "purpose": purpose,
                }
            }
            
            logger.info(f"Content generation completed in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}", exc_info=True)
            raise
    
    async def edit_slide(
        self,
        project_id: str,
        slide_id: str,
        edits: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Edit a specific slide."""
        try:
            updated_slide = await self.writer.edit_slide(
                slide_id=slide_id,
                edits=edits,
                context=context,
            )
            return updated_slide
        except Exception as e:
            logger.error(f"Slide edit failed: {e}", exc_info=True)
            raise
    
    async def regenerate_slide(
        self,
        project_id: str,
        slide_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Regenerate a specific slide."""
        try:
            new_slide = await self.writer.regenerate_slide(
                slide_id=slide_id,
                reason=reason,
                context=context,
            )
            return new_slide
        except Exception as e:
            logger.error(f"Slide regeneration failed: {e}", exc_info=True)
            raise
'''

filepath = 'app/services/v4/content_pipeline.py'
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Written {len(content)} bytes to {filepath}")

# Verify syntax
import py_compile
try:
    py_compile.compile(filepath, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check: FAILED - {e}")
