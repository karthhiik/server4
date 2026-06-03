"""
Profile verification endpoints.
Triggers async verification pipeline and returns trust score reports.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.verification import ProfileInput, TrustScoreReport
from app.services.verification.pipeline import VerificationPipeline

router = APIRouter(prefix="/api/verification", tags=["Verification"])


@router.post("/profile", response_model=TrustScoreReport)
async def verify_profile(profile: ProfileInput) -> TrustScoreReport:
    """
    Run full verification pipeline on a profile and return trust score.
    Idempotent: safe to call multiple times; recalculates fresh each time.
    """
    pipeline = VerificationPipeline()
    try:
        report = await pipeline.verify(profile)
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification pipeline failed: {exc}",
        )


@router.post("/profile/quick")
async def verify_profile_quick(profile: ProfileInput) -> dict:
    """
    Lightweight verification: email + company website + LinkedIn existence only.
    Faster, fewer API calls. Returns raw signal dict without full trust scoring.
    """
    from app.services.verification.email_verifier import EmailVerifier
    from app.services.verification.linkedin_verifier import LinkedInVerifier

    email_v = EmailVerifier()
    li_v = LinkedInVerifier()

    email_res = await email_v.verify(profile.email, profile.company_website, profile.company_name)
    li_res = await li_v.verify(profile.linkedin_url, profile.full_name, profile.company_name)

    return {
        "user_id": profile.user_id,
        "email_deliverable": email_res.deliverable,
        "email_disposable": email_res.is_disposable,
        "email_domain_match": email_res.company_domain_match,
        "linkedin_exists": li_res.exists,
        "linkedin_name_match": li_res.name_match_score,
        "tier_hint": "likely_legit"
        if email_res.deliverable and li_res.exists
        else "unverified",
    }
