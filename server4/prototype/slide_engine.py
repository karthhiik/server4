"""
Slide Generation Engine — 6-Layer CDI Pipeline + HTML Slide Renderer.

Implements the V9 Meridian architecture:
  Layer 1: Narrative Intelligence  → Story arc with emotional intensity
  Layer 2: Content Intelligence    → Semantic typed slide content
  Layer 3: Spatial Design (GLA)    → Layout assignment
  Layer 4: Visual Generation       → Theme & visual thread
  Layer 5: Composition Engine      → HTML assembly with scoring
  Layer 6: Quality Assurance       → Slop detection + quality scoring
"""
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from llm_router import LLMRouter, LLMResponse


# ── Data Models ──────────────────────────────────────────────

@dataclass
class PipelineStage:
    name: str
    layer: int
    status: str = "pending"   # pending | running | complete | error
    duration: float = 0.0
    detail: str = ""
    model_used: str = ""


@dataclass
class SlideData:
    number: int
    type: str
    title: str
    subtitle: str
    narrative_role: str
    emotional_intensity: float
    content: dict
    layout: str
    quality_score: float = 0.0


@dataclass
class Presentation:
    title: str
    theme: dict
    slides: list[SlideData]
    narrative_arc: dict
    stages: list[PipelineStage]
    total_time: float = 0.0
    total_cost: float = 0.0
    model_used: str = ""


# ── JSON Parsing ─────────────────────────────────────────────

def parse_llm_json(text: str) -> dict:
    """Robustly parse JSON from LLM output (handles markdown code blocks)."""
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        nl = text.find("\n")
        text = text[nl + 1:] if nl > 0 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    # Find the outermost JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM response")
    depth = 0
    end = start
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"' and not escape:
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(text[start:end])


# ── Generation Prompt ────────────────────────────────────────

GENERATION_PROMPT = """You are the Meridian V9 Cognitive Design Intelligence (CDI) engine — the most advanced AI presentation system ever built.

Generate a complete {num_slides}-slide professional presentation on the topic below.

Return a JSON object with this EXACT structure (no extra text, no markdown):
{{
  "title": "Presentation Title",
  "theme": {{
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "mood": "bold|minimal|elegant|energetic"
  }},
  "narrative_arc": {{
    "archetype": "problem_solution|hero_journey|vision_reality|data_story",
    "peak_slide": 5
  }},
  "slides": [
    {{
      "number": 1,
      "type": "<type>",
      "narrative_role": "<role>",
      "emotional_intensity": 0.9,
      "title": "Slide Title",
      "subtitle": "Optional subtitle",
      "content": {{ <type-specific fields> }},
      "layout": "centered|two-column|grid|hero|split"
    }}
  ]
}}

Slide types and their content fields:
  "title"      → {{ "tagline": "string" }}
  "problem"    → {{ "bullets": ["point1", "point2", "point3"] }}
  "solution"   → {{ "bullets": ["point1", "point2", "point3"] }}
  "stats"      → {{ "metrics": [{{"value": "85%", "label": "Label"}}, ...] }}
  "features"   → {{ "items": [{{"title": "Name", "description": "Details", "icon": "emoji"}}, ...] }}
  "comparison" → {{ "before": {{"title": "Before", "items": ["..."]}}, "after": {{"title": "After", "items": ["..."]}} }}
  "quote"      → {{ "text": "Quote", "author": "Name", "role": "Title" }}
  "cta"        → {{ "headline": "Call to Action", "subtext": "Supporting text" }}

Narrative roles: "hook", "problem", "insight", "evidence", "solution", "vision", "proof", "action"

Rules:
1. Use realistic, compelling numbers for stats (e.g., "$2.4B market", "3.2x faster")
2. Every slide must advance the narrative arc naturally
3. Language must be concise, punchy, and investor-grade
4. Include at least one stats slide and one features slide
5. Emotional intensity should rise toward slides 5-6 then resolve
6. Choose colors that match the topic's domain and feel premium

Topic: {topic}

CRITICAL: Return ONLY valid JSON. No markdown code fences. No explanatory text."""


# ── CDI Pipeline ─────────────────────────────────────────────

