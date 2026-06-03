"""
Pydantic models for profile verification and trust scoring.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    VERIFIED = "verified"           # >= 85
    LIKELY_LEGIT = "likely_legit"   # >= 60
    UNVERIFIED = "unverified"       # >= 40
    SUSPICIOUS = "suspicious"       # < 40


class SignalResult(BaseModel):
    """Individual verification signal outcome."""
    value: Any = Field(description="Raw signal value (bool, int, float, str)")
    points: int = Field(default=0, ge=0, le=100)
    max_points: int = Field(default=0, ge=0, le=100)
    source: str = Field(default="", description="API or engine that produced this signal")
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Debugging payload")
    error: Optional[str] = Field(default=None, description="If signal check failed")


class InvestorAddonSignals(BaseModel):
    """Extra signals applied only to profiles claiming investor status."""
    sec_edgar_filing: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    crunchbase_exists: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    portfolio_verified: SignalResult = Field(default_factory=lambda: SignalResult(value=0))
    form_adv_filed: SignalResult = Field(default_factory=lambda: SignalResult(value=False))


class VerificationSignals(BaseModel):
    """All base trust signals for a profile."""
    email_deliverable: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    email_domain_match: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    linkedin_verified: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    linkedin_connections: SignalResult = Field(default_factory=lambda: SignalResult(value=0))
    twitter_followers: SignalResult = Field(default_factory=lambda: SignalResult(value=0))
    github_public_repos: SignalResult = Field(default_factory=lambda: SignalResult(value=0))
    github_active_commits: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    photo_reverse_search: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    company_website_live: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    username_consistency: SignalResult = Field(default_factory=lambda: SignalResult(value=0))
    timeline_consistent: SignalResult = Field(default_factory=lambda: SignalResult(value=False))
    bio_consistency: SignalResult = Field(default_factory=lambda: SignalResult(value=0.0))


class TrustScoreReport(BaseModel):
    """Complete trust score report for a user profile."""
    user_id: str
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    trust_score: int = Field(default=0, ge=0, le=100)
    tier: VerificationStatus = VerificationStatus.UNVERIFIED
    signals: VerificationSignals = Field(default_factory=VerificationSignals)
    investor_addon: Optional[InvestorAddonSignals] = None
    flags: List[str] = Field(default_factory=list)
    requires_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)

    def add_flag(self, reason: str) -> None:
        self.flags.append(reason)

    def require_review(self, reason: str) -> None:
        self.requires_review = True
        if reason not in self.review_reasons:
            self.review_reasons.append(reason)


class ProfileInput(BaseModel):
    """Input required to run verification on a profile."""
    user_id: str
    email: str
    full_name: str
    role: str = Field(default="founder", description="founder | investor | mentor")
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_username: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    profile_photo_url: Optional[str] = None
    experience: Optional[List[Dict[str, Any]]] = None
    bio: Optional[str] = None
