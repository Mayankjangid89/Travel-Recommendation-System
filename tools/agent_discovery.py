"""
Agency Discovery Engine - Automatically find local travel agencies
Uses Google Search, directories, and listings to discover agencies
"""
import os
import re
import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AgencyDiscovery:
    """
    Discover travel agencies from multiple sources
    """
    
    # Major Indian cities to search
    INDIAN_CITIES = [
        "Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai",
        "Kolkata", "Pune", "Jaipur", "Ahmedabad", "Lucknow",
        "Chandigarh", "Kochi", "Indore", "Bhopal", "Visakhapatnam"
    ]
    
    # Popular tourist destinations
    TOURIST_DESTINATIONS = [
        "Goa", "Kerala", "Rajasthan", "Himachal", "Uttarakhand",
        "Kashmir", "Ladakh", "Sikkim", "Andaman", "Manali",
        "Shimla", "Ooty", "Darjeeling", "Agra", "Varanasi"
    ]
    
    def __init__(self):
        self.discovered_agencies: List[Dict[str, Any]] = []
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    def discover_from_google(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, str]]:
        """
        Discover agencies using Google Search
        
        Note: For production, use SerpAPI or ScraperAPI (paid services)
        This is a basic implementation using direct search
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of {"name": "...", "url": "...", "source": "google"}
        """
        logger.info(f"🔍 Google search: {query}")
        
        # For production, use SerpAPI:
        # SERP_API_KEY = os.getenv("SERP_API_KEY")
        # url = f"https://serpapi.com/search?q={query}&api_key={SERP_API_KEY}"
        
        # Basic implementation (may get blocked, use SerpAPI for production)
        search_url = f"https://www.google.com/search?q={query}"
        
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Google search returned status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            agencies = []
            
            # Extract search results (this is basic, SerpAPI gives better structured data)
            for result in soup.select('div.g')[:max_results]:
                try:
                    title_elem = result.select_one('h3')
                    link_elem = result.select_one('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text()
                        url = link_elem.get('href')
                        
                        if url and url.startswith('http'):
                            agencies.append({
                                "name": title,
                                "url": url,
                                "source": "google",
                                "discovery_query": query
                            })
                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue
            
            logger.info(f"✅ Found {len(agencies)} agencies from Google")
            return agencies
            
        except Exception as e:
            logger.error(f"❌ Google search error: {e}")
            return []
    
    def discover_from_justdial(self, city: str, category: str = "Travel Agents") -> List[Dict[str, str]]:
        """
        Discover agencies from JustDial
        
        Args:
            city: City name
            category: Business category
            
        Returns:
            List of agencies
        """
        logger.info(f"🔍 JustDial search: {city} - {category}")
        
        # JustDial URL format: https://www.justdial.com/city/category
        city_slug = city.lower().replace(" ", "-")
        category_slug = category.lower().replace(" ", "-")
        
        url = f"https://www.justdial.com/{city_slug}/{category_slug}"
        
        try:
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            agencies = []
            
            # Parse JustDial listings (structure may change)
            for listing in soup.select('li.cntanr')[:20]:
                try:
                    name_elem = listing.select_one('.jcn a')
                    website_elem = listing.select_one('a.comp_website')
                    
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        website = website_elem.get('href') if website_elem else None
                        
                        # Even without website, store for future investigation
                        agencies.append({
                            "name": name,
                            "url": website or f"https://www.justdial.com{name_elem.get('href', '')}",
                            "source": "justdial",
                            "city": city,
                            "has_website": website is not None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing JustDial listing: {e}")
                    continue
            
            logger.info(f"✅ Found {len(agencies)} agencies from JustDial")
            return agencies
            
        except Exception as e:
            logger.error(f"❌ JustDial error: {e}")
            return []
    
    def discover_from_directory(self, directory_url: str) -> List[Dict[str, str]]:
        """
        Discover agencies from a travel directory website
        
        Args:
            directory_url: URL of directory page
            
        Returns:
            List of agencies
        """
        logger.info(f"🔍 Directory search: {directory_url}")
        
        try:
            headers = {"User-Agent": self.user_agent}
            response = requests.get(directory_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            agencies = []
            
            # Generic approach: find all links, filter for travel agency patterns
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip if empty or too short
                if not text or len(text) < 5:
                    continue
                
                # Look for travel-related keywords in text or URL
                travel_keywords = [
                    'travel', 'tour', 'holiday', 'package', 'tourism',
                    'vacation', 'trip', 'agency', 'operator'
                ]
                
                text_lower = text.lower()
                href_lower = href.lower()
                
                if any(kw in text_lower or kw in href_lower for kw in travel_keywords):
                    # Make URL absolute
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        base = f"{urlparse(directory_url).scheme}://{urlparse(directory_url).netloc}"
                        full_url = base + href
                    else:
                        continue
                    
                    agencies.append({
                        "name": text,
                        "url": full_url,
                        "source": "directory",
                        "source_url": directory_url
                    })
            
            # Remove duplicates
            unique_agencies = []
            seen_urls = set()
            
            for agency in agencies:
                if agency["url"] not in seen_urls:
                    seen_urls.add(agency["url"])
                    unique_agencies.append(agency)
            
            logger.info(f"✅ Found {len(unique_agencies)} unique agencies from directory")
            return unique_agencies[:50]  # Limit to 50
            
        except Exception as e:
            logger.error(f"❌ Directory error: {e}")
            return []
    
    def discover_all(
        self, 
        use_google: bool = True,
        use_justdial: bool = True,
        use_directories: bool = True,
        max_per_source: int = 20
    ) -> List[Dict[str, str]]:
        """
        Run full discovery from all sources
        
        Args:
            use_google: Use Google search
            use_justdial: Use JustDial
            use_directories: Use travel directories
            max_per_source: Max agencies per source
            
        Returns:
            Combined list of discovered agencies
        """
        all_agencies = []
        
        # 1. Google Search
        if use_google:
            logger.info("🚀 Starting Google discovery...")
            
            # Search for agencies in major cities
            for city in self.INDIAN_CITIES[:5]:  # Limit to top 5 cities
                query = f"travel agency in {city}"
                agencies = self.discover_from_google(query, max_results=5)
                all_agencies.extend(agencies)
            
            # Search for destination-specific agencies
            for dest in self.TOURIST_DESTINATIONS[:5]:
                query = f"{dest} tour packages"
                agencies = self.discover_from_google(query, max_results=5)
                all_agencies.extend(agencies)
        
        # 2. JustDial
        if use_justdial:
            logger.info("🚀 Starting JustDial discovery...")
            
            for city in self.INDIAN_CITIES[:3]:
                agencies = self.discover_from_justdial(city)
                all_agencies.extend(agencies)
        
        # 3. Travel Directories
        if use_directories:
            logger.info("🚀 Starting directory discovery...")
            
            # Known travel directory sites
            directories = [
                "https://www.indiamart.com/impcat/tour-travel-services.html",
                # Add more directory URLs
            ]
            
            for directory_url in directories:
                agencies = self.discover_from_directory(directory_url)
                all_agencies.extend(agencies)
        
        # Remove duplicates based on URL
        unique_agencies = self._deduplicate_agencies(all_agencies)
        
        logger.info(f"✅ Total agencies discovered: {len(unique_agencies)}")
        
        return unique_agencies
    
    def _deduplicate_agencies(self, agencies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate agencies based on domain"""
        unique = []
        seen_domains = set()
        
        for agency in agencies:
            try:
                domain = urlparse(agency["url"]).netloc
                domain = domain.replace("www.", "")  # Normalize
                
                if domain and domain not in seen_domains:
                    seen_domains.add(domain)
                    unique.append(agency)
            except Exception:
                continue
        
        return unique
    
    def filter_valid_agencies(self, agencies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter out invalid or problematic agencies
        
        Removes:
        - Aggregators (MakeMyTrip, Goibibo, etc.)
        - Social media links
        - Non-agency sites
        """
        blocked_domains = [
            'makemytrip.com', 'goibibo.com', 'cleartrip.com', 'yatra.com',
            'booking.com', 'agoda.com', 'expedia.com', 'tripadvisor.com',
            'facebook.com', 'instagram.com', 'twitter.com', 'youtube.com',
            'google.com', 'justdial.com', 'sulekha.com'
        ]
        
        valid_agencies = []
        
        for agency in agencies:
            try:
                domain = urlparse(agency["url"]).netloc.lower()
                domain = domain.replace("www.", "")
                
                # Skip if blocked domain
                if any(blocked in domain for blocked in blocked_domains):
                    continue
                
                # Must have valid URL
                if not agency["url"].startswith("http"):
                    continue
                
                valid_agencies.append(agency)
                
            except Exception:
                continue
        
        logger.info(f"✅ Filtered to {len(valid_agencies)} valid agencies")
        return valid_agencies


# Example usage
if __name__ == "__main__":
    discovery = AgencyDiscovery()
    
    print("🚀 Starting agency discovery...\n")
    
    # Discover agencies
    agencies = discovery.discover_all(
        use_google=True,
        use_justdial=False,  # May need special handling
        use_directories=False,
        max_per_source=10
    )
    
    # Filter valid ones
    valid_agencies = discovery.filter_valid_agencies(agencies)
    
    print(f"\n📊 Discovery Results:")
    print(f"  Total discovered: {len(agencies)}")
    print(f"  Valid agencies: {len(valid_agencies)}")
    
    if valid_agencies:
        print(f"\n📋 Sample agencies:")
        for i, agency in enumerate(valid_agencies[:5], 1):
            print(f"  {i}. {agency['name']}")
            print(f"     URL: {agency['url']}")
            print(f"     Source: {agency['source']}")
            print()