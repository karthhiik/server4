"""
Template Engine - Slide Template Management
Handles template loading, selection, and rendering for slide generation.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger()


class TemplateEngine:
    """
    Template engine for slide generation.

    Handles:
    - Loading templates from MongoDB
    - Selecting appropriate templates based on criteria
    - Rendering templates with content
    - Template validation
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.get_collection("slide_templates")

    async def get_template(
        self,
        template_id: Optional[str] = None,
        category: Optional[str] = None,
        style: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID, category, or style.

        Args:
            template_id: Specific template ID
            category: Template category (pitch, sales, consulting, etc.)
            style: Visual style (modern, classic, minimal, etc.)

        Returns:
            Template data or None
        """
        query = {}
        if template_id:
            query["_id"] = template_id
        if category:
            query["category"] = category
        if style:
            query["style"] = style

        if not query:
            return None

        template = await self.collection.find_one(query)
        if template:
            template["id"] = str(template.pop("_id"))
        return template

    async def list_templates(
        self,
        category: Optional[str] = None,
        style: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        List available templates.
        """
        query = {}
        if category:
            query["category"] = category
        if style:
            query["style"] = style

        cursor = self.collection.find(query).limit(limit)
        templates = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            templates.append(doc)

        return templates

    async def get_layout_spec(self, layout_type: str) -> Dict[str, Any]:
        """
        Get layout specification for a layout type.

        Args:
            layout_type: Layout type (title-hero, two-column, bullets, etc.)

        Returns:
            Layout specification
        """
        layout_specs = {
            "title-hero": {
                "type": "title",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "subtitle", "type": "text", "required": False},
                ],
            },
            "two-column": {
                "type": "split",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "left", "type": "content", "required": True},
                    {"id": "right", "type": "content", "required": True},
                ],
            },
            "bullets": {
                "type": "list",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {
                        "id": "bullets",
                        "type": "bullet_list",
                        "required": True,
                        "min": 3,
                        "max": 7,
                    },
                ],
            },
            "bullets-with-image": {
                "type": "mixed",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "content", "type": "content", "required": True},
                    {"id": "image", "type": "image", "required": True},
                ],
            },
            "chart": {
                "type": "data",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "chart", "type": "chart", "required": True},
                    {"id": "caption", "type": "text", "required": False},
                ],
            },
            "team-grid": {
                "type": "grid",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "members", "type": "team_list", "required": True},
                ],
            },
            "comparison": {
                "type": "comparison",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "left", "type": "content", "required": True},
                    {"id": "right", "type": "content", "required": True},
                ],
            },
            "kpi-dashboard": {
                "type": "metrics",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "kpis", "type": "kpi_cards", "required": True},
                ],
            },
            "timeline": {
                "type": "sequence",
                "elements": [
                    {"id": "title", "type": "heading", "required": True},
                    {"id": "events", "type": "timeline", "required": True},
                ],
            },
            "quote": {
                "type": "quote",
                "elements": [
                    {"id": "quote", "type": "quote_text", "required": True},
                    {"id": "attribution", "type": "text", "required": True},
                ],
            },
        }

        return layout_specs.get(layout_type, layout_specs.get("bullets"))

    def validate_slide_content(
        self, layout_type: str, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that content matches layout requirements.

        Returns:
            Validation result with valid flag and errors
        """
        layout_spec = self.get_layout_spec(layout_type)
        errors = []

        for element in layout_spec.get("elements", []):
            element_id = element.get("id")
            required = element.get("required", False)
            element_type = element.get("type")

            # Check required elements
            if required and element_id not in content:
                errors.append(f"Missing required element: {element_id}")
                continue

            # Validate min/max for lists
            if element_type == "bullet_list" and element_id in content:
                items = content[element_id]
                min_items = element.get("min", 0)
                max_items = element.get("max", 50)

                if isinstance(items, list):
                    if len(items) < min_items:
                        errors.append(
                            f"{element_id}: minimum {min_items} items required"
                        )
                    if len(items) > max_items:
                        errors.append(
                            f"{element_id}: maximum {max_items} items allowed"
                        )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    async def render_slide(
        self,
        layout_type: str,
        content: Dict[str, Any],
        design: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render a slide with layout, content, and design.

        Args:
            layout_type: Slide layout type
            content: Slide content
            design: Design specifications

        Returns:
            Rendered slide data
        """
        # Validate content
        validation = self.validate_slide_content(layout_type, content)

        if not validation["valid"]:
            logger.warning(
                "slide_content_validation_failed",
                layout=layout_type,
                errors=validation["errors"],
            )

        # Get layout spec
        layout_spec = self.get_layout_spec(layout_type)

        return {
            "layout_type": layout_type,
            "layout_spec": layout_spec,
            "content": content,
            "design": design,
            "validation": validation,
        }
