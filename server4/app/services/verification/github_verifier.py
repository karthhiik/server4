"""
GitHub profile verification for technical founders.
Uses your existing GITHUB_TOKEN in settings.
Free tier: 5,000 authenticated requests/hour.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.config import settings


class GitHubVerificationResult(BaseModel):
    username: str
    exists: bool = False
    public_repos: int = 0
    followers: int = 0
    account_created_at: Optional[datetime] = None
    recent_push_events: int = 0
    primary_languages: List[str] = []
    original_repos: int = 0
    is_fork_only: bool = False
    error: Optional[str] = None


class GitHubVerifier:
    """Async GitHub profile verifier."""

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.token = settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def verify(self, username: str) -> GitHubVerificationResult:
        result = GitHubVerificationResult(username=username)
        if not username:
            result.error = "No username provided"
            return result

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            # 1. User profile
            user_data = await self._get(client, f"/users/{username}")
            if user_data is None:
                result.error = "GitHub user not found"
                return result

            result.exists = True
            result.public_repos = user_data.get("public_repos", 0)
            result.followers = user_data.get("followers", 0)
            created_str = user_data.get("created_at")
            if created_str:
                result.account_created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

            # 2. Recent events (push activity in last 6 months)
            events = await self._get_list(client, f"/users/{username}/events/public?per_page=100")
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            push_count = 0
            for ev in events:
                created = ev.get("created_at")
                if created:
                    ev_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if ev_dt.replace(tzinfo=None) >= six_months_ago and ev.get("type") == "PushEvent":
                        push_count += 1
            result.recent_push_events = push_count

            # 3. Repo summary (original vs fork)
            repos = await self._get_list(client, f"/users/{username}/repos?per_page=100&sort=updated")
            forks = sum(1 for r in repos if r.get("fork", False))
            result.original_repos = len(repos) - forks
            result.is_fork_only = result.original_repos == 0 and len(repos) > 0

            # 4. Primary languages from non-fork repos
            langs: set[str] = set()
            for r in repos[:20]:  # limit API calls
                if r.get("fork"):
                    continue
                lang = r.get("language")
                if lang:
                    langs.add(lang)
            result.primary_languages = sorted(langs)

        return result

    async def _get(self, client: httpx.AsyncClient, path: str) -> Optional[Dict[str, Any]]:
        r = await client.get(f"{self.BASE_URL}{path}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return None

    async def _get_list(self, client: httpx.AsyncClient, path: str) -> List[Dict[str, Any]]:
        r = await client.get(f"{self.BASE_URL}{path}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
        return []
