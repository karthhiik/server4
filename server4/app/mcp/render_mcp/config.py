"""Render MCP configuration."""

# PPTX settings
PPTX_SLIDE_WIDTH_EMU = 12192000   # 16:9 standard (33.87cm)
PPTX_SLIDE_HEIGHT_EMU = 6858000   # 16:9 standard (19.05cm)
PPTX_MARGIN_EMU = 457200          # 0.5 inch margins

# PDF settings
PDF_PAGE_WIDTH = "33.87cm"
PDF_PAGE_HEIGHT = "19.05cm"

# HTML/Reveal.js settings
REVEAL_CDN_VERSION = "5.1.0"

# Image rendering (Playwright)
SLIDE_RENDER_WIDTH = 1920
SLIDE_RENDER_HEIGHT = 1080
THUMBNAIL_WIDTH = 400
THUMBNAIL_HEIGHT = 225

# Export file settings
MAX_EXPORT_FILE_SIZE = 100 * 1024 * 1024  # 100MB
EXPORT_JOB_TIMEOUT = 300  # 5 minutes

# Render cache TTL
RENDER_CACHE_TTL = 3600  # 1 hour
