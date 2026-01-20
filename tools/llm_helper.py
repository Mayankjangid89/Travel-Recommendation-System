"""
LLM Helper - Google Gemini + Fallback Regex Extractor
- Extract packages from HTML using Gemini
- If Gemini fails / quota exceeded, fallback to regex-based extraction
- Generate recommendation response for demo (without LLM call)
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from dotenv import load_dotenv

# ✅ Gemini SDK
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
        If Gemini fails (quota / timeout), fallback to regex extraction.
        """
        # Retry logic for rate limits
        max_retries = 3
        base_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                prompt = f"""
You are a travel package extraction system.

Extract ALL travel packages from the HTML below.

Return STRICT JSON array only (no markdown).
Each package object must include these fields:
- package_title (string)
- price_in_inr (number or 0)
- duration_days (integer or 0)
- destinations (list of strings)
- url (string - if relative, keep it relative)

HTML:
{html[:25000]}
"""
                response = self.model.generate_content(prompt)
                text = response.text.strip()

                # ✅ Remove code block formatting if returned
                text = text.replace("```json", "").replace("```", "").strip()

                data = json.loads(text)

                if isinstance(data, list):
                    cleaned = self._clean_packages(data)
                    logger.info(f"✅ Gemini extracted {len(cleaned)} packages from {url}")
                    return cleaned
                
                logger.warning("⚠️ Gemini returned non-list JSON. Retrying...")
            
            except Exception as e:
                # Check for 429
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    wait_time = base_delay * (2 ** attempt)
                    logger.warning(f"⏳ Gemini Rate Limit hit. Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Gemini extraction error: {e}")
                    break # Don't retry other errors

        logger.warning("🟡 Switching to fallback extraction (BeautifulSoup mode)...")
        return self._fallback_extract_packages(html, url)

    # ==========================================================
    # ✅ FALLBACK: BEAUTIFULSOUP BASED EXTRACTION
    # ==========================================================
    def _fallback_extract_packages(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        Robust fallback using BeautifulSoup:
        - Tries to identify package cards
        - Extracts price/duration from within cards
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        packages = []

        # 1. Identify common card containers
        # Look for repeated elements with relevant class names
        card_candidates = soup.find_all(lambda tag: tag.name in ['div', 'li', 'article'] and 
                                      any(c in (tag.get('class') or []) for c in ['package', 'tour', 'trip', 'card', 'item', 'offer']))
        
        # If no specific classes, try generic large containers that might be cards
        if not card_candidates:
             card_candidates = soup.find_all('div', recursive=True)
             # Filter for divs that have some text content and structure
             card_candidates = [d for d in card_candidates if len(d.text) > 50 and len(d.find_all(['h1','h2','h3','h4','a'])) > 0][:50]

        logger.info(f"🔎 Found {len(card_candidates)} candidate package cards")

        count = 0
        for card in card_candidates:
            text = card.get_text(" ", strip=True)
            
            # Find Title (usually h2, h3, h4 or first strong link)
            title = ""
            header = card.find(['h2', 'h3', 'h4', 'h5'])
            if header:
                title = header.get_text(strip=True)
            else:
                # Try finding a link with substantial text
                links = card.find_all('a')
                for link in links:
                    if len(link.get_text(strip=True)) > 10:
                        title = link.get_text(strip=True)
                        break
            
            if not title or len(title) < 5:
                continue

            # Find Price
            price = 0
            price_match = re.search(r'(?:₹|Rs\.?|INR)\s?([\d,]+)', text, re.IGNORECASE)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(",", ""))
                except:
                    pass

            # Find Duration
            duration = 0
            dur_match = re.search(r'(\d+)\s?(?:Days|Day|D|Nights|Night|N)', text, re.IGNORECASE)
            if dur_match:
                try:
                    duration = int(dur_match.group(1))
                except:
                    pass
            
            # Heuristic: If we found a title but no price/duration, check if we simply missed it or if it's not a package
            # Let's be lenient on fallback: if we have a title that looks "tour-like", keep it even if price is 0
            is_tour_title = any(w in title.lower() for w in ['tour', 'trip', 'package', 'camp', 'trek', 'expedition', 'manali', 'goa'])
            
            if is_tour_title:
                 # Attempt to extract link
                card_link = url
                a_tag = card.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("http"):
                        card_link = href
                    else:
                        # simple join
                        if url.endswith("/"):
                            card_link = url + href.lstrip("/")
                        else:
                            card_link = url + "/" + href.lstrip("/")

                pkg = {
                    "package_title": title,
                    "price_in_inr": price,
                    "duration_days": duration,
                    "destinations": self._guess_destinations_from_title(title),
                    "url": card_link,
                    "scraped_at": datetime.utcnow().isoformat()
                }
                
                # Dedup by title
                if not any(p['package_title'] == title for p in packages):
                    packages.append(pkg)
                    count += 1
            
            if count >= 20: break

        if not packages:
            logger.info("⚠️ BeautifulSoup fallback found nothing, trying global regex...")
            return self._fallback_regex_global(html, url)

        logger.info(f"✅ BeautifulSoup fallback extracted {len(packages)} packages from {url}")
        return packages

    def _fallback_regex_global(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        Original regex extraction as last resort
        """
        packages = []
        clean_text = re.sub("<[^<]+?>", " ", html)
        clean_text = re.sub(r"\s+", " ", clean_text)

        title_patterns = [
            r"([A-Z][A-Za-z0-9&,\- ]{6,80}?(?:Tour|Trip|Package|Trek|Backpacking|Holiday|Camping))"
        ]
        
        # ... (simplified logic from before)
        titles = []
        for pat in title_patterns:
            titles.extend(re.findall(pat, clean_text))
        
        seen = set()
        unique_titles = []
        for t in titles:
            if t not in seen and len(t) > 10:
                seen.add(t)
                unique_titles.append(t)
        
        # Try to find loose prices/durations to map (very rough)
        prices_match = re.findall(r'(?:₹|Rs\.?|INR)\s?([\d,]+)', clean_text)
        durations_match = re.findall(r'(\d+)\s?(?:Days|Day|D)', clean_text)

        for i, title in enumerate(unique_titles[:15]):
            price = 0
            if i < len(prices_match):
                try: price = float(prices_match[i].replace(",", ""))
                except: pass
            
            duration = 0
            if i < len(durations_match):
                try: duration = int(durations_match[i])
                except: pass

            packages.append({
                "package_title": title,
                "price_in_inr": price,
                "duration_days": duration,
                "destinations": self._guess_destinations_from_title(title),
                "url": url,
                "scraped_at": datetime.utcnow().isoformat()
            })
        
        return packages

    # ==========================================================
    # ✅ CLEANING OUTPUT
    # ==========================================================
    def _clean_packages(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize packages returned by Gemini
        """
        cleaned = []

        for pkg in packages:
            title = pkg.get("package_title") or pkg.get("title") or ""
            price = pkg.get("price_in_inr") or pkg.get("price_inr") or 0
            days = pkg.get("duration_days") or 0
            dest = pkg.get("destinations") or []

            try:
                price = float(price)
            except:
                price = 0

            try:
                days = int(days)
            except:
                days = 0

            if not isinstance(dest, list):
                dest = []

            cleaned.append({
                "package_title": title.strip(),
                "price_in_inr": price,
                "duration_days": days,
                "destinations": dest,
                "url": pkg.get("url", ""),
                "scraped_at": datetime.utcnow().isoformat(),
                "source_confidence_score": 0.8
            })

        return cleaned

    # ==========================================================
    # ✅ DESTINATION GUESS HELPER (fallback)
    # ==========================================================
    def _guess_destinations_from_title(self, title: str) -> List[str]:
        known_places = [
            "Manali", "Kasol", "Jaipur", "Udaipur", "Jodhpur", "Goa",
            "Delhi", "Shimla", "Kullu", "Amritsar", "Dubai", "Abu Dhabi",
            "Kerala", "Rishikesh", "Leh", "Ladakh"
        ]

        found = []
        for place in known_places:
            if place.lower() in title.lower():
                found.append(place)

        return found

    # ==========================================================
    # ✅ STEP 8 FIX: RESPONSE GENERATOR (No Gemini calls)
    # ==========================================================
    def generate_recommendation_response(self, query: str, packages: list, top_packages: list) -> str:
        """
        Generate human-friendly response for the top ranked packages.
        No LLM call needed, works even if Gemini quota exceeded.
        """

        if not top_packages:
            return "❌ Sorry! I couldn't find any packages matching your requirements."

        lines = []
        lines.append("✅ Here are the best travel packages I found for you:\n")
        lines.append(f"📝 Your Query: {query}\n")

        for i, pkg in enumerate(top_packages, 1):
            title = pkg.get("package_title") or pkg.get("title") or "Untitled Package"
            price = pkg.get("price_in_inr") or pkg.get("price_inr") or 0
            days = pkg.get("duration_days") or 0
            dest = pkg.get("destinations") or []
            url = pkg.get("url") or ""

            dest_str = ", ".join(dest[:5]) if isinstance(dest, list) else str(dest)

            lines.append(
                f"{i}. ⭐ {title}\n"
                f"   💰 Price: ₹{price}\n"
                f"   🗓️ Duration: {days} days\n"
                f"   📍 Destinations: {dest_str}\n"
                f"   🔗 Link: {url}\n"
            )

        lines.append("🎯 Tip: Want a perfect itinerary? Tell me your starting city + travel month.")
        return "\n".join(lines)


# ==========================================================
# ✅ HELPER FUNCTION FOR PROJECT
# ==========================================================
def get_llm() -> GeminiLLM:
    return GeminiLLM()