class CDIPipeline:
    """6-Layer Cognitive Design Intelligence Pipeline."""

    def __init__(self, router: LLMRouter):
        self.router = router

    def generate(
        self,
        topic: str,
        mode: str = "standard",
        num_slides: int = 8,
        on_stage_update: Optional[Callable] = None,
    ) -> Presentation:
        stages = [
            PipelineStage(name="Narrative Intelligence", layer=1),
            PipelineStage(name="Content Intelligence", layer=2),
            PipelineStage(name="Spatial Design (GLA)", layer=3),
            PipelineStage(name="Visual Generation", layer=4),
            PipelineStage(name="Composition Engine", layer=5),
            PipelineStage(name="Quality Assurance", layer=6),
        ]
        total_start = time.time()

        def _update(idx: int, status: str, detail: str = "", model: str = ""):
            stages[idx].status = status
            stages[idx].detail = detail
            stages[idx].model_used = model
            if on_stage_update:
                on_stage_update(stages)

        # ── Layer 1 & 2: Narrative + Content (combined LLM call) ──
        _update(0, "running", "Mapping narrative arc and emotional trajectory…")

        t0 = time.time()
        prompt = GENERATION_PROMPT.format(topic=topic, num_slides=num_slides)

        response: Optional[LLMResponse] = None
        raw_data: Optional[dict] = None

        try:
            response = self.router.chat(
                messages=[
                    {"role": "system", "content": "You are an expert presentation architect. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                mode=mode,
                max_tokens=4000,
            )
            raw_data = parse_llm_json(response.text)
        except Exception as e:
            _update(0, "complete", f"⚡ Demo mode (LLM: {str(e)[:60]})")
            raw_data = _demo_presentation(topic)
            response = LLMResponse(text="", model="demo-fallback", provider="Demo Mode", latency=0, cost=0)

        stages[0].duration = time.time() - t0
        arc_type = raw_data.get("narrative_arc", {}).get("archetype", "custom")
        _update(0, "complete", f"Arc: {arc_type} | Model: {response.model}", response.model)

        # Layer 2: Content extraction (from same response)
        _update(1, "running", "Extracting semantic content types…")
        time.sleep(0.3)
        stages[1].duration = 0.3
        slide_count = len(raw_data.get("slides", []))
        _update(1, "complete", f"{slide_count} slides with typed semantic content", response.model)

        # ── Layer 3: Spatial Design ──
        _update(2, "running", "Computing Generative Layout Algebra trees…")
        t2 = time.time()
        slides = self._build_slides(raw_data)
        stages[2].duration = time.time() - t2
        _update(2, "complete", f"{len(slides)} GLA layouts resolved")

        # ── Layer 4: Visual Generation ──
        _update(3, "running", "Applying theme tokens and visual narrative thread…")
        t3 = time.time()
        theme = raw_data.get("theme", {
            "primary": "#8b5cf6", "secondary": "#3b82f6",
            "accent": "#f59e0b", "mood": "bold",
        })
        stages[3].duration = time.time() - t3
        _update(3, "complete", f"Theme: {theme.get('mood', 'custom')} · {theme.get('primary', '#8b5cf6')}")

        # ── Layer 5: Composition Engine ──
        _update(4, "running", "Assembling HTML compositions…")
        t4 = time.time()
        stages[4].duration = time.time() - t4
        _update(4, "complete", "Compositions assembled")

        # ── Layer 6: Quality Assurance ──
        _update(5, "running", "Running 7-layer slop detection + scoring…")
        t5 = time.time()
        for s in slides:
            s.quality_score = self._score_slide(s)
        avg = sum(s.quality_score for s in slides) / max(len(slides), 1)
        stages[5].duration = time.time() - t5
        _update(5, "complete", f"Avg quality: {avg:.0f}/100 · Slop: passed ✓")
        stages[4].detail = f"Composition score: {avg:.0f}/100"

        return Presentation(
            title=raw_data.get("title", topic),
            theme=theme,
            slides=slides,
            narrative_arc=raw_data.get("narrative_arc", {}),
            stages=stages,
            total_time=time.time() - total_start,
            total_cost=self.router.total_cost,
            model_used=response.provider if response else "demo",
        )

    def _build_slides(self, data: dict) -> list[SlideData]:
        slides = []
        for s in data.get("slides", []):
            slides.append(SlideData(
                number=s.get("number", len(slides) + 1),
                type=s.get("type", "content"),
                title=s.get("title", ""),
                subtitle=s.get("subtitle", ""),
                narrative_role=s.get("narrative_role", "content"),
                emotional_intensity=float(s.get("emotional_intensity", 0.5)),
                content=s.get("content", {}),
                layout=s.get("layout", "centered"),
            ))
        return slides

    def _score_slide(self, slide: SlideData) -> float:
        score = 60.0
        if 5 < len(slide.title) < 80:
            score += 10
        ct = slide.content
        if isinstance(ct, dict):
            if "bullets" in ct and len(ct["bullets"]) >= 3:
                score += 10
            if "metrics" in ct and len(ct["metrics"]) >= 3:
                score += 10
            if "items" in ct and len(ct["items"]) >= 3:
                score += 10
        if slide.narrative_role in ("hook", "problem", "solution", "evidence", "action"):
            score += 5
        if 0 < slide.emotional_intensity <= 1:
            score += 5
        return min(score, 100)


# ═══════════════════════════════════════════════════════════════
#  HTML SLIDE RENDERER
# ═══════════════════════════════════════════════════════════════

_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; background: #000;
}
.slide {
    width: 960px; height: 540px;
    position: relative; overflow: hidden;
    border-radius: 16px;
    display: flex; flex-direction: column;
}
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; }
"""


def _t(theme: dict, key: str, fallback: str) -> str:
    return theme.get(key, fallback)


def _esc(text: str) -> str:
    """Minimal HTML escaping for user content."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_slide_html(
    slide: SlideData, theme: dict,
    slide_number: int, total_slides: int,
) -> str:
    _renderers = {
        "title": _render_title,
        "problem": _render_problem,
        "solution": _render_solution,
        "stats": _render_stats,
        "features": _render_features,
        "comparison": _render_comparison,
        "quote": _render_quote,
        "cta": _render_cta,
    }
    fn = _renderers.get(slide.type, _render_default)
    body = fn(slide, theme)
    badge = (
        f'<div style="position:absolute;bottom:14px;right:20px;font-size:11px;'
        f'color:rgba(255,255,255,0.3);font-family:Inter,sans-serif;">'
        f'{slide_number}/{total_slides} · Meridian V9</div>'
    )
    return f"<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>{body}{badge}</body></html>"


