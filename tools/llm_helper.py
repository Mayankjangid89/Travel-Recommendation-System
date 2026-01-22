"""
LLM Helper - Google Gemini + BeautifulSoup Fallback Extractor

✅ Features:
- Extract packages from HTML using Gemini (STRICT JSON)
- If Gemini fails / quota exceeded -> BeautifulSoup fallback extraction
- Cleans/normalizes extracted packages so DB normalizer won't reject
- Minimal, production-safe, no heavy hallucination prompts

ENV:
- GEMINI_API_KEY
- LLM_MODEL (default: gemini-2.5-flash-lite)
"""

import os
import json
import re
import time
import logging
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

from dotenv import load_dotenv
import google.generativeai as genai

logger = logging.getLogger(__name__)
load_dotenv()


class GeminiLLM:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")

        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY missing in .env")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        logger.info(f"✅ GeminiLLM initialized with model: {self.model_name}")

    # ==========================================================
    # ✅ MAIN: PACKAGE EXTRACTION (Gemini + Fallback)
    # ==========================================================
    def extract_packages_from_html(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract travel packages from HTML using Gemini.
        If Gemini fails -> fallback to BeautifulSoup extraction.
        """
        max_retries = 2
        base_delay = 3

        for attempt in range(max_retries):
            try:
                prompt = f"""
You are a STRICT travel package extractor.

Return ONLY valid JSON array. No markdown. No explanation.

Each object MUST contain:
- package_title: string
- price_in_inr: number (0 if unknown)
- duration_days: integer (0 if unknown)
- destinations: array of strings (empty if unknown)
- url: string (absolute if possible)

Rules:
- Extract maximum possible packages from HTML.
- Ignore navigation links.
- Use visible tour/package titles.

HTML:
{html[:22000]}
"""
                response = self.model.generate_content(prompt)
                text = (response.text or "").strip()

                # remove any accidental code block wrappers
                text = text.replace("```json", "").replace("```", "").strip()

                data = json.loads(text)
                if not isinstance(data, list):
                    raise ValueError("Gemini output not a JSON list")

                cleaned = self._clean_packages(data, base_url=url)
                logger.info(f"✅ Gemini extracted {len(cleaned)} packages from {url}")
                return cleaned

            except Exception as e:
                err = str(e).lower()

                # Rate limit / quota -> retry
                if "429" in err or "quota" in err or "rate" in err:
                    wait_time = base_delay * (2 ** attempt)
                    logger.warning(
                        f"⏳ Gemini quota/rate limit hit. Waiting {wait_time}s (attempt {attempt+1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"❌ Gemini extraction error: {e}")
                break

        logger.warning("🟡 Switching to fallback extraction (BeautifulSoup mode)...")
        return self._fallback_extract_packages_bs(html, url)

    # ==========================================================
    # ✅ FALLBACK: BEAUTIFULSOUP EXTRACTION
    # ==========================================================
    def _fallback_extract_packages_bs(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        A robust fallback extractor:
        - Finds possible tour/package cards
        - Extracts title + link + price + duration
        - Keeps package if it looks like a tour even if price/duration missing
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        packages: List[Dict[str, Any]] = []

        # Remove script/style noise
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Candidate cards = repeated blocks
        candidates = soup.find_all(
            lambda t: t.name in ["div", "li", "article", "section"]
            and any(
                c in (t.get("class") or [])
                for c in ["package", "tour", "trip", "card", "offer", "product", "item"]
            )
        )

        # If nothing found, fallback to anchors with tour-like text
        if not candidates:
            candidates = soup.find_all("a", href=True)

        logger.info(f"🔎 Fallback candidates found: {len(candidates)}")

        seen_titles = set()

        for node in candidates[:250]:
            text = node.get_text(" ", strip=True)
            if not text or len(text) < 6:
                continue

            title = self._extract_title_from_node(node)
            if not title or len(title) < 6:
                continue

            # Must look like a tour
            if not self._looks_like_package_title(title):
                continue

            if title.lower() in seen_titles:
                continue

            seen_titles.add(title.lower())

            price = self._extract_price(text)
            duration = self._extract_duration(text)

            href = ""
            if node.name == "a":
                href = node.get("href", "")
            else:
                a_tag = node.find("a", href=True)
                href = a_tag.get("href", "") if a_tag else ""

            full_url = urljoin(url, href) if href else url

            pkg = {
                "package_title": title.strip(),
                "price_in_inr": float(price),
                "duration_days": int(duration),
                "destinations": self._guess_destinations_from_text(title),
                "url": full_url,
                "scraped_at": datetime.utcnow().isoformat(),
                "source_confidence_score": 0.55,
            }

            packages.append(pkg)

            # keep it small for performance
            if len(packages) >= 30:
                break

        logger.info(f"✅ BeautifulSoup fallback extracted {len(packages)} packages from {url}")
        return packages

    # ==========================================================
    # ✅ CLEANING OUTPUT
    # ==========================================================
    def _clean_packages(self, packages: List[Dict[str, Any]], base_url: str) -> List[Dict[str, Any]]:
        """
        Normalize packages returned by Gemini.
        """
        cleaned: List[Dict[str, Any]] = []

        for pkg in packages:
            if not isinstance(pkg, dict):
                continue

            title = (pkg.get("package_title") or pkg.get("title") or "").strip()
            if not title:
                continue

            raw_price = pkg.get("price_in_inr") or pkg.get("price") or 0
            raw_days = pkg.get("duration_days") or pkg.get("days") or 0

            try:
                price = float(str(raw_price).replace(",", "").replace("₹", "").strip())
            except:
                price = 0.0

            try:
                days = int(raw_days)
            except:
                days = 0

            destinations = pkg.get("destinations") or []
            if not isinstance(destinations, list):
                destinations = []

            url = (pkg.get("url") or "").strip()
            if url:
                url = urljoin(base_url, url)
            else:
                url = base_url

            cleaned.append(
                {
                    "package_title": title,
                    "price_in_inr": price,
                    "duration_days": days,
                    "destinations": destinations,
                    "url": url,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "source_confidence_score": float(pkg.get("source_confidence_score", 0.75)),
                }
            )

        return cleaned

    # ==========================================================
    # ✅ Helpers
    # ==========================================================
    def _extract_title_from_node(self, node) -> str:
        # Prefer headings
        header = node.find(["h1", "h2", "h3", "h4", "h5"])
        if header:
            return header.get_text(" ", strip=True)

        # Else anchor text
        if node.name == "a":
            return node.get_text(" ", strip=True)

        # Else find best anchor inside
        a_tag = node.find("a")
        if a_tag and a_tag.get_text(strip=True):
            return a_tag.get_text(" ", strip=True)

        # Else strong/b tags
        strong = node.find(["strong", "b"])
        if strong:
            return strong.get_text(" ", strip=True)

        return ""

    def _looks_like_package_title(self, title: str) -> bool:
        t = title.lower()
        keywords = [
            "tour",
            "trip",
            "package",
            "trek",
            "camp",
            "holiday",
            "travel",
            "expedition",
            "manali",
            "goa",
            "kashmir",
            "ladakh",
            "jaipur",
            "shimla",
        ]
        return any(k in t for k in keywords)

    def _extract_price(self, text: str) -> float:
        m = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+)", text, re.IGNORECASE)
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(",", ""))
        except:
            return 0.0

    def _extract_duration(self, text: str) -> int:
        # "5 Days", "4N/5D", "3 Nights"
        m = re.search(r"(\d+)\s*(?:days|day|d)\b", text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except:
                return 0

        m2 = re.search(r"(\d+)\s*(?:nights|night|n)\b", text, re.IGNORECASE)
        if m2:
            try:
                return int(m2.group(1))
            except:
                return 0

        # 4N/5D
        m3 = re.search(r"(\d+)\s*n\s*/\s*(\d+)\s*d", text, re.IGNORECASE)
        if m3:
            try:
                return int(m3.group(2))
            except:
                return 0

        return 0

    def _guess_destinations_from_text(self, text: str) -> List[str]:
        known_places = [
            "Manali", "Kasol", "Jaipur", "Udaipur", "Jodhpur", "Goa",
            "Delhi", "Shimla", "Kullu", "Amritsar", "Dubai", "Abu Dhabi",
            "Kerala", "Rishikesh", "Leh", "Ladakh", "Kashmir", "Agra"
        ]
        found = []
        for place in known_places:
            if place.lower() in text.lower():
                found.append(place)
        return found


def get_llm() -> GeminiLLM:
    return GeminiLLM()
