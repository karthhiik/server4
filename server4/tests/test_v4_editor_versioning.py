from __future__ import annotations

import copy
from typing import Any, Callable

import pytest
from fastapi import HTTPException

from app.routers import v4_editor
from app.routers.v4_editor import _ElementRegenerateBody, _SlicePatch, _SlidePatch, patch_slide, patch_slide_slice, regenerate_slide_element
from app.services.v4.regen_engine import ElementRegenerationResult
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import compile_slide


class FakeUpdateResult:
    def __init__(self, matched_count: int, modified_count: int) -> None:
        self.matched_count = matched_count
        self.modified_count = modified_count


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs

    def sort(self, key: str, direction: int) -> "FakeCursor":
        reverse = direction < 0
        self.docs.sort(key=lambda doc: self._get_path(doc, key) or "", reverse=reverse)
        return self

    def limit(self, count: int) -> "FakeCursor":
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        return copy.deepcopy(self.docs[:length] if length is not None else self.docs)

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


class FakeCollection:
    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = docs or []
        self.update_queries: list[dict[str, Any]] = []
        self.before_update: Callable[["FakeCollection"], None] | None = None

    async def find_one(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for doc in self.docs:
            if self._matches(doc, query):
                return copy.deepcopy(doc)
        return None

    async def find_one_and_update(self, query: dict[str, Any], update: dict[str, Any], return_document: bool = True) -> dict[str, Any] | None:
        self.update_queries.append(copy.deepcopy(query))
        if self.before_update:
            callback = self.before_update
            self.before_update = None
            callback(self)
        for doc in self.docs:
            if self._matches(doc, query):
                for path, value in (update.get("$set") or {}).items():
                    self._set_path(doc, path, value)
                return copy.deepcopy(doc)
        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> FakeUpdateResult:
        self.update_queries.append(copy.deepcopy(query))
        if self.before_update:
            callback = self.before_update
            self.before_update = None
            callback(self)
        for doc in self.docs:
            if self._matches(doc, query):
                for path, value in (update.get("$set") or {}).items():
                    self._set_path(doc, path, value)
                return FakeUpdateResult(1, 1)
        return FakeUpdateResult(0, 0)

    async def update_many(self, query: dict[str, Any], update: dict[str, Any]) -> FakeUpdateResult:
        self.update_queries.append(copy.deepcopy(query))
        matched = 0
        for doc in self.docs:
            if self._matches(doc, query):
                matched += 1
                for path, value in (update.get("$set") or {}).items():
                    self._set_path(doc, path, value)
        return FakeUpdateResult(matched, matched)

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self.docs.append(copy.deepcopy(doc))

    def find(self, query: dict[str, Any]) -> FakeCursor:
        return FakeCursor([copy.deepcopy(doc) for doc in self.docs if self._matches(doc, query)])

    def _matches(self, doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, expected in query.items():
            actual = self._get_path(doc, key)
            if isinstance(expected, dict) and "$gte" in expected:
                if actual is None or actual < expected["$gte"]:
                    return False
            elif isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif isinstance(expected, dict) and "$exists" in expected:
                exists = self._path_exists(doc, key)
                if bool(expected["$exists"]) != exists:
                    return False
            elif actual != expected:
                return False
        return True

    def _path_exists(self, doc: dict[str, Any], path: str) -> bool:
        current: Any = doc
        for part in path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return False
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if idx < 0 or idx >= len(current):
                    return False
                current = current[idx]
            else:
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
        self.slide_versions = FakeCollection([])
        self.v4_operation_ledger = FakeCollection([])

    def __getitem__(self, name: str) -> FakeCollection:
        if name == "v4_operation_ledger":
            return self.v4_operation_ledger
        raise KeyError(name)


def _compiled(*, headline: str = "Old headline", artifact_version: int = 3) -> dict[str, Any]:
    compiled = compile_slide(
        slide=GeneratedSlide(
            index=0,
            intent="title",
            layout="title-only",
            headline=headline,
            subheadline="Real subheadline",
        ),
    )
    compiled["artifact_version"] = artifact_version
    return compiled


def _slide_doc(*, headline: str = "Old headline", version: int = 1) -> dict[str, Any]:
    return {
        "_id": "slide-doc-0",
        "project_id": "project-versioning",
        "index": 0,
        "intent": "title",
        "layout": "title-only",
        "headline": headline,
        "subheadline": "Real subheadline",
        "bullets": [],
        "stat_blocks": [],
        "citations": [],
        "raw": {"source": "unit-test"},
        "version": version,
    }


def _db(*, slide_version: int = 1, artifact_version: int = 3) -> FakeDb:
    return FakeDb(
        {
            "_id": "project-versioning",
            "user_id": "dev-test-user",
            "title": "Versioning Deck",
            "compiled_slides": [_compiled(artifact_version=artifact_version)],
            "design_tokens": {},
        },
        _slide_doc(version=slide_version),
    )


@pytest.fixture(autouse=True)
def no_external_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_emit(*args: Any, **kwargs: Any) -> None:
        return None

    def _emitter(_project_id: str) -> Callable[[str, dict[str, Any]], Any]:
        return _noop_emit

    import app.services.v4.content_pipeline as content_pipeline

    monkeypatch.setattr(content_pipeline, "make_redis_progress_emitter", _emitter)
    v4_editor._DISPLAY_REPAIR_ATTEMPTS.clear()


@pytest.mark.asyncio
async def test_slice_edit_with_correct_artifact_version_persists_conditionally() -> None:
    db = _db(artifact_version=3)

    result = await patch_slide_slice(
        "project-versioning",
        0,
        _SlicePatch(
            expected_artifact_version=3,
            ops=[{"path": "headline", "value": "New headline", "op": "replace"}],
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert result["ok"] is True
    assert result["artifact_version"] == 4
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    assert persisted["artifact_version"] == 4
    assert persisted["artifacts"]["kit_jsx"]["props_json"]["headline"] == "New headline"
    assert db.presentations.update_queries[-1]["compiled_slides.0.artifact_version"] == 3


@pytest.mark.asyncio
async def test_slice_route_accepts_layout_variant_operation_name() -> None:
    db = _db(artifact_version=3)

    result = await patch_slide_slice(
        "project-versioning",
        0,
        _SlicePatch(
            expected_artifact_version=3,
            operation_id="layout-variant-unit-1",
            client_id="client-unit-1",
            ops=[{"path": "variant", "value": "solid", "op": "set-layout-variant"}],
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert result["ok"] is True
    assert result["artifact_version"] == 4
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    assert persisted["artifacts"]["kit_jsx"]["props_json"]["variant"] == "solid"
    assert db.v4_operation_ledger.docs[0]["_id"] == "layout-variant-unit-1"


@pytest.mark.asyncio
async def test_stale_slice_edit_returns_409_and_does_not_overwrite() -> None:
    db = _db(artifact_version=4)

    with pytest.raises(HTTPException) as exc:
        await patch_slide_slice(
            "project-versioning",
            0,
            _SlicePatch(
                expected_artifact_version=3,
                ops=[{"path": "headline", "value": "Stale headline", "op": "replace"}],
            ),
            user={"user_id": "dev-test-user"},
            db=db,  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "stale_artifact_version"
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    assert persisted["artifact_version"] == 4
    assert persisted["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Old headline"


@pytest.mark.asyncio
async def test_slice_race_after_read_returns_409_and_preserves_concurrent_edit() -> None:
    db = _db(artifact_version=3)

    def concurrent_update(collection: FakeCollection) -> None:
        current = collection.docs[0]["compiled_slides"][0]
        current["artifact_version"] = 4
        current["artifacts"]["kit_jsx"]["props_json"]["headline"] = "Concurrent headline"

    db.presentations.before_update = concurrent_update

    with pytest.raises(HTTPException) as exc:
        await patch_slide_slice(
            "project-versioning",
            0,
            _SlicePatch(
                expected_artifact_version=3,
                ops=[{"path": "headline", "value": "Lost update", "op": "replace"}],
            ),
            user={"user_id": "dev-test-user"},
            db=db,  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 409
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    assert persisted["artifact_version"] == 4
    assert persisted["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Concurrent headline"


@pytest.mark.asyncio
async def test_raw_slide_patch_with_correct_version_rebuilds_compiled_preview() -> None:
    db = _db(slide_version=1, artifact_version=3)

    result = await patch_slide(
        "project-versioning",
        0,
        _SlidePatch(expected_slide_version=1, headline="Semantic headline"),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert result["ok"] is True
    assert result["slide"]["version"] == 2
    assert db.slides.docs[0]["headline"] == "Semantic headline"
    assert db.slides.update_queries[-1] == {"_id": "slide-doc-0", "version": 1}
    compiled = db.presentations.docs[0]["compiled_slides"][0]
    assert compiled["artifact_version"] == 4
    assert compiled["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Semantic headline"


@pytest.mark.asyncio
async def test_element_regeneration_changes_only_requested_path_and_records_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _db(artifact_version=3)

    async def fake_regenerate_one_field(**kwargs: Any) -> ElementRegenerationResult:
        assert kwargs["path"] == "headline"
        return ElementRegenerationResult(
            ok=True,
            path="headline",
            value="AI regenerated headline",
            task_type="style_adaptation",
            changed=True,
        )

    monkeypatch.setattr(v4_editor, "regenerate_one_field", fake_regenerate_one_field)

    result = await regenerate_slide_element(
        "project-versioning",
        0,
        _ElementRegenerateBody(
            expected_artifact_version=3,
            operation_id="element-unit-1",
            client_id="client-unit-1",
            path="headline",
            kind="text",
            instruction="make it sharper",
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert result["ok"] is True
    assert result["artifact_version"] == 4
    persisted = db.presentations.docs[0]["compiled_slides"][0]
    props = persisted["artifacts"]["kit_jsx"]["props_json"]
    assert props["headline"] == "AI regenerated headline"
    assert props["subheadline"] == "Real subheadline"
    assert db.v4_operation_ledger.docs[0]["trigger"] == "element_regenerate"
    assert db.v4_operation_ledger.docs[0]["fields_changed"] == ["headline"]


@pytest.mark.asyncio
async def test_stale_raw_slide_patch_returns_409_and_does_not_update() -> None:
    db = _db(slide_version=2, artifact_version=3)

    with pytest.raises(HTTPException) as exc:
        await patch_slide(
            "project-versioning",
            0,
            _SlidePatch(expected_slide_version=1, headline="Stale semantic headline"),
            user={"user_id": "dev-test-user"},
            db=db,  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "stale_slide_version"
    assert db.slides.docs[0]["headline"] == "Old headline"
    assert db.presentations.docs[0]["compiled_slides"][0]["artifact_version"] == 3
