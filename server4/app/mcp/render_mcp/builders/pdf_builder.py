"""
PDF Builder V3 — Investor-Grade Pitch Deck Generation

Design philosophy inspired by Chronicle, Dokie, Pitch.com, and YC standards:
- Editorial/Swiss typography (oversized display, tight tracking, generous whitespace)
- Bento grid layouts with asymmetric composition
- SVG-based data visualization (line, area, bar, donut with smooth curves)
- Image treatments: duotone overlays, masks, side-by-side splits
- Minimal decorative elements (hairlines, dots, geometric accents)
- One hero element per slide, ruthless visual hierarchy
"""

import html as html_mod
import os
import math
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Optional

import structlog

from app.mcp.render_mcp.config import PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT

logger = structlog.get_logger()


def _is_placeholder_url(url) -> bool:
    """True for fake/demo image URLs that should never ship in a deck."""
    text = str(url or "").strip().lower()
    return (
        (not text)
        or "example.com" in text
        or "placeholder" in text
        or "dummyimage.com" in text
        or "placehold.co" in text
        or "via.placeholder.com" in text
    )


def _plain_text(value, *, fallback: str = "") -> str:
    """Coerce generated content into readable copy without leaking raw dicts."""
    if value is None:
        return fallback
    if isinstance(value, dict):
        for key in (
            "title", "name", "label", "value", "headline", "description",
            "detail", "body", "text", "copy",
        ):
            found = value.get(key)
            if found not in (None, ""):
                return _plain_text(found, fallback=fallback)
        return fallback
    if isinstance(value, (list, tuple)):
        parts = [_plain_text(v) for v in value]
        return ", ".join(part for part in parts if part) or fallback
    text = str(value)
    text = (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt", "<")
        .replace("&gt", ">")
    )
    return html_mod.unescape(text).strip() or fallback


def _field_text(item, keys: tuple[str, ...], *, fallback: str = "") -> str:
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return _plain_text(value, fallback=fallback)
        return fallback
    return _plain_text(item, fallback=fallback)


def _hex_rgb(color: str) -> tuple[int, int, int] | None:
    text = str(color or "").strip()
    if not text.startswith("#"):
        return None
    raw = text[1:]
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return None
    try:
        return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _rgba(color: str, alpha: float) -> str:
    rgb = _hex_rgb(color)
    if rgb is None:
        rgb = (255, 255, 255)
    alpha = max(0.0, min(1.0, float(alpha)))
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:.3f})"


def _rel_luminance(color: str) -> float | None:
    rgb = _hex_rgb(color)
    if rgb is None:
        return None
    channels = []
    for channel in rgb:
        c = channel / 255.0
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(a: str, b: str) -> float:
    la = _rel_luminance(a)
    lb = _rel_luminance(b)
    if la is None or lb is None:
        return 7.0
    lighter = max(la, lb)
    darker = min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _is_light(color: str) -> bool:
    lum = _rel_luminance(color)
    return True if lum is None else lum > 0.62


def _readable_pair(background: str, fg: str, fg2: str) -> tuple[str, str]:
    if _contrast_ratio(background, fg) < 4.5:
        fg = "#0f172a" if _is_light(background) else "#f8fafc"
    if _contrast_ratio(background, fg2) < 3.0:
        fg2 = "#475569" if _is_light(background) else "#cbd5e1"
    return fg, fg2


def _safe_border(background: str, border: str) -> str:
    raw = str(border or "").strip().lower()
    if raw in {"#fff", "#ffffff", "#fdffff"}:
        return "#d5dde8" if _is_light(background) else "#263244"
    return border


def _text_panel_colors(base_bg: str, surface: str, fg: str, fg2: str) -> tuple[str, str, str]:
    panel_bg = surface if surface and _contrast_ratio(surface, fg) >= 4.5 else base_bg
    if _contrast_ratio(panel_bg, fg) < 4.5:
        panel_bg = "#ffffff" if not _is_light(fg) else "#07111f"
    panel_fg, panel_fg2 = _readable_pair(panel_bg, fg, fg2)
    return panel_bg, panel_fg, panel_fg2

# ═══════════════════════════════════════════════════════════════════
# Inline SVG Icon Library — Lucide-style, hairline weight
# ═══════════════════════════════════════════════════════════════════

_ICONS = {
    "trending-up": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "users": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "target": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "dollar": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    "shield": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "zap": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "clock": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "check": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    "x": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    "globe": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "layers": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/></svg>',
    "arrow-right": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "activity": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "award": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>',
    "rocket": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4l.5-3.5"/><path d="M15 12h5l-.5 3.5"/></svg>',
    "lightbulb": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>',
    "mail": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    "arrow-up-right": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>',
    "minus": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "plus": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "circle-dot": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>',
}

_ICON_MAP = {
    "growth": "trending-up", "revenue": "dollar", "team": "users",
    "market": "globe", "product": "layers", "traction": "activity",
    "problem": "zap", "solution": "lightbulb", "competition": "shield",
    "vision": "target", "achievement": "award", "innovation": "rocket",
    "timeline": "clock", "contact": "mail", "default": "arrow-right",
}


def _icon(name: str, size: int = 20, color: str = "currentColor", stroke: float = 1.75) -> str:
    """Get inline SVG icon HTML."""
    key = name if name in _ICONS else _ICON_MAP.get(name, "arrow-right")
    svg = _ICONS.get(key, _ICONS["arrow-right"])
    return (svg
        .replace('width="20"', f'width="{size}"')
        .replace('height="20"', f'height="{size}"')
        .replace('stroke="currentColor"', f'stroke="{color}"')
        .replace('stroke-width="1.75"', f'stroke-width="{stroke}"'))


# ═══════════════════════════════════════════════════════════════════
# SVG Chart Builders — Editorial-grade data visualization
# ═══════════════════════════════════════════════════════════════════

def _svg_area_chart(labels: list, values: list, color: str, accent: str,
                     width: int = 580, height: int = 280) -> str:
    """SVG area chart with smooth curve and gradient fill."""
    if not values or len(values) < 2:
        return ""

    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 40
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    max_v = max(float(v) for v in values)
    min_v = min(float(v) for v in values)
    range_v = max_v - min_v or 1
    # Add 10% padding to top
    max_v_padded = max_v + range_v * 0.1
    min_v_padded = max(0, min_v - range_v * 0.05)
    range_v_padded = max_v_padded - min_v_padded or 1

    n = len(values)
    points = []
    for i, v in enumerate(values):
        x = pad_l + (i / (n - 1)) * inner_w
        y = pad_t + (1 - (float(v) - min_v_padded) / range_v_padded) * inner_h
        points.append((x, y))

    # Smooth curve using cubic bezier
    def _smooth_path(pts: list[tuple]) -> str:
        if len(pts) < 2:
            return ""
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
        for i in range(1, len(pts)):
            p_prev = pts[i - 1]
            p = pts[i]
            cp1x = p_prev[0] + (p[0] - p_prev[0]) * 0.5
            cp1y = p_prev[1]
            cp2x = p_prev[0] + (p[0] - p_prev[0]) * 0.5
            cp2y = p[1]
            d += f" C {cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {p[0]:.1f} {p[1]:.1f}"
        return d

    line_path = _smooth_path(points)
    area_path = line_path + f" L {points[-1][0]:.1f} {pad_t + inner_h} L {points[0][0]:.1f} {pad_t + inner_h} Z"

    # Y-axis labels (4 ticks)
    y_ticks = ""
    grid_lines = ""
    for i in range(5):
        v = min_v_padded + (range_v_padded * i / 4)
        y = pad_t + inner_h - (i / 4) * inner_h
        label = f"{v:.1f}" if v < 100 else f"{v:.0f}"
        y_ticks += f'<text x="{pad_l - 8}" y="{y + 3:.1f}" font-size="10" fill="#9ca3af" text-anchor="end" font-family="Inter,sans-serif">{label}</text>'
        grid_lines += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="#f3f4f6" stroke-width="1"/>'

    # X-axis labels
    x_ticks = ""
    for i, label in enumerate(labels):
        x = pad_l + (i / (n - 1)) * inner_w if n > 1 else pad_l + inner_w / 2
        x_ticks += f'<text x="{x:.1f}" y="{height - pad_b + 18}" font-size="10" fill="#9ca3af" text-anchor="middle" font-family="Inter,sans-serif">{html_mod.escape(str(label))}</text>'

    # Data point dots
    dots = ""
    for i, (x, y) in enumerate(points):
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#fff" stroke="{color}" stroke-width="2"/>'

    # Show last value as label
    last_label = ""
    if values:
        lx, ly = points[-1]
        last_v = values[-1]
        last_label = (
            f'<rect x="{lx - 28:.1f}" y="{ly - 28:.1f}" width="56" height="20" rx="4" fill="{color}"/>'
            f'<text x="{lx:.1f}" y="{ly - 14:.1f}" font-size="11" fill="#fff" text-anchor="middle" font-family="Inter,sans-serif" font-weight="600">{last_v}</text>'
        )

    return f'''<svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="display:block;">
<defs>
<linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>
<stop offset="100%" stop-color="{color}" stop-opacity="0"/>
</linearGradient>
</defs>
{grid_lines}
<path d="{area_path}" fill="url(#areaGrad)"/>
<path d="{line_path}" stroke="{color}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
{dots}
{y_ticks}
{x_ticks}
{last_label}
</svg>'''


def _svg_bar_chart(labels: list, values: list, color: str, accent: str,
                   width: int = 580, height: int = 280) -> str:
    """SVG vertical bar chart with rounded tops and gridlines."""
    if not values:
        return ""
    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 40
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    n = len(values)
    max_v = max(float(v) for v in values) or 1
    max_v_padded = max_v * 1.15

    bar_gap = 8
    bar_w = (inner_w - bar_gap * (n - 1)) / n if n > 0 else 0

    bars = ""
    value_labels = ""
    for i, v in enumerate(values):
        h = (float(v) / max_v_padded) * inner_h
        x = pad_l + i * (bar_w + bar_gap)
        y = pad_t + inner_h - h
        # Highlight last bar
        bar_color = color if i < n - 1 else accent
        bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="4" fill="{bar_color}"/>'
        value_labels += f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" font-size="10" fill="#374151" text-anchor="middle" font-family="Inter,sans-serif" font-weight="600">{v}</text>'

    # Y-axis gridlines
    grid = ""
    y_ticks = ""
    for i in range(5):
        v = max_v_padded * i / 4
        y = pad_t + inner_h - (i / 4) * inner_h
        label = f"{v:.1f}" if v < 100 else f"{v:.0f}"
        grid += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="#f3f4f6" stroke-width="1"/>'
        y_ticks += f'<text x="{pad_l - 8}" y="{y + 3:.1f}" font-size="10" fill="#9ca3af" text-anchor="end" font-family="Inter,sans-serif">{label}</text>'

    # X-axis labels
    x_ticks = ""
    for i, label in enumerate(labels):
        x = pad_l + i * (bar_w + bar_gap) + bar_w / 2
        x_ticks += f'<text x="{x:.1f}" y="{height - pad_b + 18}" font-size="10" fill="#9ca3af" text-anchor="middle" font-family="Inter,sans-serif">{html_mod.escape(str(label))}</text>'

    return f'''<svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="display:block;">
{grid}
{bars}
{value_labels}
{y_ticks}
{x_ticks}
</svg>'''


