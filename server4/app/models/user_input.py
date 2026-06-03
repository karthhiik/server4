"""
User Input Schema - Matches CEO's proposed structure
Integrates with existing structured_context.py for authoritative override
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Stage(str, Enum):
    """Company development stage"""
    IDEA = "idea"
    PRE_REVENUE = "pre-revenue"
    SEED = "seed"
    SERIES_A = "series-a"
    GROWTH = "growth"


class Purpose(str, Enum):
    """Purpose of the pitch deck"""
    FUNDRAISING = "fundraising"
    PARTNERSHIP = "partnership"
    SALES = "sales"
    HIRING = "hiring"


class DocumentSource(str, Enum):
    """Source of user input data"""
    MANUAL = "manual"
    UPLOADED_PDF = "uploaded_pdf"
    UPLOADED_PPT = "uploaded_ppt"
    UPLOADED_PPTX = "uploaded_pptx"
    URL = "url"
    UPLOADED_DECK = "uploaded_deck"


@dataclass
class ParsedDocument:
    """Structured data extracted from uploaded document"""
    company_name: Optional[str] = None
    one_liner: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_round: Optional[str] = None
    traction_metrics: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[str] = None
    market_size: Optional[str] = None
    competitors: Optional[List[str]] = None
    financials: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0


@dataclass
class UserInputContext:
    """User input context for onboarding flow - CEO's design"""
    
    # === REQUIRED (Step 1) ===
    company_name: str
    one_liner: str
    
    # === REQUIRED (Step 2) ===
    purpose: Purpose
    target_audience: List[str]  # ["vc", "corporate"]
    
    # === OPTIONAL (Step 3) ===
    funding_amount: Optional[str] = None  # "$12.5M"
    funding_round: Optional[str] = None   # "Series A"
    traction_metrics: Optional[str] = None  # "2 state pilots, 1 patent pending"
    stage: Optional[Stage] = None
    
    # === INFERRED / EXTRACTED ===
    industry: Optional[str] = None  # auto-detected from one-liner or doc
    document_source: Optional[DocumentSource] = None
    parsed_document: Optional[ParsedDocument] = None
    website_url: Optional[str] = None
    
    def to_structured_context(self) -> Dict[str, Any]:
        """Convert to existing structured_context format for pipeline integration"""
        ctx: Dict[str, Any] = {
            "company": {
                "name": self.company_name,
                "tagline": self.one_liner,
                "industry": self.industry,
                "stage": self.stage.value if self.stage else None,
            },
            "fundraising": {},
            "traction": {},
        }
        
        if self.funding_amount:
            ctx["fundraising"]["amount"] = self.funding_amount
        if self.funding_round:
            ctx["fundraising"]["round"] = self.funding_round
        if self.funding_round:
            ctx["fundraising"]["round_type"] = self.funding_round
        
        if self.traction_metrics:
            # Parse traction metrics into structured fields for parallel_writer
            metrics_lower = self.traction_metrics.lower()
            
            # Extract pilot programs / customers
            if "pilot" in metrics_lower or "customer" in metrics_lower:
                # Try to extract number
                import re
                numbers = re.findall(r'(\d+)\s*(?:pilot|customer|client|program)', metrics_lower)
                if numbers:
                    ctx["traction"]["enterprise_customers"] = int(numbers[0])
            
            # Extract users
            if "user" in metrics_lower or "active" in metrics_lower:
                import re
                numbers = re.findall(r'(\d+(?:,\d+)*)\s*(?:user|active)', metrics_lower)
                if numbers:
                    # Remove commas and convert to int
                    ctx["traction"]["active_users"] = int(numbers[0].replace(',', ''))
            
            # Extract revenue
            if "revenue" in metrics_lower or "mrr" in metrics_lower or "arr" in metrics_lower:
                import re
                money_match = re.search(r'\$?([\d,.]+)\s*(?:m|k|million|thousand)?', metrics_lower)
                if money_match:
                    ctx["traction"]["revenue"] = money_match.group(1)
            
            # Keep key_milestones for keyword extraction
            ctx["traction"]["key_milestones"] = [self.traction_metrics]
            
            # Extract patent info
            if "patent" in metrics_lower:
                ctx["traction"]["patents"] = True
            
        # Merge parsed document if available
        if self.parsed_document:
            if self.parsed_document.financials:
                ctx["financials"] = self.parsed_document.financials
            if self.parsed_document.competitors:
                ctx["competitors"] = {"companies": self.parsed_document.competitors}
            if self.parsed_document.market_size:
                ctx["market"] = {"tam": self.parsed_document.market_size}
            
        return ctx

    def to_prompt_block(self) -> str:
        """Convert to AUTHORITATIVE prompt block - CEO's enforcement design"""
        lines = [
            "=== AUTHORITATIVE USER INPUT (DO NOT OVERRIDE) ===",
            f"COMPANY: {self.company_name}",
            f"ONE-LINER: {self.one_liner}",
            f"PURPOSE: {self.purpose.value}",
            f"TARGET AUDIENCE: {', '.join(self.target_audience)}",
        ]
        
        if self.funding_amount:
            lines.append(f"FUNDING AMOUNT: {self.funding_amount}")
        if self.funding_round:
            lines.append(f"FUNDING ROUND: {self.funding_round}")
        if self.traction_metrics:
            lines.append(f"TRACTION: {self.traction_metrics}")
        if self.stage:
            lines.append(f"STAGE: {self.stage.value}")
        if self.industry:
            lines.append(f"INDUSTRY: {self.industry}")
            
        return "\n".join(lines)
    
    def get_mandatory_keywords(self) -> List[str]:
        """Extract keywords that MUST appear in slide content"""
        keywords = [self.company_name.lower()]
        
        if self.funding_amount:
            keywords.append(self.funding_amount.lower())
        if self.traction_metrics:
            # Split traction metrics into individual keywords
            parts = self.traction_metrics.lower().split()
            keywords.extend([p for p in parts if len(p) > 3])
        if self.industry:
            keywords.append(self.industry.lower())
            
        return keywords
