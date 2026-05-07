"""
HTML Compiler — Phase 7.

Compiles PresentationDSL / SlideDSL into zero-dependency HTML with
inline-only CSS, minimal vanilla JS navigation, and Chart.js integration.

Architecture:
    PresentationDSL --> HtmlCompiler --> RenderOutput (html, css, js)
    SlideDSL        --> HtmlCompiler --> str (HTML fragment)

Features:
    - Zero-dependency inline CSS (no Tailwind CDN dependency at runtime)
    - Inline custom properties for theming (--primary, --bg, ...)
    - Keyboard + touch navigation (arrow keys, swipe)
    - Chart.js lazy-load with CDN fallback
    - Speaker notes panel (press 'N')
    - Fullscreen mode (press 'F')
    - Progress bar + slide counter
    - All 17 LayoutType compilers
    - 3D scene → screenshot info panel
    - Print-friendly @media print rules
    - Offline resilience with graceful degradation
"""

import html as html_mod
import json
from typing import Optional

import structlog

from app.models.dsl_v2 import (
    LayoutType,
    PresentationDSL,
    SlideDSL,
    SlideContentV2,
    SlideType,
)
from app.services.slides_new.renderers.base_renderer import (
    BaseRenderer,
    RenderOutput,
    RendererType,
)

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════
# INLINE CSS
# ═══════════════════════════════════════════════════════════════════

