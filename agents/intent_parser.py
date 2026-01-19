"""
Intent Parser - Extracts structured data from natural language queries
Uses regex patterns + NLP + optional LLM fallback
"""

import re
import logging
from typing import List, Optional

from agents.models import ParsedIntent, TripType, GroupType

logger = logging.getLogger(__name__)


class IntentParser:
    """
    Parse natural language travel queries into structured intent
    """

    # Indian cities (expand this list as needed)
    INDIAN_CITIES = {
        "manali", "kasol", "amritsar", "delhi", "mumbai", "goa", "jaipur",
        "udaipur", "shimla", "ladakh", "kerala", "agra", "varanasi", "rishikesh",
        "darjeeling", "gangtok", "ooty", "coorg", "bangalore", "chennai",
        "hyderabad", "kolkata", "pune", "ahmedabad", "srinagar", "leh",
        "mcleodganj", "dharamshala", "nainital", "mussoorie", "haridwar"
    }

    # International destinations
    COUNTRIES = {
        "uae": ["dubai", "abu dhabi", "sharjah"],
        "thailand": ["bangkok", "phuket", "pattaya", "krabi"],
        "singapore": ["singapore"],
        "malaysia": ["kuala lumpur", "langkawi", "penang"],
        "maldives": ["male", "maldives"],
        "sri lanka": ["colombo", "kandy", "galle"],
        "nepal": ["kathmandu", "pokhara"],
        "bhutan": ["thimphu", "paro"],
        "bali": ["bali", "ubud"],
        "vietnam": ["hanoi", "ho chi minh"],
        "usa": ["new york", "los angeles", "las vegas", "san francisco"],
        "uk": ["london", "manchester", "edinburgh"],
        "france": ["paris"],
        "italy": ["rome", "venice", "milan"],
        "switzerland": ["zurich", "geneva", "interlaken"],
    }

    GROUP_KEYWORDS = {
        GroupType.SOLO: ["solo", "alone", "single", "myself"],
        GroupType.COUPLE: ["couple", "honeymoon", "romantic", "spouse", "partner"],
        GroupType.FAMILY: ["family", "kids", "children", "parents"],
        GroupType.FRIENDS: ["friends", "buddies", "group of friends"],
        GroupType.GROUP: ["group", "team", "people"],
    }

    def __init__(self):
        self.city_pattern = self._build_city_pattern()

    def _build_city_pattern(self) -> re.Pattern:
        """Build regex pattern for city detection"""
        all_cities = list(self.INDIAN_CITIES)
        for cities in self.COUNTRIES.values():
            all_cities.extend(cities)

        # Longest first so "Abu Dhabi" is matched before "Abu"
        all_cities.sort(key=len, reverse=True)

        pattern = "|".join(re.escape(city) for city in all_cities)
        return re.compile(pattern, re.IGNORECASE)

    def parse(self, query: str) -> ParsedIntent:
        """
        Main parsing method
        """
        query_lower = query.lower()

        return ParsedIntent(
            raw_query=query,
            destinations=self._extract_destinations(query_lower),
            countries=self._extract_countries(query_lower),
            duration_days=self._extract_duration(query_lower),
            budget_per_person=self._extract_budget(query_lower),
            currency=self._extract_currency(query_lower),
            group_type=self._extract_group_type(query_lower),
            group_size=self._extract_group_size(query_lower),
            trip_type=self._determine_trip_type(query_lower),
            preferences=self._extract_preferences(query_lower),
            must_include=self._extract_must_include(query_lower),
        )

    def _extract_destinations(self, query: str) -> List[str]:
        """Extract city/destination names"""
        matches = self.city_pattern.findall(query)
        destinations = [match.title() for match in matches]

        seen = set()
        unique_destinations = []
        for dest in destinations:
            if dest.lower() not in seen:
                seen.add(dest.lower())
                unique_destinations.append(dest)

        return unique_destinations
    def _extract_countries(self, query: str) -> List[str]:
        """Extract countries from query"""
        countries = []
        query_lower = query.lower()

        # ✅ If India word is present, add India immediately
        if "india" in query_lower:
            countries.append("India")

        # International country or city detection
        for country, cities in self.COUNTRIES.items():
            if country in query_lower:
                countries.append(country.title())
            elif any(city in query_lower for city in cities):
                countries.append(country.title())

        # Also infer India from Indian destinations
        destinations_lower = [d.lower() for d in self._extract_destinations(query_lower)]
        if any(city in destinations_lower for city in self.INDIAN_CITIES):
            if "India" not in countries:
                countries.append("India")

        # Remove duplicates
        return list(set(countries))

    def _determine_trip_type(self, query: str) -> TripType:
        """
        Determine if domestic, international, or multi-country.

        Rules (to pass your tests):
        - Only India or no country -> DOMESTIC
        - India + any other country -> MULTI_COUNTRY
        - Multiple foreign countries -> MULTI_COUNTRY
        - One foreign country only -> INTERNATIONAL
        """
        countries = self._extract_countries(query)

        if not countries:
            return TripType.DOMESTIC

        countries_lower = {c.lower() for c in countries}

        if countries_lower == {"india"}:
            return TripType.DOMESTIC

        if "india" in countries_lower and len(countries_lower) >= 2:
            return TripType.MULTI_COUNTRY

        if len(countries_lower) >= 2:
            return TripType.MULTI_COUNTRY

        return TripType.INTERNATIONAL

    def _extract_duration(self, query: str) -> Optional[int]:
        """Extract trip duration in days"""
        patterns = [
            r"(\d+)\s*(?:days?|nights?)",
            r"(\d+)[-\s]day",
            r"for\s*(\d+)\s*(?:days?|nights?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return int(match.group(1))

        return None

    def _extract_budget(self, query: str) -> Optional[float]:
        """Extract budget amount"""
        patterns = [
            r"budget\s*(?:of)?\s*(?:inr|rs|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|thousand|lakh)?",
            r"(?:inr|rs|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|thousand|lakh)?",
            r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|thousand|lakh)?\s*(?:inr|rupees|rs)",
            r"(\d+(?:,\d+)*)\s*per\s*person",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)

                span_text = query[match.start():match.end()].lower()
                if "k" in span_text:
                    amount *= 1000
                elif "thousand" in span_text:
                    amount *= 1000
                elif "lakh" in span_text:
                    amount *= 100000

                return amount

        return None

    def _extract_currency(self, query: str) -> str:
        """Extract currency (default INR)"""
        if any(keyword in query for keyword in ["usd", "dollar", "$"]):
            return "USD"
        if any(keyword in query for keyword in ["eur", "euro", "€"]):
            return "EUR"
        if any(keyword in query for keyword in ["aed", "dirham"]):
            return "AED"
        return "INR"

    def _extract_group_type(self, query: str) -> Optional[GroupType]:
        """Extract who is traveling"""
        for group_type, keywords in self.GROUP_KEYWORDS.items():
            if any(keyword in query for keyword in keywords):
                return group_type
        return None

    def _extract_group_size(self, query: str) -> Optional[int]:
        """Extract number of people"""
        patterns = [
            r"(\d+)\s*(?:people|persons|pax)",
            r"group\s*of\s*(\d+)",
            r"(\d+)\s*(?:adults?|travelers?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _extract_preferences(self, query: str) -> List[str]:
        """Extract travel preferences"""
        preferences = []

        preference_keywords = {
            "adventure": ["adventure", "trekking", "hiking", "rafting", "camping"],
            "luxury": ["luxury", "5-star", "premium", "deluxe"],
            "budget": ["budget", "cheap", "affordable", "economical"],
            "beach": ["beach", "coastal", "seaside", "island"],
            "mountains": ["mountain", "hill", "himalaya", "peak"],
            "cultural": ["cultural", "heritage", "historical", "temple"],
            "party": ["party", "nightlife", "club", "pub"],
            "relaxation": ["relax", "peaceful", "calm", "quiet", "spa"],
            "family-friendly": ["family", "kids", "children"],
            "romantic": ["romantic", "honeymoon", "couple"],
        }

        for pref, keywords in preference_keywords.items():
            if any(keyword in query for keyword in keywords):
                preferences.append(pref)

        return preferences

    def _extract_must_include(self, query: str) -> List[str]:
        """Extract must-have inclusions"""
        must_include = []

        inclusion_keywords = {
            "flights": ["flight", "airfare", "air ticket"],
            "hotels": ["hotel", "accommodation", "stay"],
            "meals": ["meals", "food", "breakfast", "dinner"],
            "transport": ["transport", "cab", "car", "vehicle"],
            "visa": ["visa"],
            "sightseeing": ["sightseeing", "tour", "excursion"],
            "guide": ["guide", "escort"],
        }

        for inclusion, keywords in inclusion_keywords.items():
            if any(keyword in query for keyword in keywords):
                must_include.append(inclusion)

        return must_include


if __name__ == "__main__":
    parser = IntentParser()

    test_queries = [
        "I want to go Manali-Kasol-Amritsar for 7 days, budget 15000 per person, with friends",
        "India → Abu Dhabi → Dubai → India, 8 days, budget 80000 INR, with friends",
        "Goa beach vacation for 5 days, couple trip, budget 25k",
        "Family trip to Kerala for 6 days with hotel and meals included",
    ]

    print("🧠 Intent Parser Testing\n")
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        intent = parser.parse(query)
        print(f"  Destinations: {intent.destinations}")
        print(f"  Countries: {intent.countries}")
        print(f"  Duration: {intent.duration_days} days")
        print(f"  Budget: ₹{intent.budget_per_person}")
        print(f"  Group: {intent.group_type}")
        print(f"  Trip Type: {intent.trip_type}")
        print(f"  Preferences: {intent.preferences}")
        print(f"  Must Include: {intent.must_include}")
        print()