def _svg_donut_chart(segments: list, size: int = 200, stroke: int = 28) -> str:
    """SVG donut chart with center label support."""
    if not segments:
        return ""
    cx, cy = size / 2, size / 2
    r = (size - stroke) / 2
    circumference = 2 * math.pi * r
    total = sum(s.get("value", 0) for s in segments) or 1

    paths = ""
    offset = 0
    for seg in segments:
        val = seg.get("value", 0)
        color = seg.get("color", "#6366f1")
        pct = val / total
        dash = pct * circumference
        gap = circumference - dash
        # Rotate to start from top
        paths += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                  f'stroke="{color}" stroke-width="{stroke}" '
                  f'stroke-dasharray="{dash:.1f} {gap:.1f}" '
                  f'stroke-dashoffset="{-offset:.1f}" '
                  f'transform="rotate(-90 {cx} {cy})"/>')
        offset += dash

    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{paths}</svg>'


def _svg_progress_ring(percent: float, size: int = 80, stroke: int = 6,
                        color: str = "#6366f1", track: str = "#f3f4f6") -> str:
    """SVG circular progress ring."""
    cx, cy = size / 2, size / 2
    r = (size - stroke) / 2
    circumference = 2 * math.pi * r
    dash = (percent / 100) * circumference
    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{track}" stroke-width="{stroke}"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"
