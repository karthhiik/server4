"""
Validation Gate - Post-generation enforcement
Implements CEO's validation rules for slide quality
"""

from __future__ import annotations

import re
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass

from app.models.user_input import UserInputContext
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of slide validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: float  # 0.0 to 1.0


class ValidationGate:
    """
    Post-generation enforcement - rejects bad slides
    Implements CEO's validation rules from the proposal
    """
    
    FORBIDDEN_PHRASES = [
        "strategic advantages",
        "strategic edge",
        "strategic edge in",
        "empowering",
        "empowers",
        "streamlined operations",
        "three steps to",
        "revenue streams from",
        "our approach",
        "leveraging insights",
        "significant risks",
        "our unique value proposition",
        "our strategic position",
        "our strategic edge",
    ]
    
    GENERIC_PHRASES = [
        "comprehensive solution",
        "innovative approach",
        "cutting-edge technology",
        "industry-leading",
        "world-class",
        "state-of-the-art",
        "best-in-class",
    ]
    
    def validate(
        self,
        slide: Dict[str, Any],
        user_context: UserInputContext
    ) -> ValidationResult:
        """
        Validate a slide against user context and quality rules
        Returns ValidationResult with errors, warnings, and score
        """
        errors = []
        warnings = []
        
        headline = slide.get("headline", "").lower()
        subheadline = slide.get("subheadline", "").lower()
        body = slide.get("body", "").lower()
        intent = slide.get("intent", "")
        
        # Rule 1: No forbidden phrases
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in headline:
                errors.append(f"FORBIDDEN_PHRASE: '{phrase}' in headline")
        
        # Rule 2: Intent-specific user data enforcement
        if intent == "ask":
            if user_context.funding_amount and user_context.funding_amount.lower() not in headline:
                errors.append(
                    f"MISSING_FUNDING: Ask slide must contain '{user_context.funding_amount}'"
                )
        
        if intent == "traction":
            if user_context.traction_metrics:
                traction_keywords = user_context.traction_metrics.lower().split()
                # Check if any meaningful keyword appears
                has_keyword = any(
                    kw in headline for kw in traction_keywords if len(kw) > 3
                )
                if not has_keyword:
                    errors.append(
                        f"MISSING_TRACTION: Must reference '{user_context.traction_metrics}'"
                    )
        
        if intent == "market":
            # Market slide should NOT have funding amount
            if user_context.funding_amount and user_context.funding_amount.lower() in headline:
                errors.append(
                    f"WRONG_SLIDE: Funding amount '{user_context.funding_amount}' on market slide"
                )
        
        # Rule 3: Specificity check
        company = user_context.company_name.lower()
        industry = (user_context.industry or "").lower()
        
        # Check if headline has company name, industry, or specific metric
        has_company = company in headline
        has_industry = industry in headline
        has_metric = bool(re.search(r'\d+|\$\d+|\d+%', headline))
        
        if not (has_company or has_industry or has_metric):
            errors.append(
                "TOO_GENERIC: Headline lacks company name, industry, or specific metric"
            )
        
        # Rule 4: Generic phrase detection
        for phrase in self.GENERIC_PHRASES:
            if phrase in headline:
                warnings.append(f"GENERIC_PHRASE: '{phrase}' in headline")
        
        # Rule 5: Headline length check
        if len(slide.get("headline", "")) < 15:
            errors.append("HEADLINE_TOO_SHORT: Headline must be at least 15 characters")
        
        # Rule 6: Headline length check (max)
        if len(slide.get("headline", "")) > 100:
            warnings.append("HEADLINE_TOO_LONG: Headline over 100 characters")
        
        # Calculate score based on errors and warnings
        error_penalty = len(errors) * 0.3
        warning_penalty = len(warnings) * 0.1
        score = max(0.0, 1.0 - error_penalty - warning_penalty)
        
        is_valid = len(errors) == 0
        
        logger.debug(
            "validation_result",
            intent=intent,
            is_valid=is_valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            score=score,
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=score
        )
    
    def validate_deck(
        self,
        slides: List[Dict[str, Any]],
        user_context: UserInputContext
    ) -> Dict[str, Any]:
        """
        Validate an entire deck and return summary
        """
        results = []
        total_errors = 0
        total_warnings = 0
        valid_count = 0
        
        for slide in slides:
            result = self.validate(slide, user_context)
            results.append({
                "slide_index": slide.get("index"),
                "intent": slide.get("intent"),
                "headline": slide.get("headline"),
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "score": result.score,
            })
            
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            if result.is_valid:
                valid_count += 1
        
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
        deck_valid = total_errors == 0
        
        return {
            "deck_valid": deck_valid,
            "total_slides": len(slides),
            "valid_slides": valid_count,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "average_score": avg_score,
            "slide_results": results,
        }
    
    def get_regeneration_instruction(
        self,
        slide: Dict[str, Any],
        validation_result: ValidationResult,
        user_context: UserInputContext
    ) -> str:
        """
        Generate specific regeneration instructions based on validation errors
        """
        if validation_result.is_valid:
            return ""
        
        instructions = []
        intent = slide.get("intent", "")
        
        for error in validation_result.errors:
            if "FORBIDDEN_PHRASE" in error:
                instructions.append(
                    "Remove the forbidden phrase from the headline. "
                    "Use specific, descriptive language instead."
                )
            elif "MISSING_FUNDING" in error and intent == "ask":
                instructions.append(
                    f"The Ask slide MUST include the exact funding amount: "
                    f"'{user_context.funding_amount}'. Put this in the headline."
                )
            elif "MISSING_TRACTION" in error and intent == "traction":
                instructions.append(
                    f"The Traction slide MUST reference your traction metrics: "
                    f"'{user_context.traction_metrics}'. Put this in the headline."
                )
            elif "WRONG_SLIDE" in error:
                instructions.append(
                    "This slide should not contain funding information. "
                    "Move funding-related content to the Ask slide."
                )
            elif "TOO_GENERIC" in error:
                instructions.append(
                    f"Make the headline more specific. Include the company name "
                    f"'{user_context.company_name}', industry '{user_context.industry}', "
                    "or a specific metric/number."
                )
            elif "HEADLINE_TOO_SHORT" in error:
                instructions.append(
                    "The headline is too short. Expand it to be more descriptive "
                    "and specific (15-100 characters)."
                )
        
        return "\n".join(instructions) if instructions else "Regenerate with higher specificity."
