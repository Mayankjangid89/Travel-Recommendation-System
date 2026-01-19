"""
Unit tests for Trip Planner
"""
import pytest
from agents.planner import TripPlanner
from agents.models import ParsedIntent, TripType


@pytest.fixture
def planner():
    """Create planner instance for tests"""
    return TripPlanner()


class TestSingleDestination:
    """Test single destination planning"""
    
    def test_single_city_plan(self, planner):
        intent = ParsedIntent(
            raw_query="Goa 5 days",
            destinations=["Goa"],
            countries=["India"],
            duration_days=5,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        assert plan.total_days == 5
        assert len(plan.legs) == 1
        assert plan.legs[0]["cities"] == ["Goa"]
        assert plan.legs[0]["days"] == 5


class TestMultiCityPlan:
    """Test multi-city planning"""
    
    def test_three_cities(self, planner):
        intent = ParsedIntent(
            raw_query="Manali Kasol Amritsar",
            destinations=["Manali", "Kasol", "Amritsar"],
            countries=["India"],
            duration_days=7,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        assert plan.total_days == 7
        assert len(plan.legs) == 3
        
        # Total days should equal sum of leg days
        total_leg_days = sum(leg["days"] for leg in plan.legs)
        assert total_leg_days == 7
    
    def test_two_cities(self, planner):
        intent = ParsedIntent(
            raw_query="Delhi Agra 3 days",
            destinations=["Delhi", "Agra"],
            countries=["India"],
            duration_days=3,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        assert plan.total_days == 3
        assert len(plan.legs) == 2
        assert all(leg["days"] >= 1 for leg in plan.legs)


class TestInternationalPlan:
    """Test international trip planning"""
    
    def test_multi_country_plan(self, planner):
        intent = ParsedIntent(
            raw_query="Dubai Abu Dhabi 8 days",
            destinations=["Dubai", "Abu Dhabi"],
            countries=["UAE"],
            duration_days=8,
            trip_type=TripType.INTERNATIONAL
        )
        
        plan = planner.create_plan(intent)
        
        assert plan.total_days == 8
        assert len(plan.legs) == 2
        assert plan.legs[0]["country"] == "UAE"
        assert plan.legs[1]["country"] == "UAE"


class TestDayAllocation:
    """Test day allocation logic"""
    
    def test_equal_distribution(self, planner):
        intent = ParsedIntent(
            raw_query="4 cities 8 days",
            destinations=["City1", "City2", "City3", "City4"],
            countries=["India"],
            duration_days=8,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        # 8 days / 4 cities = 2 days each
        assert all(leg["days"] == 2 for leg in plan.legs)
    
    def test_uneven_distribution(self, planner):
        intent = ParsedIntent(
            raw_query="3 cities 7 days",
            destinations=["City1", "City2", "City3"],
            countries=["India"],
            duration_days=7,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        # 7 days / 3 cities = 2 days base + 1 extra for first city
        total_days = sum(leg["days"] for leg in plan.legs)
        assert total_days == 7
        assert all(leg["days"] >= 2 for leg in plan.legs)


class TestEstimation:
    """Test duration estimation"""
    
    def test_estimate_for_no_duration(self, planner):
        intent = ParsedIntent(
            raw_query="Goa",
            destinations=["Goa"],
            countries=["India"],
            duration_days=None,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        # Should estimate minimum 5 days
        assert plan.total_days >= 5
    
    def test_estimate_for_multiple_cities(self, planner):
        intent = ParsedIntent(
            raw_query="3 cities",
            destinations=["City1", "City2", "City3"],
            countries=["India"],
            duration_days=None,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        
        # Should estimate ~3 days per city
        assert plan.total_days >= len(intent.destinations) * 2


class TestPlanSummary:
    """Test plan summary generation"""
    
    def test_single_leg_summary(self, planner):
        intent = ParsedIntent(
            raw_query="Goa 5 days",
            destinations=["Goa"],
            countries=["India"],
            duration_days=5,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        summary = planner.get_plan_summary(plan)
        
        assert "Goa" in summary
        assert "5 days" in summary
    
    def test_multi_leg_summary(self, planner):
        intent = ParsedIntent(
            raw_query="Manali Kasol 6 days",
            destinations=["Manali", "Kasol"],
            countries=["India"],
            duration_days=6,
            trip_type=TripType.DOMESTIC
        )
        
        plan = planner.create_plan(intent)
        summary = planner.get_plan_summary(plan)
        
        assert "Manali" in summary
        assert "Kasol" in summary
        assert "→" in summary  # Arrow separator for multi-leg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])