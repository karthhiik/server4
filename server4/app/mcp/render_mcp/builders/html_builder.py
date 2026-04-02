"""
HTML Builder — generates premium interactive HTML presentations.

Features:
- Tailwind CSS via CDN with theme-aware color/font configuration
- CSS animations (fade-in, slide-left, slide-up, zoom-in)
- Keyboard navigation (arrow keys, space, escape)
- Touch swipe support for mobile
- Progress bar and slide counter
- Speaker notes toggle (press 'N')
- Fullscreen mode (press 'F')
- Chart.js integration with theme colors
- Print-friendly @media print rules
- Offline detection with fallback CSS
- Responsive design for tablet/phone
"""

import html as html_mod
import json
from typing import Optional

import structlog

logger = structlog.get_logger()

_OFFLINE_JS = (
    "(function(){"
    "var i=setInterval(function(){"
    "if(typeof tailwind==='undefined'||typeof Chart==='undefined'){"
    "var s=document.createElement('style');"
    "s.textContent='.slide{display:block!important;padding:2rem 3rem;font-family:sans-serif;min-height:100vh;box-sizing:border-box;}"
    ".slide:not(.active){display:none!important;}"
    "body{background:#fff;color:#111;margin:0;}"
    "h1,h2{margin:0.5em 0;}ul{padding-left:1.5em;}"
    ".two-col{display:flex;gap:2rem;}.two-col>div{flex:1;}"
    "#progress-bar,#nav-controls,#slide-counter,#keyboard-hint{display:none!important;}';"
    "document.head.appendChild(s);clearInterval(i);"
    "if(!navigator.onLine)alert('This presentation requires an internet connection for styles and charts.\\n\\nPlease connect to the internet and reload.');"
    "}"
    "},2000);"
    "setTimeout(function(){clearInterval(i);},10000);"
    "})();"
)

_NAV_JS = (
    "(function(){"
    "var slides=document.querySelectorAll('.slide');"
    "var current=0,total=slides.length;"
    "var pEl=document.getElementById('progress-bar');"
    "var cEl=document.getElementById('slide-counter');"
    "var nPanel=document.getElementById('notes-panel');"
    "var nVis=false;"
    "function showSlide(idx){"
    "if(idx<0||idx>=total)return;"
    "slides[current].classList.remove('active','slide-enter');"
    "current=idx;"
    "slides[current].classList.add('active','slide-enter');"
    "if(pEl)pEl.style.width=((current+1)/total*100)+'%';"
    "if(cEl)cEl.textContent=(current+1)+' / '+total;"
    "renderChartsForSlide(slides[current]);"
    "}"
    "function nextSlide(){showSlide(current+1);}"
    "function prevSlide(){showSlide(current-1);}"
    "document.addEventListener('keydown',function(e){"
    "if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();nextSlide();}"
    "else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prevSlide();}"
    "else if(e.key==='Home'){e.preventDefault();showSlide(0);}"
    "else if(e.key==='End'){e.preventDefault();showSlide(total-1);}"
    "else if(e.key==='n'||e.key==='N'){e.preventDefault();nVis=!nVis;if(nPanel)nPanel.style.display=nVis?'flex':'none';}"
    "else if(e.key==='f'||e.key==='F'){e.preventDefault();if(!document.fullscreenElement)document.documentElement.requestFullscreen().catch(function(){});else document.exitFullscreen().catch(function(){});}"
    "else if(e.key==='Escape'){if(nVis){nVis=false;nPanel.style.display='none';}}"
    "});"
    "var tsx=0,tsy=0;"
    "document.addEventListener('touchstart',function(e){tsx=e.changedTouches[0].screenX;tsy=e.changedTouches[0].screenY;},{passive:true});"
    "document.addEventListener('touchend',function(e){"
    "var dx=e.changedTouches[0].screenX-tsx,dy=e.changedTouches[0].screenY-tsy;"
    "if(Math.abs(dx)>Math.abs(dy)&&Math.abs(dx)>50){if(dx<0)nextSlide();else prevSlide();}"
    "},{passive:true});"
    "if(slides.length>0){slides[0].classList.add('active','slide-enter');if(pEl)pEl.style.width=(1/total*100)+'%';if(cEl)cEl.textContent='1 / '+total;renderChartsForSlide(slides[0]);}"
    "window.PresentationNav={next:nextSlide,prev:prevSlide,goTo:showSlide,current:function(){return current;}};"
    "})();"
)