transform="rotate(-90 {cx} {cy})"/>
</svg>'''


# ═══════════════════════════════════════════════════════════════════
# Decorative Elements
# ═══════════════════════════════════════════════════════════════════

def _section_label(text: str, color: str, font: str = "Inter") -> str:
    """Editorial section label — small, uppercase, tracked."""
    return (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:18px;">'
            f'<span style="width:24px;height:1px;background:{color};"></span>'
            f'<span style="font-family:\'{font}\',sans-serif;font-size:11px;font-weight:600;'
            f'color:{color};letter-spacing:0.18em;text-transform:uppercase;">{html_mod.escape(text)}</span>'
            f'</div>')


def _hairline(color: str, width: str = "100%", height: str = "1px") -> str:
    """Subtle hairline divider."""
    return f'<div style="width:{width};height:{height};background:{color};margin:24px 0;"></div>'


def _watermark(brand: str, color: str, opacity: float = 0.6) -> str:
    """Tiny watermark at top-left corner."""
    return (f'<div style="position:absolute;top:32px;left:64px;font-size:11px;font-weight:600;'
            f'color:{color};opacity:{opacity};letter-spacing:0.12em;text-transform:uppercase;'
            f'z-index:5;">{html_mod.escape(brand)}</div>')


def _watermark_position_css(position: str) -> str:
    """Map editor brand-mark positions to print-safe CSS anchors."""
    pos = str(position or "bottom-right").strip().lower()
    if pos == "top-left":
        return "top:32px;left:64px;"
    if pos == "top-right":
        return "top:32px;right:64px;"
    if pos == "bottom-left":
        return "bottom:32px;left:64px;"
    return "bottom:32px;right:64px;"


# ═══════════════════════════════════════════════════════════════════
# PdfBuilder
# ═══════════════════════════════════════════════════════════════════

def _slide_links(slide: dict, content: dict, max_n: int = 4) -> list[dict[str, str]]:
    """Extract explicit links/sources for clickable PDF output."""
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, url: str, target: str = "text") -> None:
        clean = str(url or "").strip()
        if not clean.lower().startswith(("http://", "https://")):
            return
        if clean in seen:
            return
        seen.add(clean)
        links.append({
            "label": _plain_text(label, fallback="Open link")[:120],
            "url": clean[:500],
            "target": target if target in {"text", "button", "image", "source"} else "text",
        })

    for bucket in (content.get("links"), slide.get("links")):
        for item in bucket or []:
            if isinstance(item, dict):
                add(
                    item.get("label") or item.get("title") or "Open link",
                    item.get("url") or item.get("href") or "",
                    str(item.get("target") or "text").lower(),
                )
    for bucket in (content.get("sources"), content.get("citations"), slide.get("citations")):
        for item in bucket or []:
            if isinstance(item, dict):
                add(item.get("title") or "Source", item.get("url") or item.get("href") or "", "source")
    return links[:max_n]


def _link_footer(links: list[dict[str, str]], *, color: str, accent: str, font: str) -> str:
    if not links:
        return ""
    parts = []
    for link in links[:4]:
        label = html_mod.escape(_plain_text(link.get("label"), fallback="Open link")[:60])
        url = html_mod.escape(str(link.get("url") or ""))
        if not url:
            continue
        parts.append(f'<a href="{url}" style="color:{accent};font-weight:600;">{label}</a>')
    if not parts:
        return ""
    separator = f' <span style="color:{color};opacity:0.45;">|</span> '
    return (
        f'<div style="position:absolute;left:64px;bottom:30px;max-width:760px;'
        f'z-index:6;font-family:{repr(font)},sans-serif;font-size:9px;color:{color};'
        f'letter-spacing:0.02em;opacity:0.86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'<span style="color:{color};opacity:0.72;font-weight:500;">Links:</span> '
        f'<span style="margin-left:6px;">{separator.join(parts)}</span></div>'
    )


class PdfBuilder:
    """Investor-grade PDF builder with editorial design language."""

    def build(self, slides: list[dict], theme: dict, metadata: dict = None) -> bytes:
        """Build a PDF. Tries WeasyPrint, falls back to Playwright.

        Premium mode activates brand-driven palette enforcement and
        premium-only decorations (enhanced watermark, quality mark).
        """
        if not slides:
            # Slice 4 (Export Parity): refuse to emit a corrupt 0-page
            # PDF. Routers translate this into a structured 409 envelope.
            from app.services.v4.errors import ExportContentEmpty

            raise ExportContentEmpty("PdfBuilder.build: slides is empty")
        self._mode = (metadata or {}).get("mode", "standard")
        self._deck_design_tokens = (metadata or {}).get("design_tokens", {})
        html_content = self._build_print_html(slides, theme, metadata)
        we_err: Exception | str | None = None
        # On Windows, WeasyPrint/fontconfig can terminate the interpreter
        # with an access violation before Python can catch the exception.
        # Prefer Playwright there so export failure stays recoverable.
        if sys.platform != "win32":
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html_content).write_pdf()
                logger.info("pdf_built_weasyprint", slide_count=len(slides), size_kb=len(pdf_bytes) // 1024)
                return pdf_bytes
            except Exception as exc:
                we_err = exc
                logger.warning("weasyprint_failed", error=str(exc)[:200])
        else:
            we_err = "skipped on Windows to avoid fontconfig crash"
            logger.info("weasyprint_skipped_windows")
        try:
            pdf_bytes = self._build_with_playwright(html_content)
            logger.info("pdf_built_playwright", slide_count=len(slides), size_kb=len(pdf_bytes) // 1024)
            return pdf_bytes
        except Exception as pw_err:
            logger.error("playwright_pdf_failed", error=str(pw_err)[:200])
            try:
                pdf_bytes = self._build_text_pdf_fallback(slides, metadata)
                logger.warning(
                    "pdf_built_text_fallback",
                    slide_count=len(slides),
                    size_kb=len(pdf_bytes) // 1024,
                    playwright_error=str(pw_err)[:160],
                )
                return pdf_bytes
            except Exception as fallback_err:
                raise RuntimeError(
                    f"PDF generation failed. WeasyPrint: {we_err}. Playwright: {pw_err}. "
                    f"Fallback: {fallback_err}."
                ) from pw_err

    def _build_with_playwright(self, html_content: str) -> bytes:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            html_path = f.name
        pdf_path = ""
        try:
            if sys.platform == "win32":
                fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                script = (
                    "import pathlib, sys\n"
                    "from playwright.sync_api import sync_playwright\n"
                    "html_path, pdf_path, width, height = sys.argv[1:5]\n"
                    "with sync_playwright() as p:\n"
                    "    browser = p.chromium.launch()\n"
                    "    try:\n"
                    "        page = browser.new_page()\n"
                    "        page.set_viewport_size({'width': 1280, 'height': 720})\n"
                    "        page.goto(pathlib.Path(html_path).resolve().as_uri(), wait_until='load')\n"
                    "        page.wait_for_timeout(1000)\n"
                    "        page.pdf(path=pdf_path, width=width, height=height, print_background=True, "
                    "prefer_css_page_size=True, margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})\n"
                    "    finally:\n"
                    "        browser.close()\n"
                )
                completed = subprocess.run(
                    [sys.executable, "-c", script, html_path, pdf_path, PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT],
                    capture_output=True,
                    text=True,
                    timeout=75,
                    check=False,
                )
                if completed.returncode != 0:
                    detail = (completed.stderr or completed.stdout or "playwright subprocess failed").strip()
                    raise RuntimeError(detail[:500])
                with open(pdf_path, "rb") as pdf_file:
                    return pdf_file.read()

            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page()
                    page.set_viewport_size({"width": 1280, "height": 720})
                    page.goto(f"file:///{html_path.replace(chr(92), '/')}")
                    page.wait_for_timeout(1000)
                    return page.pdf(
                        width=PDF_PAGE_WIDTH,
                        height=PDF_PAGE_HEIGHT,
                        print_background=True,
                        prefer_css_page_size=True,
                        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    )
                finally:
                    browser.close()
        finally:
            for path in (html_path, pdf_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _build_text_pdf_fallback(self, slides: list[dict], metadata: dict | None = None) -> bytes:
        """Produce a valid readable PDF when browser-based rendering is unavailable."""
        page_w, page_h = 960, 540
        objects: list[bytes | None] = [None, None]

        def add_object(body: str | bytes) -> int:
            objects.append(body.encode("latin-1", "replace") if isinstance(body, str) else body)
            return len(objects)

        font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        page_ids: list[int] = []
        for index, slide in enumerate(slides or []):
            stream = self._fallback_page_stream(slide, index, page_w, page_h)
            content_id = add_object(
                f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\n"
                f"stream\n{stream}\nendstream"
            )
            page_id = add_object(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            )
            page_ids.append(page_id)
        if not page_ids:
            page_ids.append(add_object(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] >>"))

        objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")

        title = _plain_text((metadata or {}).get("title"), fallback="Presentation")
        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = []
        for obj_id, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{obj_id} 0 obj\n".encode("ascii"))
            pdf.extend(body or b"")
            pdf.extend(b"\nendobj\n")
        xref_pos = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
        for offset in offsets:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R "
                f"/Info << /Title ({self._pdf_escape(title)}) >> >>\n"
                f"startxref\n{xref_pos}\n%%EOF\n"
            ).encode("latin-1", "replace")
        )
        return bytes(pdf)

    def _fallback_page_stream(self, slide: dict, index: int, page_w: int, page_h: int) -> str:
        content = slide.get("content") if isinstance(slide.get("content"), dict) else {}
        title = _field_text(content, ("title", "headline"), fallback=_field_text(slide, ("headline", "title"), fallback=f"Slide {index + 1}"))
        subtitle = _field_text(content, ("subtitle", "subheadline"), fallback=_field_text(slide, ("subheadline", "subtitle"), fallback=""))
        bullets = content.get("bullets") or slide.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = [_plain_text(bullets)]
        operations = [
            "0.98 0.98 0.96 rg 0 0 {w} {h} re f".format(w=page_w, h=page_h),
            "0.05 0.06 0.08 rg",
            f"BT /F1 10 Tf 48 {page_h - 48} Td ({self._pdf_escape(str(index + 1).zfill(2))}) Tj ET",
        ]
        y = page_h - 105
        for line in self._wrap_pdf_text(title, 42)[:3]:
            operations.append(f"BT /F1 30 Tf 64 {y} Td ({self._pdf_escape(line)}) Tj ET")
            y -= 36
        if subtitle:
            y -= 12
            for line in self._wrap_pdf_text(subtitle, 82)[:2]:
                operations.append(f"BT /F1 14 Tf 66 {y} Td ({self._pdf_escape(line)}) Tj ET")
                y -= 20
        y -= 24
        for bullet in bullets[:6]:
            for line_no, line in enumerate(self._wrap_pdf_text(_plain_text(bullet), 92)[:2]):
                prefix = "- " if line_no == 0 else "  "
                operations.append(f"BT /F1 12 Tf 80 {y} Td ({self._pdf_escape(prefix + line)}) Tj ET")
                y -= 18
            y -= 4
        return "\n".join(operations)

    @staticmethod
    def _wrap_pdf_text(value: str, width: int) -> list[str]:
        cleaned = re.sub(r"\s+", " ", _plain_text(value)).strip()
        return textwrap.wrap(cleaned, width=width, break_long_words=False) or [""]

    @staticmethod
    def _pdf_escape(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _build_print_html(self, slides: list[dict], theme: dict, metadata: dict = None) -> str:
        metadata = metadata or {}
        explicit_brand = (
            metadata.get("brand")
            or metadata.get("company")
            or metadata.get("company_name")
            or ""
        )
        brand = _plain_text(explicit_brand).split(" ")[0] if explicit_brand else ""
        mode = metadata.get("mode", "standard")
        pages = []
        for i, slide in enumerate(slides):
            pages.append(self._render_slide(slide, i, len(slides), brand, mode=mode))
        title = metadata.get("title", "Presentation")
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html_mod.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@400;700;900&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@page {{ size: {PDF_PAGE_WIDTH} {PDF_PAGE_HEIGHT}; margin: 0; }}
* {{ box-sizing: border-box; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}
body {{ margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
a {{ color: inherit; text-decoration: none; }}
.tabular {{ font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
{"".join(pages)}
</body>
</html>"""

    # ── Per-slide renderer ─────────────────────────────────────────

    def _render_slide(self, slide: dict, idx: int, total: int, brand: str, mode: str = "standard") -> str:
        content = slide.get("content", {})
        kit = slide.get("kit_component", "TitleHero")
        dt = slide.get("design_tokens", {}) or {}
        is_premium = mode == "premium"
        palette = dt.get("palette", {}) or {}
        fonts = dt.get("fonts", {}) or {}

        # Color tokens with sensible fallbacks
        bg = palette.get("background", "#ffffff")
        fg = palette.get("text_primary", "#0a0a0a")
        fg2 = palette.get("text_secondary", "#737373")
        pri = palette.get("primary", "#0a0a0a")
        sec = palette.get("secondary", "#525252")
        acc = palette.get("accent", "#f59e0b")
        surf = palette.get("surface", "#fafafa")
        surf2 = palette.get("surface_alt", "#f5f5f5")
        bdr = palette.get("border", "#e5e5e5")
        gs = palette.get("gradient_start", pri)
        ge = palette.get("gradient_end", sec)
        fg, fg2 = _readable_pair(bg, fg, fg2)
        bdr = _safe_border(bg, bdr)

        # Fonts
        hf = fonts.get("heading", "Inter")
        bf = fonts.get("body", "Inter")
        df = fonts.get("display", hf)  # display font for hero
        motion_spec = slide.get("motion_spec") if isinstance(slide.get("motion_spec"), dict) else {}
        poster_frame = slide.get("poster_frame") or motion_spec.get("poster_frame") or {}
        if not isinstance(poster_frame, dict):
            poster_frame = {}
        motion_preset = html_mod.escape(str(motion_spec.get("preset") or "static"))
        poster_ms = html_mod.escape(str(poster_frame.get("time_ms") or 0))
        motion_attrs = (
            f'data-motion-preset="{motion_preset}" '
            f'data-poster-frame-ms="{poster_ms}" '
            'data-pdf-frame="poster"'
        )

        # Build body based on kit
        body = self._build_body(
            kit=kit, content=content, slide=slide, idx=idx, total=total,
            bg=bg, fg=fg, fg2=fg2, pri=pri, sec=sec, acc=acc,
            surf=surf, surf2=surf2, bdr=bdr, gs=gs, ge=ge,
            hf=hf, bf=bf, df=df, brand=brand,
        )

        # Page break logic
        page_break = "page-break-after:always;" if idx < total - 1 else ""

        # Page number (editorial style)
        page_num = ""
        if idx > 0 and idx < total - 1:
            page_num = (f'<div style="position:absolute;bottom:32px;right:64px;font-family:\'{bf}\',sans-serif;'
                       f'font-size:11px;color:{fg2};letter-spacing:0.1em;z-index:5;">'
                       f'<span class="tabular">{idx + 1:02d}</span> '
                       f'<span style="opacity:0.5;">/ {total:02d}</span></div>')

        # Brand watermark — premium decks get logo image; others get text mark
        watermark_data = (content.get("watermark") or {}) if isinstance(content, dict) else {}
        wm = ""
        premium_mark = ""
        if idx > 0 and idx < total - 1:
            logo_url = watermark_data.get("imageUrl") or watermark_data.get("image_url")
            if logo_url and not _is_placeholder_url(logo_url):
                opacity = watermark_data.get("opacity", 0.5)
                position_css = _watermark_position_css(watermark_data.get("position", "bottom-right"))
                if is_premium:
                    # Premium: larger logo + accent brand label + subtle quality mark
                    logo_size = "width:24px;height:24px;"
                    label_color = acc
                    label_size = "11px"
                    gap = "10px"
                else:
                    logo_size = "width:18px;height:18px;"
                    label_color = fg2
                    label_size = "10px"
                    gap = "8px"
                if brand:
                    label_style = (f"font-family:{repr(bf)},sans-serif;font-size:{label_size};color:{label_color}"
                                   + ";letter-spacing:0.12em;text-transform:uppercase;font-weight:600;")
                    brand_label = '<span style="' + label_style + '">' + html_mod.escape(brand) + '</span>'
                else:
                    brand_label = ''
                wm = (
                    '<div style="position:absolute;' + position_css + 'z-index:5;'
                    + f'opacity:{opacity};display:flex;align-items:center;gap:{gap};">'
                    + '<img src="' + html_mod.escape(str(logo_url)) + '" '
                    + f'style="{logo_size}border-radius:4px;object-fit:contain;">'
                    + brand_label + '</div>'
                )
            elif brand:
                wm = _watermark(brand, fg2)

        # Production exports should not expose internal mode labels.
        premium_mark = ""
        link_footer = _link_footer(
            _slide_links(slide, content),
            color=fg2,
            accent=acc,
            font=bf,
        )

        return f"""
<div {motion_attrs} style="width:100%;height:100vh;background:{bg};{page_break}position:relative;overflow:hidden;font-family:'{bf}',sans-serif;color:{fg};">
{premium_mark}
{wm}
{body}
{link_footer}
{page_num}
</div>"""

    # ── Kit-aware body builder ─────────────────────────────────────

    # Mapping from kit_component → handler method
    # Covers all 33 kits used by template_definitions.json + barise_templates_v27.json
    _HERO_KITS = {"TitleHero", "CoverSlide", "CinematicHero", "DuotoneHero",
                  "EditorialImage", "FullBleedImage"}
    _SPLIT_KITS = {"SplitContent", "SplitOverlap", "AppMockup"}
    _GRID_KITS = {"FeatureGrid", "ValuePropGrid", "BentoGrid", "ProblemSolution", "GlassCard"}
    _STAT_KITS = {"StatHero", "StatHighlight", "FloatingStat"}
    _METRICS_KITS = {"MetricsDashboard"}
    _COMPARISON_KITS = {"ComparisonBlock", "ComparisonTable"}
    _TABLE_KITS = {"TableSlide", "DataTable"}
    _BEFORE_AFTER_KITS = {"BeforeAfter"}
    _TIMELINE_KITS = {"Timeline", "TimelineBlock", "Roadmap", "ProcessFlow"}
    _DIAGRAM_KITS = {"DiagramBlock"}
    _TEAM_KITS = {"TeamGrid", "TeamMemberStrip"}
    _QUOTE_KITS = {"QuoteHighlight", "QuoteSlide", "TestimonialCard", "QuoteBlock"}
    _CHART_KITS = {"ChartSlide", "ChartBlock", "AnimatedChartBlock"}
    _PRICING_KITS = {"PricingTable"}
    _LOGO_KITS = {"LogoMarquee", "SocialProof"}
    _CLOSING_KITS = {"ClosingSlide"}

    def _build_body(self, *, kit, content, slide, idx, total, bg, fg, fg2, pri, sec, acc,
                    surf, surf2, bdr, gs, ge, hf, bf, df, brand):
        title = _plain_text(content.get("title", ""))
        subtitle = _plain_text(content.get("subtitle", ""))
        eyebrow = _plain_text(content.get("eyebrow", ""))
        body_text = _plain_text(content.get("body_text", ""))
        bullets = [_plain_text(b) for b in (content.get("bullets", []) or []) if _plain_text(b)]
        metrics = content.get("metrics", []) or []
        items = content.get("items", []) or content.get("features", []) or content.get("cards", []) or []
        milestones = content.get("milestones", []) or []
        nodes = content.get("nodes", []) or []
        if not nodes and milestones:
            nodes = [
                {
                    "label": _field_text(m, ("label", "date", "phase", "title"), fallback=f"{i + 1:02d}"),
                    "detail": _field_text(m, ("detail", "description", "body", "text", "title", "name"), fallback=_plain_text(m)),
                    "active": bool(m.get("active", False)) if isinstance(m, dict) else False,
                }
                for i, m in enumerate(milestones[:6])
            ]
        comparison_data = content.get("comparison_data", {}) or {}
        columns = content.get("columns", []) or comparison_data.get("columns", []) or []
        comparison_rows = content.get("rows", []) or comparison_data.get("rows", []) or []
        if columns and comparison_rows and not any(
            isinstance(col, dict) and col.get("features")
            for col in columns
        ):
            normalized_columns = []
            for ci, col in enumerate(columns):
                if not isinstance(col, dict):
                    continue
                col_copy = dict(col)
                col_name = str(col_copy.get("name") or col_copy.get("title") or "")
                features = []
                for row in comparison_rows:
                    if not isinstance(row, dict):
                        continue
                    label = str(row.get("feature") or row.get("label") or row.get("name") or "")
                    values = row.get("values")
                    value = None
                    if isinstance(values, list) and ci < len(values):
                        value = values[ci]
                    elif isinstance(values, dict):
                        value = values.get(col_name)
                    if label and value not in (None, ""):
                        features.append({"label": label, "value": value})
                if features:
                    col_copy["features"] = features
                normalized_columns.append(col_copy)
            if normalized_columns:
                columns = normalized_columns
        members = content.get("members", []) or []
        quote_text = content.get("quote_text", "") or ""
        quote_author = content.get("quote_author", "") or ""
        image_url = content.get("image_url", "") or slide.get("image_url", "") or ""
        section_label = content.get("section_label", eyebrow)
        watermark = content.get("watermark", {}) or {}
        layout_hint = _plain_text(content.get("layout", "") or slide.get("layout", "")).lower().replace("_", "-")
        intent_hint = _plain_text(content.get("intent", "") or slide.get("intent", "")).lower()
        structural_layout = any(
            marker in layout_hint
            for marker in (
                "comparison",
                "timeline",
                "roadmap",
                "process",
                "milestone",
                "diagram",
                "flow",
                "architecture",
                "system map",
                "network",
                "table",
                "chart",
                "metric",
                "stat",
                "two-column",
                "two column",
            )
        )

        ctx = dict(fg=fg, fg2=fg2, pri=pri, sec=sec, acc=acc, surf=surf, surf2=surf2,
                   bdr=bdr, gs=gs, ge=ge, hf=hf, bf=bf, df=df, idx=idx, total=total)

        if not bullets:
            fallback_bullets = []
            for group in (items, nodes, milestones, columns):
                for entry in list(group or [])[:6]:
                    text = _field_text(
                        entry,
                        ("title", "headline", "name", "label", "value", "description", "detail", "body", "text"),
                        fallback=_plain_text(entry),
                    )
                    if text:
                        fallback_bullets.append(text)
                    if len(fallback_bullets) >= 6:
                        break
                if len(fallback_bullets) >= 6:
                    break
            bullets = fallback_bullets

        # ── Hero family ─────────────────────────────────────────────
        if (kit in self._HERO_KITS and not structural_layout) or layout_hint in ("cover", "title-hero", "hero", "title-only"):
            # If bullets are present use editorial bullets layout
            if bullets:
                return self._bullets_editorial(title, subtitle, body_text, bullets,
                                                section_label or "Overview", **ctx)
            return self._cover_split(title, subtitle, body_text, image_url, brand,
                                      eyebrow=eyebrow, kit=kit, **ctx)

        # ── Split content (text + visual side-by-side) ──────────────
        if "two-column" in layout_hint or "two column" in layout_hint:
            if bullets:
                return self._two_column_bullets(title, subtitle, bullets, section_label, **ctx)
            return self._split_content(title, subtitle, body_text, image_url, eyebrow,
                                        section_label, kit, **ctx)

        if kit in self._SPLIT_KITS or layout_hint in ("split",):
            return self._split_content(title, subtitle, body_text, image_url, eyebrow,
                                        section_label, kit, **ctx)

        # ── Stats ───────────────────────────────────────────────────
        if kit in self._STAT_KITS or layout_hint in ("stats", "metrics"):
            # StatHighlight uses single value+label+sub_stats
            stat_value = content.get("stat_value", "")
            stat_label = content.get("stat_label", "")
            sub_stats = content.get("sub_stats", []) or []
            if stat_value or sub_stats:
                return self._stat_highlight(title, subtitle, stat_value, stat_label,
                                             content.get("stat_percentage"), sub_stats,
                                             section_label, **ctx)
            return self._stats_bento(title, subtitle, metrics, section_label, **ctx)

        if kit in self._METRICS_KITS:
            return self._metrics_dashboard(title, subtitle, metrics,
                                            content.get("chart_data", {}),
                                            section_label, **ctx)

        # ── Grid items (BentoGrid, FeatureGrid, ValuePropGrid, ProblemSolution) ──
        if kit in self._GRID_KITS or layout_hint in ("features", "grid", "bento", "grid-3"):
            if items:
                return self._items_grid(title, subtitle, items, section_label, kit, **ctx)
            # Fallback for kits with bullets instead of items
            return self._features_editorial(title, subtitle, bullets, section_label, **ctx)

        # ── Before/After ────────────────────────────────────────────
        if kit in self._BEFORE_AFTER_KITS:
            return self._before_after(title, subtitle,
                                       content.get("before", ""),
                                       content.get("after", ""),
                                       content.get("stat", ""), section_label, **ctx)

        # ── Comparison ──────────────────────────────────────────────
        if kit in self._COMPARISON_KITS or "comparison" in layout_hint:
            if columns:
                return self._comparison_columns(title, subtitle, columns,
                                                 section_label, kit, **ctx)
            return self._comparison_editorial(title, subtitle,
                                               comparison_data,
                                               section_label, **ctx)

        # ── Timeline / Roadmap / ProcessFlow ────────────────────────
        if kit in self._TIMELINE_KITS or any(marker in layout_hint for marker in ("timeline", "roadmap", "process", "milestone")):
            if nodes:
                return self._timeline_nodes(title, subtitle, nodes, section_label, kit, **ctx)
            events = content.get("timeline_events", {})
            if isinstance(events, dict):
                events = events.get("events", [])
            if not events and bullets:
                events = [{"date": f"{i + 1:02d}", "title": b} for i, b in enumerate(bullets[:6])]
            return self._timeline_editorial(title, subtitle, events, section_label, **ctx)

        # ── Diagram / Flow ────────────────────────────────────────────
        if kit in self._DIAGRAM_KITS or any(marker in layout_hint for marker in ("diagram", "flow", "architecture", "system map", "network")):
            if nodes:
                return self._timeline_nodes(title, subtitle, nodes, section_label, kit, **ctx)
            if bullets:
                bullet_nodes = [{"label": f"{i + 1:02d}", "detail": b} for i, b in enumerate(bullets[:6])]
                return self._timeline_nodes(title, subtitle, bullet_nodes, section_label, "DiagramBlock", **ctx)
            return self._bullets_editorial(title, subtitle, body_text, bullets,
                                            section_label or "Overview", **ctx)

        # ── Team ────────────────────────────────────────────────────
        if kit in self._TEAM_KITS or layout_hint in ("team",) or intent_hint == "team":
            if members:
                return self._team_members(title, subtitle, members, section_label, **ctx)
            return self._team_editorial(title, subtitle, [], section_label, **ctx)

        # ── Quote ───────────────────────────────────────────────────
        if kit in self._QUOTE_KITS or "quote" in layout_hint:
            return self._quote_editorial(title, quote_text or title, quote_author or subtitle, **ctx)

        # ── Chart ───────────────────────────────────────────────────
        if kit in self._CHART_KITS or "chart" in layout_hint:
            return self._chart_editorial(title, subtitle, content.get("chart_data", {}),
                                          section_label, **ctx)

        # ── Table ───────────────────────────────────────────────────
        if kit in self._TABLE_KITS or "table" in layout_hint:
            return self._table_editorial(title, subtitle, content.get("table_data", {}),
                                          section_label, **ctx)

        # ── Pricing ─────────────────────────────────────────────────
        if kit in self._PRICING_KITS or "pricing" in layout_hint:
            return self._pricing_tiers(title, subtitle, content.get("tiers", []),
                                        section_label, **ctx)

        # ── Logos / Social Proof ────────────────────────────────────
        if kit in self._LOGO_KITS or layout_hint in ("logos", "social-proof"):
            return self._logo_grid(title, subtitle, content.get("logos", []),
                                    section_label, **ctx)

        # ── Closing ─────────────────────────────────────────────────
        if kit in self._CLOSING_KITS or layout_hint in ("closing", "cta") or intent_hint in ("closing", "thank_you", "thanks"):
            return self._closing_split(title, subtitle, body_text, image_url,
                                        eyebrow=eyebrow or "The Ask", **ctx)

        # ── Default: editorial bullets ──────────────────────────────
        return self._bullets_editorial(title, subtitle, body_text, bullets,
                                        section_label or "Overview", **ctx)

    # ═══════════════════════════════════════════════════════════════
    # Layout: Cover (50/50 split with image OR full-bleed)
    # ═══════════════════════════════════════════════════════════════

    def _cover_split(self, title, subtitle, body_text, image_url, brand, *,
                     fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total,
                     eyebrow="", kit=""):
        top_label = html_mod.escape(eyebrow or brand or "Pitch Deck")
        if image_url:
            # 50/50 split: text left, image right
            panel_bg, panel_fg, panel_fg2 = _text_panel_colors(
                "#ffffff", surf, fg, fg2
            )
            panel_bdr = _safe_border(panel_bg, bdr)
            text_panel = f'''
