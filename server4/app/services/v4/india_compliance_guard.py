"""
India Compliance Guardian — ensures pitch decks comply with Indian regulatory requirements.

This service checks for:
- Data localization (data stored within India)
- Privacy compliance (DPDP Act 2023)
- Financial disclosures (SEBI requirements for startups)
- Content restrictions (avoiding prohibited content)
- GST compliance mentions
- Company registration verification
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class ComplianceLevel(Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


@dataclass
class ComplianceIssue:
    code: str
    severity: ComplianceLevel
    message: str
    recommendation: str
    section: Optional[str] = None


@dataclass
class ComplianceReport:
    overall_status: ComplianceLevel
    issues: list[ComplianceIssue]
    score: float  # 0-100
    summary: str


class IndiaComplianceGuard:
    """Guardian for Indian regulatory compliance in pitch decks."""

    # India-specific compliance rules
    DATA_LOCALIZATION_KEYWORDS = [
        "data center",
        "data storage",
        "server location",
        "data residency",
    ]

    PRIVACY_KEYWORDS = [
        "privacy policy",
        "data protection",
        "consent",
        "data processing",
        "user data",
    ]

    FINANCIAL_DISCLOSURE_KEYWORDS = [
        "revenue",
        "funding",
        "investment",
        "valuation",
        "profit",
        "loss",
        "financials",
    ]

    GST_KEYWORDS = [
        "gst",
        "goods and services tax",
        "tax registration",
        "tax compliance",
    ]

    COMPANY_REGISTRATION_KEYWORDS = [
        "cin",
        "company identification number",
        "incorporated",
        "registered office",
        "mca",
    ]

    PROHIBITED_CONTENT = [
        "guaranteed returns",
        "risk-free investment",
        "assured profits",
        "government approved",
        "rbi approved",  # Unless actually RBI approved
    ]

    def __init__(self):
        self.issues: list[ComplianceIssue] = []

    def check_compliance(self, slide_content: str, metadata: dict) -> ComplianceReport:
        """Run full compliance check on presentation content."""
        self.issues = []
        content_lower = slide_content.lower()

        # Check data localization
        self._check_data_localization(content_lower, metadata)

        # Check privacy compliance
        self._check_privacy_compliance(content_lower)

        # Check financial disclosures
        self._check_financial_disclosures(content_lower)

        # Check GST compliance
        self._check_gst_compliance(content_lower)

        # Check company registration
        self._check_company_registration(content_lower)

        # Check prohibited content
        self._check_prohibited_content(content_lower)

        # Calculate overall status and score
        overall_status, score, summary = self._calculate_overall_status()

        return ComplianceReport(
            overall_status=overall_status,
            issues=self.issues,
            score=score,
            summary=summary,
        )

    def _check_data_localization(self, content: str, metadata: dict) -> None:
        """Check if data localization is mentioned for Indian users."""
        has_data_keywords = any(kw in content for kw in self.DATA_LOCALIZATION_KEYWORDS)
        has_india_context = "india" in content or "indian" in content

        if has_india_context and has_data_keywords:
            # Check if India-specific data storage is mentioned
            if "india" not in content and "data" in content:
                self.issues.append(
                    ComplianceIssue(
                        code="DATA_LOC_001",
                        severity=ComplianceLevel.WARNING,
                        message="Data storage location not specified for Indian users",
                        recommendation="Mention data centers located in India or data localization compliance",
                        section="Data Storage",
                    )
                )
        elif has_india_context:
            self.issues.append(
                ComplianceIssue(
                    code="DATA_LOC_002",
                    severity=ComplianceLevel.WARNING,
                    message="Data localization strategy not mentioned",
                    recommendation="Consider adding data localization information for Indian market",
                    section="Data Storage",
                )
            )

    def _check_privacy_compliance(self, content: str) -> None:
        """Check for privacy policy and data protection mentions."""
        has_privacy_keywords = any(kw in content for kw in self.PRIVACY_KEYWORDS)

        if not has_privacy_keywords:
            self.issues.append(
                ComplianceIssue(
                    code="PRIVACY_001",
                    severity=ComplianceLevel.WARNING,
                    message="Privacy policy or data protection not mentioned",
                    recommendation="Add privacy policy reference and DPDP Act 2023 compliance statement",
                    section="Privacy",
                )
            )

    def _check_financial_disclosures(self, content: str) -> None:
        """Check for proper financial disclosures per SEBI guidelines."""
        has_financial_keywords = any(kw in content for kw in self.FINANCIAL_DISCLOSURE_KEYWORDS)

        if has_financial_keywords:
            # Check for disclaimer language
            if "disclaimer" not in content and "risk" not in content:
                self.issues.append(
                    ComplianceIssue(
                        code="FIN_001",
                        severity=ComplianceLevel.WARNING,
                        message="Financial data without proper disclaimer",
                        recommendation="Add standard investment disclaimer per SEBI guidelines",
                        section="Financials",
                    )
                )

    def _check_gst_compliance(self, content: str) -> None:
        """Check for GST registration and compliance mentions."""
        has_business_keywords = any(
            kw in content for kw in ["revenue", "sales", "business", "startup"]
        )

        if has_business_keywords and not any(kw in content for kw in self.GST_KEYWORDS):
            self.issues.append(
                ComplianceIssue(
                    code="GST_001",
                    severity=ComplianceLevel.WARNING,
                    message="GST compliance not mentioned",
                    recommendation="Consider adding GST registration and compliance information",
                    section="Legal",
                )
            )

    def _check_company_registration(self, content: str) -> None:
        """Check for company registration details."""
        has_company_keywords = any(
            kw in content for kw in ["private limited", "pvt ltd", "llp", "incorporated"]
        )

        if has_company_keywords and not any(
            kw in content for kw in self.COMPANY_REGISTRATION_KEYWORDS
        ):
            self.issues.append(
                ComplianceIssue(
                    code="COMP_001",
                    severity=ComplianceLevel.WARNING,
                    message="Company registration details incomplete",
                    recommendation="Add CIN or company registration number",
                    section="Legal",
                )
            )

    def _check_prohibited_content(self, content: str) -> None:
        """Check for prohibited investment claims."""
        for phrase in self.PROHIBITED_CONTENT:
            if phrase in content:
                self.issues.append(
                    ComplianceIssue(
                        code="PROHIBITED_001",
                        severity=ComplianceLevel.NON_COMPLIANT,
                        message=f"Prohibited phrase: '{phrase}'",
                        recommendation="Remove prohibited investment claims per SEBI regulations",
                        section="Content",
                    )
                )

    def _calculate_overall_status(self) -> tuple[ComplianceLevel, float, str]:
        """Calculate overall compliance status and score."""
        if not self.issues:
            return ComplianceLevel.COMPLIANT, 100.0, "Fully compliant with Indian regulations"

        non_compliant_count = sum(
            1 for issue in self.issues if issue.severity == ComplianceLevel.NON_COMPLIANT
        )
        warning_count = sum(
            1 for issue in self.issues if issue.severity == ComplianceLevel.WARNING
        )

        if non_compliant_count > 0:
            score = max(0, 50 - non_compliant_count * 20)
            return (
                ComplianceLevel.NON_COMPLIANT,
                score,
                f"Non-compliant: {non_compliant_count} critical issue(s) found",
            )

        if warning_count > 0:
            score = max(60, 100 - warning_count * 10)
            return (
                ComplianceLevel.WARNING,
                score,
                f"Warning: {warning_count} recommendation(s) for better compliance",
            )

        return ComplianceLevel.COMPLIANT, 100.0, "Fully compliant with Indian regulations"
