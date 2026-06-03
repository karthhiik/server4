"""
Trust score computation engine.
Translates raw verification signals into a 0-100 trust score and tier assignment.
"""

from app.models.verification import (
    InvestorAddonSignals,
    ProfileInput,
    SignalResult,
    TrustScoreReport,
    VerificationSignals,
    VerificationStatus,
)


class TrustScorer:
    """Weighted trust-score calculator with manual-review triggers."""

    # Base signal scoring matrix
    BASE_SIGNALS = {
        "email_deliverable": {"max": 15, "threshold": True},
        "email_domain_match": {"max": 10, "threshold": True},
        "linkedin_verified": {"max": 15, "threshold": True},
        "linkedin_connections": {"max": 5, "threshold": 100},
        "twitter_followers": {"max": 5, "threshold": 50},
        "github_public_repos": {"max": 10, "threshold": 10},
        "github_active_commits": {"max": 5, "threshold": True},
        "photo_reverse_search": {"max": 10, "threshold": True},
        "company_website_live": {"max": 10, "threshold": True},
        "username_consistency": {"max": 5, "threshold": 2},
        "timeline_consistent": {"max": 5, "threshold": True},
        "bio_consistency": {"max": 5, "threshold": 0.70},
    }

    # Investor addon signal scoring
    INVESTOR_ADDONS = {
        "sec_edgar_filing": {"max": 10, "threshold": True},
        "crunchbase_exists": {"max": 5, "threshold": True},
        "portfolio_verified": {"max": 5, "threshold": 1},
        "form_adv_filed": {"max": 10, "threshold": True},
    }

    def __init__(self):
        pass

    def score(
        self,
        profile: ProfileInput,
        signals: VerificationSignals,
        investor_addon: InvestorAddonSignals,
    ) -> TrustScoreReport:
        report = TrustScoreReport(user_id=profile.user_id)
        report.signals = signals
        report.investor_addon = investor_addon

        total = 0

        # Score base signals
        for key, meta in self.BASE_SIGNALS.items():
            signal: SignalResult = getattr(signals, key)
            pts = self._calculate_points(signal.value, meta["threshold"], meta["max"])
            signal.points = pts
            signal.max_points = meta["max"]
            total += pts

        # Score investor addon (only if role is investor)
        if profile.role.lower() == "investor":
            for key, meta in self.INVESTOR_ADDONS.items():
                signal: SignalResult = getattr(investor_addon, key)
                pts = self._calculate_points(signal.value, meta["threshold"], meta["max"])
                signal.points = pts
                signal.max_points = meta["max"]
                total += pts

        report.trust_score = min(100, max(0, total))
        report.tier = self._tier_from_score(report.trust_score)

        # Hard flags for manual review
        self._apply_hard_flags(report, profile)

        return report

    def _calculate_points(self, value, threshold, max_points: int) -> int:
        """Calculate points based on signal value and threshold."""
        if isinstance(threshold, bool):
            return max_points if bool(value) else 0
        if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
            return max_points if value >= threshold else 0
        return 0

    def _tier_from_score(self, score: int) -> VerificationStatus:
        if score >= 85:
            return VerificationStatus.VERIFIED
        elif score >= 60:
            return VerificationStatus.LIKELY_LEGIT
        elif score >= 40:
            return VerificationStatus.UNVERIFIED
        return VerificationStatus.SUSPICIOUS

    def _apply_hard_flags(self, report: TrustScoreReport, profile: ProfileInput) -> None:
        s = report.signals

        # Disposable email = immediate review
        if s.email_deliverable.value is False or getattr(s.email_deliverable, "is_disposable", False):
            report.require_review("Disposable or undeliverable email")

        # LinkedIn name mismatch
        if isinstance(s.linkedin_verified.value, bool) and s.linkedin_verified.value:
            if hasattr(s.linkedin_verified, "name_match_score") and s.linkedin_verified.name_match_score < 60:
                report.require_review("LinkedIn name mismatch")

        # Stock photo
        if s.photo_reverse_search.value is False:
            report.require_review("Photo failed reverse image search or stock photo detected")

        # Too low score
        if report.trust_score < 40:
            report.require_review(f"Trust score too low: {report.trust_score}")

        # Impossible claim: brand new GitHub + senior claim
        if profile.role.lower() == "founder" and isinstance(s.github_public_repos.value, int):
            if s.github_public_repos.value < 1 and profile.experience:
                # If claiming 5+ years in tech but no GitHub presence
                report.add_flag("No GitHub presence despite technical founder claim")
