"""
Cross Verifier - Verifies council responses against sources and each other
Implements cross-model verification and source verification
"""

from typing import List, Dict, Any
from app.services.v4.zero_defect.council.council_config import ZeroDefectCouncilConfig


class CrossVerifier:
    """
    Cross-verifies council responses
    Models verify each other's responses against sources
    """
    
    def __init__(self):
        self.config = ZeroDefectCouncilConfig()
    
    async def verify(
        self,
        content: str,
        verification_council: List[str],
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify a single response using verification council
        
        Args:
            content: Content to verify
            verification_council: List of models for verification
            task: Original task
            context: Context dictionary
            
        Returns:
            Dictionary with verification results
        """
        from app.services.llm.model_router import ModelRouter
        
        model_router = ModelRouter()
        
        verification_scores = []
        
        # Run each verification model in parallel
        import asyncio
        tasks = []
        for model in verification_council:
            task_coroutine = self._verify_with_model(
                model_router,
                model,
                content,
                task,
                context
            )
            tasks.append(task_coroutine)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"Verification error: {result}")
                continue
            verification_scores.append(result)
        
        # Calculate aggregate verification score
        if not verification_scores:
            return {
                "verified": False,
                "confidence": 0.0,
                "sources": []
            }
        
        aggregate_confidence = sum(s["confidence"] for s in verification_scores) / len(verification_scores)
        verified = aggregate_confidence >= self.config.CONFIDENCE_THRESHOLD
        
        # Collect all sources
        all_sources = []
        for score in verification_scores:
            all_sources.extend(score.get("sources", []))
        
        return {
            "verified": verified,
            "confidence": aggregate_confidence,
            "sources": list(set(all_sources)),  # Deduplicate
            "individual_scores": verification_scores
        }
    
    async def _verify_with_model(
        self,
        model_router,
        model: str,
        content: str,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify content with a specific model"""
        system_prompt = """You are a fact verification expert. Your task is to verify the accuracy of generated content against the original task requirements and any provided sources.

Evaluate:
- Factual accuracy: Are the facts in the content accurate?
- Task alignment: Does the content address the task requirements?
- Consistency: Is the content internally consistent?
- Completeness: Is the content complete for the task?

Return JSON with:
- verified: true/false if content is accurate
- confidence: 0.0-1.0 confidence score
- sources: list of relevant sources if any
- explanation: brief explanation of verification"""

        user_prompt = f"""Original Task: {task}

Content to Verify:
{content}

Context:
{context}

Return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return result
            
        except Exception as e:
            print(f"Error verifying with {model}: {e}")
            return {
                "verified": False,
                "confidence": 0.0,
                "sources": [],
                "explanation": str(e)
            }
    
    def verify_cross_model_agreement(
        self,
        stage1_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify cross-model agreement among council responses
        
        Args:
            stage1_results: Results from Stage 1 (First Opinions)
            
        Returns:
            Dictionary with agreement analysis
        """
        if len(stage1_results) < 2:
            return {
                "agreement": 1.0,
                "analysis": "Insufficient models for comparison"
            }
        
        # Calculate pairwise similarity (simplified)
        # In production, use more sophisticated semantic similarity
        agreements = 0
        total_comparisons = 0
        
        for i in range(len(stage1_results)):
            for j in range(i + 1, len(stage1_results)):
                similarity = self._calculate_similarity(
                    stage1_results[i]["content"],
                    stage1_results[j]["content"]
                )
                agreements += similarity
                total_comparisons += 1
        
        average_agreement = agreements / total_comparisons if total_comparisons > 0 else 0.0
        
        return {
            "agreement": average_agreement,
            "analysis": f"Cross-model agreement: {average_agreement:.2f}"
        }
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content strings
        Simplified version - use semantic similarity in production
        """
        # Simple Jaccard similarity on word sets
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
