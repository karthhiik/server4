"""
Shareable Link Service — Phase 3 (permissioned share contract).

Manages shareable presentation links with full permission, access mode,
allowlist, and version-pin support. Replaces the v4-4 minimal shape.

Schema (mirrors the frontend contract)::

    visibility: "public" | "private"
    access:     "view" | "edit"
    allowed_emails: list[str]      # private only
    allowed_usernames: list[str]   # private only
    require_email: bool             # public — viewer must enter email
    password_enabled: bool          # link is gated by a password
    expires_at: datetime | None
    version_mode: "snapshot" | "live_latest"
    snapshot_version: int | None    # set when version_mode=="snapshot"

Passwords are hashed with bcrypt; the plaintext is never stored. Links
can be revoked (``is_active=False``) or extended (``expires_at``).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import structlog

logger = structlog.get_logger(__name__)


# ── Allowed enum literals ─────────────────────────────────────────


VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"
ACCESS_VIEW = "view"
ACCESS_EDIT = "edit"
VERSION_SNAPSHOT = "snapshot"
VERSION_LIVE_LATEST = "live_latest"


_VALID_VISIBILITY = {VISIBILITY_PUBLIC, VISIBILITY_PRIVATE}
_VALID_ACCESS = {ACCESS_VIEW, ACCESS_EDIT}
_VALID_VERSION_MODE = {VERSION_SNAPSHOT, VERSION_LIVE_LATEST}


def _as_utc_aware(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetimes read from Mongo/Cosmos to aware UTC.

    Motor can return naive datetimes even when we wrote aware UTC
    values. Share validation compares against ``datetime.now(timezone.utc)``,
    so normalize here before any comparison.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass
class ShareLink:
    """Shareable-link record. Fields without defaults are required."""

    share_id: str
    project_id: str
    created_at: datetime

    # Permission contract
    visibility: str = VISIBILITY_PUBLIC          # "public" | "private"
    access: str = ACCESS_VIEW                    # "view" | "edit"
    allowed_emails: list[str] = field(default_factory=list)
    allowed_usernames: list[str] = field(default_factory=list)
    require_email: bool = False
    password_hash: Optional[str] = None          # bcrypt hash, never plaintext

    # Lifecycle
    expires_at: Optional[datetime] = None
    is_active: bool = True
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    # Version pin
    version_mode: str = VERSION_LIVE_LATEST      # "snapshot" | "live_latest"
    snapshot_version: Optional[int] = None       # only set when version_mode == "snapshot"

    # Optional founder-authored note shown inside the public viewer.
    viewer_note_enabled: bool = False
    viewer_note: Optional[str] = None

    # Telemetry counters (lazy)
    view_count: int = 0
    last_viewed_at: Optional[datetime] = None
    last_viewed_by: Optional[str] = None         # email when require_email=True


# ── Service ──────────────────────────────────────────────────────


class ShareService:
    """Service for creating, validating, and authorizing share links."""

    def __init__(self) -> None:
        self.logger = logger

    # ── ID + URL ─────────────────────────────────────────────────

    def generate_share_id(self) -> str:
        """Cryptographically random share id (~16 chars, URL-safe)."""
        return secrets.token_urlsafe(12)

    def get_share_url(
        self,
        share_id: str,
        base_url: str = "https://barise.ai",
    ) -> str:
        # The migrated frontend mounts the public viewer at
        # `/presentations/share/:shareId` (the destination app's
        # routing namespace). Earlier the route was `/share/:shareId`
        # which only existed on the standalone barise-editorial-main
        # build; opening that URL on the destination app showed
        # "Couldn't open deck." The destination keeps a redirect from
        # the old path to the new one for safety, but every newly
        # minted share URL points to the canonical namespaced route.
        return f"{base_url.rstrip('/')}/presentations/share/{share_id}"

    # ── Password handling ────────────────────────────────────────

    @staticmethod
    def hash_password(plaintext: str) -> str:
        """bcrypt-hash a plaintext password. Never store the plaintext."""
        if not plaintext:
            raise ValueError("password must be non-empty")
        digest = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt())
        return digest.decode("utf-8")

    @staticmethod
    def verify_password_hash(hash_value: Optional[str], plaintext: str) -> bool:
        """Constant-time check against a stored bcrypt hash."""
        if not hash_value:
            # No hash on file → only valid if the caller supplied no password.
            return not plaintext
        try:
            return bcrypt.checkpw(plaintext.encode("utf-8"), hash_value.encode("utf-8"))
        except Exception:  # noqa: BLE001
            return False

    # ── Create / mutate ───────────────────────────────────────────

    def create_share_link(
        self,
        *,
        project_id: str,
        visibility: str = VISIBILITY_PUBLIC,
        access: str = ACCESS_VIEW,
        allowed_emails: Optional[list[str]] = None,
        allowed_usernames: Optional[list[str]] = None,
        require_email: bool = False,
        password: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        version_mode: str = VERSION_LIVE_LATEST,
        snapshot_version: Optional[int] = None,
        viewer_note_enabled: bool = False,
        viewer_note: Optional[str] = None,
    ) -> ShareLink:
        """Validate inputs and return an in-memory ShareLink record.

        Caller persists it via ``db.share_links.insert_one(...)``.
        """
        if visibility not in _VALID_VISIBILITY:
            raise ValueError(f"visibility must be one of {_VALID_VISIBILITY}")
        if access not in _VALID_ACCESS:
            raise ValueError(f"access must be one of {_VALID_ACCESS}")
        if version_mode not in _VALID_VERSION_MODE:
            raise ValueError(f"version_mode must be one of {_VALID_VERSION_MODE}")
        # snapshot_version is allowed to be None — the route layer
        # mints the actual version number when persisting the snapshot.
        # We just enforce that it's an int when supplied.
        if snapshot_version is not None and not isinstance(snapshot_version, int):
            raise ValueError("snapshot_version must be an int when supplied")

        # Normalize allowlists (lower-case emails, strip whitespace).
        emails = [e.strip().lower() for e in (allowed_emails or []) if e and e.strip()]
        usernames = [u.strip() for u in (allowed_usernames or []) if u and u.strip()]
        if visibility == VISIBILITY_PRIVATE and not (emails or usernames):
            raise ValueError(
                "private link requires at least one allowed_email or allowed_username"
            )

        share_id = self.generate_share_id()
        created_at = datetime.now(timezone.utc)
        expires_at = (
            created_at + timedelta(days=int(expires_in_days))
            if expires_in_days
            else None
        )

        password_hash = self.hash_password(password) if password else None

        link = ShareLink(
            share_id=share_id,
            project_id=project_id,
            created_at=created_at,
            visibility=visibility,
            access=access,
            allowed_emails=emails,
            allowed_usernames=usernames,
            require_email=bool(require_email),
            password_hash=password_hash,
            expires_at=expires_at,
            is_active=True,
            revoked_at=None,
            revoked_reason=None,
            version_mode=version_mode,
            snapshot_version=snapshot_version,
            viewer_note_enabled=bool(viewer_note_enabled and viewer_note),
            viewer_note=viewer_note.strip() if viewer_note and viewer_note.strip() else None,
            view_count=0,
            last_viewed_at=None,
            last_viewed_by=None,
        )

        self.logger.info(
            "share_link_created",
            share_id=share_id,
            project_id=project_id,
            visibility=visibility,
            access=access,
            version_mode=version_mode,
            expires_at=expires_at.isoformat() if expires_at else None,
            has_password=bool(password_hash),
            allowed_emails_count=len(emails),
        )
        return link

    # ── Validity gates ────────────────────────────────────────────

    def is_share_valid(self, link: ShareLink) -> bool:
        if not link.is_active:
            return False
        expires_at = _as_utc_aware(link.expires_at)
        if expires_at and datetime.now(timezone.utc) > expires_at:
            return False
        return True

    def authorize_viewer(
        self,
        link: ShareLink,
        *,
        password: Optional[str] = None,
        viewer_email: Optional[str] = None,
        viewer_username: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Decide whether this viewer can see the deck.

        Returns ``(allowed, reason)`` so callers can emit clean
        diagnostics — never throw, the route layer maps the reason to
        an HTTP status.
        """
        if not self.is_share_valid(link):
            return False, "share_inactive_or_expired"

        # Password gate (applies regardless of visibility).
        if link.password_hash:
            if not password:
                return False, "password_required"
            if not self.verify_password_hash(link.password_hash, password):
                return False, "password_invalid"

        # Public — anyone with link, optionally collecting email.
        if link.visibility == VISIBILITY_PUBLIC:
            if link.require_email and not viewer_email:
                return False, "email_required"
            return True, "ok"

        # Private — must match an allowlist entry.
        email_lc = (viewer_email or "").strip().lower()
        username = (viewer_username or "").strip()
        if email_lc and email_lc in link.allowed_emails:
            return True, "ok"
        if username and username in link.allowed_usernames:
            return True, "ok"
        return False, "viewer_not_allowlisted"

    def authorize_editor(
        self,
        link: ShareLink,
        *,
        password: Optional[str] = None,
        viewer_email: Optional[str] = None,
        viewer_username: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Edit access requires the link to be in edit mode AND the
        viewer to pass the standard gate."""
        if link.access != ACCESS_EDIT:
            return False, "edit_not_allowed"
        return self.authorize_viewer(
            link,
            password=password,
            viewer_email=viewer_email,
            viewer_username=viewer_username,
        )

    # ── Mutations (returned so the caller can persist) ───────────

    def increment_view_count(
        self,
        link: ShareLink,
        *,
        viewer_email: Optional[str] = None,
    ) -> ShareLink:
        link.view_count += 1
        link.last_viewed_at = datetime.now(timezone.utc)
        if viewer_email:
            link.last_viewed_by = viewer_email.strip().lower()
        return link

    def revoke(self, link: ShareLink, reason: str = "manual_revoke") -> ShareLink:
        link.is_active = False
        link.revoked_at = datetime.now(timezone.utc)
        link.revoked_reason = reason[:200]
        return link
