"""
gstack browse skill implementation for OpenCode.
Uses Playwright for browser automation.

Install: pip install playwright && playwright install chromium
"""

import os
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Page, Browser
except ImportError:
    sync_playwright = None


class BrowseSession:
    """Browser session for automation."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.cookies: Dict[str, Any] = {}
        self.screenshots: List[str] = []

    def start(self):
        """Start browser session."""
        if sync_playwright is None:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        return self

    def goto(self, url: str, wait_until: str = "load") -> str:
        """Navigate to URL."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        self.page.goto(url, wait_until=wait_until)
        return f"Navigated to {url}"

    def click(self, selector: str) -> str:
        """Click element by CSS selector."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        self.page.click(selector)
        return f"Clicked {selector}"

    def type(self, selector: str, text: str, delay: int = 0) -> str:
        """Type text into element."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        self.page.fill(selector, text)
        if delay > 0:
            self.page.wait_for_timeout(delay)
        return f"Typed '{text}' into {selector}"

    def screenshot(self, name: Optional[str] = None) -> str:
        """Take screenshot, return base64."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        if name is None:
            name = f"screenshot_{len(self.screenshots)}.png"
        path = f"/tmp/{name}"
        self.page.screenshot(path=path)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        self.screenshots.append(name)
        return f"Screenshot saved: {name} ({len(b64)} bytes base64)"

    def html(self) -> str:
        """Get page HTML."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page.content()

    def text(self) -> str:
        """Get page text."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page.inner_text("body")

    def evaluate(self, js: str) -> Any:
        """Execute JavaScript."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page.evaluate(js)

    def get_elements(self, selector: str) -> List[Dict[str, str]]:
        """Get elements matching selector."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        elements = self.page.query_selector_all(selector)
        return [
            {
                "tag": el.evaluate("el => el.tagName"),
                "text": el.inner_text()[:100],
                "id": el.get_attribute("id"),
                "class": el.get_attribute("class"),
            }
            for el in elements
        ]

    def get_cookies(self) -> List[Dict[str, Any]]:
        """Get all cookies."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page.context.cookies()

    def set_cookies(self, cookies: List[Dict[str, Any]]):
        """Set cookies."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        self.page.context.add_cookies(cookies)

    def wait_for_selector(self, selector: str, timeout: int = 5000):
        """Wait for selector to appear."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        self.page.wait_for_selector(selector, timeout=timeout)

    def get_console_logs(self) -> List[Dict[str, str]]:
        """Get console logs."""
        if not self.page:
            return []
        logs = []
        self.page.on(
            "console", lambda msg: logs.append({"type": msg.type, "text": msg.text})
        )
        return logs

    def close(self):
        """Close browser session."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


# Convenience functions for OpenCode integration


def browse(url: str, action: str = "goto", selector: str = "", text: str = "") -> str:
    """
    Simple browse function for quick usage.

    Usage:
        browse("https://example.com")  # goto
        browse("click", selector=".btn")  # click
        browse("screenshot")  # take screenshot
    """
    session = BrowseSession(headless=True).start()
    try:
        if action == "goto" or not action:
            return session.goto(url)
        elif action == "click":
            return session.click(selector)
        elif action == "type":
            return session.type(selector, text)
        elif action == "screenshot":
            return session.screenshot()
        elif action == "html":
            return session.html()[:2000]  # Limit output
        elif action == "text":
            return session.text()[:2000]
        else:
            return f"Unknown action: {action}"
    finally:
        session.close()


if __name__ == "__main__":
    # Quick test
    print("Testing browse...")
    session = BrowseSession(headless=False).start()
    session.goto("https://example.com")
    print(f"Title: {session.page.title()}")
    print(f"Text: {session.text()[:200]}")
    session.close()
    print("Done!")