<div style="flex:1;display:flex;flex-direction:column;justify-content:space-between;padding:80px;background:{panel_bg};position:relative;border-right:1px solid {panel_bdr};">
<div style="display:flex;align-items:center;gap:10px;font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{pri};letter-spacing:0.18em;text-transform:uppercase;">
<span style="width:24px;height:1px;background:{pri};"></span>{top_label}
</div>
<div>
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(48px,7vw,84px);font-weight:700;color:{panel_fg};margin:0 0 20px 0;line-height:0.95;letter-spacing:-0.02em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:20px;color:{panel_fg2};margin:0 0 28px 0;line-height:1.4;max-width:480px;font-weight:400;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{panel_fg2};margin:0;line-height:1.6;max-width:440px;">{html_mod.escape(body_text)}</p>' if body_text else ''}
</div>
<div style="display:flex;justify-content:space-between;align-items:center;font-family:'{bf}',sans-serif;font-size:11px;color:{panel_fg2};letter-spacing:0.1em;text-transform:uppercase;">
<span>Confidential</span><span class="tabular">2026</span>
</div>
</div>'''
            image_panel = f'''
<div style="flex:1;position:relative;background:#000;overflow:hidden;">
<img src="{html_mod.escape(image_url)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(1.1) contrast(1.05);">
<div style="position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,0,0,0.15),rgba(0,0,0,0.45));"></div>
</div>'''
            return f'<div style="display:flex;width:100%;height:100%;">{text_panel}{image_panel}</div>'

        # No-image covers should still feel designed, not like a generic
        # gradient template. Use the deck's dark canvas with restrained brand
        # accents so technical/investor decks preserve contrast and credibility.
        canvas_bg = "#05070d" if not _is_light(surf) else "#f8fafc"
        subtle_primary = _rgba(pri, 0.22)
        subtle_accent = _rgba(acc, 0.16)
        hairline = _rgba(pri, 0.55)
        title_color = "#ffffff" if _contrast_ratio(canvas_bg, "#ffffff") >= 4.5 else fg
        subtitle_color = "rgba(255,255,255,0.72)" if title_color == "#ffffff" else fg2
        return f'''
