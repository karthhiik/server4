from __future__ import annotations

import json
import time

from app.services.v4.content_pipeline import TEAM_RESOLUTION_TIMEOUT_S
from app.services.v4.schema_guard import validate_writer_output


def test_team_resolution_budget_stays_non_blocking() -> None:
    assert TEAM_RESOLUTION_TIMEOUT_S <= 0.75


def test_writer_schema_validation_overhead_stays_under_budget() -> None:
    payload = json.dumps({
        "headline": "Verified onboarding risk falls when evidence is visible",
        "subheadline": "A real slide with enough visible content for schema validation.",
        "bullets": ["Approvals stay traceable", "Reviewers see source context"],
        "citations": [{"url": "https://docs.python.org/3/library/json.html", "title": "Python JSON docs"}],
    })

    start = time.perf_counter()
    for index in range(50):
        parsed = validate_writer_output(payload, slide_index=index)
        assert parsed["headline"].startswith("Verified onboarding")
    per_slide_ms = (time.perf_counter() - start) * 1000 / 50

    assert per_slide_ms < 50.0
