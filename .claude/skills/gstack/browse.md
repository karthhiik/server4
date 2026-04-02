---
name: /browse
description: QA Engineer browser automation — navigate pages, click, screenshot, extract data
---

## When to use
When user wants to view a webpage, navigate through it, click elements, take screenshots, or extract data.

## How it works
1. Accept URL and action (navigate, click, screenshot, extract)
2. Use Playwright or webfetch to interact with page
3. Return results (HTML, screenshots, data)

## Usage
```
/browse https://example.com
/browse click "Login Button"
/browse screenshot
/browse extract "all prices"
```

## Implementation Options

### Option 1: Playwright (preferred)
```python
# Create a simple browser wrapper
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url)
    # navigate, click, screenshot, etc.
```

### Option 2: webfetch fallback
For simple page viewing, use webfetch tool.

## Actions supported
- `goto <url>` — Navigate to URL
- `click <selector>` — Click element
- `type <selector> <text>` — Type text
- `screenshot` — Take screenshot
- `html` — Get page HTML
- `text` — Get page text
- `evaluate <js>` — Run JavaScript

## Notes
- Requires playwright: `pip install playwright && playwright install chromium`
- Use headless=True for automation
- Store cookies for authenticated sessions