"""
Scraper Engine - Playwright + Requests fallback
✅ Supports JS sites (Playwright)
✅ Auto-scroll to load more cards
✅ Tries clicking "Load More" buttons
✅ Saves HTML to output_last_scrape.html
✅ Extracts packages using LLM Helper (Gemini / fallback)
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeout

from tools.llm_helper import get_llm

load_dotenv()
logger = logging.getLogger(__name__)


class ScraperEngine:
    def __init__(self):
        self.timeout_ms = int(os.getenv("SCRAPER_TIMEOUT", "30")) * 1000
        self.headless = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
        self.browser_type = os.getenv("SCRAPER_BROWSER", "chromium")
        self.max_retries = int(os.getenv("SCRAPER_MAX_RETRIES", "2"))

        # ✅ scrolling config
        self.scroll_steps = int(os.getenv("SCRAPER_SCROLL_STEPS", "6"))
        self.scroll_pause_ms = int(os.getenv("SCRAPER_SCROLL_PAUSE_MS", "1200"))

        self.llm = get_llm()

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.mode = "requests"  # becomes playwright if successful

        logger.info("✅ ScraperEngine initialized")

    async def __aenter__(self):
        try:
            self.playwright = await async_playwright().start()

            try:
                if self.browser_type == "chromium":
                    self.browser = await self.playwright.chromium.launch(headless=self.headless)
                elif self.browser_type == "firefox":
                    self.browser = await self.playwright.firefox.launch(headless=self.headless)
                else:
                    self.browser = await self.playwright.webkit.launch(headless=self.headless)

                self.mode = "playwright"
                logger.info(f"🌐 Browser launched: {self.browser_type} (headless={self.headless})")
                return self

            except Exception as e:
                logger.warning(f"⚠️ Playwright browser launch failed: {e}")
                self.browser = None
                self.mode = "requests"
                return self

        except Exception as e:
            logger.warning(f"⚠️ Playwright unavailable, using requests mode: {e}")
            self.playwright = None
            self.browser = None
            self.mode = "requests"
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        logger.info("🔴 ScraperEngine closed")

    # ----------------------------
    # Requests fallback
    # ----------------------------
    def _fetch_html_requests(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.text

        except requests.exceptions.SSLError:
            logger.warning("⚠️ SSL failed, retrying with verify=False")
            r = requests.get(url, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            return r.text

    # ----------------------------
    # ✅ Auto-scroll + Load More clicker
    # ----------------------------
    async def _auto_scroll(self, page):
        """
        Scroll down to load more packages.
        Also tries clicking 'Load More' buttons if available.
        """
        try:
            for step in range(self.scroll_steps):
                # ✅ try load more button first
                await self._try_click_load_more(page)

                # ✅ scroll down
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(self.scroll_pause_ms)

            logger.info(f"✅ Auto-scroll completed ({self.scroll_steps} steps)")
        except Exception as e:
            logger.warning(f"⚠️ Auto-scroll failed: {e}")

    async def _try_click_load_more(self, page):
        """
        Try to click common load more buttons.
        """
        selectors = [
            "text=Load More",
            "text=Show More",
            "text=View More",
            "text=More",
            "button:has-text('Load')",
            "button:has-text('More')",
        ]

        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(timeout=2000)
                    await page.wait_for_timeout(1200)
                    logger.info("✅ Clicked Load More button")
                    return
            except Exception:
                continue

    # ----------------------------
    # ✅ Main scrape
    # ----------------------------
    async def scrape_agency(self, url: str, agency_name: str, extract_packages: bool = True) -> Dict[str, Any]:
        result = {
            "url": url,
            "agency_name": agency_name,
            "success": False,
            "packages": [],
            "error": None,
            "html_length": 0,
            "mode": self.mode
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔍 Scraping {url} (attempt {attempt}/{self.max_retries}) mode={self.mode}")

                # ✅ 1) Get HTML
                if self.browser is None:
                    html = self._fetch_html_requests(url)

                else:
                    page = await self.browser.new_page(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )

                    # ✅ better wait strategy
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    await page.wait_for_timeout(1500)

                    # ✅ extra wait for heavy JS
                    try:
                        await page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass

                    # ✅ auto-scroll to load more packages
                    await self._auto_scroll(page)

                    html = await page.content()

                    await page.close()

                # ✅ Save HTML for debugging
                try:
                    with open("output_last_scrape.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("✅ HTML saved to output_last_scrape.html")
                except Exception:
                    pass

                result["html_length"] = len(html)

                # ✅ 2) Extract packages
                if extract_packages:
                    packages = self.llm.extract_packages_from_html(html, url)
                    result["packages"] = packages
                    logger.info(f"✅ Found {len(packages)} packages from {url}")

                result["success"] = True
                return result

            except PlaywrightTimeout:
                result["error"] = "timeout"
                logger.warning(f"⏱️ Timeout scraping {url} (attempt {attempt})")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                result["error"] = str(e)
                logger.error(f"❌ Error scraping {url}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        return result

    # ----------------------------
    # ✅ Scrape multiple agencies
    # ----------------------------
    async def scrape_multiple_agencies(self, agencies: List[Dict[str, str]], max_concurrent: int = 3) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for i in range(0, len(agencies), max_concurrent):
            batch = agencies[i:i + max_concurrent]
            tasks = [self.scrape_agency(a["url"], a["name"]) for a in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    logger.error(f"❌ Batch error: {r}")
                else:
                    results.append(r)

            if i + max_concurrent < len(agencies):
                await asyncio.sleep(2)

        return results


async def scrape_url(url: str, agency_name: str = "Unknown") -> Dict[str, Any]:
    async with ScraperEngine() as scraper:
        return await scraper.scrape_agency(url, agency_name)
