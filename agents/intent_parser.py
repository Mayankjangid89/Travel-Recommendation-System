"""
Intent Parser - Extract structured intent from user travel queries

Examples:
- "I want to go Manali-Kasol for 5 days, budget 20000 per person, with friends"
- "Goa beach trip 4 days under 15000 couple"
- "Dubai Abu Dhabi 6 days max 80000 with friends"
"""

from __future__ import annotations

import re
from typing import List, Optional

from agents.models import ParsedIntent, TripType, GroupType


class IntentParser:
    def __init__(self):
        # A small list of popular Indian cities + destinations
        # Later: replace with DB + Geo lookup (Nominatim/Google Places)
        self.known_places = [
            "manali", "kasol", "kullu", "amritsar", "shimla", "jaipur", "udaipur",
            "jodhpur", "goa", "kerala", "kochi", "munnar", "delhi", "agra",
            "varanasi", "rishikesh", "haridwar", "leh", "ladakh", "srinagar",
            "dharamshala", "dalhousie", "chandigarh", "mysore", "ooty",
            "kashmir", "pune", "mumbai", "bangalore", "hyderabad", "ahmedabad",
            "gandhinagar", "gurugram", "udaipur", "pushkar"
        ]

        # Simple country keyword list for trip-type detection
        self.country_keywords = [
            "india", "uae", "dubai", "abu dhabi", "singapore", "malaysia",
            "thailand", "bali", "indonesia", "nepal", "bhutan", "sri lanka",
            "vietnam", "usa", "uk", "canada", "australia"
        ]

        # Group type keywords
        self.group_map = {
            GroupType.SOLO: ["solo", "alone", "single"],
            GroupType.COUPLE: ["couple", "honeymoon", "partner", "wife", "husband"],
            GroupType.FAMILY: ["family", "parents", "kids", "children"],
            GroupType.FRIENDS: ["friends", "bros", "gang", "group of friends"],
            GroupType.GROUP: ["group", "team", "corporate"]
        }

    # -------------------------------------------------------------------------
    # MAIN PARSE
    # -------------------------------------------------------------------------
    def parse(self, query: str) -> ParsedIntent:
        q = query.strip()

        destinations = self._extract_destinations(q)
        countries = self._extract_countries(q)
        duration_days = self._extract_duration_days(q)
        budget = self._extract_budget(q)
        group_type = self._extract_group_type(q)
        group_size = self._extract_group_size(q)

        trip_type = self._determine_trip_type(destinations, countries)

        preferences = self._extract_preferences(q)
        must_include = self._extract_must_include(q)

        return ParsedIntent(
            raw_query=q,
            destinations=destinations,
            countries=countries,
            duration_days=duration_days,
            budget_per_person=budget,
            currency="INR",
            group_type=group_type,
            group_size=group_size,
            trip_type=trip_type,
            preferences=preferences,
            must_include=must_include,
            flexibility_days=2
        )

    # -------------------------------------------------------------------------
    # DESTINATIONS
    # -------------------------------------------------------------------------
    def _extract_destinations(self, query: str) -> List[str]:
        q = query.lower()

        # Extract from "Manali-Kasol" type patterns
        hyphen_matches = re.findall(r"([a-zA-Z]+(?:\s[a-zA-Z]+)*)\s*-\s*([a-zA-Z]+(?:\s[a-zA-Z]+)*)", query)
        found = []
        for a, b in hyphen_matches:
            found.append(a.strip())
            found.append(b.strip())

        # Add known places
        for place in self.known_places:
            if re.search(rf"\b{re.escape(place)}\b", q):
                found.append(place)

        # Cleanup: remove duplicates + normalize title case
        cleaned = []
        seen = set()
        for d in found:
            dd = d.strip().lower()
            if dd and dd not in seen:
                seen.add(dd)
                cleaned.append(dd.title())

        return cleaned

    # -------------------------------------------------------------------------
    # COUNTRIES
    # -------------------------------------------------------------------------
    def _extract_countries(self, query: str) -> List[str]:
        q = query.lower()
        found = []

        for word in self.country_keywords:
            if re.search(rf"\b{re.escape(word)}\b", q):
                found.append(word)

        # Normalize
        countries = []
        seen = set()
        for c in found:
            cc = c.strip().lower()
            if cc not in seen:
                seen.add(cc)
                countries.append(cc.title())

        # If only Indian cities were detected, keep India
        if countries and "India" not in countries:
            # allow international without forcing India
            return countries

        if "India" in countries:
            return ["India"]

        # If no explicit country but query has Indian cities → India
        if any(d.lower() in self.known_places for d in self._extract_destinations(query)):
            return ["India"]

        return countries

    # -------------------------------------------------------------------------
    # DURATION
    # -------------------------------------------------------------------------
    def _extract_duration_days(self, query: str) -> Optional[int]:
        q = query.lower()

        # "5 days"
        m = re.search(r"(\d+)\s*days?", q)
        if m:
            return int(m.group(1))

        # "7d"
        m = re.search(r"(\d+)\s*d\b", q)
        if m:
            return int(m.group(1))

        # "3 nights" -> approximate to nights+1 days
        m = re.search(r"(\d+)\s*nights?", q)
        if m:
            return int(m.group(1)) + 1

        return None

    # -------------------------------------------------------------------------
    # BUDGET (✅ FIXED: under/below/max/within/upto + 15k support)
    # -------------------------------------------------------------------------
    def _extract_budget(self, query: str) -> Optional[float]:
        """
        Extract budget from query.

        Supports:
        - budget 20000
        - ₹20000
        - 20k / 20 k
        - under 15000
        - below 15000
        - within 15000
        - max 15000
        - upto 15000 / up to 15000
        """
        q = query.lower().strip()

        patterns = [
            r"(?:budget|price|cost)\s*(?:is|=|:)?\s*₹?\s*([\d,]+)",
            r"(?:under|below|max|within|upto|up to)\s*₹?\s*([\d,]+)",
            r"₹\s*([\d,]+)",
            r"(\d+(?:\.\d+)?)\s*k\b",  # 15k
        ]

        for p in patterns:
            m = re.search(p, q)
            if not m:
                continue

            value = m.group(1).replace(",", "").strip()

            # if 15k
            if "k" in p:
                try:
                    return float(value) * 1000
                except:
                    continue

            try:
                return float(value)
            except:
                continue

        return None

    # -------------------------------------------------------------------------
    # GROUP TYPE
    # -------------------------------------------------------------------------
    def _extract_group_type(self, query: str) -> Optional[GroupType]:
        q = query.lower()

        for group_type, keywords in self.group_map.items():
            for kw in keywords:
                if kw in q:
                    return group_type

        return None

    # -------------------------------------------------------------------------
    # GROUP SIZE
    # -------------------------------------------------------------------------
    def _extract_group_size(self, query: str) -> Optional[int]:
        q = query.lower()
        # "4 people", "5 persons", "group of 6"
        m = re.search(r"(group of\s*)?(\d+)\s*(people|persons|members|friends)?", q)
        if m:
            val = int(m.group(2))
            # ignore tiny random numbers like "5 days" incorrectly matched
            if "days" in q and str(val) in q:
                # protect from duration collision
                # only accept group size if keyword exists
                if any(k in q for k in ["people", "persons", "members", "friends", "group of"]):
                    return val
                return None
            return val

        return None

    # -------------------------------------------------------------------------
    # TRIP TYPE
    # -------------------------------------------------------------------------
    def _determine_trip_type(self, destinations: List[str], countries: List[str]) -> TripType:
        """
        Determine domestic/international/multi-country.
        """
        # If user has multiple countries, treat as multi-country
        if len(countries) >= 2:
            return TripType.MULTI_COUNTRY

        # If explicit India or Indian cities
        if countries == ["India"]:
            return TripType.DOMESTIC

        # If countries exists but not India => international
        if len(countries) == 1 and countries[0].lower() != "india":
            return TripType.INTERNATIONAL

        # Default
        return TripType.DOMESTIC

    # -------------------------------------------------------------------------
    # PREFERENCES / MUST INCLUDE (basic placeholders)
    # -------------------------------------------------------------------------
    def _extract_preferences(self, query: str) -> List[str]:
        q = query.lower()
        prefs = []

        possible = [
            "beach", "mountains", "adventure", "trek", "luxury", "budget",
            "honeymoon", "camping", "snow", "sightseeing", "shopping"
        ]
        for p in possible:
            if p in q:
                prefs.append(p)

        return prefs

    def _extract_must_include(self, query: str) -> List[str]:
        q = query.lower()
        must = []

        # Detect simple "must include" terms
        if "breakfast" in q:
            must.append("breakfast")
        if "hotel" in q:
            must.append("hotel")
        if "cab" in q or "taxi" in q:
            must.append("cab")
        if "flight" in q:
            must.append("flight")
        if "train" in q:
            must.append("train")

        return must


# -----------------------------------------------------------------------------
# Standalone Testing
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = IntentParser()

    test_queries = [
        "i want to go manali under 15000",
        "Manali Kasol 5 days budget 20000 with friends",
        "Goa 4 days below 12k couple",
        "Dubai Abu Dhabi 6 days max 80000 with friends",
        "Rajasthan tour 7 days budget 30000 with family"
    ]

    print("\n🧠 Intent Parser Testing\n" + "=" * 70)
    for i, q in enumerate(test_queries, 1):
        intent = parser.parse(q)
        print(f"\nQuery {i}: {q}")
        print(f"  Destinations: {intent.destinations}")
        print(f"  Countries: {intent.countries}")
        print(f"  Duration: {intent.duration_days}")
        print(f"  Budget: {intent.budget_per_person}")
        print(f"  Group: {intent.group_type}")
        print(f"  Trip Type: {intent.trip_type}")
        print(f"  Preferences: {intent.preferences}")
        print(f"  Must Include: {intent.must_include}")
