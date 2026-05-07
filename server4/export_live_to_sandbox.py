"""One-off: export the real STD-1 live-compiled slides into the sandbox mocks/
folder so we can validate the full LLM→compiler→sandbox loop in-browser.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app.services.v4.slide_compiler import compile_slides  # noqa: E402
from app.services.v4.parallel_writer import GeneratedSlide  # noqa: E402


def _slide_from_dict(d: dict) -> GeneratedSlide:
    # GeneratedSlide is a dataclass — filter to known fields.
    import dataclasses
    allowed = {f.name for f in dataclasses.fields(GeneratedSlide)}
    filt = {k: v for k, v in d.items() if k in allowed}
    return GeneratedSlide(**filt)


def main() -> None:
    raw = json.loads((HERE / "test_v4_live_local_raw.json").read_text(encoding="utf-8"))
    std1 = raw[0]
    slides = [_slide_from_dict(s) for s in std1["slides"]]
    compiled = compile_slides(slides=slides, deck_title="Northwind AI")

    out = [
        {
            "slide_id": c["slide_id"],
            "kit": c["kit_component"],
            "jsx_source": c["jsx_source"],
        }
        for c in compiled
    ]

    tokens = {
        "palette": {
            "primary": "#6366f1",
            "accent": "#f59e0b",
            "background": "#0b0d12",
            "surface": "#111827",
            "text_primary": "#f8fafc",
            "text_muted": "#94a3b8",
            "border": "#1f2937",
        },
        "fonts": {"heading": "Inter", "body": "Inter"},
        "scale": 1.0,
        "spacing": 1.0,
        "weights": {"heading": 800, "body": 400},
        "density": "comfortable",
        "line_height": 1.4,
        "letter_spacing_em": 0,
        "provided_by": "live",
    }

    dest = Path(r"d:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\sandbox\public\mocks\live_std1.json")
    dest.write_text(json.dumps({"tokens": tokens, "slides": out}, indent=2), encoding="utf-8")
    print(f"wrote {dest} ({len(out)} slides)")
    print("kits:", [c["kit_component"] for c in compiled])


if __name__ == "__main__":
    main()
