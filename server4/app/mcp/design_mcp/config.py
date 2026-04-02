"""Design MCP configuration."""

# Layout constraints per layout type
LAYOUT_CONSTRAINTS = {
    "title-hero": {"max_title_chars": 60, "max_subtitle_chars": 120, "max_bullets": 0},
    "two-column": {"max_title_chars": 40, "max_content_chars": 400, "max_bullets": 0},
    "bullets": {"max_title_chars": 40, "max_bullets": 8, "max_bullet_chars": 100},
    "bullets-with-image": {"max_title_chars": 40, "max_bullets": 5, "max_bullet_chars": 80},
    "full-image": {"max_title_chars": 40, "max_subtitle_chars": 80, "max_bullets": 0},
    "chart": {"max_title_chars": 40, "max_subtitle_chars": 80, "max_data_points": 12},
    "comparison": {"max_title_chars": 40, "max_items": 6, "max_item_chars": 60},
    "timeline": {"max_title_chars": 40, "max_events": 8, "max_event_chars": 80},
    "quote": {"max_quote_chars": 200, "max_author_chars": 40},
    "team-grid": {"max_title_chars": 40, "max_members": 6, "max_bio_chars": 60},
    "kpi-dashboard": {"max_title_chars": 40, "max_metrics": 6},
    "blank": {"max_title_chars": 60, "max_body_chars": 1000},
}

# WCAG AA minimum contrast ratio
MIN_CONTRAST_RATIO = 4.5

# Font size minimums (pt)
FONT_SIZE_MINIMUMS = {
    "title": 28,
    "subtitle": 18,
    "body": 14,
    "bullet": 16,
    "caption": 12,
    "metric_value": 36,
    "metric_label": 12,
}

# Theme cache TTL
THEME_CACHE_TTL = 86400  # 24 hours