_CHART_JS = (
    "var __chartInstances={};"
    "function renderChartsForSlide(slideEl){"
    "if(typeof Chart==='undefined')return;"
    "slideEl.querySelectorAll('canvas.slide-chart').forEach(function(canvas){"
    "var id=canvas.id||('chart-'+Math.random().toString(36).substr(2,9));"
    "canvas.id=id;"
    "if(__chartInstances[id]){__chartInstances[id].destroy();}"
    "try{"
    "var data=JSON.parse(canvas.dataset.chart||'{}');"
    "var type=canvas.dataset.type||'bar';"
    "var primary=getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim()||'#2563eb';"
    "var colors=[primary,'#7c3aed','#059669','#d97706','#dc2626','#0891b2'];"
    "if(data.labels){"
    "__chartInstances[id]=new Chart(canvas,{type:type==='donut'?'doughnut':type,data:{labels:data.labels,datasets:(data.datasets||[]).map(function(ds,i){return{label:ds.label,data:ds.values,backgroundColor:colors[i%colors.length],borderColor:colors[i%colors.length],borderWidth:1};})},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:data.datasets&&data.datasets.length>1}}}});"
    "}"
    "}catch(e){console.warn('Chart render failed:',e);}"
    "});"
    "}"
)


class HtmlBuilder:
    """Builds premium interactive HTML presentations with Tailwind CSS."""

    def build(self, slides: list[dict], theme: dict, metadata: dict = None) -> str:
        """Build a complete interactive HTML presentation."""
        metadata = metadata or {}
        colors = theme.get("colors", {})
        fonts = theme.get("fonts", {})

        slides_html = "\n".join(
            self._render_slide(slide, colors, fonts) for slide in slides
        )

        title = metadata.get("title", "Presentation")
        full_html = self._wrap_html(slides_html, title, colors, fonts)
        logger.info("html_built", slide_count=len(slides))
        return full_html

    def _render_slide(self, slide: dict, colors: dict, fonts: dict) -> str:
        """Render a single slide to HTML."""
        layout = slide.get("layout", "bullets")
        content = slide.get("content", {})
        notes = slide.get("speaker_notes", "")

        renderer = getattr(self, f"_render_{layout.replace('-', '_')}", None)
        if renderer:
            inner = renderer(content, colors, fonts)
        else:
            inner = self._render_bullets(content, colors, fonts)

        notes_html = ""
        if notes:
            escaped_notes = html_mod.escape(notes)
            notes_html = (
                f'\n<div class="slide-notes hidden p-4 bg-gray-50 border-t '
                f'border-gray-200 text-sm text-gray-600 overflow-y-auto">'
                f"{escaped_notes}</div>"
            )

        return (
            f'<div class="slide" data-layout="{layout}">\n{inner}{notes_html}\n</div>'
        )

    # ── Layout Renderers ─────────────────────────────────────────────

    def _render_title_hero(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        subtitle = html_mod.escape(content.get("subtitle", ""))
        primary = colors.get("primary", "#2563eb")
        accent = colors.get("accent", "#7c3aed")
        hf = fonts.get("heading", "Inter")
        sub = (
            f'<p class="text-xl md:text-2xl text-white/80 max-w-2xl">{subtitle}</p>'
            if subtitle
            else ""
        )
        return (
            f'<div class="flex flex-col items-center justify-center h-full '
            f'text-center px-8 animate-fade-in" style="background:linear-gradient('
            f'135deg,{primary},{accent})">'
            f'<h1 class="text-5xl md:text-6xl font-bold text-white mb-4 '
            f'tracking-tight leading-tight" style="font-family:\'{hf}\',sans-serif">'
            f"{title}</h1>{sub}</div>"
        )

    def _render_bullets(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        bullets = content.get("bullets", [])
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        items = "\n".join(
            f'      <li class="flex items-start gap-3 py-2">'
            f'<span class="mt-1.5 w-2 h-2 rounded-full flex-shrink-0" '
            f'style="background:{primary}"></span>'
            f'<span class="text-lg leading-relaxed">{html_mod.escape(str(b))}</span></li>'
            for b in bullets
        )
        return (
            f'<div class="px-10 py-8 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-6 pb-3 border-b-2" style="color:{primary};'
            f"border-color:{primary};font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<ul class="space-y-2 flex-1">\n{items}\n  </ul></div>'
        )

    def _render_bullets_with_image(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        bullets = content.get("bullets", [])
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        items = "\n".join(
            f'      <li class="flex items-start gap-3 py-1.5">'
            f'<span class="mt-1.5 w-2 h-2 rounded-full flex-shrink-0" '
            f'style="background:{primary}"></span>'
            f'<span class="text-base leading-relaxed">{html_mod.escape(str(b))}</span></li>'
            for b in bullets
        )
        img = content.get("image_url") or ""
        if img:
            img_html = (
                f'<img src="{html_mod.escape(img)}" alt="slide image" '
                f'class="w-full h-full object-cover rounded-xl shadow-lg">'
            )
        else:
            img_html = (
                f'<div class="w-full h-full flex items-center justify-center '
                f'rounded-xl text-gray-400 bg-gray-100 text-sm p-4">'
                f"{html_mod.escape(content.get('image_prompt', 'Image placeholder'))}</div>"
            )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-4" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 min-h-0">'
            f'<div class="flex flex-col justify-center"><ul class="space-y-1.5">'
            f"\n{items}\n      </ul></div>"
            f'<div class="flex items-center justify-center">{img_html}</div>'
            f"</div></div>"
        )

    def _render_two_column(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        left = html_mod.escape(content.get("left_content", ""))
        right = html_mod.escape(content.get("right_content", ""))
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        surf = colors.get("surface", "#f9fafb")
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-6" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-8">'
            f'<div class="p-6 rounded-xl" style="background:{surf}">'
            f'<p class="text-base leading-relaxed whitespace-pre-wrap">{left}</p></div>'
            f'<div class="p-6 rounded-xl" style="background:{surf}">'
            f'<p class="text-base leading-relaxed whitespace-pre-wrap">{right}</p></div>'
            f"</div></div>"
        )

    def _render_chart(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        chart_data = content.get("chart_data", {})
        source = html_mod.escape(content.get("source_attribution", ""))
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        chart_id = f"chart-{hash(json.dumps(chart_data)) % 100000}"
        data_json = html_mod.escape(json.dumps(chart_data))
        src_html = (
            f"<p class='text-xs mt-3' style='color:{colors.get('text_secondary', '#9ca3af')}'>"
            f"Source: {source}</p>"
            if source
            else ""
        )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-4" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 flex items-center justify-center min-h-0">'
            f'<div class="w-full max-w-3xl h-80">'
            f'<canvas id="{chart_id}" class="slide-chart" data-chart=\'{data_json}\' '
            f'data-type="{content.get("chart_type", "bar")}"></canvas></div></div>'
            f"{src_html}</div>"
        )

    def _render_comparison(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        left_label = html_mod.escape(content.get("left_label", ""))
        right_label = html_mod.escape(content.get("right_label", ""))
        primary = colors.get("primary", "#2563eb")
        accent = colors.get("accent", "#7c3aed")
        hf = fonts.get("heading", "Inter")
        surf = colors.get("surface", "#f9fafb")
        left_items = "\n".join(
            f'<li class="flex items-start gap-2 py-1.5">'
            f'<span class="text-green-500 font-bold">\u2713</span>'
            f"<span>{html_mod.escape(str(i))}</span></li>"
            for i in content.get("left_items", [])
        )
        right_items = "\n".join(
            f'<li class="flex items-start gap-2 py-1.5">'
            f'<span class="text-red-500 font-bold">\u2717</span>'
            f"<span>{html_mod.escape(str(i))}</span></li>"
            for i in content.get("right_items", [])
        )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-6" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">'
            f'<div class="p-6 rounded-xl border-2" style="border-color:{primary};background:{surf}">'
            f'<h3 class="text-xl font-bold mb-3" style="color:{primary}">{left_label}</h3>'
            f'<ul class="space-y-1">{left_items}</ul></div>'
            f'<div class="p-6 rounded-xl border-2 border-gray-200" style="background:{surf}">'
            f'<h3 class="text-xl font-bold mb-3 text-gray-600">{right_label}</h3>'
            f'<ul class="space-y-1">{right_items}</ul></div>'
            f"</div></div>"
        )

    def _render_timeline(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        events = content.get("events", [])
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        items = "\n".join(
            f'<div class="flex flex-col items-center text-center flex-1 min-w-0 px-2">'
            f'<div class="w-4 h-4 rounded-full mb-3 flex-shrink-0" style="background:{primary}"></div>'
            f'<strong class="text-sm mb-1" style="color:{primary}">'
            f"{html_mod.escape(e.get('date', ''))}</strong>"
            f'<p class="text-sm leading-snug">{html_mod.escape(e.get("description", ""))}</p></div>'
            for e in events
        )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-8" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 flex items-start relative">'
            f'<div class="absolute top-2 left-0 right-0 h-0.5" style="background:{primary};opacity:0.3"></div>'
            f'<div class="flex w-full relative z-10 pt-4">\n{items}\n    </div></div></div>'
        )

    def _render_quote(self, content, colors, fonts):
        quote = html_mod.escape(content.get("quote_text", ""))
        author = html_mod.escape(content.get("quote_author", ""))
        role = html_mod.escape(content.get("quote_role", ""))
        primary = colors.get("primary", "#2563eb")
        surf = colors.get("surface", "#f9fafb")
        role_html = f'<span class="text-gray-500 ml-1">, {role}</span>' if role else ""
        return (
            f'<div class="px-12 py-8 h-full flex flex-col items-center justify-center '
            f'text-center animate-fade-in" style="background:{surf}">'
            f'<div class="text-6xl mb-4 opacity-20" style="color:{primary}">"</div>'
            f'<blockquote class="text-2xl md:text-3xl font-medium italic leading-relaxed '
            f'max-w-3xl mb-6" style="color:{colors.get("text_primary", "#111827")}">'
            f'"{quote}"</blockquote>'
            f'<cite class="not-italic">'
            f'<span class="font-bold text-lg" style="color:{primary}">\u2014 {author}</span>'
            f"{role_html}</cite></div>"
        )

    def _render_team_grid(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        members = content.get("members", [])
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        surf = colors.get("surface", "#f9fafb")
        cards = "\n".join(
            f'<div class="p-5 rounded-xl text-center" style="background:{surf}">'
            f'<div class="w-16 h-16 rounded-full mx-auto mb-3 flex items-center '
            f'justify-center text-white text-xl font-bold" style="background:{primary}">'
            f"{html_mod.escape(m.get('name', '?')[:1].upper())}</div>"
            f'<h3 class="font-bold text-lg">{html_mod.escape(m.get("name", ""))}</h3>'
            f'<p class="text-sm font-medium mb-1" style="color:{primary}">'
            f"{html_mod.escape(m.get('role', ''))}</p>"
            f'<p class="text-xs text-gray-500 leading-snug">'
            f"{html_mod.escape(m.get('bio', ''))}</p></div>"
            for m in members
        )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-6" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 grid grid-cols-2 md:grid-cols-3 gap-4 content-start">'
            f"\n{cards}\n  </div></div>"
        )

    def _render_kpi_dashboard(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        metrics = content.get("metrics", [])
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        surf = colors.get("surface", "#f9fafb")
        cards = "\n".join(
            f'<div class="p-6 rounded-xl text-center" style="background:{surf}">'
            f'<div class="text-4xl font-bold mb-1" style="color:{primary}">'
            f"{html_mod.escape(str(m.get('value', '')))}</div>"
            f'<div class="text-sm font-medium mb-1 '
            f'{"text-green-600" if str(m.get("change", "")).startswith("+") else "text-red-600"}">'
            f"{html_mod.escape(str(m.get('change', '')))}</div>"
            f'<div class="text-xs text-gray-500">'
            f"{html_mod.escape(str(m.get('label', '')))}</div></div>"
            for m in metrics
        )
        return (
            f'<div class="px-8 py-6 h-full flex flex-col animate-slide-up">'
            f'<h2 class="text-3xl font-bold mb-6" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<div class="flex-1 grid grid-cols-2 md:grid-cols-3 gap-4 content-start">'
            f"\n{cards}\n  </div></div>"
        )

    def _render_full_image(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        subtitle = html_mod.escape(content.get("subtitle", ""))
        img = content.get("image_url") or ""
        if img:
            bg_style = (
                f"background-image:url({html_mod.escape(img)});"
                f"background-size:cover;background-position:center;"
            )
        else:
            bg_style = f"background:{colors.get('primary', '#2563eb')};"
        sub = f'<p class="text-lg text-white/80">{subtitle}</p>' if subtitle else ""
        return (
            f'<div class="h-full w-full flex flex-col items-center justify-center '
            f'text-center px-8 animate-fade-in" style="{bg_style}">'
            f'<div class="bg-black/40 backdrop-blur-sm p-8 rounded-xl max-w-2xl">'
            f'<h2 class="text-4xl font-bold text-white mb-2">{title}</h2>{sub}'
            f"</div></div>"
        )

    def _render_blank(self, content, colors, fonts):
        title = html_mod.escape(content.get("title", ""))
        body = html_mod.escape(content.get("body_text", ""))
        primary = colors.get("primary", "#2563eb")
        hf = fonts.get("heading", "Inter")
        return (
            f'<div class="px-10 py-8 h-full flex flex-col items-center justify-center '
            f'text-center animate-fade-in">'
            f'<h2 class="text-3xl font-bold mb-4" style="color:{primary};'
            f"font-family:'{hf}',sans-serif\">{title}</h2>"
            f'<p class="text-lg max-w-2xl leading-relaxed">{body}</p></div>'
        )

    # ── Document Wrapper ─────────────────────────────────────────────

    def _wrap_html(
        self, slides_html: str, title: str, colors: dict, fonts: dict
    ) -> str:
        """Wrap slides in a complete interactive HTML document."""
        primary = colors.get("primary", "#2563eb")
        bg = colors.get("background", "#ffffff")
        text = colors.get("text_primary", "#111827")
        heading_font = fonts.get("heading", "Inter")
        body_font = fonts.get("body", "Inter")
        accent = colors.get("accent", "#7c3aed")
        surface = colors.get("surface", "#f9fafb")
        text_sec = colors.get("text_secondary", "#9ca3af")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html_mod.escape(title)}</title>
<meta name="generator" content="Barise Presentation Service">

<!-- Offline detection (runs before CDNs load) -->
<script>{_OFFLINE_JS}</script>

<!-- Tailwind CSS CDN with theme config -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        primary: '{primary}',
        accent: '{accent}',
        surface: '{surface}',
      }},
      fontFamily: {{
        heading: ['{heading_font}', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body: ['{body_font}', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      }},
      animation: {{
        'fade-in': 'fadeIn 0.6s ease-out both',
        'slide-up': 'slideUp 0.5s ease-out both',
        'slide-left': 'slideLeft 0.5s ease-out both',
        'zoom-in': 'zoomIn 0.4s ease-out both',
      }},
      keyframes: {{
        fadeIn: {{ '0%': {{ opacity: '0' }}, '100%': {{ opacity: '1' }} }},
        slideUp: {{ '0%': {{ opacity: '0', transform: 'translateY(20px)' }}, '100%': {{ opacity: '1', transform: 'translateY(0)' }} }},
        slideLeft: {{ '0%': {{ opacity: '0', transform: 'translateX(30px)' }}, '100%': {{ opacity: '1', transform: 'translateX(0)' }} }},
        zoomIn: {{ '0%': {{ opacity: '0', transform: 'scale(0.95)' }}, '100%': {{ opacity: '1', transform: 'scale(1)' }} }},
      }},
    }}
  }}
}}
</script>