_BASE_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body{width:100%;height:100%;overflow:hidden;font-family:var(--font-body,'Calibri',sans-serif);}
body{background:var(--bg,#fff);color:var(--text,#111827);}
.slide{display:none;width:100vw;height:100vh;padding:3rem 4rem;position:relative;overflow:hidden;}
.slide.active{display:flex;flex-direction:column;justify-content:flex-start;animation:fadeIn .4s ease-out;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.slide-title{font-family:var(--font-heading,'Calibri',sans-serif);font-size:2.5rem;font-weight:700;color:var(--heading,var(--text));line-height:1.2;margin-bottom:.75rem;}
.slide-subtitle{font-size:1.25rem;color:var(--text-muted,#6B7280);margin-bottom:1rem;}
.slide-body{font-size:1rem;line-height:1.6;color:var(--text);flex:1;}
.slide-bullets{list-style:none;padding:0;margin:.5rem 0;}
.slide-bullets li{padding:.4rem 0;font-size:1.1rem;position:relative;padding-left:1.5rem;}
.slide-bullets li::before{content:'\\2022';position:absolute;left:0;color:var(--primary,#2563EB);font-weight:bold;}
.hero-slide{justify-content:center;align-items:center;text-align:center;background:var(--primary,#2563EB);color:#fff;}
.hero-slide .slide-title{color:#fff;font-size:3rem;}
.hero-slide .slide-subtitle{color:rgba(255,255,255,.8);}
.split-container{display:flex;gap:2rem;flex:1;min-height:0;}
.split-half{flex:1;display:flex;flex-direction:column;justify-content:flex-start;}
.grid-2x2{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;flex:1;}
.grid-3x1{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;flex:1;}
.grid-cell{padding:1.5rem;border-radius:.5rem;background:var(--surface,#F9FAFB);display:flex;flex-direction:column;justify-content:center;}
.kpi-value{font-size:2.5rem;font-weight:800;color:var(--primary);font-family:var(--font-heading);}
.kpi-change{font-size:.9rem;font-weight:600;}
.kpi-change.positive{color:#059669;}
.kpi-change.negative{color:#DC2626;}
.kpi-label{font-size:.85rem;color:var(--text-muted);margin-top:.25rem;}
.quote-mark{font-size:5rem;line-height:1;color:var(--primary);font-family:Georgia,serif;text-align:center;}
.quote-text{font-size:1.5rem;font-style:italic;text-align:center;max-width:40rem;margin:0 auto;line-height:1.5;}
.quote-author{font-size:1rem;text-align:center;color:var(--primary);font-weight:600;margin-top:1rem;}
.team-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1.5rem;flex:1;}
.team-card{text-align:center;padding:1.5rem;border-radius:.5rem;background:var(--surface,#F9FAFB);}
.team-name{font-weight:700;font-size:1.1rem;color:var(--heading,var(--text));}
.team-role{color:var(--primary);font-size:.9rem;margin:.25rem 0;}
.team-bio{font-size:.8rem;color:var(--text-muted);line-height:1.4;}
.timeline-container{display:flex;gap:.5rem;flex:1;align-items:flex-start;padding-top:1rem;}
.timeline-item{flex:1;text-align:center;padding:1rem;position:relative;}
.timeline-item::after{content:'';position:absolute;right:0;top:50%;width:1px;height:60%;background:var(--primary);opacity:.3;}
.timeline-item:last-child::after{display:none;}
.timeline-date{font-size:.85rem;font-weight:700;color:var(--primary);margin-bottom:.5rem;}
.timeline-title{font-weight:600;font-size:1rem;margin-bottom:.25rem;}
.timeline-desc{font-size:.8rem;color:var(--text-muted);line-height:1.4;}
.comparison-row{display:flex;gap:2rem;flex:1;}
.comparison-col{flex:1;padding:1.5rem;border-radius:.5rem;}
.comparison-col.us{background:rgba(37,99,235,.05);border:1px solid rgba(37,99,235,.2);}
.comparison-col.them{background:rgba(107,114,128,.05);border:1px solid rgba(107,114,128,.2);}
.comparison-header{font-weight:700;font-size:1.1rem;margin-bottom:1rem;}
.comparison-item{padding:.4rem 0;font-size:.95rem;}
.chart-container{flex:1;min-height:0;position:relative;}
.chart-container canvas{width:100%!important;height:100%!important;}
.image-placeholder{flex:1;display:flex;align-items:center;justify-content:center;background:var(--surface,#F9FAFB);border-radius:.5rem;color:var(--text-muted);font-style:italic;}
.overlay-slide{justify-content:center;align-items:center;text-align:center;background:linear-gradient(135deg,var(--primary,#2563EB),var(--secondary,#7C3AED));}
.overlay-slide .slide-title,.overlay-slide .slide-body{color:#fff;}
.three-d-notice{padding:1rem;border-radius:.5rem;background:var(--surface);text-align:center;color:var(--text-muted);border:1px dashed var(--primary);}
#progress-bar{position:fixed;top:0;left:0;height:3px;background:var(--primary,#2563EB);transition:width .3s;z-index:100;}
#slide-counter{position:fixed;bottom:1rem;right:1.5rem;font-size:.75rem;color:var(--text-muted);z-index:100;}
#keyboard-hint{position:fixed;bottom:1rem;left:1.5rem;font-size:.65rem;color:var(--text-muted);opacity:.5;z-index:100;}
#notes-panel{position:fixed;bottom:0;left:0;right:0;height:25vh;background:#f9fafb;border-top:2px solid var(--primary);display:none;flex-direction:column;padding:1rem 2rem;overflow-y:auto;z-index:200;font-size:.9rem;color:#374151;}
#notes-panel h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--primary);margin-bottom:.5rem;}
@media print{
.slide{display:block!important;page-break-after:always;height:auto;min-height:100vh;padding:2rem;}
#progress-bar,#slide-counter,#keyboard-hint,#notes-panel{display:none!important;}
}
"""

# ═══════════════════════════════════════════════════════════════════
# NAVIGATION JS
# ═══════════════════════════════════════════════════════════════════

_NAV_JS = """
(function(){
var slides=document.querySelectorAll('.slide');
var current=0,total=slides.length;
var pBar=document.getElementById('progress-bar');
var counter=document.getElementById('slide-counter');
var nPanel=document.getElementById('notes-panel');
var nVisible=false;

function show(idx){
  if(idx<0||idx>=total)return;
  slides[current].classList.remove('active');
  current=idx;
  slides[current].classList.add('active');
  if(pBar)pBar.style.width=((current+1)/total*100)+'%';
  if(counter)counter.textContent=(current+1)+' / '+total;
  renderCharts(slides[current]);
  updateNotes();
}
function next(){show(current+1);}
function prev(){show(current-1);}
function updateNotes(){
  if(!nPanel)return;
  var notesEl=slides[current].querySelector('.slide-notes');
  var content=notesEl?notesEl.textContent:'';
  nPanel.querySelector('.notes-content').textContent=content||'No notes for this slide.';
}

document.addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();next();}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prev();}
  else if(e.key==='Home'){e.preventDefault();show(0);}
  else if(e.key==='End'){e.preventDefault();show(total-1);}
  else if(e.key==='n'||e.key==='N'){e.preventDefault();nVisible=!nVisible;nPanel.style.display=nVisible?'flex':'none';}
  else if(e.key==='f'||e.key==='F'){e.preventDefault();if(!document.fullscreenElement)document.documentElement.requestFullscreen().catch(function(){});else document.exitFullscreen().catch(function(){});}
  else if(e.key==='Escape'&&nVisible){nVisible=false;nPanel.style.display='none';}
});

var tx=0;
document.addEventListener('touchstart',function(e){tx=e.changedTouches[0].screenX;},{passive:true});
document.addEventListener('touchend',function(e){
  var dx=e.changedTouches[0].screenX-tx;
  if(Math.abs(dx)>50){dx<0?next():prev();}
},{passive:true});

if(total>0){slides[0].classList.add('active');if(pBar)pBar.style.width=(1/total*100)+'%';if(counter)counter.textContent='1 / '+total;renderCharts(slides[0]);}
window.PresentationNav={next:next,prev:prev,goTo:show,current:function(){return current;}};
})();
"""

# ═══════════════════════════════════════════════════════════════════
# CHART.JS INTEGRATION
# ═══════════════════════════════════════════════════════════════════

_CHART_JS = """
var __ci={};
function renderCharts(slideEl){
  if(typeof Chart==='undefined')return;
  slideEl.querySelectorAll('canvas.slide-chart').forEach(function(c){
    var id=c.id||('c'+Math.random().toString(36).substr(2,9));c.id=id;
    if(__ci[id]){__ci[id].destroy();}
    try{
      var d=JSON.parse(c.dataset.chart||'{}');
      var t=c.dataset.type||'bar';
      var pr=getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()||'#2563eb';
      var clrs=[pr,'#7c3aed','#059669','#d97706','#dc2626','#0891b2'];
      if(d.labels){
        __ci[id]=new Chart(c,{type:t==='donut'?'doughnut':t,data:{labels:d.labels,
        datasets:(d.datasets||[]).map(function(ds,i){return{label:ds.label,data:ds.values,
        backgroundColor:clrs[i%clrs.length],borderColor:clrs[i%clrs.length],borderWidth:1};})},
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:d.datasets&&d.datasets.length>1}}}});
      }
    }catch(e){console.warn('Chart error:',e);}
  });
}
"""


def _esc(text: str) -> str:
    """HTML-escape text safely."""
    return html_mod.escape(str(text or ""), quote=True)


# ═══════════════════════════════════════════════════════════════════
# THEME EXTRACTION
# ═══════════════════════════════════════════════════════════════════


def _theme_css_vars(dsl: PresentationDSL) -> str:
    """Generate CSS custom properties from PresentationDSL theme."""
    theme = dsl.presentation.theme
    overrides = theme.customOverrides or {}

    # Support both CSS var format (--primary-color) and simple keys (primary)
    def _get(key: str, css_key: str, default: str) -> str:
        return overrides.get(css_key, overrides.get(key, default))

    props = {
        "--bg": _get("background", "--background-color", "#FFFFFF"),
        "--surface": _get("surface", "--surface-color", "#F9FAFB"),
        "--primary": _get("primary", "--primary-color", "#2563EB"),
        "--secondary": _get("secondary", "--secondary-color", "#7C3AED"),
        "--accent": _get("accent", "--accent-color", "#F59E0B"),
        "--text": _get("text", "--text-color", "#111827"),
        "--text-muted": _get("textMuted", "--text-muted", "#6B7280"),
        "--heading": _get("heading", "--heading-color", _get("text", "--text-color", "#111827")),
        "--font-heading": f"'{overrides.get('--font-heading', 'Calibri')}',sans-serif",
        "--font-body": f"'{overrides.get('--font-body', 'Calibri')}',sans-serif",
    }

    return ":root{" + ";".join(f"{k}:{v}" for k, v in props.items()) + "}"


# ═══════════════════════════════════════════════════════════════════
# HTML COMPILER
# ═══════════════════════════════════════════════════════════════════


class HtmlCompiler(BaseRenderer):
    """Compiles PresentationDSL into zero-dependency interactive HTML.

    The output is a complete, self-contained HTML document with:
    - Inline CSS (no CDN dependency for styles)
    - Chart.js loaded via CDN only when chart slides exist
    - Keyboard + touch navigation
    - Speaker notes panel
    - Progress bar + slide counter

    Usage::

        compiler = HtmlCompiler()
        output = compiler.render_presentation(presentation_dsl)
        html_string = output.html

    Offline mode (no Chart.js CDN)::

        compiler = HtmlCompiler(offline=True)
        output = compiler.render_presentation(presentation_dsl)
    """

    def __init__(self, *, offline: bool = False):
        """Initialize HTML compiler.

        Args:
            offline: If True, skip Chart.js CDN (charts won't render).
        """
        self._offline = offline

    def get_renderer_type(self) -> RendererType:
        """Return the renderer type identifier."""
        return RendererType.HTML

    def render_presentation(
        self, presentation_dsl: PresentationDSL, theme_css: str = ""
    ) -> RenderOutput:
        """Compile full PresentationDSL into interactive HTML."""
        try:
            has_charts = any(s.content.chart_data for s in presentation_dsl.slides)
            has_3d = any(s.threeScene for s in presentation_dsl.slides)

            # Compile all slides
            slide_fragments = []
            notes_data: list[dict] = []

            for slide_dsl in presentation_dsl.slides:
                fragment = self._compile_slide(slide_dsl)
                slide_fragments.append(fragment)

                if slide_dsl.speakerNotes:
                    notes_data.append({
                        "index": slide_dsl.index,
                        "notes": _esc(slide_dsl.speakerNotes),
                    })

            # Assemble the document
            theme_vars = _theme_css_vars(presentation_dsl)
            full_css = theme_vars + "\n" + _BASE_CSS
            if theme_css:
                full_css += "\n" + theme_css

            title = _esc(presentation_dsl.presentation.title)
            slides_html = "\n".join(slide_fragments)

            chart_cdn = ""
            if has_charts and not self._offline:
                chart_cdn = (
                    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/'
                    'chart.umd.min.js" defer></script>'
                )

            html_doc = self._wrap_document(
                title=title,
                css=full_css,
                slides_html=slides_html,
                chart_cdn=chart_cdn,
                has_charts=has_charts,
            )

            logger.info(
                "html_compiled",
                slides=len(presentation_dsl.slides),
                has_charts=has_charts,
                has_3d=has_3d,
                offline=self._offline,
                size_kb=len(html_doc) // 1024,
            )

            return RenderOutput(
                renderer=RendererType.HTML,
                html=html_doc,
                css=full_css,
                js=_NAV_JS,
                assets={
                    "slide_notes": notes_data,
                    "has_charts": has_charts,
                    "has_3d": has_3d,
                },
                metadata={
                    "renderer": "html",
                    "offline_mode": self._offline,
                    "chart_cdn_loaded": has_charts and not self._offline,
                },
                success=True,
                slide_count=len(presentation_dsl.slides),
            )

        except Exception as exc:
            try:
                logger.exception("html_compile_failed", error=str(exc))
            except (UnicodeEncodeError, OSError):
                pass  # Encoding issues on Windows consoles
            return RenderOutput(
                renderer=RendererType.HTML,
                success=False,
                error=str(exc),
            )

    def render_slide(
        self, slide_dsl: SlideDSL, theme_css: str = ""
    ) -> str:
        """Render a single slide to an HTML fragment."""
        return self._compile_slide(slide_dsl)

    # ──────────────────────────────────────────────────────────
    # DOCUMENT WRAPPER
    # ──────────────────────────────────────────────────────────

    def _wrap_document(
        self,
        title: str,
        css: str,
        slides_html: str,
        chart_cdn: str,
        has_charts: bool,
    ) -> str:
        """Wrap slides in a complete HTML document."""
        chart_script = _CHART_JS if has_charts else "function renderCharts(){}"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
{chart_cdn}
</head>
<body>
<div id="progress-bar"></div>
{slides_html}
<div id="slide-counter"></div>
<div id="keyboard-hint">\u2190 \u2192 Navigate &middot; N Notes &middot; F Fullscreen</div>
<div id="notes-panel">
  <h3>Speaker Notes</h3>
  <div class="notes-content"></div>
</div>
<script>{chart_script}</script>
<script>{_NAV_JS}</script>
</body>
</html>"""

    # ──────────────────────────────────────────────────────────
    # SLIDE COMPILER DISPATCH
    # ──────────────────────────────────────────────────────────

    def _compile_slide(self, slide_dsl: SlideDSL) -> str:
        """Compile a SlideDSL to an HTML fragment."""
        layout = slide_dsl.layout
        content = slide_dsl.content
        style = slide_dsl.style

        compiler_map = {
            LayoutType.CENTER_FOCUS: self._compile_center_focus,
            LayoutType.SPLIT_SCREEN: self._compile_split_screen,
            LayoutType.FULL_BLEED: self._compile_full_bleed,
            LayoutType.GRID_2X2: self._compile_grid_2x2,
            LayoutType.GRID_3X1: self._compile_grid_3x1,
            LayoutType.TEXT_LEFT_VISUAL_RIGHT: self._compile_text_left_visual_right,
            LayoutType.TEXT_RIGHT_VISUAL_LEFT: self._compile_text_right_visual_left,
            LayoutType.TOP_BOTTOM: self._compile_top_bottom,
            LayoutType.OVERLAY: self._compile_overlay,
            LayoutType.BULLETS: self._compile_bullets,
            LayoutType.COMPARISON: self._compile_comparison,
            LayoutType.TIMELINE: self._compile_timeline,
            LayoutType.KPI_DASHBOARD: self._compile_kpi_dashboard,
            LayoutType.QUOTE: self._compile_quote,
            LayoutType.TEAM_GRID: self._compile_team_grid,
            LayoutType.CHART: self._compile_chart,
            LayoutType.BLANK: self._compile_blank,
        }

        compiler = compiler_map.get(layout, self._compile_center_focus)
        inner_html = compiler(content)

        # Inline style overrides from DSL
        inline_style = self._inline_style(style)

        # 3D fallback notice
        three_d_html = ""
        if slide_dsl.threeScene:
            scene_type = slide_dsl.threeScene.type.value.replace("-", " ").title()
            three_d_html = (
                f'<div class="three-d-notice">'
                f'[Interactive {_esc(scene_type)} Scene &mdash; '
                f'view in browser for full 3D]</div>'
            )

        # Speaker notes (hidden)
        notes_html = ""
        if slide_dsl.speakerNotes:
            notes_html = (
                f'<div class="slide-notes" style="display:none">'
                f'{_esc(slide_dsl.speakerNotes)}</div>'
            )

        layout_name = layout.value if layout else "center-focus"
        return (
            f'<div class="slide" data-layout="{_esc(layout_name)}" '
            f'data-index="{slide_dsl.index}"{inline_style}>'
            f'\n{inner_html}\n{three_d_html}{notes_html}\n</div>'
        )

    def _inline_style(self, style) -> str:
        """Extract inline style string from SlideDSL.style."""
        parts = []
        if style.background and style.background.colors:
            parts.append(f"background:{style.background.colors[0]}")
        if style.accentColor:
            parts.append(f"color:{style.accentColor}")
        if not parts:
            return ""
        return f' style="{";".join(parts)}"'

    # ══════════════════════════════════════════════════════════
    # 17 LAYOUT COMPILERS
    # ══════════════════════════════════════════════════════════

    def _compile_center_focus(self, c: SlideContentV2) -> str:
        """Hero / center focus."""
        title = f'<h1 class="slide-title">{_esc(c.title)}</h1>'
        sub = (
            f'<p class="slide-subtitle">{_esc(c.subtitle)}</p>'
            if c.subtitle else ""
        )
        tagline = (
            f'<p class="slide-body" style="margin-top:1rem;font-size:.9rem;'
            f'color:var(--text-muted)">{_esc(c.tagline)}</p>'
            if c.tagline else ""
        )
        presenter = (
            f'<p style="margin-top:1.5rem;font-size:.85rem;color:var(--primary);'
            f'font-weight:600">{_esc(c.presenter)}</p>'
            if c.presenter else ""
        )
        return (
            f'<div class="hero-slide" style="display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center;text-align:center;flex:1">'
            f'{title}{sub}{tagline}{presenter}</div>'
        )

    def _compile_split_screen(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        left = _esc(c.left_content or c.body_text or "")
        right = _esc(c.right_content or "")
        return (
            f'{title}<div class="split-container">'
            f'<div class="split-half"><div class="slide-body">{left}</div></div>'
            f'<div class="split-half"><div class="slide-body">{right}</div></div>'
            f'</div>'
        )

    def _compile_full_bleed(self, c: SlideContentV2) -> str:
        title = f'<h1 class="slide-title" style="color:#fff;font-size:3rem">{_esc(c.title)}</h1>'
        sub = (
            f'<p class="slide-subtitle" style="color:rgba(255,255,255,.8)">{_esc(c.subtitle)}</p>'
            if c.subtitle else ""
        )
        bg_style = ""
        if c.image_url:
            bg_style = (
                f'style="background:url(\'{_esc(c.image_url)}\') center/cover;'
                f'justify-content:center;align-items:center;text-align:center"'
            )
        return (
            f'<div class="hero-slide" {bg_style}>{title}{sub}</div>'
        )

    def _compile_grid_2x2(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        cells = []
        if c.kpi_metrics:
            for m in c.kpi_metrics[:4]:
                cells.append(self._render_kpi_cell(m))
        elif c.bullets:
            for b in c.bullets[:4]:
                cells.append(f'<div class="grid-cell">{_esc(b)}</div>')
        return f'{title}<div class="grid-2x2">{"".join(cells)}</div>'

    def _compile_grid_3x1(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        cells = []
        if c.kpi_metrics:
            for m in c.kpi_metrics[:3]:
                cells.append(self._render_kpi_cell(m))
        elif c.bullets:
            for b in c.bullets[:3]:
                cells.append(f'<div class="grid-cell" style="text-align:center">{_esc(b)}</div>')
        return f'{title}<div class="grid-3x1">{"".join(cells)}</div>'

    def _compile_text_left_visual_right(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        bullets = self._render_bullet_list(c.bullets) if c.bullets else ""
        prompt = _esc(c.image_prompt or "Visual")
        img = (
            f'<div class="image-placeholder">[{prompt}]</div>'
        )
        return (
            f'{title}<div class="split-container">'
            f'<div class="split-half">{bullets}</div>'
            f'<div class="split-half">{img}</div>'
            f'</div>'
        )

    def _compile_text_right_visual_left(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        bullets = self._render_bullet_list(c.bullets) if c.bullets else ""
        prompt = _esc(c.image_prompt or "Visual")
        img = f'<div class="image-placeholder">[{prompt}]</div>'
        return (
            f'{title}<div class="split-container">'
            f'<div class="split-half">{img}</div>'
            f'<div class="split-half">{bullets}</div>'
            f'</div>'
        )

    def _compile_top_bottom(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title" style="text-align:center">{_esc(c.title)}</h2>'
        body = _esc(c.body_text or c.subtitle or "")
        return (
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center">'
            f'{title}<div class="slide-body" style="text-align:center;margin-top:2rem">{body}</div>'
            f'</div>'
        )

    def _compile_overlay(self, c: SlideContentV2) -> str:
        title = f'<h1 class="slide-title">{_esc(c.title)}</h1>'
        body = (
            f'<div class="slide-body">{_esc(c.body_text)}</div>'
            if c.body_text else ""
        )
        return (
            f'<div class="overlay-slide" style="display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center;text-align:center;flex:1">'
            f'{title}{body}</div>'
        )

    def _compile_bullets(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        bullets = self._render_bullet_list(c.bullets) if c.bullets else ""
        return f'{title}{bullets}'

    def _compile_comparison(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        if not c.comparison_items:
            return title

        us_items = ""
        them_items = ""
        for item in c.comparison_items:
            if item.us:
                us_items += (
                    f'<div class="comparison-item">'
                    f'\u2713 {_esc(item.label)}: {_esc(item.us)}</div>'
                )
            if item.them:
                them_items += (
                    f'<div class="comparison-item">'
                    f'\u2717 {_esc(item.label)}: {_esc(item.them)}</div>'
                )

        return (
            f'{title}<div class="comparison-row">'
            f'<div class="comparison-col us">'
            f'<div class="comparison-header" style="color:var(--primary)">Our Solution</div>'
            f'{us_items}</div>'
            f'<div class="comparison-col them">'
            f'<div class="comparison-header" style="color:var(--text-muted)">Competition</div>'
            f'{them_items}</div>'
            f'</div>'
        )

    def _compile_timeline(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        if not c.timeline_items:
            return title

        items_html = ""
        for event in c.timeline_items[:6]:
            desc = (
                f'<div class="timeline-desc">{_esc(event.description)}</div>'
                if event.description else ""
            )
            items_html += (
                f'<div class="timeline-item">'
                f'<div class="timeline-date">{_esc(event.date)}</div>'
                f'<div class="timeline-title">{_esc(event.title)}</div>'
                f'{desc}</div>'
            )

        return f'{title}<div class="timeline-container">{items_html}</div>'

    def _compile_kpi_dashboard(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        if not c.kpi_metrics:
            return title

        cols = 3 if len(c.kpi_metrics) > 2 else len(c.kpi_metrics)
        grid_class = f"grid-{cols}x1" if cols == 3 else "grid-2x2"
        cells = [self._render_kpi_cell(m) for m in c.kpi_metrics[:6]]
        return (
            f'{title}<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
            f'gap:1.5rem;flex:1">{"".join(cells)}</div>'
        )

    def _compile_quote(self, c: SlideContentV2) -> str:
        text = c.quote_text or c.body_text or ""
        author = c.quote_author or ""
        title_html = (
            f'<h2 class="slide-title" style="margin-bottom:1rem">{_esc(c.title)}</h2>'
            if c.title else ""
        )
        author_html = (
            f'<div class="quote-author">&mdash; {_esc(author)}</div>'
            if author else ""
        )
        return (
            f'{title_html}'
            f'<div style="flex:1;display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center">'
            f'<div class="quote-mark">\u201C</div>'
            f'<div class="quote-text">{_esc(text)}</div>'
            f'{author_html}</div>'
        )

    def _compile_team_grid(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        if not c.team_members:
            return title

        cards = ""
        for member in c.team_members[:8]:
            bio = (
                f'<div class="team-bio">{_esc(member.bio)}</div>'
                if member.bio else ""
            )
            cards += (
                f'<div class="team-card">'
                f'<div class="team-name">{_esc(member.name)}</div>'
                f'<div class="team-role">{_esc(member.role)}</div>'
                f'{bio}</div>'
            )

        return f'{title}<div class="team-grid">{cards}</div>'

    def _compile_chart(self, c: SlideContentV2) -> str:
        title = f'<h2 class="slide-title">{_esc(c.title)}</h2>'
        chart_data = c.chart_data or {}
        chart_type = chart_data.get("type", "bar")
        chart_json = html_mod.escape(json.dumps(chart_data), quote=True)

        return (
            f'{title}<div class="chart-container">'
            f'<canvas class="slide-chart" '
            f'data-chart="{chart_json}" '
            f'data-type="{_esc(chart_type)}"></canvas>'
            f'</div>'
        )

    def _compile_blank(self, c: SlideContentV2) -> str:
        title = (
            f'<h2 class="slide-title" style="text-align:center">{_esc(c.title)}</h2>'
            if c.title else ""
        )
        body = (
            f'<div class="slide-body" style="text-align:center">{_esc(c.body_text)}</div>'
            if c.body_text else ""
        )
        return (
            f'<div style="flex:1;display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center">{title}{body}</div>'
        )

    # ──────────────────────────────────────────────────────────
    # SHARED FRAGMENT HELPERS
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _render_bullet_list(bullets: list[str]) -> str:
        """Render a bullet list to HTML."""
        items = "".join(f"<li>{_esc(b)}</li>" for b in bullets)
        return f'<ul class="slide-bullets">{items}</ul>'

    @staticmethod
    def _render_kpi_cell(metric) -> str:
        """Render a single KPI metric card."""
        change_class = ""
        change_html = ""
        if metric.change:
            is_positive = str(metric.change).startswith("+")
            change_class = "positive" if is_positive else "negative"
            change_html = (
                f'<div class="kpi-change {change_class}">'
                f'{_esc(metric.change)}</div>'
            )
        return (
            f'<div class="grid-cell" style="text-align:center">'
            f'<div class="kpi-value">{_esc(metric.value)}</div>'
            f'{change_html}'
            f'<div class="kpi-label">{_esc(metric.label)}</div>'
            f'</div>'
        )
