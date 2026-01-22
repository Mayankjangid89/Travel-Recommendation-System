"""
Data Normalizer (Production Friendly)

✅ Takes raw packages from scraper (Gemini / BS4)
✅ Cleans fields
✅ Ensures minimum valid schema
✅ Drops only truly useless entries
✅ Avoids rejecting everything
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataNormalizer:
    def __init__(self):
        pass

    def normalize_packages_batch(self, raw_packages: List[Dict[str, Any]], agency_id: int) -> List[Dict[str, Any]]:
        normalized = []
        if not raw_packages:
            logger.info("⚠️ No raw packages received for normalization")
            return normalized

        for pkg in raw_packages:
            clean = self.normalize_one(pkg, agency_id)
            if clean:
                normalized.append(clean)
            else:
                # ✅ this is what you see as "Invalid package data: Unknown"
                name = pkg.get("package_title") if isinstance(pkg, dict) else "Unknown"
                print(f"❌ Invalid package data: {name}")

        logger.info(f"✅ Normalized {len(normalized)}/{len(raw_packages)} packages")
        return normalized

    def normalize_one(self, pkg: Dict[str, Any], agency_id: int) -> Optional[Dict[str, Any]]:
        if not isinstance(pkg, dict):
            return None

        title = str(pkg.get("package_title") or "").strip()
        url = str(pkg.get("url") or "").strip()

        # ✅ if title missing, reject (without title, it's useless)
        if not title or len(title) < 5:
            return None

        # ✅ Clean numeric fields
        price = pkg.get("price_in_inr", 0)
        price = self._safe_float(price)

        days = pkg.get("duration_days", 0)
        days = self._safe_int(days)

        destinations = pkg.get("destinations", [])
        if not isinstance(destinations, list):
            destinations = []

        destinations = [str(d).strip() for d in destinations if str(d).strip()]

        # ✅ if url missing, keep it empty (DON'T reject)
        # many sites don't give direct package url on listing page
        if url and not self._looks_like_url(url):
            url = ""

        clean_pkg = {
            "agency_id": agency_id,
            "package_title": title,
            "url": url,
            "price_in_inr": price,
            "duration_days": days,
            "duration_nights": max(days - 1, 0) if days else 0,
            "destinations": destinations,
            "countries": pkg.get("countries") or ["India"],
            "inclusions": pkg.get("inclusions") or [],
            "exclusions": pkg.get("exclusions") or [],
            "highlights": pkg.get("highlights") or [],
            "rating": self._safe_float(pkg.get("rating", 0)),
            "reviews_count": self._safe_int(pkg.get("reviews_count", 0)),
            "source_confidence_score": self._safe_float(pkg.get("source_confidence_score", 0.55)),
            "is_active": True,
        }

        return clean_pkg

    def _safe_float(self, val: Any) -> float:
        try:
            if isinstance(val, str):
                val = val.replace(",", "").replace("₹", "").replace("INR", "").strip()
            return float(val)
        except:
            return 0.0

    def _safe_int(self, val: Any) -> int:
        try:
            return int(float(val))
        except:
            return 0

    def _looks_like_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except:
            return False