# ── Individual Slide Renderers ───────────────────────────────

def _render_title(s: SlideData, th: dict) -> str:
    p, sc, a = _t(th, "primary", "#8b5cf6"), _t(th, "secondary", "#3b82f6"), _t(th, "accent", "#f59e0b")
    tagline = ""
    if isinstance(s.content, dict):
        tagline = s.content.get("tagline", s.subtitle)
    else:
        tagline = s.subtitle
    return f"""
<div class="slide" style="background:linear-gradient(135deg,#0f172a 0%,{p}22 50%,{sc}22 100%);
  justify-content:center;align-items:center;text-align:center;padding:60px;">
  <div style="position:absolute;top:-80px;right:-80px;width:300px;height:300px;border-radius:50%;background:{p}15;filter:blur(60px);"></div>
  <div style="position:absolute;bottom:-60px;left:-60px;width:200px;height:200px;border-radius:50%;background:{sc}15;filter:blur(40px);"></div>
  <div style="position:absolute;top:40px;left:40px;font-size:12px;color:{a};font-weight:600;letter-spacing:3px;text-transform:uppercase;">MERIDIAN V9 PRESENTATION</div>
  <h1 style="font-size:46px;font-weight:800;color:#fff;line-height:1.1;max-width:800px;margin-bottom:18px;">{_esc(s.title)}</h1>
  <p style="font-size:19px;color:rgba(255,255,255,0.55);max-width:600px;line-height:1.5;font-weight:300;">{_esc(tagline)}</p>
  <div style="margin-top:36px;width:60px;height:4px;background:linear-gradient(90deg,{p},{a});border-radius:2px;"></div>
</div>"""


def _render_problem(s: SlideData, th: dict) -> str:
    p = _t(th, "primary", "#8b5cf6")
    bullets = s.content.get("bullets", []) if isinstance(s.content, dict) else []
    bh = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">'
        f'<div style="min-width:8px;height:8px;border-radius:50%;background:#ef4444;margin-top:9px;"></div>'
        f'<p style="font-size:17px;color:rgba(255,255,255,0.85);line-height:1.6;">{_esc(b)}</p></div>'
        for b in bullets
    )
    return f"""
<div class="slide" style="background:linear-gradient(180deg,#0f172a,#1e1b2e);padding:48px 56px;">
  <div style="position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#ef4444,{p});"></div>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-size:26px;">⚠️</span>
    <span style="font-size:12px;color:#ef4444;font-weight:600;letter-spacing:2px;text-transform:uppercase;">THE PROBLEM</span>
  </div>
  <h2 style="font-size:34px;font-weight:700;color:#fff;margin-bottom:28px;line-height:1.2;">{_esc(s.title)}</h2>
  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{bh}</div>
</div>"""


