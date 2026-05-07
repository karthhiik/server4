from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from app.routers.v4_editor import (
    _CompiledHistoryMoveBody,
    _SlicePatch,
    get_compiled_slide_history,
    patch_slide_slice,
    redo_compiled_slide_operation,
    undo_compiled_slide_operation,
)
from test_v4_editor_versioning import _db


def _headline(db: Any) -> str:
    return db.presentations.docs[0]["compiled_slides"][0]["artifacts"]["kit_jsx"]["props_json"]["headline"]


def _artifact_version(db: Any) -> int:
    return db.presentations.docs[0]["compiled_slides"][0]["artifact_version"]


@pytest.mark.asyncio
async def test_slice_history_records_undo_and_redo_snapshots() -> None:
    db = _db(artifact_version=3)

    edit = await patch_slide_slice(
        "project-versioning",
        0,
        _SlicePatch(
            expected_artifact_version=3,
            operation_id="slice-unit-1",
            client_id="client-unit-1",
            ops=[{"path": "headline", "value": "Ledger headline", "op": "replace"}],
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert edit["operation_id"] == "slice-unit-1"
    assert _artifact_version(db) == 4
    assert _headline(db) == "Ledger headline"
    assert len(db.v4_operation_ledger.docs) == 1
    assert db.v4_operation_ledger.docs[0]["trigger"] == "slice_edit"
    assert db.v4_operation_ledger.docs[0]["before_artifact_version"] == 3
    assert db.v4_operation_ledger.docs[0]["after_artifact_version"] == 4

    history = await get_compiled_slide_history(
        "project-versioning",
        0,
        limit=50,
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )
    assert history["can_undo"] is True
    assert history["can_redo"] is False
    assert history["history"][0]["operation_id"] == "slice-unit-1"
    assert "before_compiled_slide" not in history["history"][0]

    undo = await undo_compiled_slide_operation(
        "project-versioning",
        0,
        _CompiledHistoryMoveBody(
            expected_artifact_version=4,
            operation_id="undo-unit-1",
            client_id="client-unit-1",
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert undo["ok"] is True
    assert undo["undone_operation_id"] == "slice-unit-1"
    assert undo["can_redo"] is True
    assert _artifact_version(db) == 5
    assert _headline(db) == "Old headline"

    redo = await redo_compiled_slide_operation(
        "project-versioning",
        0,
        _CompiledHistoryMoveBody(
            expected_artifact_version=5,
            operation_id="redo-unit-1",
            client_id="client-unit-1",
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    assert redo["ok"] is True
    assert redo["redone_operation_id"] == "undo-unit-1"
    assert redo["can_undo"] is True
    assert _artifact_version(db) == 6
    assert _headline(db) == "Ledger headline"
    assert [doc["trigger"] for doc in db.v4_operation_ledger.docs] == ["slice_edit", "undo", "redo"]


@pytest.mark.asyncio
async def test_new_slice_edit_after_undo_invalidates_redo_stack() -> None:
    db = _db(artifact_version=3)

    await patch_slide_slice(
        "project-versioning",
        0,
        _SlicePatch(
            expected_artifact_version=3,
            operation_id="slice-branch-1",
            client_id="client-unit-1",
            ops=[{"path": "headline", "value": "First branch", "op": "replace"}],
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )
    await undo_compiled_slide_operation(
        "project-versioning",
        0,
        _CompiledHistoryMoveBody(
            expected_artifact_version=4,
            operation_id="undo-branch-1",
            client_id="client-unit-1",
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    await patch_slide_slice(
        "project-versioning",
        0,
        _SlicePatch(
            expected_artifact_version=5,
            operation_id="slice-branch-2",
            client_id="client-unit-1",
            ops=[{"path": "headline", "value": "Second branch", "op": "replace"}],
        ),
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )

    undo_doc = next(doc for doc in db.v4_operation_ledger.docs if doc["_id"] == "undo-branch-1")
    assert undo_doc["invalidated_by"] == "slice-branch-2"
    history = await get_compiled_slide_history(
        "project-versioning",
        0,
        limit=50,
        user={"user_id": "dev-test-user"},
        db=db,  # type: ignore[arg-type]
    )
    assert history["can_redo"] is False
    assert _headline(db) == "Second branch"

    with pytest.raises(HTTPException) as exc:
        await redo_compiled_slide_operation(
            "project-versioning",
            0,
            _CompiledHistoryMoveBody(
                expected_artifact_version=6,
                operation_id="redo-branch-1",
                client_id="client-unit-1",
            ),
            user={"user_id": "dev-test-user"},
            db=db,  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "nothing_to_redo"
