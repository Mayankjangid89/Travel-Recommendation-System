"""
Data Normalizer - Cleans and validates scraped data
Converts messy scraped data into clean database-ready format
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Normalizes scraped travel package data
    Handles data cleaning, validation, and standardization
    """
    
    def normalize_package(self, raw_package: Dict[str, Any], agency_id: int) -> Optional[Dict[str, Any]]:
        """
        Normalize a single package
        
        Args:
            raw_package: Raw scraped data
            agency_id: Database agency ID
        
        Returns:
            Normalized package dict or None if invalid
        """
        try:
            normalized = {
                "agency_id": agency_id,
                "package_title": self._clean_title(raw_package.get("title", "")),
                "url": raw_package.get("url", ""),
                "price_in_inr": self._parse_price(raw_package.get("price_inr", 0)),
                "duration_days": self._parse_duration(raw_package.get("duration_days", 0)),
                "destinations": self._normalize_destinations(raw_package.get("destinations", [])),
                "inclusions": self._normalize_list(raw_package.get("inclusions", [])),
                "exclusions": self._normalize_list(raw_package.get("exclusions", [])),
                "highlights": self._normalize_list(raw_package.get("highlights", [])),
                "scraped_at": datetime.utcnow(),
                "is_active": True
            }
            
            # Validate required fields
            if not self._validate_package(normalized):
                logger.warning(f"❌ Invalid package data: {raw_package.get('title', 'Unknown')}")
                return None
            
            return normalized
            
        except Exception as e:
            logger.error(f"❌ Error normalizing package: {e}")
            return None
    
    def normalize_packages_batch(
        self, 
        raw_packages: List[Dict[str, Any]], 
        agency_id: int
    ) -> List[Dict[str, Any]]:
        """
        Normalize multiple packages
        
        Args:
            raw_packages: List of raw package dicts
            agency_id: Database agency ID
        
        Returns:
            List of normalized packages (invalid ones filtered out)
        """
        normalized = []
        
        for raw_pkg in raw_packages:
            norm_pkg = self.normalize_package(raw_pkg, agency_id)
            if norm_pkg:
                normalized.append(norm_pkg)
        
        logger.info(f"✅ Normalized {len(normalized)}/{len(raw_packages)} packages")
        return normalized
    
    def _clean_title(self, title: str) -> str:
        """Clean package title"""
        if not title:
            return "Untitled Package"
        
        # Remove extra whitespace
        title = " ".join(title.split())
        
        # Capitalize properly
        title = title.title()
        
        # Limit length
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    def _parse_price(self, price: Any) -> float:
        """Parse price to float"""
        if isinstance(price, (int, float)):
            return float(price)
        
        if isinstance(price, str):
            # Remove currency symbols and commas
            price = re.sub(r'[₹$€,\s]', '', price)
            try:
                return float(price)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def _parse_duration(self, duration: Any) -> int:
        """Parse duration to integer days"""
        if isinstance(duration, int):
            return duration
        
        if isinstance(duration, str):
            # Extract number from strings like "5 Days", "5D/4N"
            match = re.search(r'(\d+)', duration)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _normalize_destinations(self, destinations: Any) -> List[str]:
        """Normalize destination list"""
        if not destinations:
            return []
        
        if isinstance(destinations, str):
            # Split by common separators
            destinations = re.split(r'[,\-→>]', destinations)
        
        if not isinstance(destinations, list):
            return []
        
        # Clean each destination
        cleaned = []
        for dest in destinations:
            if isinstance(dest, str):
                dest = dest.strip().title()
                if dest and dest not in cleaned:
                    cleaned.append(dest)
        
        return cleaned
    
    def _normalize_list(self, items: Any) -> List[str]:
        """Normalize a list of strings"""
        if not items:
            return []
        
        if isinstance(items, str):
            items = [items]
        
        if not isinstance(items, list):
            return []
        
        cleaned = []
        for item in items:
            if isinstance(item, str):
                item = item.strip()
                if item and item not in cleaned:
                    cleaned.append(item)
        
        return cleaned
    
    def _validate_package(self, package: Dict[str, Any]) -> bool:
        """
        Validate package has minimum required fields
        
        Returns:
            True if valid
        """
        # Must have title
        if not package.get("package_title"):
            return False
        
        # Must have valid price
        if package.get("price_in_inr", 0) <= 0:
            return False
        
        # Must have valid duration
        if package.get("duration_days", 0) <= 0:
            return False
        
        # Must have at least one destination
        if not package.get("destinations"):
            return False
        
        # Price should be reasonable (1000 to 10,000,000 INR)
        price = package.get("price_in_inr", 0)
        if price < 1000 or price > 10000000:
            return False
        
        # Duration should be reasonable (1 to 90 days)
        days = package.get("duration_days", 0)
        if days < 1 or days > 90:
            return False
        
        return True