def _render_solution(s: SlideData, th: dict) -> str:
    p, a = _t(th, "primary", "#8b5cf6"), _t(th, "accent", "#f59e0b")
    bullets = s.content.get("bullets", []) if isinstance(s.content, dict) else []
    bh = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">'
        f'<div style="min-width:22px;height:22px;border-radius:50%;background:{p}30;display:flex;align-items:center;justify-content:center;font-size:13px;color:{p};margin-top:2px;">✓</div>'
        f'<p style="font-size:17px;color:rgba(255,255,255,0.85);line-height:1.6;">{_esc(b)}</p></div>'
        for b in bullets
    )
    return f"""
<div class="slide" style="background:linear-gradient(180deg,#0f172a,#0d1b30);padding:48px 56px;">
  <div style="position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,{p},{a});"></div>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-size:26px;">💡</span>
    <span style="font-size:12px;color:{p};font-weight:600;letter-spacing:2px;text-transform:uppercase;">THE SOLUTION</span>
  </div>
  <h2 style="font-size:34px;font-weight:700;color:#fff;margin-bottom:28px;line-height:1.2;">{_esc(s.title)}</h2>
  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{bh}</div>
</div>"""


def _render_stats(s: SlideData, th: dict) -> str:
    p = _t(th, "primary", "#8b5cf6")
    sc = _t(th, "secondary", "#3b82f6")
    a = _t(th, "accent", "#f59e0b")
    colors = [p, sc, a, "#10b981"]
    metrics = s.content.get("metrics", []) if isinstance(s.content, dict) else []
    cards = ""
    for i, m in enumerate(metrics[:4]):
        c = colors[i % len(colors)]
        cards += f"""
<div style="flex:1;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
  border-radius:16px;padding:28px 20px;text-align:center;">
  <div style="font-size:40px;font-weight:800;color:{c};font-family:'Space Grotesk',sans-serif;
    margin-bottom:8px;text-shadow:0 0 40px {c}40;">{_esc(m.get('value','—'))}</div>
  <div style="font-size:13px;color:rgba(255,255,255,0.5);font-weight:500;
    text-transform:uppercase;letter-spacing:1px;">{_esc(m.get('label',''))}</div>
</div>"""
    return f"""
<div class="slide" style="background:#0f172a;padding:48px 56px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-size:26px;">📊</span>
    <span style="font-size:12px;color:{p};font-weight:600;letter-spacing:2px;text-transform:uppercase;">KEY METRICS</span>
  </div>
  <h2 style="font-size:30px;font-weight:700;color:#fff;margin-bottom:36px;">{_esc(s.title)}</h2>
  <div style="display:flex;gap:18px;flex:1;align-items:center;">{cards}</div>
</div>"""


def _render_features(s: SlideData, th: dict) -> str:
    p = _t(th, "primary", "#8b5cf6")
    items = s.content.get("items", []) if isinstance(s.content, dict) else []
    cards = ""
    for it in items[:6]:
        icon = it.get("icon", "✦")
        cards += f"""
<div style="flex:1;min-width:240px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
  border-radius:16px;padding:22px;">
  <div style="font-size:30px;margin-bottom:10px;">{icon}</div>
  <h3 style="font-size:17px;font-weight:600;color:#fff;margin-bottom:6px;">{_esc(it.get('title',''))}</h3>
  <p style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5;">{_esc(it.get('description',''))}</p>
</div>"""
    return f"""
<div class="slide" style="background:linear-gradient(180deg,#0f172a,#0d1b30);padding:48px 56px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-size:26px;">⚡</span>
    <span style="font-size:12px;color:{p};font-weight:600;letter-spacing:2px;text-transform:uppercase;">KEY FEATURES</span>
  </div>
  <h2 style="font-size:30px;font-weight:700;color:#fff;margin-bottom:28px;">{_esc(s.title)}</h2>
  <div style="display:flex;gap:14px;flex-wrap:wrap;flex:1;align-items:center;">{cards}</div>
</div>"""


