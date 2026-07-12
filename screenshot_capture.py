"""
Captures a full-page screenshot of each source URL (for Pixel-RAG) and, as a
cheap fallback/complement, also pulls the raw visible text (for normal
text-RAG). Uses Playwright (open source, local browser automation) -- no API.

Run once before first use:
    playwright install chromium
"""

import os
import re
import hashlib
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import config


@dataclass
class PageCapture:
    url: str
    screenshot_path: Optional[str]
    text: str


def _safe_filename(url: str) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:40]
    return f"{slug}_{h}.png"


def capture_page(url: str, out_dir: str = config.SCREENSHOT_DIR) -> PageCapture:
    os.makedirs(out_dir, exist_ok=True)
    screenshot_path = os.path.join(out_dir, _safe_filename(url))
    text = ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, timeout=config.PAGE_LOAD_TIMEOUT_MS, wait_until="networkidle")

            # Full page screenshot -> this is what Pixel-RAG will tile & read.
            page.screenshot(path=screenshot_path, full_page=True)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

            browser.close()
    except Exception as e:
        print(f"[screenshot_capture] failed for {url}: {e}")
        return PageCapture(url=url, screenshot_path=None, text="")

    return PageCapture(url=url, screenshot_path=screenshot_path, text=text)


if __name__ == "__main__":
    cap = capture_page("https://en.wikipedia.org/wiki/Voltage_reference")
    print(cap.screenshot_path, len(cap.text))
