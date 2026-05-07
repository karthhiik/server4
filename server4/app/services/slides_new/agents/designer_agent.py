"""
Designer Agent - Visual Design & Layout Intelligence
Agent 3: Creates visual design system, selects color palettes, defines typography,
determines layouts, and generates design specifications for each slide.
"""

from typing import Any, Dict, List, Optional

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)
from app.services.slides_new.design.icon_registry import (
    get_icons_for_slide,
    get_icons_for_content,
    get_icons_for_industry,
    suggest_icon_variant,
)
from app.services.slides_new.design.style_transfer import (
    infer_style,
    score_specificity,
    build_design_prompt,
)


class DesignerAgent(BaseAgent):
    """
    Agent 3: Visual design and layout intelligence.

    Responsibilities:
    - Create design system (colors, typography, spacing)
    - Define slide layouts for each content type
    - Generate visual specifications for each slide
    - Select appropriate imagery style
    - Define animation/transitions
    - Apply Anti-AI-Slop design principles

    Uses design intelligence to avoid generic AI aesthetics.
    """

    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["cf-glm", "cf-gemma", "mistral-medium", "phi-4-reasoning"]

    # ── BACKGROUND INTELLIGENCE ──────────────────────────────────
    # Maps slide type to recommended background treatments.
    # The designer prompt uses this to avoid flat solid backgrounds.
    SLIDE_BACKGROUND_MAP = {
        "title-hero": {
            "preferred": ["gradient-mesh", "image-overlay", "gradient-conic"],
            "effect": "glass",
            "pattern": None,
            "notes": "High-impact opening. Use rich mesh gradient with brand colors or cinematic image overlay with dark scrim. Never a flat white background.",
        },
        "problem": {
            "preferred": ["gradient-linear", "noise", "pattern"],
            "effect": "elevated",
            "pattern": "diagonal-lines",
            "notes": "Create tension. Dark gradient background with subtle pattern overlay. Diagonal lines suggest urgency. Noise adds grit/texture.",
        },
        "solution": {
            "preferred": ["gradient-radial", "glass", "gradient-mesh"],
            "effect": "glass",
            "pattern": None,
            "notes": "Light, optimistic. Radial gradient creates focus. Frosted glass cards float over gradient. Clean, aspirational.",
        },
        "market": {
            "preferred": ["gradient-linear", "pattern", "solid"],
            "effect": "flat",
            "pattern": "grid",
            "notes": "Data-first. Subtle grid pattern suggests structure and scale. Keep background subdued so charts pop.",
        },
        "traction": {
            "preferred": ["gradient-linear", "noise", "solid"],
            "effect": "elevated",
            "pattern": "dots",
            "notes": "Metrics focus. Subtle dot pattern adds texture without distraction. Light noise adds sophistication.",
        },
        "team": {
            "preferred": ["gradient-radial", "gradient-mesh", "image-overlay"],
            "effect": "glass",
            "pattern": None,
            "notes": "Warm, human. Soft radial gradient or lifestyle image overlay with blur. Glass cards for member profiles.",
        },
        "competition": {
            "preferred": ["gradient-linear", "pattern", "solid"],
            "effect": "elevated",
            "pattern": "cross-hatch",
            "notes": "Strategic. Cross-hatch pattern suggests analysis grid. Dark gradient adds weight and authority.",
        },
        "business-model": {
            "preferred": ["gradient-conic", "gradient-linear", "pattern"],
            "effect": "flat",
            "pattern": "hexagons",
            "notes": "Structural. Hexagon pattern suggests interconnected systems. Conic gradient adds visual interest to financial data.",
        },
        "financials": {
            "preferred": ["gradient-linear", "pattern", "solid"],
            "effect": "flat",
            "pattern": "grid",
            "notes": "Clean and precise. Grid pattern aligns with data tables. Minimal background so charts and numbers dominate.",
        },
        "ask": {
            "preferred": ["gradient-mesh", "gradient-conic", "glass"],
            "effect": "glass",
            "pattern": None,
            "notes": "Confident closing energy. Rich gradient shows polish. Glass effect on the ask amount creates emphasis. Bold, decisive.",
        },
        "closing": {
            "preferred": ["gradient-mesh", "image-overlay", "gradient-conic"],
            "effect": "glass",
            "pattern": None,
            "notes": "Memorable exit. Rich, cinematic background. Think Apple keynote final slide. Image overlay with brand gradient for lasting impression.",
        },
        "quote": {
            "preferred": ["image-overlay", "gradient-radial", "noise"],
            "effect": "frosted",
            "pattern": None,
            "notes": "Atmospheric. Image overlay with heavy blur creates depth behind quote. Subtle noise adds editorial feel. Quote floats on frosted surface.",
        },
        "timeline": {
            "preferred": ["gradient-linear", "pattern", "solid"],
            "effect": "flat",
            "pattern": "waves",
            "notes": "Progressive. Waves pattern suggests forward motion. Left-to-right gradient mirrors timeline progression.",
        },
        "kpi-dashboard": {
            "preferred": ["gradient-linear", "pattern", "noise"],
            "effect": "elevated",
            "pattern": "dots",
            "notes": "Dashboard feel. Subtle dot matrix pattern like a monitor. Elevated card surfaces for each KPI. Dark mode preferred.",
        },
        "comparison": {
            "preferred": ["gradient-linear", "pattern", "solid"],
            "effect": "flat",
            "pattern": "grid",
            "notes": "Structured. Grid pattern for visual alignment. Split gradient (left/right) to differentiate comparison columns.",
        },
        "section-header": {
            "preferred": ["gradient-mesh", "gradient-conic", "image-overlay"],
            "effect": "glass",
            "pattern": None,
            "notes": "Visual breather. Rich background marks section transition. Similar to title-hero but less intense. Accent gradient on the section name.",
        },
        "bullets": {
            "preferred": ["gradient-linear", "noise", "solid"],
            "effect": "flat",
            "pattern": "dots",
            "notes": "Content-focused. Subtle background so text is easily readable. Very light dot pattern adds texture. Avoid distraction from content.",
        },
    }

    # ── GRADIENT PALETTES ─────────────────────────────────────────
    # Premium multi-stop gradient pairs inspired by Stripe, Vercel, Linear, Apple.
    GRADIENT_PALETTES = {
        "aurora": ["#0F0C29", "#302B63", "#24243E"],
        "sunset_blush": ["#ee9ca7", "#ffdde1"],
        "ocean_blue": ["#2193b0", "#6dd5ed"],
        "stripe": ["#a960ee", "#f97794", "#fcf6bd", "#d0f4ea"],
        "vercel_dark": ["#000000", "#111827", "#1e1b4b"],
        "linear_gradient": ["#5865f2", "#eb459e"],
        "emerald_frost": ["#0d9488", "#10b981", "#34d399"],
        "midnight_indigo": ["#0f172a", "#1e1b4b", "#312e81"],
        "warm_amber": ["#f59e0b", "#d97706", "#b45309"],
        "rose_gold": ["#be185d", "#e11d48", "#f43f5e"],
        "cosmos": ["#667eea", "#764ba2"],
        "electric_violet": ["#4f46e5", "#7c3aed", "#a855f7"],
        "deep_space": ["#0c0c1d", "#1a1a3e", "#2d1b69"],
        "ice_crystal": ["#e0f2fe", "#bae6fd", "#7dd3fc"],
        "carbon_fiber": ["#1a1a1a", "#2d2d2d", "#404040"],
        "tropical_heat": ["#f97316", "#ef4444", "#ec4899"],
    }

    # ── ICON LIBRARY ──────────────────────────────────────────────
    # Commonly needed Lucide icon names per slide concept.
    ICON_MAP = {
        "growth": ["trending-up", "bar-chart-3", "arrow-up-right", "rocket"],
        "problem": ["alert-triangle", "x-circle", "flame", "skull"],
        "solution": ["check-circle", "sparkles", "zap", "lightbulb"],
        "team": ["users", "user-check", "crown", "star"],
        "market": ["globe-2", "pie-chart", "target", "building-2"],
        "money": ["dollar-sign", "wallet", "credit-card", "coins"],
        "time": ["clock", "timer", "calendar", "history"],
        "technology": ["cpu", "code-2", "server", "database"],
        "security": ["shield-check", "lock", "key", "fingerprint"],
        "communication": ["message-circle", "mail", "phone", "megaphone"],
        "data": ["bar-chart-2", "activity", "layers", "git-branch"],
        "navigation": ["arrow-right", "chevron-right", "external-link", "compass"],
    }

    ANTI_AI_SLOP_PRESETS = {
        # ── LIGHT MODE PRESETS ───────────────────────────────────
        "yc_pitch": {
            "name": "YC/Sequoia Anti-AI",
            "description": "Clean, founder-led aesthetic — not startup generic",
            "theme": "light",
            "fonts": {
                "heading": "DM Sans",
                "body": "Inter",
                "accent": "Space Mono",
            },
            "colors": {
                "primary": "#1A1A2E",
                "secondary": "#16213E",
                "accent": "#E94560",
                "background": "#FFFFFF",
                "text": "#1A1A2E",
                "muted": "#6B7280",
                "surface": "#F9FAFB",
                "gradient_from": "#1A1A2E",
                "gradient_to": "#E94560",
            },
            "gradient_pairs": [["#1A1A2E", "#E94560"], ["#16213E", "#0F172A"]],
            "chart_palette": ["#E94560", "#1A1A2E", "#6366F1", "#10B981", "#F59E0B", "#EC4899"],
            "spacing": {"base": 8, "tight": 4, "loose": 16, "section": 32},
            "border_radius": {"small": 4, "medium": 8, "large": 12},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 4px 6px rgba(0,0,0,0.07)",
                "elevated": "0 10px 25px rgba(0,0,0,0.1)",
                "glow": "0 0 20px rgba(233,69,96,0.15)",
            },
            "icon_style": "lucide",
        },
        "consulting": {
            "name": "Premium Consulting",
            "description": "McKinsey/BCG style — authoritative, clean, editorial",
            "theme": "light",
            "fonts": {
                "heading": "Playfair Display",
                "body": "Source Sans Pro",
                "accent": "Lora",
            },
            "colors": {
                "primary": "#0F172A",
                "secondary": "#334155",
                "accent": "#0EA5E9",
                "background": "#F8FAFC",
                "text": "#1E293B",
                "muted": "#64748B",
                "surface": "#FFFFFF",
                "gradient_from": "#0F172A",
                "gradient_to": "#0EA5E9",
            },
            "gradient_pairs": [["#0F172A", "#0EA5E9"], ["#334155", "#64748B"]],
            "chart_palette": ["#0EA5E9", "#0F172A", "#6366F1", "#14B8A6", "#F59E0B", "#F43F5E"],
            "spacing": {"base": 8, "tight": 4, "loose": 24, "section": 48},
            "border_radius": {"small": 2, "medium": 4, "large": 8},
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.1)",
                "card": "0 4px 12px rgba(0,0,0,0.08)",
                "elevated": "0 8px 30px rgba(0,0,0,0.12)",
                "glow": "0 0 20px rgba(14,165,233,0.12)",
            },
            "icon_style": "lucide",
        },
        "investor_update": {
            "name": "Investor Update",
            "description": "Data-first, clean metrics display with accent highlights",
            "theme": "light",
            "fonts": {
                "heading": "Sora",
                "body": "Inter",
                "accent": "JetBrains Mono",
            },
            "colors": {
                "primary": "#18181B",
                "secondary": "#27272A",
                "accent": "#10B981",
                "background": "#FAFAFA",
                "text": "#18181B",
                "muted": "#71717A",
                "surface": "#FFFFFF",
                "gradient_from": "#18181B",
                "gradient_to": "#10B981",
            },
            "gradient_pairs": [["#18181B", "#10B981"], ["#047857", "#059669"]],
            "chart_palette": ["#10B981", "#18181B", "#6366F1", "#F59E0B", "#EF4444", "#8B5CF6"],
            "spacing": {"base": 8, "tight": 4, "loose": 16, "section": 32},
            "border_radius": {"small": 4, "medium": 6, "large": 8},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 2px 8px rgba(0,0,0,0.06)",
                "elevated": "0 8px 20px rgba(0,0,0,0.08)",
                "glow": "0 0 15px rgba(16,185,129,0.15)",
            },
            "icon_style": "lucide",
        },
        "sales": {
            "name": "Sales Deck",
            "description": "Persuasive, benefit-focused design with bold accents",
            "theme": "light",
            "fonts": {
                "heading": "Clash Display",
                "body": "Satoshi",
                "accent": "General Sans",
            },
            "colors": {
                "primary": "#0D0D0D",
                "secondary": "#262626",
                "accent": "#FF4D4D",
                "background": "#FFFFFF",
                "text": "#0D0D0D",
                "muted": "#737373",
                "surface": "#FAFAFA",
                "gradient_from": "#0D0D0D",
                "gradient_to": "#FF4D4D",
            },
            "gradient_pairs": [["#0D0D0D", "#FF4D4D"], ["#FF4D4D", "#FF8C42"]],
            "chart_palette": ["#FF4D4D", "#0D0D0D", "#6366F1", "#10B981", "#F59E0B", "#EC4899"],
            "spacing": {"base": 8, "tight": 4, "loose": 20, "section": 40},
            "border_radius": {"small": 4, "medium": 8, "large": 16},
            "shadows": {
                "subtle": "0 2px 4px rgba(0,0,0,0.08)",
                "card": "0 8px 24px rgba(0,0,0,0.12)",
                "elevated": "0 12px 40px rgba(0,0,0,0.16)",
                "glow": "0 0 25px rgba(255,77,77,0.2)",
            },
            "icon_style": "lucide",
        },
        "marketing": {
            "name": "Product Launch",
            "description": "Bold, premium product aesthetic — Apple/Vercel energy",
            "theme": "light",
            "fonts": {
                "heading": "Cabinet Grotesk",
                "body": "Satoshi",
                "accent": "Space Grotesk",
            },
            "colors": {
                "primary": "#000000",
                "secondary": "#1A1A1A",
                "accent": "#6366F1",
                "background": "#FFFFFF",
                "text": "#000000",
                "muted": "#525252",
                "surface": "#F5F5F5",
                "gradient_from": "#6366F1",
                "gradient_to": "#EC4899",
            },
            "gradient_pairs": [["#6366F1", "#EC4899"], ["#4F46E5", "#7C3AED"]],
            "chart_palette": ["#6366F1", "#EC4899", "#10B981", "#F59E0B", "#EF4444", "#06B6D4"],
            "spacing": {"base": 8, "tight": 4, "loose": 24, "section": 48},
            "border_radius": {"small": 4, "medium": 8, "large": 24},
            "shadows": {
                "subtle": "0 2px 8px rgba(0,0,0,0.08)",
                "card": "0 12px 32px rgba(0,0,0,0.12)",
                "elevated": "0 20px 50px rgba(0,0,0,0.16)",
                "glow": "0 0 30px rgba(99,102,241,0.2)",
            },
            "icon_style": "lucide",
        },

        # ── DARK MODE PRESETS ────────────────────────────────────
        "yc_pitch_dark": {
            "name": "YC Demo Day Dark",
            "description": "Dark-stage pitch aesthetic — cinematic, dramatic contrast",
            "theme": "dark",
            "fonts": {
                "heading": "DM Sans",
                "body": "Inter",
                "accent": "Space Mono",
            },
            "colors": {
                "primary": "#FFFFFF",
                "secondary": "#E5E7EB",
                "accent": "#E94560",
                "background": "#0A0A0F",
                "text": "#F3F4F6",
                "muted": "#6B7280",
                "surface": "#1A1A2E",
                "gradient_from": "#0A0A0F",
                "gradient_to": "#1A1A2E",
            },
            "gradient_pairs": [["#0A0A0F", "#1A1A2E"], ["#E94560", "#6366F1"]],
            "chart_palette": ["#E94560", "#6366F1", "#10B981", "#F59E0B", "#06B6D4", "#F43F5E"],
            "spacing": {"base": 8, "tight": 4, "loose": 16, "section": 32},
            "border_radius": {"small": 6, "medium": 10, "large": 16},
            "shadows": {
                "subtle": "0 1px 4px rgba(0,0,0,0.3)",
                "card": "0 4px 12px rgba(0,0,0,0.4)",
                "elevated": "0 12px 40px rgba(0,0,0,0.6)",
                "glow": "0 0 30px rgba(233,69,96,0.25)",
            },
            "icon_style": "lucide",
        },
        "aurora_dark": {
            "name": "Aurora",
            "description": "Glassmorphism + northern-lights gradients — premium SaaS feel",
            "theme": "dark",
            "fonts": {
                "heading": "Outfit",
                "body": "Plus Jakarta Sans",
                "accent": "Fira Code",
            },
            "colors": {
                "primary": "#F0F9FF",
                "secondary": "#BAE6FD",
                "accent": "#8B5CF6",
                "background": "#0C0A1D",
                "text": "#E2E8F0",
                "muted": "#64748B",
                "surface": "rgba(30,27,75,0.6)",
                "gradient_from": "#5865F2",
                "gradient_to": "#EB459E",
            },
            "gradient_pairs": [
                ["#5865F2", "#EB459E"],
                ["#8B5CF6", "#06B6D4"],
                ["#0C0A1D", "#1E1B4B", "#312E81"],
            ],
            "chart_palette": ["#8B5CF6", "#06B6D4", "#F59E0B", "#10B981", "#EC4899", "#EF4444"],
            "spacing": {"base": 8, "tight": 4, "loose": 20, "section": 40},
            "border_radius": {"small": 8, "medium": 12, "large": 20},
            "shadows": {
                "subtle": "0 2px 8px rgba(0,0,0,0.3)",
                "card": "0 8px 32px rgba(0,0,0,0.4)",
                "elevated": "0 16px 48px rgba(0,0,0,0.6)",
                "glow": "0 0 40px rgba(139,92,246,0.3)",
            },
            "icon_style": "lucide",
            "surface_effects": {
                "card": "backdrop-filter: blur(16px); background: rgba(30,27,75,0.4); border: 1px solid rgba(255,255,255,0.08);",
                "hero_bg": "background: radial-gradient(ellipse at 30% 0%, rgba(88,101,242,0.3), transparent 50%), radial-gradient(ellipse at 70% 100%, rgba(235,69,158,0.2), transparent 50%);",
            },
        },
        "stripe_premium": {
            "name": "Stripe Premium",
            "description": "Famous Stripe gradient mesh — vibrant, professional, futuristic",
            "theme": "dark",
            "fonts": {
                "heading": "Sora",
                "body": "Inter",
                "accent": "Fira Code",
            },
            "colors": {
                "primary": "#FFFFFF",
                "secondary": "#C4B5FD",
                "accent": "#A78BFA",
                "background": "#0A0118",
                "text": "#E9E3FF",
                "muted": "#7C6CA5",
                "surface": "rgba(139,92,246,0.08)",
                "gradient_from": "#A960EE",
                "gradient_to": "#F97794",
            },
            "gradient_pairs": [
                ["#A960EE", "#F97794", "#FCF6BD", "#D0F4EA"],
                ["#667EEA", "#764BA2"],
            ],
            "chart_palette": ["#A960EE", "#F97794", "#FCF6BD", "#D0F4EA", "#667EEA", "#764BA2"],
            "spacing": {"base": 8, "tight": 4, "loose": 20, "section": 40},
            "border_radius": {"small": 6, "medium": 12, "large": 20},
            "shadows": {
                "subtle": "0 2px 8px rgba(0,0,0,0.3)",
                "card": "0 8px 24px rgba(0,0,0,0.4)",
                "elevated": "0 16px 56px rgba(0,0,0,0.5)",
                "glow": "0 0 50px rgba(169,96,238,0.3)",
            },
            "icon_style": "lucide",
            "surface_effects": {
                "card": "backdrop-filter: blur(12px); background: rgba(139,92,246,0.06); border: 1px solid rgba(169,96,238,0.15);",
                "hero_bg": "background: conic-gradient(from 225deg at 50% 50%, #A960EE, #F97794, #FCF6BD, #D0F4EA, #A960EE);",
            },
        },
        "editorial": {
            "name": "Editorial Magazine",
            "description": "Magazine/editorial layout — serif headings, generous whitespace, photographic",
            "theme": "light",
            "fonts": {
                "heading": "Newsreader",
                "body": "Source Serif 4",
                "accent": "IBM Plex Mono",
            },
            "colors": {
                "primary": "#1C1917",
                "secondary": "#44403C",
                "accent": "#B91C1C",
                "background": "#FFFBF5",
                "text": "#292524",
                "muted": "#78716C",
                "surface": "#FFFFFF",
                "gradient_from": "#1C1917",
                "gradient_to": "#B91C1C",
            },
            "gradient_pairs": [["#1C1917", "#B91C1C"], ["#78716C", "#44403C"]],
            "chart_palette": ["#B91C1C", "#1C1917", "#D97706", "#047857", "#6D28D9", "#0369A1"],
            "spacing": {"base": 8, "tight": 4, "loose": 32, "section": 56},
            "border_radius": {"small": 0, "medium": 2, "large": 4},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.06)",
                "card": "0 1px 3px rgba(0,0,0,0.1)",
                "elevated": "0 4px 12px rgba(0,0,0,0.08)",
                "glow": "none",
            },
            "icon_style": "lucide",
        },
        "keynote_dark": {
            "name": "Apple Keynote Dark",
            "description": "Cinematic dark stage — Apple WWDC keynote aesthetic",
            "theme": "dark",
            "fonts": {
                "heading": "SF Pro Display",
                "body": "SF Pro Text",
                "accent": "SF Mono",
            },
            "colors": {
                "primary": "#FFFFFF",
                "secondary": "#A1A1AA",
                "accent": "#3B82F6",
                "background": "#000000",
                "text": "#F4F4F5",
                "muted": "#71717A",
                "surface": "#18181B",
                "gradient_from": "#000000",
                "gradient_to": "#1E1B4B",
            },
            "gradient_pairs": [["#000000", "#1E1B4B"], ["#3B82F6", "#8B5CF6"]],
            "chart_palette": ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#06B6D4"],
            "spacing": {"base": 8, "tight": 4, "loose": 24, "section": 56},
            "border_radius": {"small": 8, "medium": 14, "large": 22},
            "shadows": {
                "subtle": "0 2px 4px rgba(0,0,0,0.4)",
                "card": "0 8px 24px rgba(0,0,0,0.5)",
                "elevated": "0 20px 60px rgba(0,0,0,0.7)",
                "glow": "0 0 40px rgba(59,130,246,0.2)",
            },
            "icon_style": "lucide",
            "surface_effects": {
                "card": "backdrop-filter: blur(20px); background: rgba(24,24,27,0.7); border: 1px solid rgba(255,255,255,0.06);",
                "hero_bg": "background: radial-gradient(ellipse at 50% -20%, rgba(59,130,246,0.15), transparent 60%);",
            },
        },
        "tech_modern": {
            "name": "Tech Modern",
            "description": "Linear/Vercel/Raycast style — developer-grade minimalism",
            "theme": "dark",
            "fonts": {
                "heading": "Geist",
                "body": "Geist",
                "accent": "Geist Mono",
            },
            "colors": {
                "primary": "#EDEDED",
                "secondary": "#A1A1A1",
                "accent": "#FFFFFF",
                "background": "#0A0A0A",
                "text": "#EDEDED",
                "muted": "#666666",
                "surface": "#171717",
                "gradient_from": "#0A0A0A",
                "gradient_to": "#171717",
            },
            "gradient_pairs": [["#0A0A0A", "#171717"], ["#EDEDED", "#666666"]],
            "chart_palette": ["#FFFFFF", "#A1A1A1", "#666666", "#404040", "#262626", "#171717"],
            "spacing": {"base": 8, "tight": 4, "loose": 20, "section": 48},
            "border_radius": {"small": 6, "medium": 10, "large": 14},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.5)",
                "card": "0 2px 8px rgba(0,0,0,0.4)",
                "elevated": "0 8px 24px rgba(0,0,0,0.6)",
                "glow": "0 0 1px rgba(255,255,255,0.2)",
            },
            "icon_style": "lucide",
            "surface_effects": {
                "card": "background: #171717; border: 1px solid #262626;",
                "hero_bg": "background: radial-gradient(ellipse at 50% 0%, rgba(255,255,255,0.03), transparent 70%);",
            },
        },
    }

    LAYOUT_SPECS = {
        "title-hero": {
            "elements": [
                {"type": "heading", "style": "hero", "size": "64px", "align": "center"},
                {
                    "type": "subtitle",
                    "style": "subtle",
                    "size": "24px",
                    "align": "center",
                },
                {"type": "background", "style": "gradient"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
        "two-column": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "column", "side": "left", "width": "50%"},
                {"type": "column", "side": "right", "width": "50%"},
            ],
            "grid": {"cols": 2, "rows": "auto", "gap": 24},
        },
        "bullets": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "bullet_list", "items": 5, "icon": "disc"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 12},
        },
        "bullets-with-image": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "column", "side": "left", "width": "60%"},
                {"type": "image", "side": "right", "width": "40%"},
            ],
            "grid": {"cols": 2, "rows": "auto", "gap": 24},
        },
        "chart": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "chart_container", "height": "300px"},
                {"type": "caption", "style": "muted", "size": "14px"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
        "team-grid": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "grid", "cols": 4, "card": "team_member"},
            ],
            "grid": {"cols": 4, "rows": "auto", "gap": 16},
        },
        "comparison": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "comparison_table", "cols": 2},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 24},
        },
        "kpi-dashboard": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "kpi_cards", "cols": 4},
            ],
            "grid": {"cols": 4, "rows": "auto", "gap": 16},
        },
        "timeline": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "timeline", "items": 5},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 8},
        },
        "quote": {
            "elements": [
                {"type": "quote_mark", "style": "large"},
                {"type": "quote_text", "size": "28px", "style": "italic"},
                {"type": "attribution", "size": "16px"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
    }

    @property
    def agent_type(self) -> AgentType:
        return AgentType.DESIGNER

    async def execute(self) -> AgentOutput:
        """
        Execute Designer Agent - create design system and specifications.

        Steps:
        1. Get CEO output for structure and writing style
        2. Query Design Memory for learned lessons
        3. Select appropriate Anti-AI-Slop preset
        4. Generate design system if custom
        5. Create layout specs for each slide
        6. Return design output
        """
        self.log_progress("Starting Designer Agent execution")

        # Get CEO output
        ceo_output = self.context.previous_outputs.get(AgentType.CEO)
        if not ceo_output or not ceo_output.success:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["CEO Agent output not available"],
            )

        structure = ceo_output.output.get("structure", [])
        writing_style = ceo_output.output.get("writing_style", "general")

        # Phase 13: Style intelligence — analyze user input specificity
        style_intel = self._build_style_intelligence(
            topic=self.context.topic,
            purpose=self.context.purpose,
            audience=self.context.audience,
            industry=self.context.company_name,
        )

        # Query Design Memory for learned lessons (self-learning integration)
        learned_context = await self._get_learned_design_context(structure)

        # Select design preset
        design_preset = self._select_preset(writing_style)

        # Create design specifications for each slide
        slide_specs = await self._generate_slide_specs(structure, design_preset)

        # Compile design output
        design = {
            "preset": design_preset["name"],
            "preset_description": design_preset["description"],
            "theme": design_preset.get("theme", "light"),
            "fonts": design_preset["fonts"],
            "colors": design_preset["colors"],
            "spacing": design_preset["spacing"],
            "border_radius": design_preset["border_radius"],
            "shadows": design_preset["shadows"],
            "gradient_pairs": design_preset.get("gradient_pairs", []),
            "chart_palette": design_preset.get("chart_palette", []),
            "icon_style": design_preset.get("icon_style", "lucide"),
            "surface_effects": design_preset.get("surface_effects", {}),
            "slide_specs": slide_specs,
            "global_styles": self._generate_global_styles(design_preset),
            "learned_context": learned_context,
            "style_intelligence": style_intel,
        }

        # Write to Context Board (Phase 2 fix: was missing)
        await self.write_to_board("design_system", {
            "preset": design_preset["name"],
            "theme": design_preset.get("theme", "light"),
            "fonts": design_preset["fonts"],
            "colors": design_preset["colors"],
            "spacing": design_preset["spacing"],
            "gradient_pairs": design_preset.get("gradient_pairs", []),
            "chart_palette": design_preset.get("chart_palette", []),
            "icon_style": design_preset.get("icon_style", "lucide"),
        })
        await self.write_to_board("design_slide_specs", {
            "count": len(slide_specs),
            "layouts": [s.get("layout", "unknown") for s in slide_specs],
        })

        self.log_progress(f"Design system created with {len(slide_specs)} slide specs")

        return AgentOutput(
            success=True,
            agent_type=self.agent_type,
            output=design,
            warnings=[],
            context_board_writes=self._board_writes,
        )

    def _select_preset(self, writing_style: str) -> Dict:
        """Select appropriate Anti-AI-Slop preset based on writing style."""
        preset_map = {
            "yc_pitch": "yc_pitch",
            "yc_pitch_dark": "yc_pitch_dark",
            "analytical": "consulting",
            "consulting": "consulting",
            "investor_update": "investor_update",
            "sales": "sales",
            "marketing": "marketing",
            "general": "yc_pitch",
            "aurora": "aurora_dark",
            "aurora_dark": "aurora_dark",
            "stripe": "stripe_premium",
            "stripe_premium": "stripe_premium",
            "editorial": "editorial",
            "keynote": "keynote_dark",
            "keynote_dark": "keynote_dark",
            "tech": "tech_modern",
            "tech_modern": "tech_modern",
            "dark": "yc_pitch_dark",
        }

        preset_key = preset_map.get(writing_style, "yc_pitch")
        return self.ANTI_AI_SLOP_PRESETS[preset_key]

    async def _get_learned_design_context(
        self, structure: List[Dict]
    ) -> str:
        """
        Query Design Memory for lessons relevant to this generation.
        Returns formatted text for injection into design decisions.
        """
        try:
            from app.services.slides_new.learning.design_memory import DesignMemory

            memory = DesignMemory(self.db)
            await memory.initialize()

            # Extract slide types from structure
            slide_types = [
                s.get("layout", "bullets") for s in structure
            ]

            lessons_text = await memory.get_lessons_for_prompt(
                slide_type=slide_types[0] if slide_types else None,
                audience=self.context.audience,
                purpose=self.context.purpose,
            )
            patterns_text = await memory.get_patterns_for_prompt(
                slide_types=slide_types,
                audience=self.context.audience,
                purpose=self.context.purpose,
            )

            parts = []
            if lessons_text:
                parts.append(lessons_text)
            if patterns_text:
                parts.append(patterns_text)

            return "\n\n".join(parts) if parts else ""

        except Exception as e:
            # Learning failures should never block design generation
            self.log_progress(
                f"Design memory query failed (non-fatal): {e}", level="warning"
            )
            return ""

    async def _generate_slide_specs(
        self, structure: List[Dict], preset: Dict
    ) -> List[Dict]:
        """Generate design specifications for each slide"""
        slide_specs = []

        for slide in structure:
            slide_index = slide.get("index", 0)
            layout = slide.get("layout", "bullets")
            title = slide.get("title", "")

            # Get layout spec
            layout_spec = self.LAYOUT_SPECS.get(layout, self.LAYOUT_SPECS["bullets"])

            # Generate specific spec for this slide
            spec = await self._generate_single_slide_spec(
                slide_index=slide_index,
                title=title,
                layout=layout,
                layout_spec=layout_spec,
                preset=preset,
            )

            slide_specs.append(spec)

        return slide_specs

    async def _generate_single_slide_spec(
        self,
        slide_index: int,
        title: str,
        layout: str,
        layout_spec: Dict,
        preset: Dict,
    ) -> Dict[str, Any]:
        """Generate detailed design spec for a single slide with rich backgrounds."""
        # Get background intelligence for this slide type
        slide_type = layout  # layout often matches slide type
        bg_intel = self.SLIDE_BACKGROUND_MAP.get(
            slide_type, self.SLIDE_BACKGROUND_MAP.get("bullets", {})
        )
        preferred_bgs = bg_intel.get("preferred", ["gradient-linear"])
        surface_effect = bg_intel.get("effect", "flat")
        pattern_type = bg_intel.get("pattern")
        bg_notes = bg_intel.get("notes", "")

        # Phase 13: Get Fluent UI icon suggestions for this slide type
        fluent_icons = get_icons_for_slide(slide_type)
        fluent_icon_names = [icon.name for icon in fluent_icons[:4]]

        # Pick a gradient pair from the preset
        gradient_pairs = preset.get("gradient_pairs", [])
        gradient_pair = gradient_pairs[slide_index % len(gradient_pairs)] if gradient_pairs else [
            preset["colors"].get("gradient_from", preset["colors"]["primary"]),
            preset["colors"].get("gradient_to", preset["colors"]["accent"]),
        ]

        # Theme-aware background guidance
        is_dark = preset.get("theme", "light") == "dark"
        surface_effects_css = preset.get("surface_effects", {})

        prompt = f"""Generate visual design specification for slide {slide_index}.

SLIDE: {title}
LAYOUT: {layout}

PRESET: {preset["name"]}
THEME: {"dark" if is_dark else "light"}
COLORS: {preset["colors"]}
FONTS: {preset["fonts"]}
GRADIENT PAIR for this slide: {gradient_pair}
CHART PALETTE: {preset.get("chart_palette", [])}

## BACKGROUND DESIGN INTELLIGENCE:
Recommended background types for this slide: {preferred_bgs}
Surface effect: {surface_effect}
Pattern type: {pattern_type or "none"}
Design guidance: {bg_notes}

### BACKGROUND TYPE OPTIONS (pick ONE that best fits):
- "gradient-linear": Two-color gradient with angle. Use gradient_pair colors. Add 'angle' (135° for diagonal).
- "gradient-radial": Radial gradient. Colors radiate from center. Creates focus and warmth.
- "gradient-mesh": Multi-point mesh gradient (like Stripe). Use 3-4 mesh_points with x/y/color/spread.
- "gradient-conic": Conic/sweep gradient rotating around a center point. Dramatic and unique.
- "image-overlay": Background image with color overlay. Set image_prompt (cinematic), overlay_color, overlay_opacity (0.6-0.8).
- "pattern": Repeating CSS pattern (dots, grid, diagonal-lines, cross-hatch, waves, hexagons, topography). Set pattern + pattern_opacity (0.04-0.12).
- "noise": Film grain texture overlay on gradient. Set noise_intensity (0.03-0.07). Adds editorial sophistication.
- "glass": Frosted glass effect — blur background with semi-transparent overlay. Set blur (8-20), overlay_color, overlay_opacity.
- "solid": ONLY use for data-heavy slides where any background would distract. Always add noise_intensity for texture.

### SURFACE EFFECTS (for cards/containers on this slide):
- "glass": backdrop-filter: blur(12-20px), semi-transparent bg, subtle border — for hero slides, quotes, CTAs
- "frosted": heavier blur + noise, like frosted glass — for overlay content on images
- "elevated": box-shadow with offset, solid surface — for KPIs, metrics, comparison cards
- "neumorphic": soft inset/outset shadows — for buttons, toggles, interactive-feeling elements
- "flat": no elevation — for content-heavy slides, bullets, timelines

### ICON INTEGRATION:
Icon set: {preset.get("icon_style", "lucide")}
Available icon concepts: growth, problem, solution, team, market, money, time, technology, security, data, navigation
Fluent UI icon suggestions for this slide type: {', '.join(fluent_icon_names) if fluent_icon_names else "none"}

## ACCESSIBILITY & QUALITY RULES:
1. Text-to-background contrast ratio MUST be ≥ 4.5:1 (WCAG AA). {"Light text on dark bg." if is_dark else "Dark text on light bg."}
2. Heading text ≥ 24px (large text can have 3:1 contrast minimum)
3. Never use color alone to convey meaning — add icons or labels
4. Font weight for body text ≥ 400; for emphasis ≥ 600
5. Maximum 3 font sizes per slide (heading, subheading, body)
6. Whitespace ratio: at least 40% of slide area should be empty space
7. No more than 7 content elements per slide (Miller's Law)

## DESIGN INTELLIGENCE:
- Hero slides: large type (48-72px), mesh/conic gradient, minimal elements, glass surface. Think Apple WWDC.
- Data slides: clear hierarchy, KPI numbers in accent color, elevated card surfaces, subtle grid pattern behind data
- Problem slides: create tension with dark gradient + diagonal pattern. Red/orange accents signal urgency.
- Solution slides: optimistic gradient (blues/greens), glass cards floating on gradient, radial gradient creates focus
- Team slides: warm gradient or image overlay with blur, glass cards for each member profile, avatar placeholders
- Quote slides: image overlay background with heavy frosted glass for quote text. Large decorative quote mark.
- Timeline slides: left-to-right gradient matching progression, wave pattern, connected dot indicators
- Comparison slides: split gradient (different shades per column), grid pattern for structure, elevated cards per competitor
- Section headers: rich gradient or mesh to mark transition, accent glow on the title text

Provide JSON:
{{
  "slide_index": {slide_index},
  "title": "{title}",
  "layout": "{layout}",
  "background": {{
    "type": "<background-type from options above>",
    "colors": [<2-4 hex colors from gradient_pair or preset>],
    "angle": <gradient angle if linear/conic, null otherwise>,
    "image_prompt": "<cinematic image description if image-overlay, null otherwise>",
    "overlay_color": "<hex with alpha if image-overlay/glass, null otherwise>",
    "overlay_opacity": <0.0-1.0 if overlay, null otherwise>,
    "blur": <0-20 if glass, null otherwise>,
    "pattern": "<pattern-type or null>",
    "pattern_opacity": <0.03-0.15 if pattern, null otherwise>,
    "noise_intensity": <0.02-0.08 if noise, null otherwise>,
    "mesh_points": [<{{x, y, color, spread}} objects if mesh gradient>]
  }},
  "heading": {{"color": "<heading color>", "font": "{preset["fonts"]["heading"]}"}},
  "body": {{"color": "<body text color>", "font": "{preset["fonts"]["body"]}"}},
  "accent": {{"color": "{preset["colors"]["accent"]}"}},
  "surface_style": "<glass|frosted|elevated|neumorphic|flat>",
  "icon_set": "{preset.get("icon_style", "lucide")}",
  "shadow_level": "<subtle|card|elevated|glow>",
  "elements": [
    {{"type": "heading", "spec": "specific styling for {title}"}},
    {{"type": "content", "spec": "content area styling"}},
    {{"type": "decorative", "spec": "optional decorative element (gradient border, glow accent, pattern overlay)"}}
  ],
  "visual_notes": "specific design notes for this slide — what makes it visually distinctive",
  "accessibility": {{
    "contrast_check": "pass",
    "min_font_size": "16px",
    "aria_notes": "semantic structure notes"
  }}
}}

Respond with ONLY valid JSON."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.4,
            max_tokens=2000,
            system_prompt=(
                "You are an award-winning presentation designer who has created keynotes for Apple, designed pitch decks "
                "for YC Demo Day, and art-directed campaigns for Stripe and Vercel. You understand that the BACKGROUND "
                "is the most important visual element — it sets mood, creates depth, and separates amateur slides from "
                "professional ones. You NEVER use flat white/solid backgrounds unless data absolutely demands it. "
                "You think in layers: background → surface → content → decoration. "
                "You use glassmorphism for floating cards, mesh gradients for hero slides, subtle patterns for "
                "texture, noise for editorial sophistication, and image overlays for emotional impact. "
                "Your color choices follow color theory — complementary for contrast, analogous for harmony, "
                "triadic for vibrancy. You use the 60-30-10 rule: 60% dominant color, 30% secondary, 10% accent. "
                "Every pixel has purpose. Your slides look like they belong in a design portfolio, not a template gallery."
            ),
        )

        if result.success:
            return result.output

        # Return rich default spec on failure (not flat)
        return {
            "slide_index": slide_index,
            "title": title,
            "layout": layout,
            "background": {
                "type": preferred_bgs[0] if preferred_bgs else "gradient-linear",
                "colors": gradient_pair,
                "angle": 135,
                "pattern": pattern_type,
                "pattern_opacity": 0.06 if pattern_type else None,
                "noise_intensity": 0.04,
            },
            "heading": {
                "color": preset["colors"]["primary"],
                "font": preset["fonts"]["heading"],
            },
            "body": {
                "color": preset["colors"]["text"],
                "font": preset["fonts"]["body"],
            },
            "accent": {"color": preset["colors"]["accent"]},
            "surface_style": surface_effect,
            "icon_set": preset.get("icon_style", "lucide"),
            "shadow_level": "card",
            "elements": layout_spec.get("elements", []),
            "visual_notes": f"Fallback design with {preferred_bgs[0]} background and {surface_effect} surface.",
        }

    def _generate_global_styles(self, preset: Dict) -> Dict:
        """Generate global CSS/style properties with rich background, gradient, and surface utilities."""
        colors = preset["colors"]
        fonts = preset["fonts"]
        spacing = preset["spacing"]
        border_radius = preset["border_radius"]
        shadows = preset["shadows"]
        is_dark = preset.get("theme", "light") == "dark"
        gradient_pairs = preset.get("gradient_pairs", [])
        surface_effects = preset.get("surface_effects", {})

        # Build gradient CSS from pairs
        gradient_css_vars = {}
        for i, pair in enumerate(gradient_pairs):
            stops = ", ".join(pair)
            gradient_css_vars[f"--gradient-{i + 1}"] = f"linear-gradient(135deg, {stops})"

        root_vars = {
            "--color-primary": colors["primary"],
            "--color-secondary": colors["secondary"],
            "--color-accent": colors["accent"],
            "--color-background": colors["background"],
            "--color-text": colors["text"],
            "--color-muted": colors["muted"],
            "--color-surface": colors.get("surface", colors["background"]),
            "--font-heading": fonts["heading"],
            "--font-body": fonts["body"],
            "--font-accent": fonts["accent"],
            "--spacing-base": f"{spacing['base']}px",
            "--spacing-tight": f"{spacing['tight']}px",
            "--spacing-loose": f"{spacing['loose']}px",
            "--spacing-section": f"{spacing['section']}px",
            "--radius-small": f"{border_radius['small']}px",
            "--radius-medium": f"{border_radius['medium']}px",
            "--radius-large": f"{border_radius['large']}px",
            "--shadow-subtle": shadows["subtle"],
            "--shadow-card": shadows["card"],
            "--shadow-elevated": shadows.get("elevated", shadows["card"]),
            "--shadow-glow": shadows.get("glow", "none"),
            **gradient_css_vars,
        }

        # Surface utilities CSS
        surface_css = ""
        if surface_effects.get("card"):
            surface_css += f"\n.surface-glass {{ {surface_effects['card']} }}"
        if surface_effects.get("hero_bg"):
            surface_css += f"\n.hero-bg {{ {surface_effects['hero_bg']} }}"

        global_css = f"""
            :root {{ color-scheme: {"dark" if is_dark else "light"}; }}
            .slide {{ background: {colors["background"]}; color: {colors["text"]}; }}
            .heading {{ font-family: {fonts["heading"]}, sans-serif; color: {colors["primary"]}; }}
            .body {{ font-family: {fonts["body"]}, sans-serif; color: {colors["text"]}; }}
            .accent {{ color: {colors["accent"]}; }}
            .surface {{ background: {colors.get("surface", colors["background"])}; }}
            .card-elevated {{ box-shadow: {shadows.get("elevated", shadows["card"])}; border-radius: {border_radius["large"]}px; }}
            .glow {{ box-shadow: {shadows.get("glow", "none")}; }}
            .noise-overlay {{ background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E"); }}
            .pattern-dots {{ background-image: radial-gradient(circle, {colors["muted"]} 1px, transparent 1px); background-size: 20px 20px; opacity: 0.06; }}
            .pattern-grid {{ background-image: linear-gradient({colors["muted"]}10 1px, transparent 1px), linear-gradient(90deg, {colors["muted"]}10 1px, transparent 1px); background-size: 40px 40px; }}
            {surface_css}
        """

        return {
            "root_variables": root_vars,
            "global_css": global_css,
            "theme": "dark" if is_dark else "light",
            "gradient_pairs": gradient_pairs,
            "chart_palette": preset.get("chart_palette", []),
            "icon_style": preset.get("icon_style", "lucide"),
        }

    def _build_style_intelligence(
        self,
        topic: str,
        purpose: str,
        audience: str,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Phase 13: Build style intelligence from user inputs.

        Uses style_transfer module (adapted from ArcadeAI/agent-style-transfer
        and stitch-kit patterns) to analyze:
        - Inferred style from topic/purpose text
        - Input specificity score (how detailed the design brief is)
        - Structured design prompt for LLM consumption
        """
        # Infer style from the combined text
        style = infer_style(topic, purpose, audience)

        # Score how specific the design brief is
        specificity = score_specificity(
            topic=topic,
            purpose=purpose,
            audience=audience,
            company_name=industry,
        )

        # Build structured prompt if we have enough context
        structured_prompt = None
        if not specificity.needs_ideation:
            prompt_obj = build_design_prompt(
                topic=topic,
                purpose=purpose,
                audience=audience,
                company_name=industry,
            )
            structured_prompt = prompt_obj.to_prompt_string()

        return {
            "inferred_style": {
                "tone": style.tone.value,
                "formality_level": style.formality_level,
                "vocabulary_level": style.vocabulary_level.value,
                "visual_energy": style.visual_energy,
                "color_warmth": style.color_warmth,
                "whitespace_ratio": style.whitespace_ratio,
                "personality_traits": style.personality_traits,
            },
            "specificity": {
                "total": specificity.total,
                "needs_ideation": specificity.needs_ideation,
                "ideation_depth": specificity.ideation_depth,
                "has_audience": specificity.has_audience,
                "has_purpose": specificity.has_purpose,
                "has_industry": specificity.has_industry,
            },
            "structured_prompt": structured_prompt,
        }
