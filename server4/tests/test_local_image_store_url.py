from __future__ import annotations

import pytest

from app.config import settings
from app.services.storage import local_image_store


def test_public_base_url_allows_localhost_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8003")

    assert local_image_store._public_base_url() == "http://127.0.0.1:8003"


def test_public_base_url_rejects_localhost_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8003")

    with pytest.raises(RuntimeError, match="PUBLIC_BASE_URL must be a public HTTPS URL"):
        local_image_store._public_base_url()


def test_public_base_url_requires_https_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "http://api.pitchduck.com")

    with pytest.raises(RuntimeError, match="PUBLIC_BASE_URL must be a public HTTPS URL"):
        local_image_store._public_base_url()


def test_public_base_url_accepts_public_https_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://api.pitchduck.com/")

    assert local_image_store._public_base_url() == "https://api.pitchduck.com"
