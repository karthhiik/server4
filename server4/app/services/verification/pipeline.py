"""
Profile verification pipeline orchestrator.
Collects all signals in parallel, computes trust score, and returns a report.
Designed to be called from a FastAPI endpoint or Celery task.
"""

from typing import Optional

from app.models.verification import (
    InvestorAddonSignals,
    ProfileInput,
    TrustScoreReport,
    VerificationSignals,
)
from app.services.verification.email_verifier import EmailVerifier
from app.services.verification.github_verifier import GitHubVerifier
from app.services.verification.investor_verifier import InvestorVerifier
from app.services.verification.linkedin_verifier import LinkedInVerifier
from app.services.verification.photo_verifier import PhotoVerifier
from app.services.verification.trust_scorer import TrustScorer


class VerificationPipeline:
    """End-to-end async verification pipeline."""

    def __init__(self):
        self.email_verifier = EmailVerifier()
        self.linkedin_verifier = LinkedInVerifier()
        self.github_verifier = GitHubVerifier()
        self.photo_verifier = PhotoVerifier()
        self.investor_verifier = InvestorVerifier()
        self.trust_scorer = TrustScorer()

    async def verify(self, profile: ProfileInput) -> TrustScoreReport:
        """Run full verification pipeline and return trust score report."""
        signals = await self._collect_signals(profile)

        # Investor addon
        investor_addon = InvestorAddonSignals()
        if profile.role.lower() == "investor":
            investor_addon = await self._check_investor(profile)

        # Trust score
        report = self.trust_scorer.score(profile, signals, investor_addon)
        return report

    async def _collect_signals(self, profile: ProfileInput) -> VerificationSignals:
        s = VerificationSignals()

        # Email
        email_res = await self.email_verifier.verify(
            profile.email,
            company_website=profile.company_website,
            company_name=profile.company_name,
        )
        s.email_deliverable = self._signal(
            email_res.deliverable and not email_res.is_disposable,
            15,
            source="email_verifier",
        )
        s.email_domain_match = self._signal(
            email_res.company_domain_match,
            10,
            source="email_verifier",
        )

        # LinkedIn
        li_res = await self.linkedin_verifier.verify(
            profile.linkedin_url,
            claimed_name=profile.full_name,
            claimed_company=profile.company_name,
        )
        s.linkedin_verified = self._signal(
            li_res.exists and li_res.name_match_score >= 60,
            15,
            source="linkedin_verifier",
            raw_data={"name_match_score": li_res.name_match_score, "headline": li_res.headline},
        )
        # Sub-signal: connections
        s.linkedin_connections = self._signal(
            li_res.connection_count or 0,
            5,
            source="linkedin_verifier",
        )

        # Twitter (placeholder — integrate Twitter API or Nitter scraper)
        s.twitter_followers = self._signal(0, 5, source="not_implemented")

        # GitHub
        if profile.github_username:
            gh_res = await self.github_verifier.verify(profile.github_username)
            s.github_public_repos = self._signal(
                gh_res.public_repos,
                10,
                source="github_verifier",
            )
            s.github_active_commits = self._signal(
                gh_res.recent_push_events >= 3,
                5,
                source="github_verifier",
                raw_data={"recent_push_events": gh_res.recent_push_events},
            )
        else:
            s.github_public_repos = self._signal(0, 10, source="missing")
            s.github_active_commits = self._signal(False, 5, source="missing")

        # Photo
        photo_res = await self.photo_verifier.verify(profile.profile_photo_url)
        s.photo_reverse_search = self._signal(
            photo_res.passed and not photo_res.stock_photo_detected,
            10,
            source="photo_verifier",
            raw_data={"exact_matches": photo_res.exact_matches_found},
        )

        # Company website
        website_live = await self._is_website_live(profile.company_website)
        s.company_website_live = self._signal(
            website_live,
            10,
            source="http_check",
        )

        # Timeline consistency (rules engine)
        timeline_ok = self._check_timeline(profile.experience)
        s.timeline_consistent = self._signal(
            timeline_ok,
            5,
            source="rules_engine",
        )

        # Username consistency (placeholder; integrate sherlock in production)
        s.username_consistency = self._signal(0, 5, source="not_implemented")

        # Bio consistency (placeholder)
        s.bio_consistency = self._signal(0.0, 5, source="not_implemented")

        return s

    async def _check_investor(self, profile: ProfileInput) -> InvestorAddonSignals:
        addon = InvestorAddonSignals()
        inv_res = await self.investor_verifier.verify(
            name=profile.full_name,
            firm_name=profile.company_name,
            claimed_portfolio=None,  # expand model to accept portfolio list
        )
        addon.sec_edgar_filing = self._signal(
            inv_res.sec_edgar_filing_found,
            10,
            source="sec_edgar",
        )
        addon.form_adv_filed = self._signal(
            inv_res.form_adv_filed,
            10,
            source="sec_edgar",
        )
        addon.crunchbase_exists = self._signal(
            inv_res.crunchbase_exists,
            5,
            source="crunchbase",
        )
        addon.portfolio_verified = self._signal(
            inv_res.portfolio_companies_verified,
            5,
            source="cross_reference",
        )
        return addon

    def _signal(self, value, max_points: int, source: str, raw_data=None):
        return self._to_signal(value, max_points, source, raw_data)

    def _to_signal(self, value, max_points: int, source: str, raw_data=None):
        from app.models.verification import SignalResult
        return SignalResult(value=value, max_points=max_points, source=source, raw_data=raw_data)

    def _error_signal(self):
        from app.models.verification import SignalResult
        return SignalResult(value=False, error="Verification check raised exception")

    async def _is_website_live(self, url: Optional[str]) -> bool:
        if not url:
            return False
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    title = r.text.lower()
                    # Detect parked domains
                    parked_keywords = ["domain parked", "sedo", "buy this domain", "godaddy", " namecheap"]
                    return not any(kw in title for kw in parked_keywords[:3])
        except Exception:
            pass
        return False

    def _check_timeline(self, experience: Optional[list]) -> bool:
        if not experience:
            return True  # No claims = no contradictions
        from datetime import datetime
        intervals = []
        for exp in experience:
            start = exp.get("start_date")
            end = exp.get("end_date") or datetime.utcnow().isoformat()
            try:
                s_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00")) if start else None
                e_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00")) if end else None
            except Exception:
                continue
            if s_dt and e_dt and s_dt > e_dt:
                return False  # End before start
            intervals.append((s_dt, e_dt))
        # Overlap check (simplified: flag if >1 FT role overlaps > 90 days)
        for i in range(len(intervals)):
            for j in range(i + 1, len(intervals)):
                s1, e1 = intervals[i]
                s2, e2 = intervals[j]
                if s1 and e1 and s2 and e2:
                    overlap_start = max(s1, s2)
                    overlap_end = min(e1, e2)
                    if overlap_end > overlap_start:
                        overlap_days = (overlap_end - overlap_start).days
                        if overlap_days > 90:
                            return False
        return True