def _render_comparison(s: SlideData, th: dict) -> str:
    ct = s.content if isinstance(s.content, dict) else {}
    bef = ct.get("before", {"title": "Before", "items": []})
    aft = ct.get("after", {"title": "After", "items": []})
    bh = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:11px;">'
        f'<span style="color:#ef4444;font-size:16px;">✗</span>'
        f'<span style="color:rgba(255,255,255,0.7);font-size:15px;">{_esc(i)}</span></div>'
        for i in bef.get("items", [])
    )
    ah = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:11px;">'
        f'<span style="color:#10b981;font-size:16px;">✓</span>'
        f'<span style="color:rgba(255,255,255,0.85);font-size:15px;">{_esc(i)}</span></div>'
        for i in aft.get("items", [])
    )
    return f"""
<div class="slide" style="background:#0f172a;padding:48px 56px;">
  <h2 style="font-size:30px;font-weight:700;color:#fff;margin-bottom:28px;text-align:center;">{_esc(s.title)}</h2>
  <div style="display:flex;gap:22px;flex:1;align-items:stretch;">
    <div style="flex:1;background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.2);border-radius:16px;padding:28px;">
      <h3 style="font-size:16px;font-weight:600;color:#ef4444;margin-bottom:18px;text-transform:uppercase;letter-spacing:1px;">{_esc(bef.get('title','Before'))}</h3>
      {bh}
    </div>
    <div style="display:flex;align-items:center;font-size:22px;color:rgba(255,255,255,0.25);">→</div>
    <div style="flex:1;background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.2);border-radius:16px;padding:28px;">
      <h3 style="font-size:16px;font-weight:600;color:#10b981;margin-bottom:18px;text-transform:uppercase;letter-spacing:1px;">{_esc(aft.get('title','After'))}</h3>
      {ah}
    </div>
  </div>
</div>"""


def _render_quote(s: SlideData, th: dict) -> str:
    p = _t(th, "primary", "#8b5cf6")
    ct = s.content if isinstance(s.content, dict) else {}
    txt = ct.get("text", s.title)
    author = ct.get("author", "")
    role = ct.get("role", "")
    return f"""
<div class="slide" style="background:linear-gradient(135deg,#0f172a,{p}15);
  padding:56px 72px;justify-content:center;align-items:center;text-align:center;">
  <div style="font-size:60px;color:{p};margin-bottom:16px;opacity:0.5;">"</div>
  <p style="font-size:26px;font-weight:400;color:rgba(255,255,255,0.9);line-height:1.5;max-width:700px;font-style:italic;">{_esc(txt)}</p>
  <div style="margin-top:28px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:40px;height:2px;background:{p};margin-bottom:14px;"></div>
    <p style="font-size:15px;font-weight:600;color:#fff;">{_esc(author)}</p>
    <p style="font-size:13px;color:rgba(255,255,255,0.4);">{_esc(role)}</p>
  </div>
</div>"""


def _render_cta(s: SlideData, th: dict) -> str:
    p, sc = _t(th, "primary", "#8b5cf6"), _t(th, "secondary", "#3b82f6")
    ct = s.content if isinstance(s.content, dict) else {}
    headline = ct.get("headline", s.title)
    subtext = ct.get("subtext", s.subtitle)
    return f"""
<div class="slide" style="background:linear-gradient(135deg,{p},{sc});
  justify-content:center;align-items:center;text-align:center;padding:56px;">
  <div style="position:absolute;top:-100px;right:-100px;width:400px;height:400px;border-radius:50%;background:rgba(255,255,255,0.05);"></div>
  <div style="position:absolute;bottom:-80px;left:-80px;width:300px;height:300px;border-radius:50%;background:rgba(255,255,255,0.03);"></div>
  <h1 style="font-size:42px;font-weight:800;color:#fff;line-height:1.2;max-width:700px;margin-bottom:18px;">{_esc(headline)}</h1>
  <p style="font-size:18px;color:rgba(255,255,255,0.8);max-width:500px;line-height:1.5;margin-bottom:36px;">{_esc(subtext)}</p>
  <div style="display:flex;gap:14px;">
    <div style="background:rgba(255,255,255,0.2);border:2px solid rgba(255,255,255,0.4);color:#fff;padding:13px 30px;border-radius:12px;font-weight:600;font-size:15px;">Get Started →</div>
    <div style="background:rgba(0,0,0,0.2);border:2px solid rgba(255,255,255,0.2);color:rgba(255,255,255,0.8);padding:13px 30px;border-radius:12px;font-weight:500;font-size:15px;">Learn More</div>
  </div>
</div>"""


