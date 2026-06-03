"""
Prompt Regenerator - Regenerates slides based on user prompts
Allows users to specify exactly what changes they want
"""

from typing import Dict, Any, List, Optional
from app.services.llm.model_router import ModelRouter


class PromptRegenerator:
    """
    Regenerates slides based on user prompts
    Allows specific, directed changes to slide content and design
    """
    
    def __init__(self):
        self.model_router = ModelRouter()
    
    async def regenerate_with_prompt(
        self,
        slide: Dict[str, Any],
        prompt: str,
        target_element: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerate a slide based on user prompt
        
        Args:
            slide: Original slide
            prompt: User's regeneration prompt
            target_element: Optional target element (headline, bullets, etc.)
            
        Returns:
            Regenerated slide
        """
        # Determine what to regenerate based on prompt
        regeneration_plan = await self._analyze_prompt(prompt, slide)
        
        # Execute regeneration
        regenerated_slide = await self._execute_regeneration(slide, regeneration_plan)
        
        return regenerated_slide
    
    async def _analyze_prompt(self, prompt: str, slide: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user prompt to determine regeneration plan
        
        Args:
            prompt: User's regeneration prompt
            slide: Original slide
            
        Returns:
            Dictionary with regeneration plan
        """
        system_prompt = """You are a slide regeneration expert. Analyze the user's prompt to determine what needs to be regenerated.

Analyze the prompt and determine:
- target_element: Which element to regenerate (headline, subheadline, bullets, body, image, design, all)
- changes_needed: What changes to make
- preserve_content: Whether to preserve the original content
- design_changes: Any design changes requested

Return JSON with:
- target_element: string
- changes_needed: string description
- preserve_content: boolean
- design_changes: object with design changes"""

        user_prompt = f"""User Prompt: {prompt}

Current Slide:
{slide}

Analyze the prompt and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            plan = json.loads(response.content)
            
            return plan
            
        except Exception as e:
            print(f"Error analyzing prompt: {e}")
            
            # Fallback: simple keyword matching
            return self._fallback_prompt_analysis(prompt)
    
    def _fallback_prompt_analysis(self, prompt: str) -> Dict[str, Any]:
        """Fallback simple prompt analysis"""
        prompt_lower = prompt.lower()
        
        target_element = "all"
        if "headline" in prompt_lower:
            target_element = "headline"
        elif "bullet" in prompt_lower:
            target_element = "bullets"
        elif "image" in prompt_lower:
            target_element = "image"
        elif "design" in prompt_lower:
            target_element = "design"
        
        preserve_content = "keep" in prompt_lower or "preserve" in prompt_lower
        
        return {
            "target_element": target_element,
            "changes_needed": prompt,
            "preserve_content": preserve_content,
            "design_changes": {}
        }
    
    async def _execute_regeneration(
        self,
        slide: Dict[str, Any],
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute regeneration based on plan
        
        Args:
            slide: Original slide
            plan: Regeneration plan
            
        Returns:
            Regenerated slide
        """
        target_element = plan.get("target_element", "all")
        preserve_content = plan.get("preserve_content", True)
        
        regenerated_slide = slide.copy()
        
        if target_element in ["headline", "all"]:
            regenerated_slide["headline"] = await self._regenerate_element(
                slide.get("headline"),
                plan.get("changes_needed"),
                "headline",
                preserve_content
            )
        
        if target_element in ["subheadline", "all"]:
            regenerated_slide["subheadline"] = await self._regenerate_element(
                slide.get("subheadline"),
                plan.get("changes_needed"),
                "subheadline",
                preserve_content
            )
        
        if target_element in ["bullets", "all"]:
            regenerated_slide["bullets"] = await self._regenerate_element(
                slide.get("bullets"),
                plan.get("changes_needed"),
                "bullets",
                preserve_content
            )
        
        if target_element in ["body", "all"]:
            regenerated_slide["body"] = await self._regenerate_element(
                slide.get("body"),
                plan.get("changes_needed"),
                "body",
                preserve_content
            )
        
        if target_element in ["image", "all"] or "image" in plan.get("changes_needed", "").lower():
            regenerated_slide["image_prompt"] = await self._generate_image_prompt(
                slide,
                plan.get("changes_needed")
            )
        
        if target_element in ["design", "all"] or "design" in plan.get("changes_needed", "").lower():
            regenerated_slide["design"] = plan.get("design_changes", {})
        
        return regenerated_slide
    
    async def _regenerate_element(
        self,
        current_content: Any,
        changes_needed: str,
        element_type: str,
        preserve_content: bool
    ) -> Any:
        """
        Regenerate a specific element
        
        Args:
            current_content: Current element content
            changes_needed: Description of changes needed
            element_type: Type of element
            preserve_content: Whether to preserve content
            
        Returns:
            Regenerated element content
        """
        if preserve_content:
            # Modify existing content
            if isinstance(current_content, list):
                return await self._modify_list(current_content, changes_needed)
            else:
                return await self._modify_text(current_content, changes_needed)
        else:
            # Generate new content
            return await self._generate_new_content(changes_needed, element_type)
    
    async def _modify_text(self, text: str, changes_needed: str) -> str:
        """Modify text based on changes needed"""
        system_prompt = """You are a text editing expert. Modify the text based on the user's request.

Return JSON with:
- modified_text: the modified text"""

        user_prompt = f"""Original Text: {text}

Changes Needed: {changes_needed}

Modify the text and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=500,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return result.get("modified_text", text)
            
        except Exception as e:
            print(f"Error modifying text: {e}")
            return text
    
    async def _modify_list(self, items: List[str], changes_needed: str) -> List[str]:
        """Modify list based on changes needed"""
        system_prompt = """You are a list editing expert. Modify the list items based on the user's request.

Return JSON with:
- modified_list: the modified list of strings"""

        user_prompt = f"""Original List: {items}

Changes Needed: {changes_needed}

Modify the list and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=500,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return result.get("modified_list", items)
            
        except Exception as e:
            print(f"Error modifying list: {e}")
            return items
    
    async def _generate_new_content(self, changes_needed: str, element_type: str) -> Any:
        """Generate new content based on changes needed"""
        system_prompt = f"""You are a content generation expert. Generate new {element_type} content based on the user's request.

Return JSON with:
- generated_content: the generated content"""

        user_prompt = f"""Request: {changes_needed}

Generate new {element_type} content and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return result.get("generated_content", "")
            
        except Exception as e:
            print(f"Error generating content: {e}")
            return ""
    
    async def _generate_image_prompt(self, slide: Dict[str, Any], changes_needed: str) -> str:
        """Generate image prompt for image regeneration"""
        system_prompt = """You are an image generation expert. Generate a detailed image prompt based on the slide content and user's request.

Return JSON with:
- image_prompt: the detailed image prompt"""

        user_prompt = f"""Slide Content:
Headline: {slide.get('headline')}
Subheadline: {slide.get('subheadline')}
Bullets: {slide.get('bullets')}

Changes Needed: {changes_needed}

Generate a detailed image prompt and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return result.get("image_prompt", "")
            
        except Exception as e:
            print(f"Error generating image prompt: {e}")
            return ""
