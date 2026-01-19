"""
Scraper Engine - Playwright-based scraping with Gemini extraction
Handles both static and JavaScript-rendered websites

Fallback:
1) Playwright browser (if installed)
2) Requests-only mode (no JS rendering)

SSL Fix:
- If SSL verification fails, retry with verify=False (temporary)
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeout

from tools.llm_helper import get_llm

load_dotenv()
logger = logging.getLogger(__name__)


class ScraperEngine:
    """
    Web scraper using Playwright + Gemini extraction.
    Falls back to requests if Playwright browser missing.
    """

    def __init__(self):
        self.timeout = int(os.getenv("SCRAPER_TIMEOUT", "30")) * 1000
        self.headless = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
        self.browser_type = os.getenv("SCRAPER_BROWSER", "chromium")
        self.max_retries = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))

        self.llm = get_llm()

        self.playwright = None
        self.browser: Optional[Browser] = None

        self.fallback_mode = "playwright"  # "playwright" or "requests"

        logger.info("✅ Scraper Engine initialized (Playwright + Gemini)")

    async def __aenter__(self):
        """
        Start Playwright browser.
        If it fails, switch to requests mode.
        """
        try:
            self.playwright = await async_playwright().start()

            try:
                if self.browser_type == "chromium":
                    self.browser = await self.playwright.chromium.launch(headless=self.headless)
                elif self.browser_type == "firefox":
                    self.browser = await self.playwright.firefox.launch(headless=self.headless)
                else:
                    self.browser = await self.playwright.webkit.launch(headless=self.headless)

                self.fallback_mode = "playwright"
                logger.info(f"🌐 Browser launched: {self.browser_type}")
                return self

            except Exception as e:
                logger.warning(f"⚠️ Playwright browser launch failed: {e}")
                logger.warning("🟡 Switching to REQUESTS fallback mode (no JS support)")
                self.browser = None
                self.fallback_mode = "requests"
                return self

        except Exception as e:
            logger.warning(f"🟡 Playwright totally unavailable: {e}")
            self.playwright = None
            self.browser = None
            self.fallback_mode = "requests"
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser safely."""
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

        logger.info("🔴 Scraper engine closed")

    # ----------------------------
    # Requests fallback
    # ----------------------------
    def _fetch_html_requests(self, url: str) -> str:
        """
        Fetch HTML via requests.
        If SSL fails, retry with verify=False (temporary).
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.text

        except requests.exceptions.SSLError:
            logger.warning("⚠️ SSL verification failed. Retrying with verify=False (temporary fix)")
            r = requests.get(url, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            return r.text

    # ----------------------------
    # Main scrape
    # ----------------------------
    async def scrape_agency(self, url: str, agency_name: str, extract_packages: bool = True) -> Dict[str, Any]:
        """
        Scrape one agency.
        """
        result = {
            "url": url,
            "agency_name": agency_name,
            "success": False,
            "packages": [],
            "error": None,
            "html_length": 0,
            "mode": self.fallback_mode
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔍 Scraping {url} (attempt {attempt}/{self.max_retries}) mode={self.fallback_mode}")

                # requests fallback
                if self.browser is None:
                    html_content = self._fetch_html_requests(url)

                # playwright mode
                else:
                    page = await self.browser.new_page(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    await page.wait_for_timeout(2000)

                    html_content = await page.content()
                    await page.close()

                result["html_length"] = len(html_content)

                if extract_packages:
                    packages = self.llm.extract_packages_from_html(html_content, url)
                    result["packages"] = packages
                    logger.info(f"✅ Found {len(packages)} packages from {url}")

                result["success"] = True
                return result

            except PlaywrightTimeout:
                logger.warning(f"⏱️ Timeout scraping {url} (attempt {attempt})")
                result["error"] = "timeout"

                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"❌ Error scraping {url}: {e}")
                result["error"] = str(e)

                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        return result

    async def scrape_multiple_agencies(self, agencies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Scrape multiple agencies concurrently."""
        max_concurrent = int(os.getenv("SCRAPER_MAX_CONCURRENT", "5"))

        results: List[Dict[str, Any]] = []

        for i in range(0, len(agencies), max_concurrent):
            batch = agencies[i:i + max_concurrent]

            tasks = [
                self.scrape_agency(agency["url"], agency["name"])
                for agency in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    logger.error(f"❌ Batch error: {r}")
                else:
                    results.append(r)

            if i + max_concurrent < len(agencies):
                await asyncio.sleep(3)

        return results

    async def find_package_pages(self, base_url: str) -> List[str]:
        """
        Find package pages via browser DOM parsing.
        If requests mode -> return [].
        """
        if self.browser is None:
            logger.warning("⚠️ find_package_pages skipped (requests mode)")
            return []

        try:
            page = await self.browser.new_page()
            await page.goto(base_url, wait_until="domcontentloaded", timeout=self.timeout)

            links = await page.evaluate(
                "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
            )
            await page.close()

            package_keywords = ["package", "tour", "holiday", "itinerary", "destination", "trip", "travel"]
            package_urls: List[str] = []

            base_domain = urlparse(base_url).netloc

            for link in links:
                link_lower = link.lower()
                link_domain = urlparse(link).netloc

                if link_domain != base_domain:
                    continue

                if any(keyword in link_lower for keyword in package_keywords):
                    if link not in package_urls:
                        package_urls.append(link)

            return package_urls[:10]

        except Exception as e:
            logger.error(f"❌ Error finding package pages: {e}")
            return []


async def scrape_url(url: str, agency_name: str = "Unknown") -> Dict[str, Any]:
    """Quick scrape one url."""
    async with ScraperEngine() as scraper:
        return await scraper.scrape_agency(url, agency_name)


if __name__ == "__main__":
    async def test_scraper():
        test_agency = {"name": "Youth Camping", "url": "https://youthcamping.in/"}

        async with ScraperEngine() as scraper:
            result = await scraper.scrape_agency(test_agency["url"], test_agency["name"])

            print("\n📊 Results:")
            print("Success:", result["success"])
            print("Mode:", result["mode"])
            print("Packages:", len(result["packages"]))
            print("HTML Length:", result["html_length"])

    asyncio.run(test_scraper())