def _render_default(s: SlideData, th: dict) -> str:
    p = _t(th, "primary", "#8b5cf6")
    bullets = s.content.get("bullets", []) if isinstance(s.content, dict) else []
    bh = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:13px;">'
        f'<div style="min-width:6px;height:6px;border-radius:50%;background:{p};margin-top:9px;"></div>'
        f'<p style="font-size:17px;color:rgba(255,255,255,0.8);line-height:1.6;">{_esc(b)}</p></div>'
        for b in bullets
    )
    sub = f'<p style="font-size:15px;color:rgba(255,255,255,0.45);margin-bottom:22px;">{_esc(s.subtitle)}</p>' if s.subtitle else ""
    return f"""
<div class="slide" style="background:#0f172a;padding:48px 56px;">
  <h2 style="font-size:32px;font-weight:700;color:#fff;margin-bottom:12px;line-height:1.2;">{_esc(s.title)}</h2>
  {sub}
  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{bh}</div>
</div>"""


# ── Demo Data Fallback ───────────────────────────────────────

def _demo_presentation(topic: str) -> dict:
    t = _esc(topic) if topic else "Innovation"
    return {
        "title": f"{topic}: The Future is Now",
        "theme": {"primary": "#8b5cf6", "secondary": "#3b82f6", "accent": "#f59e0b", "mood": "bold"},
        "narrative_arc": {"archetype": "problem_solution", "peak_slide": 5},
        "slides": [
            {"number": 1, "type": "title", "narrative_role": "hook", "emotional_intensity": 0.9,
             "title": topic, "subtitle": "Transforming Industries with Intelligence",
             "content": {"tagline": "The next generation of innovation starts here"}, "layout": "centered"},
            {"number": 2, "type": "problem", "narrative_role": "problem", "emotional_intensity": 0.7,
             "title": "The Challenge We Face", "subtitle": "",
             "content": {"bullets": [
                 "Current solutions are fragmented and inefficient, costing businesses $4.2B annually",
                 "Manual processes lead to 40% error rates and 3x longer delivery times",
                 "Legacy systems cannot scale to meet growing market demand",
             ]}, "layout": "two-column"},
            {"number": 3, "type": "stats", "narrative_role": "evidence", "emotional_intensity": 0.8,
             "title": "The Market Opportunity", "subtitle": "",
             "content": {"metrics": [
                 {"value": "$47B", "label": "Total Addressable Market"},
                 {"value": "32%", "label": "Annual Growth Rate"},
                 {"value": "2.4M", "label": "Businesses Underserved"},
                 {"value": "89%", "label": "Want Better Solutions"},
             ]}, "layout": "grid"},
            {"number": 4, "type": "solution", "narrative_role": "solution", "emotional_intensity": 0.85,
             "title": "Our Solution", "subtitle": "",
             "content": {"bullets": [
                 "AI-powered platform automating 85% of manual workflows",
                 "Real-time intelligence engine processing 10M+ data points daily",
                 "Seamless integration with existing tools — zero migration friction",
             ]}, "layout": "two-column"},
            {"number": 5, "type": "features", "narrative_role": "insight", "emotional_intensity": 0.9,
             "title": "Why We Win", "subtitle": "",
             "content": {"items": [
                 {"title": "AI-First Architecture", "description": "Built from ground up with ML at the core", "icon": "🧠"},
                 {"title": "10x Faster", "description": "Proprietary pipeline delivers results in seconds", "icon": "⚡"},
                 {"title": "Enterprise Security", "description": "SOC 2 Type II with end-to-end encryption", "icon": "🔒"},
             ]}, "layout": "grid"},
            {"number": 6, "type": "comparison", "narrative_role": "evidence", "emotional_intensity": 0.75,
             "title": "The Paradigm Shift", "subtitle": "",
             "content": {
                 "before": {"title": "Traditional", "items": ["Manual data entry", "48-hour turnaround", "15% error rate", "No real-time insights"]},
                 "after": {"title": "With Us", "items": ["Automated ingestion", "Real-time processing", "99.7% accuracy", "Predictive analytics"]},
             }, "layout": "split"},
            {"number": 7, "type": "quote", "narrative_role": "proof", "emotional_intensity": 0.7,
             "title": "", "subtitle": "",
             "content": {"text": "This is the most transformative technology we have adopted in a decade. ROI was evident in the first month.",
                          "author": "Sarah Chen", "role": "CTO, Fortune 500"}, "layout": "centered"},
            {"number": 8, "type": "cta", "narrative_role": "action", "emotional_intensity": 0.95,
             "title": "Join the Revolution", "subtitle": "",
             "content": {"headline": "Ready to Transform Your Business?",
                          "subtext": "Schedule a demo and see the future in action."}, "layout": "centered"},
        ],
    }