<div style="position:absolute;inset:0;background:
radial-gradient(circle at 84% 10%,{subtle_primary},transparent 30%),
radial-gradient(circle at 6% 92%,{subtle_accent},transparent 28%),
linear-gradient(135deg,{canvas_bg} 0%,#080b12 62%,#10131b 100%);z-index:0;"></div>
<div style="position:absolute;inset:0;z-index:0;opacity:0.22;background-image:linear-gradient({hairline} 1px,transparent 1px),linear-gradient(90deg,{hairline} 1px,transparent 1px);background-size:96px 96px;mask-image:linear-gradient(180deg,transparent,black 18%,black 80%,transparent);"></div>
<div style="position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;justify-content:center;padding:88px;color:{title_color};">
<div style="display:inline-flex;align-items:center;gap:10px;font-family:'{bf}',sans-serif;font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:{pri};margin-bottom:34px;">
<span style="width:26px;height:2px;background:{pri};"></span>{top_label}
</div>
<div style="max-width:920px;">
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(54px,7vw,92px);font-weight:750;color:{title_color};margin:0 0 24px 0;line-height:0.96;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:22px;color:{subtitle_color};margin:0 0 32px 0;line-height:1.42;max-width:640px;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:{subtitle_color};margin:0;line-height:1.6;max-width:560px;">{html_mod.escape(body_text)}</p>' if body_text else ''}
</div>
<div style="position:absolute;left:80px;right:80px;bottom:48px;display:flex;justify-content:space-between;align-items:center;font-family:'{bf}',sans-serif;font-size:11px;color:{subtitle_color};letter-spacing:0.12em;text-transform:uppercase;">
<span>Confidential</span><span class="tabular">2026</span>
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Stats — Bento grid with featured large stat
    # ═══════════════════════════════════════════════════════════════

    def _stats_bento(self, title, subtitle, metrics, section_label, *,
                     fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not metrics:
            metrics = []

        sl = _section_label(section_label or "Traction", pri, bf)
        header = f'''
<div style="margin-bottom:48px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(36px,5vw,56px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;max-width:800px;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:17px;color:{fg2};margin:0;line-height:1.5;max-width:640px;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        # Bento grid: first metric is featured (2x2), rest are 1x1
        if len(metrics) == 0:
            cells = ""
        elif len(metrics) == 1:
            m = metrics[0]
            cells = self._stat_card_xl(m, pri, surf, bdr, fg, fg2, hf, bf, df)
        else:
            featured = self._stat_card_xl(metrics[0], pri, surf, bdr, fg, fg2, hf, bf, df, span=True)
            small_cells = ""
            icons = ["trending-up", "users", "target", "dollar"]
            for i, m in enumerate(metrics[1:5]):
                small_cells += self._stat_card_sm(m, pri, surf2, bdr, fg, fg2, hf, bf, df, icons[i % 4])
            cells = f'<div style="display:grid;grid-template-columns:1.6fr 1fr;gap:16px;">{featured}<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">{small_cells}</div></div>'

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}{cells}</div>'''

    def _stat_card_xl(self, m, pri, surf, bdr, fg, fg2, hf, bf, df, span=False):
        val = html_mod.escape(str(m.get("value", "")))
        lbl = html_mod.escape(str(m.get("label", "")))
        delta = m.get("delta", "")
        delta_html = ""
        if delta:
            d_str = html_mod.escape(str(delta))
            d_color = "#10b981" if "+" in d_str or "↑" in d_str else (pri if "-" not in d_str else "#ef4444")
            delta_html = (f'<div style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;'
                         f'background:{d_color}15;color:{d_color};border-radius:50px;font-size:12px;'
                         f'font-weight:600;font-family:\'{bf}\',sans-serif;">{_icon("arrow-up-right", 12, d_color)} {d_str}</div>')
        return f'''
<div style="background:{surf};border-radius:16px;padding:48px;border:1px solid {bdr};display:flex;flex-direction:column;justify-content:space-between;min-height:340px;">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{pri};letter-spacing:0.16em;text-transform:uppercase;">{lbl}</div>
<div>
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:clamp(64px,9vw,112px);font-weight:700;color:{fg};line-height:0.9;letter-spacing:-0.04em;">{val}</div>
{delta_html}
</div>
</div>'''

    def _stat_card_sm(self, m, pri, surf, bdr, fg, fg2, hf, bf, df, icon_name):
        val = html_mod.escape(str(m.get("value", "")))
        lbl = html_mod.escape(str(m.get("label", "")))
        return f'''
<div style="background:{surf};border-radius:14px;padding:24px;border:1px solid {bdr};display:flex;flex-direction:column;justify-content:space-between;min-height:160px;">
<div style="color:{pri};">{_icon(icon_name, 18, pri)}</div>
<div>
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:clamp(28px,3.5vw,44px);font-weight:700;color:{fg};line-height:1;letter-spacing:-0.03em;margin-bottom:6px;">{val}</div>
<div style="font-family:'{bf}',sans-serif;font-size:12px;color:{fg2};font-weight:500;">{lbl}</div>
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Features — Editorial numbered grid
    # ═══════════════════════════════════════════════════════════════

    def _features_editorial(self, title, subtitle, bullets, section_label, *,
                            fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Capabilities", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        items = ""
        for i, b in enumerate(bullets[:6]):
            # Parse "Title — Description" pattern
            bs = _plain_text(b)
            if " — " in bs or " - " in bs:
                parts = bs.replace(" - ", " — ").split(" — ", 1)
                ftitle = html_mod.escape(parts[0].strip())
                fdesc = html_mod.escape(parts[1].strip()) if len(parts) > 1 else ""
            else:
                ftitle = html_mod.escape(bs)
                fdesc = ""
            items += f'''
<div style="padding:28px 0;border-top:1px solid {bdr};display:grid;grid-template-columns:80px 1fr;gap:24px;align-items:start;">
<div class="tabular" style="font-family:'{df}',sans-serif;font-size:32px;font-weight:300;color:{pri};line-height:1;letter-spacing:-0.02em;">{i + 1:02d}</div>
<div>
<h3 style="font-family:'{hf}',sans-serif;font-size:18px;font-weight:600;color:{fg};margin:0 0 6px 0;line-height:1.3;letter-spacing:-0.01em;">{ftitle}</h3>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{fg2};margin:0;line-height:1.55;max-width:560px;">{fdesc}</p>' if fdesc else ''}
</div>
</div>'''
        # Last divider
        items += f'<div style="border-top:1px solid {bdr};"></div>'

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}<div>{items}</div></div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Quote — Oversized centered editorial
    # ═══════════════════════════════════════════════════════════════

    def _two_column_bullets(self, title, subtitle, bullets, section_label, *,
                            fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Details", pri, bf)
        header = f'''
<div style="margin-bottom:44px;max-width:760px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        clean = [str(b).strip() for b in bullets if str(b).strip()]
        pivot = max(1, (len(clean) + 1) // 2)
        groups = [clean[:pivot], clean[pivot:]]

        def _column(entries, label, bg_col):
            rows = ""
            for entry in entries:
                text = html_mod.escape(_plain_text(entry))
                rows += f'''
<div style="display:flex;gap:14px;align-items:flex-start;padding:16px 0;border-bottom:1px solid {bdr};">
<span style="flex:0 0 auto;margin-top:2px;color:{pri};">{_icon("arrow-right", 15, pri, 2.4)}</span>
<span style="font-family:'{bf}',sans-serif;font-size:15px;color:{fg};line-height:1.55;">{text}</span>
</div>'''
            return f'''
<div style="background:{bg_col};border:1px solid {bdr};border-radius:16px;padding:30px;min-height:260px;">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:700;color:{pri};letter-spacing:0.14em;text-transform:uppercase;margin-bottom:10px;">{label}</div>
{rows}
</div>'''

        left = _column(groups[0], "Signal", surf)
        right = _column(groups[1], "Implication", surf2) if groups[1] else ""
        grid_cols = "1fr 1fr" if groups[1] else "1fr"
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:grid;grid-template-columns:{grid_cols};gap:20px;">{left}{right}</div>
</div>'''

    def _quote_editorial(self, title, quote_text, quote_author, *,
                         fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        return f'''
<div style="padding:80px;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;">
<div style="font-family:'{df}',sans-serif;font-size:120px;color:{pri};line-height:0.5;margin-bottom:16px;font-weight:700;">"</div>
<blockquote style="font-family:'{bf}',sans-serif;font-size:clamp(26px,3.2vw,40px);font-weight:400;color:{fg};margin:0;line-height:1.35;letter-spacing:-0.01em;max-width:880px;">
{html_mod.escape(quote_text)}
</blockquote>
{f'<div style="margin-top:48px;"><div style="width:48px;height:1px;background:{pri};margin:0 auto 16px;"></div><cite style="font-family:\'{bf}\',sans-serif;font-style:normal;font-size:13px;color:{fg2};letter-spacing:0.12em;text-transform:uppercase;font-weight:500;">{html_mod.escape(quote_author)}</cite></div>' if quote_author else ''}
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Timeline — Horizontal connected dots
    # ═══════════════════════════════════════════════════════════════

    def _timeline_editorial(self, title, subtitle, events, section_label, *,
                            fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not events:
            events = []
        sl = _section_label(section_label or "Roadmap", pri, bf)

        header = f'''
<div style="margin-bottom:60px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        # Vertical timeline (more elegant for 5+ events)
        items = ""
        for i, e in enumerate(events[:6]):
            if isinstance(e, dict):
                date = html_mod.escape(str(e.get("date", e.get("year", ""))))
                evt_title = html_mod.escape(str(e.get("title", e.get("description", ""))))
                evt_desc = html_mod.escape(str(e.get("description", ""))) if e.get("title") else ""
            else:
                date = ""
                evt_title = html_mod.escape(str(e))
                evt_desc = ""
            is_last = i == len(events[:6]) - 1
            line = "" if is_last else f'<div style="position:absolute;top:16px;left:5px;width:1px;height:calc(100% + 24px);background:{bdr};"></div>'
            items += f'''
<div style="position:relative;padding-left:36px;padding-bottom:32px;">
{line}
<div style="position:absolute;top:6px;left:0;width:11px;height:11px;border-radius:50%;background:{pri};box-shadow:0 0 0 4px #ffffff, 0 0 0 5px {pri};"></div>
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{pri};letter-spacing:0.14em;text-transform:uppercase;margin-bottom:6px;" class="tabular">{date}</div>
<h3 style="font-family:'{hf}',sans-serif;font-size:17px;font-weight:600;color:{fg};margin:0 0 4px 0;line-height:1.3;">{evt_title}</h3>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{fg2};margin:0;line-height:1.5;max-width:520px;">{evt_desc}</p>' if evt_desc else ''}
</div>'''

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}<div>{items}</div></div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Comparison — Asymmetric 60/40 split
    # ═══════════════════════════════════════════════════════════════

    def _comparison_editorial(self, title, subtitle, comparison, section_label, *,
                              fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not isinstance(comparison, dict):
            comparison = {}
        left = comparison.get("left", {})
        right = comparison.get("right", {})
        l_title = html_mod.escape(str(left.get("title", "Us")))
        r_title = html_mod.escape(str(right.get("title", "Them")))
        l_items = [str(i) for i in left.get("points", left.get("items", []))]
        r_items = [str(i) for i in right.get("points", right.get("items", []))]

        sl = _section_label(section_label or "Competitive Edge", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        def _col(items, ctitle, color, bg_col, icon_name, is_winner=True):
            lis = ""
            for item in items:
                ic = _icon("check" if is_winner else "x", 14, color, 2.5)
                lis += f'''
<div style="display:flex;align-items:flex-start;gap:12px;padding:14px 0;border-bottom:1px solid {bdr};">
<span style="flex-shrink:0;margin-top:2px;color:{color};">{ic}</span>
<span style="font-family:'{bf}',sans-serif;font-size:14px;color:{fg};line-height:1.5;">{html_mod.escape(item)}</span>
</div>'''
            return f'''
<div style="background:{bg_col};border-radius:16px;padding:32px;border:1px solid {bdr};">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
<h3 style="font-family:'{hf}',sans-serif;font-size:20px;font-weight:600;color:{color};margin:0;letter-spacing:-0.01em;">{ctitle}</h3>
<span style="width:8px;height:8px;border-radius:50%;background:{color};"></span>
</div>
{lis}
</div>'''

        cols = (
            f'<div style="display:grid;grid-template-columns:1.15fr 1fr;gap:20px;">'
            f'{_col(l_items, l_title, pri, surf, "shield", True)}'
            f'{_col(r_items, r_title, fg2, surf2, "x", False)}'
            f'</div>'
        )

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}{cols}</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Chart — SVG-based with editorial framing
    # ═══════════════════════════════════════════════════════════════

    def _chart_editorial(self, title, subtitle, chart, section_label, *,
                         fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not isinstance(chart, dict):
            chart = {}
        chart_type = chart.get("type", "bar").lower()
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])

        sl = _section_label(section_label or "Data", pri, bf)
        header = f'''
<div style="margin-bottom:32px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        # Build chart SVG
        chart_svg = ""
        chart_callout = ""
        if datasets:
            ds = datasets[0]
            data = ds.get("data", [])
            ds_label = html_mod.escape(str(ds.get("label", "")))

            if chart_type in ("line", "area"):
                chart_svg = _svg_area_chart(labels, data, pri, acc)
            elif chart_type == "donut" or chart_type == "pie":
                colors = [pri, sec, acc, "#10b981", "#ef4444", "#8b5cf6"]
                segs = [{"value": float(v), "color": colors[i % len(colors)]} for i, v in enumerate(data)]
                donut = _svg_donut_chart(segs, 220, 32)
                # Legend
                total_val = sum(float(v) for v in data) or 1
                legend = ""
                for i, label in enumerate(labels):
                    c = colors[i % len(colors)]
                    pct = (float(data[i]) / total_val * 100) if i < len(data) else 0
                    legend += f'''
<div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid {bdr};">
<span style="width:10px;height:10px;background:{c};border-radius:2px;flex-shrink:0;"></span>
<span style="flex:1;font-family:'{bf}',sans-serif;font-size:14px;color:{fg};">{html_mod.escape(str(label))}</span>
<span class="tabular" style="font-family:'{bf}',sans-serif;font-size:13px;color:{fg2};font-weight:500;">{pct:.1f}%</span>
</div>'''
                chart_svg = f'<div style="display:grid;grid-template-columns:auto 1fr;gap:48px;align-items:center;">{donut}<div>{legend}</div></div>'
            else:
                # Default bar
                chart_svg = _svg_bar_chart(labels, data, pri, acc)

            # Compute callout if line/area/bar
            if data and chart_type != "donut":
                try:
                    growth = ((float(data[-1]) - float(data[0])) / float(data[0]) * 100) if float(data[0]) != 0 else 0
                    if abs(growth) > 5:
                        sign = "+" if growth > 0 else ""
                        chart_callout = f'''
<div style="display:inline-flex;align-items:center;gap:8px;padding:8px 16px;background:{pri}12;border-radius:50px;margin-bottom:24px;">
{_icon("trending-up", 14, pri)}
<span class="tabular" style="font-family:'{bf}',sans-serif;font-size:13px;font-weight:600;color:{pri};">{sign}{growth:.0f}% growth</span>
</div>'''
                except Exception:
                    pass

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
{chart_callout}
<div style="background:{surf};border-radius:16px;padding:40px;border:1px solid {bdr};flex:1;display:flex;align-items:center;">
<div style="width:100%;">{chart_svg}</div>
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Table — Editorial styled with zebra-strip
    # ═══════════════════════════════════════════════════════════════

    def _table_editorial(self, title, subtitle, table, section_label, *,
                         fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not isinstance(table, dict):
            table = {}
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        sl = _section_label(section_label or "Projections", pri, bf)
        header = f'''
<div style="margin-bottom:36px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        ths = "".join(
            f'<th style="padding:16px 20px;border-bottom:2px solid {fg};font-family:\'{bf}\',sans-serif;font-size:11px;color:{fg};text-align:{"left" if i == 0 else "right"};text-transform:uppercase;letter-spacing:0.12em;font-weight:600;">{html_mod.escape(str(h))}</th>'
            for i, h in enumerate(headers)
        )
        trs = ""
        for ri, row in enumerate(rows):
            zebra = surf if ri % 2 == 1 else "transparent"
            tds = ""
            for ci, c in enumerate(row):
                is_first = ci == 0
                weight = "600" if is_first else "500"
                color = fg if is_first else fg2
                align = "left" if is_first else "right"
                tds += f'<td class="tabular" style="padding:18px 20px;border-bottom:1px solid {bdr};font-family:\'{bf}\',sans-serif;font-size:14px;color:{color};text-align:{align};font-weight:{weight};">{html_mod.escape(str(c))}</td>'
            trs += f'<tr style="background:{zebra};">{tds}</tr>'

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="border:1px solid {bdr};border-radius:12px;overflow:hidden;background:{surf};">
<table style="width:100%;border-collapse:collapse;">
<thead><tr>{ths}</tr></thead>
<tbody>{trs}</tbody>
</table>
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Team — Editorial cards with avatars
    # ═══════════════════════════════════════════════════════════════

    def _team_editorial(self, title, subtitle, team, section_label, *,
                        fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        if not team:
            team = []
        sl = _section_label(section_label or "Team", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        cards = ""
        for member in team[:4]:
            if isinstance(member, dict):
                name = html_mod.escape(str(member.get("name", "")))
                role = html_mod.escape(str(member.get("role", member.get("title", ""))))
                bio = html_mod.escape(str(member.get("bio", member.get("description", ""))))
                avatar = member.get("avatar", "") or member.get("image", "")
            else:
                name = html_mod.escape(str(member))
                role = ""; bio = ""; avatar = ""
            initials = "".join(w[0] for w in name.split()[:2] if w).upper()
            avatar_html = (
                f'<img src="{html_mod.escape(avatar)}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;">'
                if avatar else
                f'<div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,{pri},{sec});display:flex;align-items:center;justify-content:center;color:#fff;font-family:\'{hf}\',sans-serif;font-size:22px;font-weight:600;">{initials}</div>'
            )
            cards += f'''
<div style="background:{surf};border-radius:14px;padding:28px;border:1px solid {bdr};">
<div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
{avatar_html}
<div>
<h3 style="font-family:'{hf}',sans-serif;font-size:16px;font-weight:600;color:{fg};margin:0 0 2px 0;letter-spacing:-0.01em;">{name}</h3>
<p style="font-family:'{bf}',sans-serif;font-size:12px;color:{pri};margin:0;font-weight:500;letter-spacing:0.04em;text-transform:uppercase;">{role}</p>
</div>
</div>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{fg2};margin:0;line-height:1.5;">{bio}</p>' if bio else ''}
</div>'''
        cols = "1fr 1fr" if len(team) <= 2 else "1fr 1fr 1fr 1fr"
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}<div style="display:grid;grid-template-columns:{cols};gap:16px;">{cards}</div></div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Closing — Centered with decorative geometry
    # ═══════════════════════════════════════════════════════════════

    def _closing_split(self, title, subtitle, body_text, image_url, *,
                       fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total,
        eyebrow="The Ask"):
        if image_url:
            panel_bg, panel_fg, panel_fg2 = _text_panel_colors("#ffffff", surf, fg, fg2)
            panel_bdr = _safe_border(panel_bg, bdr)
            text_panel = f'''
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:80px;background:{panel_bg};border-right:1px solid {panel_bdr};">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{pri};letter-spacing:0.18em;text-transform:uppercase;margin-bottom:24px;display:flex;align-items:center;gap:10px;">
<span style="width:24px;height:1px;background:{pri};"></span>The Ask
</div>
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(40px,5vw,64px);font-weight:700;color:{panel_fg};margin:0 0 20px 0;line-height:0.95;letter-spacing:-0.02em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:20px;color:{panel_fg2};margin:0 0 24px 0;line-height:1.4;font-weight:400;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{panel_fg2};margin:0 0 36px 0;line-height:1.6;max-width:480px;">{html_mod.escape(body_text)}</p>' if body_text else ''}
<div style="display:inline-flex;align-items:center;gap:10px;padding:14px 28px;background:{panel_fg};border-radius:50px;color:{panel_bg};font-family:'{bf}',sans-serif;font-size:14px;font-weight:500;width:fit-content;">{_icon("mail", 16, panel_bg)} Get in Touch</div>
</div>'''
            image_panel = f'''
<div style="flex:1;position:relative;background:#000;overflow:hidden;">
<img src="{html_mod.escape(image_url)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(1.1);">
<div style="position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,0,0,0.2),rgba(0,0,0,0.5));"></div>
</div>'''
            return f'<div style="display:flex;width:100%;height:100%;">{text_panel}{image_panel}</div>'

        return f'''
<div style="position:absolute;inset:0;background:linear-gradient(135deg,{gs},{ge});z-index:0;"></div>
<div style="position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:80px;color:#fff;">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:32px;opacity:0.85;display:flex;align-items:center;gap:10px;">
<span style="width:24px;height:1px;background:#fff;"></span>The Ask
</div>
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(56px,7vw,96px);font-weight:700;color:#fff;margin:0 0 24px 0;line-height:0.95;letter-spacing:-0.04em;max-width:1000px;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:22px;color:rgba(255,255,255,0.85);margin:0 0 32px 0;line-height:1.4;max-width:700px;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:rgba(255,255,255,0.7);margin:0 0 48px 0;line-height:1.6;max-width:560px;">{html_mod.escape(body_text)}</p>' if body_text else ''}
<div style="display:inline-flex;align-items:center;gap:10px;padding:16px 32px;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:50px;color:#fff;font-family:'{bf}',sans-serif;font-size:15px;font-weight:500;backdrop-filter:blur(8px);">{_icon("mail", 16, "#fff")} Get in Touch</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Default Bullets — Editorial with hairlines
    # ═══════════════════════════════════════════════════════════════

    def _bullets_editorial(self, title, subtitle, body_text, bullets, section_label, *,
                           fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Overview", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:17px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        body_html = ""
        if body_text:
            body_html = f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:{fg};line-height:1.7;margin:0 0 32px 0;max-width:680px;">{html_mod.escape(body_text)}</p>'

        items = ""
        for i, b in enumerate(bullets):
            bs = _plain_text(b)
            if " — " in bs or " - " in bs:
                parts = bs.replace(" - ", " — ").split(" — ", 1)
                btitle = html_mod.escape(parts[0].strip())
                bdesc = html_mod.escape(parts[1].strip()) if len(parts) > 1 else ""
            else:
                btitle = html_mod.escape(bs)
                bdesc = ""
            items += f'''
<div style="padding:20px 0;border-top:1px solid {bdr};display:grid;grid-template-columns:60px 1fr;gap:20px;align-items:start;">
<div class="tabular" style="font-family:'{df}',sans-serif;font-size:24px;font-weight:300;color:{pri};line-height:1;letter-spacing:-0.02em;">{i + 1:02d}</div>
<div>
<h3 style="font-family:'{hf}',sans-serif;font-size:16px;font-weight:600;color:{fg};margin:0 0 4px 0;line-height:1.4;letter-spacing:-0.01em;">{btitle}</h3>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{fg2};margin:0;line-height:1.55;max-width:600px;">{bdesc}</p>' if bdesc else ''}
</div>
</div>'''
        if items:
            items += f'<div style="border-top:1px solid {bdr};"></div>'

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}{body_html}<div>{items}</div></div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Split Content (text left, visual right OR overlap)
    # ═══════════════════════════════════════════════════════════════

    def _split_content(self, title, subtitle, body_text, image_url, eyebrow,
                       section_label, kit, *,
                       fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        eb = html_mod.escape(eyebrow or section_label or "Detail")
        right_panel_content = ""
        if image_url:
            right_panel_content = (
                f'<img src="{html_mod.escape(image_url)}" '
                f'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;'
                f'filter:saturate(1.05) contrast(1.03);">'
                f'<div style="position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,0,0,0.05),rgba(0,0,0,0.25));"></div>'
            )
        else:
            # Decorative gradient panel with geometric accent
            right_panel_content = (
                f'<div style="position:absolute;inset:0;background:linear-gradient(135deg,{gs},{ge});"></div>'
                f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                f'width:60%;aspect-ratio:1;border:1px solid rgba(255,255,255,0.18);border-radius:50%;"></div>'
                f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                f'width:40%;aspect-ratio:1;border:1px solid rgba(255,255,255,0.28);border-radius:50%;"></div>'
                f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                f'width:20%;aspect-ratio:1;background:rgba(255,255,255,0.18);border-radius:50%;"></div>'
            )

        panel_bg, panel_fg, panel_fg2 = _text_panel_colors("#ffffff", surf, fg, fg2)
        panel_bdr = _safe_border(panel_bg, bdr)
        text_panel = f'''
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:80px;background:{panel_bg};border-right:1px solid {panel_bdr};">
<div style="display:flex;align-items:center;gap:10px;font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{pri};letter-spacing:0.18em;text-transform:uppercase;margin-bottom:24px;">
<span style="width:24px;height:1px;background:{pri};"></span>{eb}
</div>
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(36px,5vw,60px);font-weight:700;color:{panel_fg};margin:0 0 16px 0;line-height:1.05;letter-spacing:-0.02em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:18px;color:{panel_fg2};margin:0 0 20px 0;line-height:1.45;max-width:480px;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{panel_fg};line-height:1.7;margin:0;max-width:480px;">{html_mod.escape(body_text)}</p>' if body_text else ''}
</div>'''
        right_panel = f'<div style="flex:1;position:relative;background:#000;overflow:hidden;">{right_panel_content}</div>'
        return f'<div style="display:flex;width:100%;height:100%;">{text_panel}{right_panel}</div>'

    # ═══════════════════════════════════════════════════════════════
    # Layout: StatHighlight — Single mega stat with sub-stats
    # ═══════════════════════════════════════════════════════════════

    def _stat_highlight(self, title, subtitle, stat_value, stat_label, percentage,
                        sub_stats, section_label, *,
                        fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "The Number", pri, bf)
        # Big stat hero with optional progress ring
        ring = ""
        if percentage is not None:
            try:
                pct = float(percentage)
                ring = f'<div style="margin-top:16px;display:flex;align-items:center;gap:12px;">{_svg_progress_ring(pct, 56, 5, pri, surf2)}<span class="tabular" style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{fg2};">{pct:.0f}% confidence</span></div>'
            except (TypeError, ValueError):
                ring = ""

        sub_html = ""
        if sub_stats:
            cards = ""
            for s in sub_stats[:4]:
                if isinstance(s, dict):
                    sv = html_mod.escape(str(s.get("value", "")))
                    sllbl = html_mod.escape(str(s.get("label", "")))
                else:
                    sv = html_mod.escape(str(s)); sllbl = ""
                cards += f'''
<div style="flex:1;padding:24px;background:{surf};border-radius:12px;border:1px solid {bdr};">
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:36px;font-weight:700;color:{fg};line-height:1;letter-spacing:-0.03em;margin-bottom:6px;">{sv}</div>
<div style="font-family:'{bf}',sans-serif;font-size:12px;color:{fg2};">{sllbl}</div>
</div>'''
            sub_html = f'<div style="display:flex;gap:16px;margin-top:48px;">{cards}</div>'

        hero = f'''
<div style="text-align:center;max-width:900px;margin:0 auto;">
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:clamp(96px,16vw,200px);font-weight:700;color:{pri};line-height:0.9;letter-spacing:-0.05em;margin-bottom:20px;">{html_mod.escape(stat_value or title)}</div>
<p style="font-family:'{bf}',sans-serif;font-size:clamp(18px,2.2vw,26px);color:{fg};font-weight:500;margin:0 0 8px 0;line-height:1.3;max-width:600px;margin-left:auto;margin-right:auto;">{html_mod.escape(stat_label or subtitle or title)}</p>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:14px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle and stat_label else ''}
{ring}
</div>'''

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;justify-content:center;">
<div style="margin-bottom:48px;">{sl}</div>
{hero}
{sub_html}
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: MetricsDashboard — Stats + chart side-by-side
    # ═══════════════════════════════════════════════════════════════

    def _metrics_dashboard(self, title, subtitle, metrics, chart_data, section_label, *,
                           fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Traction", pri, bf)
        header = f'''
<div style="margin-bottom:36px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        # Metrics column (3 stacked cards)
        metric_cards = ""
        for m in metrics[:3]:
            val = html_mod.escape(str(m.get("value", "")))
            lbl = html_mod.escape(str(m.get("label", "")))
            delta = m.get("delta", "") or m.get("trend", "")
            delta_html = ""
            if delta:
                d_str = html_mod.escape(str(delta))
                d_color = "#10b981" if "+" in d_str or "↑" in d_str else (pri if "-" not in d_str else "#ef4444")
                delta_html = (f'<div style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;'
                             f'background:{d_color}15;color:{d_color};border-radius:50px;font-size:11px;'
                             f'font-weight:600;margin-top:8px;">{_icon("arrow-up-right", 11, d_color, 2.2)} {d_str}</div>')
            metric_cards += f'''
<div style="background:{surf};border-radius:12px;padding:24px;border:1px solid {bdr};">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{fg2};letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px;">{lbl}</div>
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:36px;font-weight:700;color:{fg};line-height:1;letter-spacing:-0.03em;">{val}</div>
{delta_html}
</div>'''

        # Chart on the right
        chart_svg = ""
        if isinstance(chart_data, dict) and chart_data.get("datasets"):
            ds = chart_data["datasets"][0]
            data = ds.get("data", [])
            labels = chart_data.get("labels", [])
            ctype = chart_data.get("type", "bar")
            if ctype in ("line", "area"):
                chart_svg = _svg_area_chart(labels, data, pri, acc, 460, 280)
            else:
                chart_svg = _svg_bar_chart(labels, data, pri, acc, 460, 280)

        chart_panel = (
            f'<div style="background:{surf};border-radius:12px;padding:28px;border:1px solid {bdr};">{chart_svg}</div>'
            if chart_svg else
            f'<div style="background:{surf};border-radius:12px;padding:28px;border:1px solid {bdr};display:flex;align-items:center;justify-content:center;color:{fg2};">No chart data</div>'
        )

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="flex:1;display:grid;grid-template-columns:1fr 1.5fr;gap:20px;">
<div style="display:grid;grid-template-rows:1fr 1fr 1fr;gap:14px;">{metric_cards}</div>
{chart_panel}
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Items Grid — BentoGrid, FeatureGrid, ValuePropGrid, ProblemSolution
    # ═══════════════════════════════════════════════════════════════

    def _items_grid(self, title, subtitle, items, section_label, kit, *,
                    fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        # Bento-style with span support: span="2" doubles the column width
        is_problem = kit == "ProblemSolution"
        default_label = "Problem" if is_problem else ("Why Choose Us" if kit == "ValuePropGrid" else "Capabilities")
        sl = _section_label(section_label or default_label, pri, bf)

        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        cards = ""
        normalized_items = list(items[:6])
        for i, it in enumerate(normalized_items):
            it_title = html_mod.escape(
                _field_text(it, ("title", "name", "label", "value", "headline"), fallback=f"Item {i + 1}")
            )
            it_desc = html_mod.escape(
                _field_text(it, ("description", "detail", "body", "subtitle", "text", "copy"))
            )
            icon_name = _field_text(it, ("icon",), fallback="default")
            span = _field_text(it, ("span",), fallback="1")
            try:
                col_span = int(span)
            except (TypeError, ValueError):
                col_span = 1
            col_span = max(1, min(2, col_span))
            is_accent = bool(it.get("accent", False)) if isinstance(it, dict) else False

            # Accent card has gradient bg, others are neutral
            card_bg = f'linear-gradient(135deg,{gs},{ge})' if is_accent else surf
            card_color = "#ffffff" if is_accent else fg
            sub_color = "rgba(255,255,255,0.85)" if is_accent else fg2
            border = "transparent" if is_accent else bdr
            marker_bg = "rgba(255,255,255,0.16)" if is_accent else f"{pri}14"
            marker_color = "#ffffff" if is_accent else pri

            cards += f'''
<div style="grid-column:span {col_span};background:{card_bg};border-radius:14px;padding:26px;border:1px solid {border};display:flex;flex-direction:column;gap:18px;min-height:184px;">
<div style="width:38px;height:38px;border-radius:12px;background:{marker_bg};display:flex;align-items:center;justify-content:center;color:{marker_color};">{_icon(icon_name, 18, marker_color, 2)}</div>
<div>
<h3 style="font-family:'{hf}',sans-serif;font-size:clamp(17px,1.7vw,21px);font-weight:650;color:{card_color};margin:0 0 8px 0;line-height:1.18;letter-spacing:-0.01em;">{it_title}</h3>
{f'<div style="font-family:\'{bf}\',sans-serif;font-size:13.5px;color:{sub_color};line-height:1.45;font-weight:450;">{it_desc}</div>' if it_desc else ''}
</div>
</div>'''

        # Smart column count: 4 items → 4 cols; 5 → 3+2 bento; else 3 cols
        n_items = len(normalized_items)
        if n_items == 4:
            grid_cols = "repeat(4,minmax(0,1fr))"
        elif n_items == 5:
            grid_cols = "repeat(3,minmax(0,1fr))"
        else:
            grid_cols = f"repeat({max(1, min(3, n_items))},minmax(0,1fr))"
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:grid;grid-template-columns:{grid_cols};gap:16px;">{cards}</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: BeforeAfter — Side-by-side transformation
    # ═══════════════════════════════════════════════════════════════

    def _before_after(self, title, subtitle, before, after, stat, section_label, *,
                      fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Transformation", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        stat_pill = ""
        if stat:
            stat_pill = f'<div style="display:inline-flex;align-items:center;gap:10px;padding:14px 24px;background:{pri};color:#fff;border-radius:50px;font-family:\'{bf}\',sans-serif;font-size:15px;font-weight:600;margin:32px auto 0;">{_icon("arrow-up-right", 16, "#fff")} {html_mod.escape(stat)}</div>'

        before_panel = f'''
<div style="flex:1;background:{surf};border-radius:14px;padding:48px;border:1px solid {bdr};display:flex;flex-direction:column;justify-content:center;">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:{fg2};letter-spacing:0.18em;text-transform:uppercase;margin-bottom:20px;">Before</div>
<div style="font-family:'{bf}',sans-serif;font-size:clamp(20px,2.4vw,28px);font-weight:500;color:{fg};line-height:1.35;letter-spacing:-0.01em;text-decoration:line-through;text-decoration-color:{bdr};text-decoration-thickness:2px;opacity:0.7;">{html_mod.escape(before)}</div>
</div>'''
        arrow = f'<div style="display:flex;align-items:center;justify-content:center;width:48px;height:48px;background:{pri};color:#fff;border-radius:50%;align-self:center;">{_icon("arrow-right", 22, "#fff")}</div>'
        after_panel = f'''
<div style="flex:1;background:linear-gradient(135deg,{gs},{ge});border-radius:14px;padding:48px;color:#fff;display:flex;flex-direction:column;justify-content:center;">
<div style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:600;color:rgba(255,255,255,0.85);letter-spacing:0.18em;text-transform:uppercase;margin-bottom:20px;">After</div>
<div style="font-family:'{bf}',sans-serif;font-size:clamp(20px,2.4vw,28px);font-weight:600;color:#fff;line-height:1.35;letter-spacing:-0.01em;">{html_mod.escape(after)}</div>
</div>'''

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:flex;gap:20px;align-items:stretch;">{before_panel}{arrow}{after_panel}</div>
<div style="text-align:center;">{stat_pill}</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Comparison Columns — N-column with features list
    # ═══════════════════════════════════════════════════════════════

    def _comparison_columns(self, title, subtitle, columns, section_label, kit, *,
                            fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Compare", pri, bf)
        header = f'''
<div style="margin-bottom:36px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(32px,4vw,46px);font-weight:700;color:{fg};margin:0 0 10px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        cols_html = ""
        for col in columns[:4]:
            if not isinstance(col, dict):
                continue
            cname = html_mod.escape(str(col.get("name", "")))
            highlight = bool(col.get("highlight", False))
            features = col.get("features", []) or []
            bg_col = f'linear-gradient(180deg,{surf},{surf2})' if highlight else surf
            border = pri if highlight else bdr
            border_w = "2px" if highlight else "1px"
            badge = ""
            if highlight:
                badge = f'<div style="display:inline-block;padding:4px 10px;background:{pri};color:#fff;border-radius:50px;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:12px;">Recommended</div>'

            rows = ""
            for feat in features[:8]:
                if not isinstance(feat, dict):
                    continue
                flbl = html_mod.escape(str(feat.get("label", "")))
                fval = feat.get("value", "")
                if fval is True:
                    val_html = f'<span style="color:{pri};">{_icon("check", 16, pri, 2.5)}</span>'
                elif fval is False:
                    val_html = f'<span style="color:{fg2};opacity:0.5;">{_icon("x", 16, fg2, 2)}</span>'
                else:
                    val_html = f'<span class="tabular" style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{fg};font-weight:500;">{html_mod.escape(str(fval))}</span>'
                rows += f'''
<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid {bdr};">
<span style="font-family:'{bf}',sans-serif;font-size:13px;color:{fg};">{flbl}</span>
{val_html}
</div>'''
            cols_html += f'''
<div style="background:{bg_col};border-radius:14px;padding:28px;border:{border_w} solid {border};display:flex;flex-direction:column;">
{badge}
<h3 style="font-family:'{hf}',sans-serif;font-size:18px;font-weight:600;color:{fg};margin:0 0 20px 0;letter-spacing:-0.01em;">{cname}</h3>
{rows}
</div>'''

        n = min(len(columns), 4)
        grid = "1fr " * n if n > 0 else "1fr"
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:grid;grid-template-columns:{grid.strip()};gap:16px;">{cols_html}</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Timeline Nodes — Roadmap, ProcessFlow, Timeline
    # ═══════════════════════════════════════════════════════════════

    def _timeline_nodes(self, title, subtitle, nodes, section_label, kit, *,
                        fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        is_process = kit == "ProcessFlow"
        is_roadmap = kit == "Roadmap"
        default_label = "Process" if is_process else ("Roadmap" if is_roadmap else "Timeline")
        sl = _section_label(section_label or default_label, pri, bf)

        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        # Horizontal connected nodes
        n = len(nodes[:6])
        if n == 0:
            return f'''<div style="padding:80px;height:100%;">{header}</div>'''

        cards = ""
        for i, node in enumerate(nodes[:6]):
            label = html_mod.escape(
                _field_text(node, ("label", "date", "phase", "when"), fallback=f"{i + 1:02d}")
            )
            detail = html_mod.escape(
                _field_text(node, ("detail", "description", "title", "name", "body", "text"), fallback=_plain_text(node))
            )
            active = bool(node.get("active", False)) if isinstance(node, dict) else False
            is_last = i == n - 1

            # Node circle
            if active:
                dot = f'<div style="width:18px;height:18px;border-radius:50%;background:{pri};box-shadow:0 0 0 5px {surf},0 0 0 7px {pri};"></div>'
                num_color = pri
            else:
                dot = f'<div style="width:16px;height:16px;border-radius:50%;background:{surf};border:3px solid {pri};opacity:0.9;"></div>'
                num_color = fg

            # Connector line to next
            line = "" if is_last else f'<div style="position:absolute;top:9px;left:50%;width:100%;height:2px;background:{pri};opacity:0.35;"></div>'

            cards += f'''
<div style="flex:1;position:relative;text-align:center;padding:0 12px;">
<div style="position:relative;display:flex;justify-content:center;margin-bottom:24px;">{line}<div style="position:relative;z-index:2;">{dot}</div></div>
<div class="tabular" style="font-family:'{bf}',sans-serif;font-size:11px;font-weight:700;color:{num_color};letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px;">{label}</div>
<div style="font-family:'{hf}',sans-serif;font-size:15px;font-weight:600;color:{fg};line-height:1.35;">{detail}</div>
</div>'''

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
<div style="display:flex;width:100%;align-items:flex-start;transform:scale(1.05);transform-origin:center;">{cards}</div>
</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Team Members — Editorial cards with avatar/initials
    # ═══════════════════════════════════════════════════════════════

    def _team_members(self, title, subtitle, members, section_label, *,
                      fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Team", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(34px,4.5vw,52px);font-weight:700;color:{fg};margin:0 0 12px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:16px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        cards = ""
        for member in members[:6]:
            if not isinstance(member, dict):
                continue
            name = html_mod.escape(str(member.get("name", "")))
            role = html_mod.escape(str(member.get("role", member.get("title", ""))))
            bio = html_mod.escape(str(member.get("bio", member.get("description", ""))))
            avatar = member.get("avatar", "") or member.get("image", "")
            initials = "".join(w[0] for w in (member.get("name", "")).split()[:2] if w).upper()
            avatar_html = (
                f'<img src="{html_mod.escape(avatar)}" style="width:72px;height:72px;border-radius:50%;object-fit:cover;border:2px solid {bdr};">'
                if avatar else
                f'<div style="width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,{pri},{sec});display:flex;align-items:center;justify-content:center;color:#fff;font-family:\'{bf}\',sans-serif;font-size:26px;font-weight:700;letter-spacing:-0.02em;">{initials}</div>'
            )
            cards += f'''
<div style="background:{surf};border-radius:14px;padding:28px;border:1px solid {bdr};">
<div style="display:flex;align-items:center;gap:18px;margin-bottom:18px;">
{avatar_html}
<div>
<h3 style="font-family:'{hf}',sans-serif;font-size:17px;font-weight:600;color:{fg};margin:0 0 4px 0;letter-spacing:-0.01em;">{name}</h3>
<p style="font-family:'{bf}',sans-serif;font-size:11px;color:{pri};margin:0;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">{role}</p>
</div>
</div>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{fg2};margin:0;line-height:1.55;">{bio}</p>' if bio else ''}
</div>'''
        n = len(members[:6])
        cols = "1fr 1fr" if n <= 2 else ("1fr 1fr 1fr" if n <= 3 else "1fr 1fr 1fr 1fr" if n == 4 else "1fr 1fr 1fr")
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">{header}<div style="display:grid;grid-template-columns:{cols};gap:16px;">{cards}</div></div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Pricing Tiers
    # ═══════════════════════════════════════════════════════════════

    def _pricing_tiers(self, title, subtitle, tiers, section_label, *,
                       fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Pricing", pri, bf)
        header = f'''
<div style="margin-bottom:36px;max-width:720px;">
{sl}
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(32px,4vw,46px);font-weight:700;color:{fg};margin:0 0 10px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        tier_html = ""
        for t in tiers[:3]:
            if not isinstance(t, dict):
                continue
            tname = html_mod.escape(str(t.get("name", "")))
            price = html_mod.escape(str(t.get("price", "")))
            period = html_mod.escape(str(t.get("period", "/mo")))
            features = t.get("features", [])
            featured = bool(t.get("featured", False))

            bg_col = f'linear-gradient(180deg,{gs},{ge})' if featured else surf
            text_col = "#ffffff" if featured else fg
            sub_col = "rgba(255,255,255,0.8)" if featured else fg2
            border = "transparent" if featured else bdr

            badge = f'<div style="display:inline-block;padding:4px 10px;background:rgba(255,255,255,0.2);color:#fff;border-radius:50px;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">Most Popular</div>' if featured else ""

            feat_html = ""
            for f in features[:6]:
                feat_text = html_mod.escape(_plain_text(f))
                feat_html += f'<li style="font-family:\'{bf}\',sans-serif;font-size:13px;color:{text_col};padding:8px 0;border-bottom:1px solid {sub_col}30;display:flex;gap:10px;align-items:center;">{_icon("check", 14, text_col, 2.5)} {feat_text}</li>'

            tier_html += f'''
<div style="background:{bg_col};border-radius:16px;padding:32px;border:1px solid {border};display:flex;flex-direction:column;">
{badge}
<h3 style="font-family:'{hf}',sans-serif;font-size:16px;font-weight:600;color:{text_col};margin:0 0 12px 0;letter-spacing:-0.01em;">{tname}</h3>
<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:24px;">
<span class="tabular" style="font-family:'{bf}',sans-serif;font-size:48px;font-weight:750;color:{text_col};line-height:1;letter-spacing:-0.02em;font-variant-numeric:tabular-nums;white-space:nowrap;">{price}</span>
<span style="font-family:'{bf}',sans-serif;font-size:14px;color:{sub_col};">{period}</span>
</div>
<ul style="list-style:none;padding:0;margin:0;flex:1;">{feat_html}</ul>
</div>'''
        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">{tier_html}</div>
</div>'''

    # ═══════════════════════════════════════════════════════════════
    # Layout: Logo Grid — Customer logos / social proof
    # ═══════════════════════════════════════════════════════════════

    def _logo_grid(self, title, subtitle, logos, section_label, *,
                   fg, fg2, pri, sec, acc, surf, surf2, bdr, gs, ge, hf, bf, df, idx, total):
        sl = _section_label(section_label or "Trusted By", pri, bf)
        header = f'''
<div style="margin-bottom:48px;max-width:720px;text-align:center;margin-left:auto;margin-right:auto;">
<div style="display:flex;justify-content:center;">{sl}</div>
<h1 style="font-family:'{df}',sans-serif;font-size:clamp(32px,4vw,46px);font-weight:700;color:{fg};margin:0 0 10px 0;line-height:1.05;letter-spacing:-0.03em;">{html_mod.escape(title)}</h1>
{f'<p style="font-family:\'{bf}\',sans-serif;font-size:15px;color:{fg2};margin:0;line-height:1.5;">{html_mod.escape(subtitle)}</p>' if subtitle else ''}
</div>'''

        logo_html = ""
        for logo in (logos or [])[:8]:
            if isinstance(logo, dict):
                name = html_mod.escape(str(logo.get("name", "")))
                url = logo.get("url", "")
                if url and not _is_placeholder_url(url):
                    cell = f'<img src="{html_mod.escape(url)}" alt="{name}" style="max-width:80%;max-height:48px;object-fit:contain;filter:grayscale(1) opacity(0.7);">'
                else:
                    # Styled monogram block for text-only logos
                    initials = "".join(w[0] for w in name.split()[:2] if w).upper()
                    cell = (f'<div style="display:flex;align-items:center;gap:12px;">'
                            f'<div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,{pri},{sec});'
                            f'display:flex;align-items:center;justify-content:center;color:#fff;font-family:\'{bf}\',sans-serif;'
                            f'font-size:16px;font-weight:700;letter-spacing:-0.02em;">{initials}</div>'
                            f'<span style="font-family:\'{hf}\',sans-serif;font-size:16px;font-weight:600;color:{fg};letter-spacing:-0.01em;">{name}</span></div>')
            else:
                name_str = html_mod.escape(str(logo))
                initials = "".join(w[0] for w in name_str.split()[:2] if w).upper()
                cell = (f'<div style="display:flex;align-items:center;gap:12px;">'
                        f'<div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,{pri},{sec});'
                        f'display:flex;align-items:center;justify-content:center;color:#fff;font-family:\'{bf}\',sans-serif;'
                        f'font-size:16px;font-weight:700;letter-spacing:-0.02em;">{initials}</div>'
                        f'<span style="font-family:\'{hf}\',sans-serif;font-size:16px;font-weight:600;color:{fg};letter-spacing:-0.01em;">{name_str}</span></div>')
            logo_html += f'<div style="aspect-ratio:2.4/1;display:flex;align-items:center;justify-content:center;background:{surf};border:1px solid {bdr};border-radius:10px;">{cell}</div>'

        return f'''<div style="padding:80px;height:100%;display:flex;flex-direction:column;">
{header}
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;flex:1;align-content:center;">{logo_html}</div>
</div>'''
