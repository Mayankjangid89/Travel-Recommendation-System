"""
Trip Planner - Creates structured trip plans from parsed intent
Handles multi-city itineraries with day allocation
"""
from typing import List, Dict, Any
from agents.models import ParsedIntent, TripType, GroupType, TripPlan
import logging

logger = logging.getLogger(__name__)


class TripPlanner:
    """
    Create structured trip plans with multi-leg support
    """
    
    def create_plan(self, intent: ParsedIntent) -> TripPlan:
        """
        Create a trip plan from parsed intent
        
        Args:
            intent: Parsed user intent
            
        Returns:
            TripPlan with legs and day allocation
        """
        destinations = intent.destinations
        total_days = intent.duration_days or self._estimate_days(destinations)
        
        if len(destinations) == 0:
            logger.warning("No destinations found, creating empty plan")
            return TripPlan(total_days=total_days, legs=[])
        
        if len(destinations) == 1:
            # Single destination
            return TripPlan(
                total_days=total_days,
                legs=[{
                    "cities": destinations,
                    "days": total_days,
                    "country": intent.countries[0] if intent.countries else "India"
                }]
            )
        
        # Multi-city trip: allocate days proportionally
        legs = self._create_multi_city_legs(destinations, total_days, intent.countries)
        
        return TripPlan(total_days=total_days, legs=legs)
    
    def _estimate_days(self, destinations: List[str]) -> int:
        """
        Estimate trip duration based on number of destinations
        Default: 3 days per destination, minimum 5 days
        """
        if len(destinations) == 0:
            return 5
        elif len(destinations) == 1:
            return 5
        else:
            return max(5, len(destinations) * 3)
    
    def _create_multi_city_legs(
        self, 
        destinations: List[str], 
        total_days: int,
        countries: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create legs for multi-city trip with smart day allocation
        
        Strategy:
        1. If destinations have natural groupings (nearby cities), group them
        2. Allocate more days to major destinations
        3. Allocate fewer days to smaller towns
        """
        if len(destinations) <= 1:
            return [{
                "cities": destinations,
                "days": total_days,
                "country": countries[0] if countries else "India"
            }]
        
        # Check for natural groupings (for now, simple split)
        # Future: Add geographic proximity logic
        legs = self._split_into_legs(destinations, total_days, countries)
        
        return legs
    
    def _split_into_legs(
        self,
        destinations: List[str],
        total_days: int,
        countries: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Split destinations into logical legs
        
        For now: Each destination is a leg with proportional days
        Future: Group nearby cities, use geographic data
        """
        num_destinations = len(destinations)
        
        # Base allocation: divide days equally
        base_days = total_days // num_destinations
        remaining_days = total_days % num_destinations
        
        legs = []
        for i, city in enumerate(destinations):
            # Give extra days to first destinations
            days = base_days + (1 if i < remaining_days else 0)
            days = max(1, days)  # Minimum 1 day per destination
            
            # Determine country for this city
            country = self._get_country_for_city(city, countries)
            
            legs.append({
                "cities": [city],
                "days": days,
                "country": country
            })
        
        return legs
    
    def _get_country_for_city(self, city: str, countries: List[str]) -> str:
        """
        Determine which country a city belongs to
        """
        # Simple mapping (expand as needed)
        city_lower = city.lower()
        
        international_cities = {
            'dubai': 'UAE',
            'abu dhabi': 'UAE',
            'sharjah': 'UAE',
            'bangkok': 'Thailand',
            'phuket': 'Thailand',
            'pattaya': 'Thailand',
            'singapore': 'Singapore',
            'kuala lumpur': 'Malaysia',
            'male': 'Maldives',
            'maldives': 'Maldives',
            'colombo': 'Sri Lanka',
            'kathmandu': 'Nepal',
            'pokhara': 'Nepal',
            'bali': 'Indonesia',
            'paris': 'France',
            'london': 'UK',
            'new york': 'USA'
        }
        
        if city_lower in international_cities:
            return international_cities[city_lower]
        
        # Default to first country in list or India
        if countries:
            return countries[0]
        return 'India'
    
    def get_plan_summary(self, plan: TripPlan) -> str:
        """
        Generate human-readable summary of trip plan
        
        Returns:
            Summary string
        """
        if not plan.legs:
            return f"{plan.total_days}-day trip (destinations to be determined)"
        
        summary_parts = []
        for i, leg in enumerate(plan.legs, 1):
            cities = ", ".join(leg["cities"])
            days = leg["days"]
            country = leg.get("country", "")
            
            if len(plan.legs) > 1:
                summary_parts.append(f"Leg {i}: {cities} ({country}) - {days} days")
            else:
                summary_parts.append(f"{cities} ({country}) - {days} days")
        
        return " → ".join(summary_parts)


# Example usage and testing
if __name__ == "__main__":
    from agents.intent_parser import IntentParser
    
    parser = IntentParser()
    planner = TripPlanner()
    
    # Test queries
    test_queries = [
        "I want to go Manali-Kasol-Amritsar for 7 days, budget 15000 per person",
        "India → Abu Dhabi → Dubai → India, 8 days",
        "Goa beach vacation for 5 days",
        "Kerala backwaters for 6 days"
    ]
    
    print("🗺️ Trip Planner Testing\n")
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        
        # Parse intent
        intent = parser.parse(query)
        
        # Create plan
        plan = planner.create_plan(intent)
        
        print(f"  Total Days: {plan.total_days}")
        print(f"  Legs: {len(plan.legs)}")
        for j, leg in enumerate(plan.legs, 1):
            print(f"    Leg {j}: {leg}")
        
        print(f"  Summary: {planner.get_plan_summary(plan)}")
        print()