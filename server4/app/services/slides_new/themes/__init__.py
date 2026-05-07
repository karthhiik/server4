"""
Theme package - Phase 4.

Built-in themes (24), generative theme engine, and CSS compilation
for reveal.js presentations.
"""

from app.services.slides_new.themes.theme_models import (
    BuiltInThemes,
    ThemeDefinition,
    ThemeMutation,
    ThemeTier,
)
from app.services.slides_new.themes.css_compiler import CSSCompiler
from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine

__all__ = [
    "BuiltInThemes",
    "ThemeDefinition",
    "ThemeMutation",
    "ThemeTier",
    "CSSCompiler",
    "GenerativeThemeEngine",
]
