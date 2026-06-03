"""
Email verification service.
Checks deliverability, MX records, disposable domains, and company-domain alignment.
Zero-cost tier: DNS + local disposable domain list.
"""

import asyncio
from typing import Dict, List, Optional, Tuple

import dns.resolver
import httpx
from pydantic import BaseModel

from app.config import settings
from app.services.llm.model_router import ModelRouter, TaskType


# Top disposable email domains (subset; load full list from file in production)
DISPOSABLE_DOMAINS: set[str] = {
    "10minutemail.com", "guerrillamail.com", "mailinator.com", "tempmail.com",
    "throwawaymail.com", "yopmail.com", "sharklasers.com", "getairmail.com",
    "burnermail.io", "temp-mail.org", "mailnesia.com", "discard.email",
    "trashmail.com", "fakeinbox.com", "getnada.com", "inboxalias.com",
    "mailcatch.com", "mohmal.com", "mytemp.email", "spamgourmet.com",
    "tempinbox.com", "guerrillamail.net", "guerrillamail.org", "guerrillamail.de",
    "mailinator.net", "mailinator.org", "chacuo.net", "bccto.me",
    "bbdss.com", "smashmail.de", "wegwerfmail.de", "wegwerfmail.net",
    "wegwerfmail.org", "jetable.org", "tempail.com", "tmpmail.org",
}


def _domain(email: str) -> str:
    return email.lower().split("@")[-1]


def _normalize_domain(url_or_domain: str) -> str:
    """Strip protocol, www, and trailing paths from a URL or domain."""
    d = url_or_domain.lower().strip()
    if d.startswith("http://"):
        d = d[7:]
    elif d.startswith("https://"):
        d = d[8:]
    if d.startswith("www."):
        d = d[4:]
    d = d.split("/")[0]
    return d


class EmailVerificationResult(BaseModel):
    email: str
    deliverable: bool = False
    mx_valid: bool = False
    is_disposable: bool = False
    domain: str = ""
    mx_records: List[str] = []
    company_domain_match: bool = False
    error: Optional[str] = None


class EmailVerifier:
    """Async email verifier with free-tier API fallbacks."""

    def __init__(self):
        self.disposable_domains = DISPOSABLE_DOMAINS

    async def verify(
        self,
        email: str,
        company_website: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> EmailVerificationResult:
        domain = _domain(email)
        result = EmailVerificationResult(email=email, domain=domain)

        # 1. Disposable check (free, local)
        if domain in self.disposable_domains:
            result.is_disposable = True
            return result

        # 2. DNS MX lookup (free, local)
        try:
            mx_records = await self._mx_lookup(domain)
            result.mx_records = mx_records
            result.mx_valid = len(mx_records) > 0
            result.deliverable = result.mx_valid
        except Exception as e:
            result.error = f"MX lookup failed: {e}"
            return result

        # 3. Company domain alignment
        if company_website:
            company_domain = _normalize_domain(company_website)
            if company_domain and domain:
                # Exact match OR known parent corp mapping
                result.company_domain_match = self._domains_match(domain, company_domain)

        # 4. (Optional) Free API fallback for deeper deliverability
        # Uncomment when you have ZeroBounce / Hunter keys:
        # api_result = await self._check_with_zerobounce(email)
        # if api_result:
        #     result.deliverable = api_result.get("deliverable", result.deliverable)

        return result

    async def _mx_lookup(self, domain: str) -> List[str]:
        """Async MX record lookup via aiodns or threaded dns.resolver."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_mx_lookup, domain)

    def _sync_mx_lookup(self, domain: str) -> List[str]:
        answers = dns.resolver.resolve(domain, "MX")
        return [str(r.exchange).rstrip(".") for r in answers]

    def _domains_match(self, email_domain: str, company_domain: str) -> bool:
        """Check if email domain matches company domain exactly or as parent."""
        ed = email_domain.lower().strip()
        cd = company_domain.lower().strip()
        if ed == cd:
            return True
        # Sub-domain match: e.g., john@eng.apple.com vs apple.com
        if ed.endswith("." + cd):
            return True
        # Known alias mappings (expand as needed)
        aliases: Dict[str, str] = {
            "fb.com": "facebook.com",
            "googlemail.com": "gmail.com",
        }
        if aliases.get(ed, ed) == cd:
            return True
        return False

    async def _check_with_zerobounce(self, email: str) -> Optional[Dict]:
        """ZeroBounce free tier: 100 credits/mo."""
        # Add ZEROBOUNCE_API_KEY to .env and settings to enable
        api_key = getattr(settings, "ZEROBOUNCE_API_KEY", None)
        if not api_key:
            return None
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.zerobounce.net/v2/validate",
                params={"api_key": api_key, "email": email},
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "deliverable": data.get("status") == "valid",
                    "free_email": data.get("free_email"),
                    "did_you_mean": data.get("did_you_mean"),
                }
        return None

    async def _check_with_hunter(self, email: str) -> Optional[Dict]:
        """Hunter.io free tier: 25 verifications/mo."""
        api_key = getattr(settings, "HUNTER_API_KEY", None)
        if not api_key:
            return None
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": api_key},
            )
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {
                    "deliverable": data.get("status") == "valid",
                    "score": data.get("score"),
                    "source": "hunter",
                }
        return None