<style>
:root {{ --primary-color: {primary}; --bg-color: {bg}; --text-color: {text}; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: {bg}; color: {text}; font-family: '{body_font}', sans-serif; }}

/* Slide container */
.slide {{ width: 100vw; height: 100vh; display: none; position: relative; overflow: hidden; }}
.slide.active {{ display: flex; }}
.slide-enter {{ animation: fadeIn 0.4s ease-out; }}

/* Progress bar */
#progress-bar {{ position: fixed; bottom: 0; left: 0; height: 3px; background: {primary}; transition: width 0.3s ease; z-index: 100; }}

/* Slide counter */
#slide-counter {{ position: fixed; bottom: 12px; right: 16px; font-size: 0.75rem; color: {text_sec}; z-index: 100; font-family: monospace; }}

/* Navigation controls */
#nav-controls {{ position: fixed; bottom: 12px; left: 16px; display: flex; gap: 8px; z-index: 100; }}
.nav-btn {{ width: 32px; height: 32px; border: none; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; background: {primary}; color: white; opacity: 0.8; transition: opacity 0.2s; }}
.nav-btn:hover {{ opacity: 1; }}

/* Notes panel */
#notes-panel {{ position: fixed; bottom: 0; left: 0; right: 0; height: 30vh; background: white; border-top: 2px solid {primary}; z-index: 200; display: none; flex-direction: column; }}
#notes-panel .notes-header {{ padding: 8px 16px; background: {primary}; color: white; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }}
#notes-panel .notes-content {{ flex: 1; overflow-y: auto; padding: 16px; font-size: 0.9rem; line-height: 1.6; }}

