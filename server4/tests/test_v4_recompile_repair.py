from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from app.config import settings
from app.routers import v4_editor
from app.routers.v4_editor import (
    _DisplayRepairBody,
    recompile_slide_display_artifact,
    repair_slide_display_artifact,
)
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import compile_slide


class FakeCollection:
    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = docs or []

    async def find_one(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return copy.deepcopy(doc)
        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                for path, value in (update.get("$set") or {}).items():
                    self._set_path(doc, path, value)
                return None
        return None

    async def count_documents(self, query: dict[str, Any]) -> int:
        count = 0
        for doc in self.docs:
            if self._matches(doc, query):
                count += 1
        return count

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self.docs.append(copy.deepcopy(doc))
        return None

    def _matches(self, doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, expected in query.items():
            actual = self._get_path(doc, key)
            if isinstance(expected, dict) and "$gte" in expected:
                if actual is None or actual < expected["$gte"]:
                    return False
            elif actual != expected:
                return False
        return True

    def _get_path(self, doc: dict[str, Any], path: str) -> Any:
        current: Any = doc
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
        return current

    def _set_path(self, doc: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split(".")
        current: Any = doc
        for part in parts[:-1]:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                raise AssertionError(f"unsupported path {path}")
        last = parts[-1]
        if isinstance(current, dict):
            current[last] = value
        elif isinstance(current, list) and last.isdigit():
            current[int(last)] = value
        else:
            raise AssertionError(f"unsupported path {path}")


class FakeDb:
    def __init__(self, presentation: dict[str, Any], slide_doc: dict[str, Any]) -> None:
        self.presentations = FakeCollection([presentation])
        self.slides = FakeCollection([slide_doc])
        self.collections: dict[str, FakeCollection] = {
            settings.QUALITY_METRICS_COLLECTION: FakeCollection([]),
        }

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self.collections:
            self.collections[name] = FakeCollection([])
        return self.collections[name]


def _slide_doc() -> dict[str, Any]:
    return {
        "_id": "slide-doc-0",
        "project_id": "project-repair",
        "index": 0,
        "intent": "title",
        "layout": "title-only",
        "headline": "Real saved headline",
        "subheadline": "Real saved subheadline",
        "bullets": [],
        "stat_blocks": [],
        "citations": [],
        "raw": {"source": "unit-test"},
    }


def _compiled() -> dict[str, Any]:
    compiled = compile_slide(slide=GeneratedSlide(index=0, intent="title", layout="title-only", headline="Real saved headline", subheadline="Real saved subheadline"))
    compiled["artifact_version"] = 1
    return compiled


def _db() -> FakeDb:
    slide_doc = _slide_doc()
    return FakeDb(
        {
            "_id": "project-repair",
            "user_id": "dev-test-user",
            "title": "Repair Deck",
            "compiled_slides": [_compiled()],
            "design_tokens": {},
        },
        slide_doc,
    )


@pytest.fixture(autouse=True)
def no_external_emit_or_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_emit(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(v4_editor, "_emit_display_repair", _noop_emit)
    monkeypatch.setattr(v4_editor, "record_quality_event", _noop_emit)
    v4_editor._DISPLAY_REPAIR_ATTEMPTS.clear()


@pytest.mark.asyncio
async def test_recompile_rebuilds_artifact_without_mutating_source_slide() -> None:
    db = _db()
    before_slide_doc = copy.deepcopy(db.slides.docs[0])

    result = await recompile_slide_display_artifact(
        "project-repair",
        0,
        _DisplayRepairBody(issue_code="compile_props_parse_failed", source="preview"),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert result["ok"] is True
    assert result["artifact_version"] == 2
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    assert persisted["artifact_version"] == 2
    assert persisted["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Real saved headline"
    assert db.slides.docs[0] == before_slide_doc


@pytest.mark.asyncio
async def test_repair_refuses_to_fabricate_missing_content_or_images() -> None:
    with pytest.raises(HTTPException) as exc:
        await repair_slide_display_artifact(
            "project-repair",
            0,
            _DisplayRepairBody(issue_code="data_empty_required", source="preview"),
            user={"user_id": "dev-test-user"},
            db=_db(),  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_repair_circuit_counts_persisted_attempts() -> None:
    db = _db()

    first = await repair_slide_display_artifact(
        "project-repair",
        0,
        _DisplayRepairBody(issue_code="runtime_kit_failed", source="preview"),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )
    assert first["ok"] is True

    with pytest.raises(HTTPException) as exc:
        await repair_slide_display_artifact(
            "project-repair",
            0,
            _DisplayRepairBody(issue_code="runtime_kit_failed", source="preview"),
            user={"user_id": "dev-test-user"},
            db=db,  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 409
    attempts = [doc for doc in db[settings.QUALITY_METRICS_COLLECTION].docs if doc.get("event") == "display_repair_attempt"]
    assert len(attempts) == 1
    assert attempts[0]["tags"]["issue_code"] == "runtime_kit_failed"
