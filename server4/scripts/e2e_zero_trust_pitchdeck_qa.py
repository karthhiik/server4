"""End-to-end QA harness for the zero-trust edge pitch-deck prompt.

This script exercises the real V4 HTTP surface exactly as a user would:

1. Generate Standard and Premium decks from the same prompt.
2. Poll generation status until completion.
3. Export slide-content JSON, compiled preview JSON, PDF, PPTX.
4. Render PDF page snapshots.
5. Score prompt coverage, narrative hygiene, design artifacts, and edit routes.

It intentionally does not import the pipeline directly. If a route, payload
contract, fallback model, compiler, export, or editor endpoint breaks, the
report should capture that production-facing failure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx


PROMPT = """Presentation Topic: Autonomous Zero-Trust Identity Orchestration for Edge Computing.
Description: We are building a self-healing security layer for IoT devices that uses decentralized identifiers (DIDs) and zero-knowledge proofs. It must explain how we eliminate the need for a central authority while maintaining sub-millisecond authentication latency in low-bandwidth environments. Key points: $O(1)$ scalability, hardware-root-of-trust integration, and our "Neural-Guardian" consensus algorithm.
Target Audience: Technical VCs and Senior Security Architects.
Purpose: Investor Pitch.
Slide Count: 15."""

TARGET_SLIDE_COUNT = 15

REQUIRED_CONCEPTS: list[tuple[str, list[str]]] = [
    ("autonomous", [r"\bautonomous\b"]),
    ("zero_trust", [r"\bzero[- ]trust\b", r"\bzero trust\b"]),
    ("identity_orchestration", [r"\bidentity orchestration\b", r"\borchestrat\w+ identit"]),
    ("edge_computing", [r"\bedge computing\b", r"\bedge\b"]),
    ("iot_devices", [r"\biot\b", r"\bdevice fleet\b", r"\bconnected devices\b"]),
    ("self_healing", [r"\bself[- ]healing\b", r"\bauto[- ]remediat"]),
    ("dids", [r"\bDIDs?\b", r"\bdecentralized identifiers?\b"]),
    ("zkp", [r"\bzero[- ]knowledge\b", r"\bZKPs?\b", r"\bzk proof"]),
    ("no_central_authority", [r"\bcentral authorit", r"\bdecentralized trust\b", r"\bwithout centralized"]),
    ("sub_millisecond_latency", [r"\bsub[- ]millisecond\b", r"\b<\s*1\s*ms\b", r"\bless than 1\s*ms\b"]),
    ("low_bandwidth", [r"\blow[- ]bandwidth\b", r"\bbandwidth[- ]constrained\b"]),
    ("o1_scalability", [r"\bO\(1\)\b", r"\bconstant[- ]time\b", r"\bconstant time\b"]),
    ("hardware_root_of_trust", [r"\bhardware[- ]root[- ]of[- ]trust\b", r"\broot of trust\b", r"\bsecure element\b", r"\bTPM\b"]),
    ("neural_guardian", [r"\bNeural[- ]Guardian\b"]),
    ("consensus_algorithm", [r"\bconsensus algorithm\b", r"\bconsensus\b"]),
    ("technical_vcs", [r"\btechnical VCs?\b", r"\binvestors?\b", r"\bVCs?\b"]),
    ("security_architects", [r"\bsecurity architects?\b", r"\barchitects?\b"]),
    ("investor_pitch", [r"\binvestor pitch\b", r"\bfundrais", r"\binvestment\b", r"\bventure\b"]),
]

NARRATIVE_BEATS: list[tuple[str, list[str]]] = [
    ("cover", [r"\bautonomous\b", r"\bzero[- ]trust\b", r"\btitle\b"]),
    ("problem", [r"\bproblem\b", r"\bpain\b", r"\battack surface\b", r"\bcentral authorit"]),
    ("solution", [r"\bsolution\b", r"\bplatform\b", r"\borchestration\b"]),
    ("architecture", [r"\barchitecture\b", r"\bhow it works\b", r"\bDID\b", r"\bZKP\b"]),
    ("performance", [r"\bsub[- ]millisecond\b", r"\blatency\b", r"\bO\(1\)\b"]),
    ("market", [r"\bmarket\b", r"\bopportunity\b", r"\bIoT\b", r"\bedge\b"]),
    ("business", [r"\bbusiness model\b", r"\bpricing\b", r"\bgo[- ]to[- ]market\b"]),
    ("moat", [r"\bmoat\b", r"\bdifferenti", r"\bcompetitive\b"]),
    ("roadmap", [r"\broadmap\b", r"\bmilestone\b", r"\bdeployment\b"]),
    ("ask", [r"\bask\b", r"\binvestment\b", r"\bfunding\b", r"\bnext step"]),
]

BAD_COPY_PATTERNS: list[tuple[str, str]] = [
    ("lorem_ipsum", r"\blorem\s+ipsum\b"),
    ("tbd_marker", r"\b(TBD|TBA|TODO|FIXME|XXX)\b"),
    ("template_token", r"\{\{\s*[a-z_][a-z0-9_]*\s*\}\}"),
    ("your_company", r"\[?\byour\s+(company|startup|product|brand)\b\]?"),
    ("generic_unlock", r"\bunlock(ing)?\s+(the\s+)?potential\b"),
    ("transform_industries", r"\btransform(ing)?\s+industr"),
    ("cutting_edge", r"\bcutting[- ]edge\b"),
    ("placeholder_url", r"https?://(www\.)?(example|test)\.(com|org|net)\b"),
]


def _now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _http_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = response.text[:2000]
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {body}") from exc
    if not response.content:
        return None
    return response.json()


def _payload_for(mode: str) -> dict[str, Any]:
    if mode == "standard":
        return {
            "mode": "standard",
            "input_method": "prompt",
            "standard_input": {
                "prompt": PROMPT,
                "slide_count": TARGET_SLIDE_COUNT,
                "purpose": "pitch_deck",
                "generate_images": False,
                "generate_notes": True,
            },
        }
    if mode == "premium":
        return {
            "mode": "premium",
            "input_method": "prompt",
            "premium_prompt_input": {
                "prompt": PROMPT,
                "purpose": "pitch_deck",
                "slide_count": TARGET_SLIDE_COUNT,
                "writing_style": "yc_crisp",
                "content_directives": {
                    "include_slides": [
                        "problem",
                        "solution",
                        "architecture",
                        "performance",
                        "security model",
                        "market",
                        "business model",
                        "go-to-market",
                        "moat",
                        "roadmap",
                        "investment ask",
                    ],
                    "emphasis": [
                        "sub-millisecond authentication latency",
                        "O(1) scalability",
                        "hardware-root-of-trust integration",
                        "Neural-Guardian consensus algorithm",
                    ],
                    "key_messages": [
                        "Eliminates central authority with DIDs and zero-knowledge proofs",
                        "Designed for low-bandwidth edge and IoT environments",
                        "Investor-ready for technical VCs and senior security architects",
                    ],
                    "tone_keywords": ["technical", "precise", "investor-grade"],
                },
                "generate_images": True,
                "generate_notes": True,
            },
        }
    raise ValueError(f"Unknown mode: {mode}")


def _visible_text_parts(value: Any, *, parent_key: str = "") -> list[str]:
    skip = {
        "url",
        "href",
        "image_url",
        "imageUrl",
        "photoUrl",
        "logoUrl",
        "source",
        "jsx_source",
        "fingerprint",
        "id",
        "slide_id",
        "project_id",
    }
    out: list[str] = []
    if isinstance(value, str):
        text = value.strip()
        if text and parent_key not in skip:
            out.append(text)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in skip:
                continue
            out.extend(_visible_text_parts(child, parent_key=str(key)))
    elif isinstance(value, list):
        for child in value:
            out.extend(_visible_text_parts(child, parent_key=parent_key))
    return out


def _deck_text(slides: list[dict[str, Any]]) -> str:
    return "\n".join(_visible_text_parts(slides))


def _match_cluster(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _score_content(export_payload: dict[str, Any]) -> dict[str, Any]:
    slides = export_payload.get("slides") or []
    if not isinstance(slides, list):
        slides = []
    text = _deck_text(slides)

    concept_hits = {
        name: _match_cluster(text, patterns)
        for name, patterns in REQUIRED_CONCEPTS
    }
    concept_score = 60.0 * (sum(concept_hits.values()) / max(1, len(concept_hits)))

    slide_count = len(slides)
    count_score = 10.0 if slide_count == TARGET_SLIDE_COUNT else max(
        0.0,
        10.0 - abs(slide_count - TARGET_SLIDE_COUNT) * 2.5,
    )

    beat_hits = {
        name: _match_cluster(text, patterns)
        for name, patterns in NARRATIVE_BEATS
    }
    narrative_score = 10.0 * (sum(beat_hits.values()) / max(1, len(beat_hits)))

    bad_copy = []
    for name, pattern in BAD_COPY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            bad_copy.append(name)
    hygiene_score = max(0.0, 10.0 - len(bad_copy) * 2.5)

    specificity_markers = [
        "DID",
        "zero-knowledge",
        "sub-millisecond",
        "O(1)",
        "hardware-root-of-trust",
        "Neural-Guardian",
        "low-bandwidth",
    ]
    specificity_hits = [
        marker for marker in specificity_markers
        if marker.lower() in text.lower()
    ]
    specificity_score = 10.0 * (len(specificity_hits) / len(specificity_markers))

    score = round(
        concept_score + count_score + narrative_score + hygiene_score + specificity_score,
        1,
    )

    return {
        "score": min(100.0, score),
        "slide_count": slide_count,
        "concept_hits": concept_hits,
        "missing_concepts": [name for name, ok in concept_hits.items() if not ok],
        "narrative_hits": beat_hits,
        "missing_narrative_beats": [name for name, ok in beat_hits.items() if not ok],
        "bad_copy_findings": bad_copy,
        "specificity_hits": specificity_hits,
    }


def _extract_quality_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        score = float(value)
        return score * 10.0 if score <= 10 else score
    if isinstance(value, dict):
        for key in ("overall_score", "overall", "score"):
            if isinstance(value.get(key), (int, float)):
                score = float(value[key])
                return score * 10.0 if score <= 10 else score
    return None


def _compiled_props(compiled: dict[str, Any]) -> dict[str, Any]:
    artifacts = compiled.get("artifacts") if isinstance(compiled.get("artifacts"), dict) else {}
    kit = artifacts.get("kit_jsx") if isinstance(artifacts, dict) else {}
    props = kit.get("props_json") if isinstance(kit, dict) else None
    return props if isinstance(props, dict) else {}


def _score_design(compiled_payload: dict[str, Any]) -> dict[str, Any]:
    slides = compiled_payload.get("compiled_slides") or []
    if not isinstance(slides, list):
        slides = []

    quality_scores: list[float] = []
    composition_scores: list[float] = []
    missing_props: list[int] = []
    l1_errors: list[dict[str, Any]] = []
    pending_images: list[int] = []
    low_quality_slides: list[dict[str, Any]] = []

    for index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        slide_index = slide.get("slide_index", index)
        q = _extract_quality_number(slide.get("quality_gate"))
        if q is None:
            q = _extract_quality_number(slide.get("quality_score"))
        if q is not None:
            quality_scores.append(q)
            if q < 90:
                low_quality_slides.append({"slide": slide_index, "quality_score": round(q, 1)})

        comp = slide.get("composition_score")
        if isinstance(comp, dict) and isinstance(comp.get("overall"), (int, float)):
            composition_scores.append(float(comp["overall"]) * 100.0)

        if not _compiled_props(slide):
            missing_props.append(int(slide_index) if isinstance(slide_index, int) else index)

        l1 = slide.get("l1_validation")
        if isinstance(l1, dict) and l1.get("ok") is False:
            l1_errors.append({"slide": slide_index, "issues": l1.get("issues") or []})

        if slide.get("pending_image"):
            pending_images.append(int(slide_index) if isinstance(slide_index, int) else index)

    avg_quality = statistics.mean(quality_scores) if quality_scores else 0.0
    avg_composition = statistics.mean(composition_scores) if composition_scores else avg_quality
    structural_penalty = (
        len(missing_props) * 8.0
        + len(l1_errors) * 10.0
        + len(pending_images) * 2.0
    )
    deck_count_penalty = 0.0 if len(slides) == TARGET_SLIDE_COUNT else abs(len(slides) - TARGET_SLIDE_COUNT) * 5.0
    score = max(0.0, min(100.0, (avg_quality * 0.55 + avg_composition * 0.45) - structural_penalty - deck_count_penalty))

    return {
        "score": round(score, 1),
        "slide_count": len(slides),
        "average_quality_score": round(avg_quality, 1),
        "average_composition_score": round(avg_composition, 1),
        "missing_props": missing_props,
        "l1_errors": l1_errors,
        "pending_images": pending_images,
        "low_quality_slides": low_quality_slides,
    }


def _render_pdf_snapshots(pdf_path: Path, snapshots_dir: Path) -> dict[str, Any]:
    try:
        import fitz  # type: ignore
        from PIL import Image, ImageStat  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"snapshot dependencies unavailable: {exc}"}

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    doc = fitz.open(str(pdf_path))
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        out_path = snapshots_dir / f"slide_{page_index + 1:02d}.png"
        pix.save(str(out_path))
        with Image.open(out_path) as image:
            stat = ImageStat.Stat(image.convert("L"))
            extrema = image.convert("L").getextrema()
            mean = stat.mean[0] if stat.mean else 0
            variance = stat.var[0] if stat.var else 0
        results.append(
            {
                "slide": page_index,
                "path": str(out_path),
                "mean_luma": round(float(mean), 2),
                "variance": round(float(variance), 2),
                "nonblank": bool(extrema and extrema[0] != extrema[1] and variance > 5.0),
            }
        )
    doc.close()
    return {
        "ok": True,
        "page_count": len(results),
        "all_nonblank": all(item["nonblank"] for item in results),
        "snapshots": results,
    }


def _download_binary(client: httpx.Client, path: str) -> bytes:
    response = client.get(path)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"GET {path} failed: {response.status_code} {response.text[:2000]}") from exc
    return response.content


def _poll_generation(
    client: httpx.Client,
    project_id: str,
    *,
    timeout_seconds: int,
    poll_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    transient_errors = 0
    while time.monotonic() < deadline:
        try:
            last = _http_json(client, "GET", f"/api/v4/generation/{project_id}")
            transient_errors = 0
        except httpx.TransportError as exc:
            transient_errors += 1
            if transient_errors > 5:
                raise
            print(f"[poll] transient transport error; retrying: {exc}", flush=True)
            time.sleep(min(poll_seconds, 3.0))
            continue
        status = str(last.get("status") or "").lower()
        progress = last.get("progress")
        message = last.get("message")
        print(f"[poll] {project_id} status={status} progress={progress} message={message}", flush=True)
        if status in {"completed", "complete", "succeeded", "failed", "error"}:
            return last
        time.sleep(poll_seconds)
    raise TimeoutError(f"generation timed out for {project_id}; last={last}")


def _exercise_edit_routes(
    client: httpx.Client,
    project_id: str,
    compiled_payload: dict[str, Any],
    *,
    exercise_regeneration: bool,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    slides = compiled_payload.get("compiled_slides") or []
    if not slides:
        return {"ok": False, "error": "no compiled slides"}

    first = slides[0]
    props = _compiled_props(first)
    artifact_version = first.get("artifact_version")
    current_headline = (
        first.get("headline")
        or props.get("headline")
        or "Autonomous Zero-Trust Identity Orchestration"
    )

    results["patch_slide"] = _http_json(
        client,
        "PATCH",
        f"/api/v4/projects/{project_id}/slides/0",
        json={"headline": current_headline},
    )

    latest = _http_json(client, "GET", f"/api/v4/generation/{project_id}/slides")
    latest_first = (latest.get("compiled_slides") or [{}])[0]
    latest_props = _compiled_props(latest_first)
    artifact_version = latest_first.get("artifact_version") or artifact_version
    if latest_props and isinstance(artifact_version, int):
        path = "props_json.headline"
        results["slice_patch"] = _http_json(
            client,
            "PATCH",
            f"/api/v4/projects/{project_id}/slides/0/slice",
            json={
                "expected_artifact_version": artifact_version,
                "operation_id": f"qa-slice-{project_id}",
                "ops": [{"path": path, "op": "replace", "value": latest_props.get("headline") or current_headline}],
            },
        )

    results["recompile"] = _http_json(
        client,
        "POST",
        f"/api/v4/projects/{project_id}/slides/0/recompile",
        json={"issue_code": "qa_manual_recompile", "source": "e2e_zero_trust_pitchdeck_qa"},
    )

    icon_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
        '<rect width="128" height="128" rx="24" fill="#0f172a"/>'
        '<path d="M34 88V34h13l34 34V34h13v54H81L47 54v34H34z" fill="#22d3ee"/>'
        "</svg>"
    ).encode("utf-8")
    icon_resp = client.post(
        f"/api/v4/projects/{project_id}/company-icon",
        files={"file": ("neural-guardian.svg", icon_svg, "image/svg+xml")},
    )
    results["company_icon_upload"] = {
        "status_code": icon_resp.status_code,
        "ok": icon_resp.status_code < 400,
        "body": icon_resp.json() if icon_resp.headers.get("content-type", "").startswith("application/json") else icon_resp.text[:500],
    }

    if icon_resp.status_code < 400:
        icon_url = results["company_icon_upload"]["body"].get("company_icon_url")
        results["company_icon_patch"] = _http_json(
            client,
            "PATCH",
            f"/api/v4/projects/{project_id}/slides/0",
            json={
                "company_icon_url": icon_url,
                "company_icon_position": "top-right",
                "company_icon_opacity": 0.22,
            },
        )

    if exercise_regeneration:
        results["regenerate_slide"] = _http_json(
            client,
            "POST",
            f"/api/v4/projects/{project_id}/slides/1/regenerate",
            json={
                "instruction": (
                    "Tighten this slide for technical VCs. Preserve the user's terms: "
                    "DIDs, zero-knowledge proofs, O(1), sub-millisecond latency, "
                    "hardware-root-of-trust, and Neural-Guardian."
                )
            },
        )
        results["regenerate_batch"] = _http_json(
            client,
            "POST",
            f"/api/v4/projects/{project_id}/slides/regenerate-batch",
            json={
                "slide_indices": [2, 3],
                "instruction": "Increase technical specificity without inventing customer traction or financials.",
                "preserve_images": True,
                "concurrency": 1,
            },
        )

    return {"ok": True, "results": results}


def _run_mode(
    client: httpx.Client,
    mode: str,
    output_dir: Path,
    *,
    timeout_seconds: int,
    poll_seconds: float,
    exercise_edits: bool,
    exercise_regeneration: bool,
) -> dict[str, Any]:
    print(f"[mode:{mode}] starting generation", flush=True)
    start = time.monotonic()
    payload = _payload_for(mode)
    _write_json(output_dir / f"{mode}_request.json", payload)

    started = _http_json(client, "POST", "/api/v4/generate", json=payload)
    project_id = started["project_id"]
    print(f"[mode:{mode}] project_id={project_id}", flush=True)

    status = _poll_generation(
        client,
        project_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    if str(status.get("status") or "").lower() in {"failed", "error"}:
        raise RuntimeError(f"{mode} generation failed: {status}")

    compiled = _http_json(client, "GET", f"/api/v4/generation/{project_id}/slides")
    exported = _http_json(client, "GET", f"/api/v4/projects/{project_id}/export/json")
    _write_json(output_dir / f"{mode}_compiled_slides.json", compiled)
    _write_json(output_dir / f"{mode}_slide_content.json", exported)

    edit_report = None
    if exercise_edits:
        print(f"[mode:{mode}] exercising edit endpoints", flush=True)
        edit_report = _exercise_edit_routes(
            client,
            project_id,
            compiled,
            exercise_regeneration=exercise_regeneration,
        )
        _write_json(output_dir / f"{mode}_edit_report.json", edit_report)
        compiled = _http_json(client, "GET", f"/api/v4/generation/{project_id}/slides")
        exported = _http_json(client, "GET", f"/api/v4/projects/{project_id}/export/json")
        _write_json(output_dir / f"{mode}_compiled_slides_after_edits.json", compiled)
        _write_json(output_dir / f"{mode}_slide_content_after_edits.json", exported)

    content_score = _score_content(exported)
    design_score = _score_design(compiled)

    print(f"[mode:{mode}] exporting PDF/PPTX", flush=True)
    pdf_bytes = _download_binary(client, f"/api/v4/projects/{project_id}/export/pdf")
    pptx_bytes = _download_binary(client, f"/api/v4/projects/{project_id}/export/pptx")
    pdf_path = output_dir / f"{mode}_deck.pdf"
    pptx_path = output_dir / f"{mode}_deck.pptx"
    _write_bytes(pdf_path, pdf_bytes)
    _write_bytes(pptx_path, pptx_bytes)

    snapshot_report = _render_pdf_snapshots(pdf_path, output_dir / f"{mode}_snapshots")
    _write_json(output_dir / f"{mode}_snapshot_report.json", snapshot_report)

    report = {
        "mode": mode,
        "project_id": project_id,
        "duration_seconds": round(time.monotonic() - start, 2),
        "generation_status": status,
        "content_score": content_score,
        "design_score": design_score,
        "edit_report": edit_report,
        "exports": {
            "slide_content_json": str(output_dir / f"{mode}_slide_content.json"),
            "compiled_slides_json": str(output_dir / f"{mode}_compiled_slides.json"),
            "pdf": str(pdf_path),
            "pptx": str(pptx_path),
            "snapshots_dir": str(output_dir / f"{mode}_snapshots"),
        },
        "snapshot_report": snapshot_report,
    }
    _write_json(output_dir / f"{mode}_qa_report.json", report)
    return report


def _summarize(reports: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prompt": PROMPT,
        "target_slide_count": TARGET_SLIDE_COUNT,
        "modes": {
            report["mode"]: {
                "project_id": report["project_id"],
                "duration_seconds": report["duration_seconds"],
                "content_score": report["content_score"]["score"],
                "design_score": report["design_score"]["score"],
                "slide_count": report["content_score"]["slide_count"],
                "missing_concepts": report["content_score"]["missing_concepts"],
                "missing_narrative_beats": report["content_score"]["missing_narrative_beats"],
                "bad_copy_findings": report["content_score"]["bad_copy_findings"],
                "design_findings": {
                    "missing_props": report["design_score"]["missing_props"],
                    "l1_errors": report["design_score"]["l1_errors"],
                    "pending_images": report["design_score"]["pending_images"],
                    "low_quality_slides": report["design_score"]["low_quality_slides"],
                },
                "exports": report["exports"],
                "snapshots_ok": report["snapshot_report"].get("ok") and report["snapshot_report"].get("all_nonblank"),
            }
            for report in reports
        },
    }
    _write_json(output_dir / "qa_summary.json", summary)

    lines = [
        "# Zero Trust Pitch Deck QA",
        "",
        f"Generated: {summary['generated_at']}",
        "",
    ]
    for mode, item in summary["modes"].items():
        lines.extend(
            [
                f"## {mode.title()}",
                "",
                f"- Project ID: `{item['project_id']}`",
                f"- Slide count: {item['slide_count']} / {TARGET_SLIDE_COUNT}",
                f"- Content score: {item['content_score']}",
                f"- Design score: {item['design_score']}",
                f"- Snapshots nonblank: {item['snapshots_ok']}",
                f"- Missing concepts: {', '.join(item['missing_concepts']) or 'none'}",
                f"- Missing narrative beats: {', '.join(item['missing_narrative_beats']) or 'none'}",
                f"- Bad copy findings: {', '.join(item['bad_copy_findings']) or 'none'}",
                f"- PDF: `{item['exports']['pdf']}`",
                f"- Slide content JSON: `{item['exports']['slide_content_json']}`",
                "",
            ]
        )
    (output_dir / "qa_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--mode", choices=["standard", "premium", "both"], default="both")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=float, default=8.0)
    parser.add_argument("--exercise-edits", action="store_true")
    parser.add_argument("--exercise-regeneration", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.output_dir) if args.output_dir else Path("qa_outputs") / f"zero_trust_pitchdeck_{_now_stamp()}"
    root.mkdir(parents=True, exist_ok=True)

    modes = ["standard", "premium"] if args.mode == "both" else [args.mode]
    reports: list[dict[str, Any]] = []
    with httpx.Client(base_url=args.base_url, timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        health = _http_json(client, "GET", "/health")
        _write_json(root / "health.json", health)
        for mode in modes:
            reports.append(
                _run_mode(
                    client,
                    mode,
                    root,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                    exercise_edits=args.exercise_edits,
                    exercise_regeneration=args.exercise_regeneration,
                )
            )

    summary = _summarize(reports, root)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"[done] output_dir={root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