/* Keyboard hint */
#keyboard-hint {{ position: fixed; top: 12px; right: 16px; font-size: 0.7rem; color: {text_sec}; z-index: 100; opacity: 0.6; }}

/* Print styles */
@media print {{
  .slide {{ display: block !important; page-break-after: always; width: 100%; height: auto; min-height: 100vh; }}
  #progress-bar, #nav-controls, #slide-counter, #keyboard-hint {{ display: none !important; }}
  body {{ overflow: visible; }}
}}

/* Responsive adjustments */
@media (max-width: 768px) {{
  .slide {{ padding: 0; }}
  h2 {{ font-size: 1.5rem !important; }}
  .text-3xl {{ font-size: 1.25rem !important; }}
  .text-4xl {{ font-size: 1.5rem !important; }}
  .text-5xl {{ font-size: 1.75rem !important; }}
}}
</style>
</head>
<body>

<!-- Slides -->
{slides_html}

<!-- Progress bar -->
<div id="progress-bar"></div>

<!-- Slide counter -->
<div id="slide-counter"></div>

<!-- Navigation controls -->
<div id="nav-controls">
  <button class="nav-btn" onclick="window.PresentationNav && window.PresentationNav.prev()" title="Previous slide (&larr;)">&#9664;</button>
  <button class="nav-btn" onclick="window.PresentationNav && window.PresentationNav.next()" title="Next slide (&rarr;)">&#9654;</button>
</div>

<!-- Keyboard hint -->
<div id="keyboard-hint">&larr; &rarr; navigate &middot; N notes &middot; F fullscreen</div>

<!-- Speaker notes panel -->
<div id="notes-panel">
  <div class="notes-header">
    <span>Speaker Notes</span>
    <button onclick="document.getElementById('notes-panel').style.display='none'" style="background:none;border:none;color:white;cursor:pointer;font-size:18px;">&#10005;</button>
  </div>
  <div class="notes-content" id="notes-content"></div>
</div>

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>

<!-- Navigation and chart scripts -->
<script>{_CHART_JS}</script>
<script>{_NAV_JS}</script>

</body>
</html>"""
