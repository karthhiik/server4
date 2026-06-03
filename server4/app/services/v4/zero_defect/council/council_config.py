"""
Zero-Defect Council Configuration
Configured with models from server4/.env
"""

import os
from typing import List, Dict, Any
from app.config import settings


class ZeroDefectCouncilConfig:
    """
    Zero-Defect Council Configuration
    Uses models defined in server4/.env
    """
    
    # Primary Council (5 models for Standard Mode)
    PRIMARY_COUNCIL = [
        os.getenv("AZURE_KIMI_MODEL", "Kimi-K2-Thinking"),      # Planning/Reasoning
        os.getenv("DEEPSEEK_MODEL_NAME", "DeepSeek-V3.2"),    # Storytelling
        os.getenv("AZURE_GPT4O_MINI_MODEL", "gpt-4o-mini"),   # Fast structured JSON
        os.getenv("AZURE_GPT4O_MINI_MODEL", "gpt-4o-mini"),   # Backup fast model
        "glm",  # Cloudflare Workers GLM fallback
    ]
    
    # Verification Council (3 models for cross-verification)
    VERIFICATION_COUNCIL = [
        os.getenv("AZURE_KIMI_MODEL", "Kimi-K2-Thinking"),      # Fact verification
        os.getenv("DEEPSEEK_MODEL_NAME", "DeepSeek-V3.2"),    # Technical verification
        os.getenv("AZURE_GPT4O_MINI_MODEL", "gpt-4o-mini"),   # Fast verification
    ]
    
    # Premium Council (7 models for Premium Mode)
    PREMIUM_COUNCIL = [
        os.getenv("AZURE_KIMI_MODEL", "Kimi-K2-Thinking"),      # Planning/Reasoning
        os.getenv("AZURE_KIMI26_MODEL", "Kimi-K2.6"),          # Premium strategist
        os.getenv("PHI4_REASONING_DEPLOYMENT", "Phi-4-reasoning"), # Reasoning
        os.getenv("DEEPSEEK_MODEL_NAME", "DeepSeek-V3.2"),    # Storytelling
        os.getenv("AZURE_GPT4O_MINI_MODEL", "gpt-4o-mini"),   # Fast structured JSON
        os.getenv("AZURE_GPT4O_MINI_MODEL", "gpt-4o-mini"),   # Backup fast model
        "glm",  # Cloudflare Workers GLM
    ]
    
    # Chairman (Best model for synthesis)
    CHAIRMAN = os.getenv("AZURE_KIMI_MODEL", "Kimi-K2-Thinking")
    
    # Confidence Thresholds
    CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence for acceptance
    LOW_CONFIDENCE_THRESHOLD = 0.5  # Threshold for flagging
    
    # Retry Limits
    MAX_RETRIES = 3  # Maximum retries per generation
    
    # Model Capabilities
    MODEL_CAPABILITIES = {
        "Kimi-K2-Thinking": {
            "strengths": ["reasoning", "analysis", "synthesis"],
            "weaknesses": ["speed"],
            "cost": "high",
            "tier": "T0"
        },
        "Kimi-K2.6": {
            "strengths": ["reasoning", "creative", "chinese"],
            "weaknesses": ["speed", "cost"],
            "cost": "high",
            "tier": "T0+"
        },
        "Phi-4-reasoning": {
            "strengths": ["reasoning", "speed"],
            "weaknesses": ["creative"],
            "cost": "medium",
            "tier": "T0.5"
        },
        "DeepSeek-V3.2": {
            "strengths": ["reasoning", "storytelling", "speed"],
            "weaknesses": ["deep_analysis"],
            "cost": "medium",
            "tier": "T1"
        },
        "gpt-4o-mini": {
            "strengths": ["structured_json", "speed", "cost"],
            "weaknesses": ["deep_analysis"],
            "cost": "low",
            "tier": "T2"
        },
        "nv-glm-4.7": {
            "strengths": ["technical", "code", "precision"],
            "weaknesses": ["creative"],
            "cost": "medium",
            "tier": "T3"
        },
        "glm": {
            "strengths": ["creative", "chinese", "cost"],
            "weaknesses": ["technical_precision"],
            "cost": "low",
            "tier": "T5"
        }
    }
    
    # Fallback Chain (for model failures)
    FALLBACK_CHAIN = {
        "Kimi-K2-Thinking": ["DeepSeek-V3.2", "gpt-4o-mini", "nv-glm-4.7"],
        "Kimi-K2.6": ["Kimi-K2-Thinking", "DeepSeek-V3.2", "gpt-4o-mini"],
        "Phi-4-reasoning": ["Kimi-K2-Thinking", "DeepSeek-V3.2", "gpt-4o-mini"],
        "DeepSeek-V3.2": ["Kimi-K2-Thinking", "gpt-4o-mini", "glm"],
        "gpt-4o-mini": ["Kimi-K2-Thinking", "DeepSeek-V3.2", "glm"],
        "nv-glm-4.7": ["DeepSeek-V3.2", "gpt-4o-mini", "glm"],
        "glm": ["DeepSeek-V3.2", "gpt-4o-mini", "nv-glm-4.7"]
    }
    
    @classmethod
    def get_primary_council(cls) -> List[str]:
        """Get primary council models"""
        return cls.PRIMARY_COUNCIL
    
    @classmethod
    def get_verification_council(cls) -> List[str]:
        """Get verification council models"""
        return cls.VERIFICATION_COUNCIL
    
    @classmethod
    def get_premium_council(cls) -> List[str]:
        """Get premium council models"""
        return cls.PREMIUM_COUNCIL
    
    @classmethod
    def get_chairman(cls) -> str:
        """Get chairman model"""
        return cls.CHAIRMAN
    
    @classmethod
    def get_fallback_chain(cls, model: str) -> List[str]:
        """Get fallback chain for a model"""
        return cls.FALLBACK_CHAIN.get(model, [])
    
    @classmethod
    def get_model_capabilities(cls, model: str) -> Dict[str, Any]:
        """Get capabilities for a model"""
        return cls.MODEL_CAPABILITIES.get(model, {})
