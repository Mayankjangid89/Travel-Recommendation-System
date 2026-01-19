"""
Unit tests for Intent Parser
"""
import pytest
from agents.intent_parser import IntentParser
from agents.models import TripType, GroupType


@pytest.fixture
def parser():
    """Create parser instance for tests"""
    return IntentParser()


class TestDestinationExtraction:
    """Test destination extraction"""
    
    def test_single_destination(self, parser):
        query = "I want to visit Goa for 5 days"
        intent = parser.parse(query)
        assert "Goa" in intent.destinations
        assert len(intent.destinations) == 1
    
    def test_multiple_destinations(self, parser):
        query = "Manali-Kasol-Amritsar trip"
        intent = parser.parse(query)
        assert "Manali" in intent.destinations
        assert "Kasol" in intent.destinations
        assert "Amritsar" in intent.destinations
        assert len(intent.destinations) == 3
    
    def test_international_destinations(self, parser):
        query = "Dubai and Abu Dhabi tour"
        intent = parser.parse(query)
        assert "Dubai" in intent.destinations
        assert "Abu Dhabi" in intent.destinations


class TestDurationExtraction:
    """Test duration extraction"""
    
    def test_days_format(self, parser):
        query = "7 days trip to Kerala"
        intent = parser.parse(query)
        assert intent.duration_days == 7
    
    def test_day_format(self, parser):
        query = "5-day vacation in Goa"
        intent = parser.parse(query)
        assert intent.duration_days == 5
    
    def test_for_days_format(self, parser):
        query = "Trip for 10 days"
        intent = parser.parse(query)
        assert intent.duration_days == 10
    
    def test_no_duration(self, parser):
        query = "Visit Manali"
        intent = parser.parse(query)
        assert intent.duration_days is None


class TestBudgetExtraction:
    """Test budget extraction"""
    
    def test_budget_with_number(self, parser):
        query = "budget 15000 per person"
        intent = parser.parse(query)
        assert intent.budget_per_person == 15000
    
    def test_budget_with_k(self, parser):
        query = "budget 25k"
        intent = parser.parse(query)
        assert intent.budget_per_person == 25000
    
    def test_budget_with_inr(self, parser):
        query = "INR 50000 budget"
        intent = parser.parse(query)
        assert intent.budget_per_person == 50000
    
    def test_budget_with_comma(self, parser):
        query = "budget 1,50,000"
        intent = parser.parse(query)
        assert intent.budget_per_person == 150000
    
    def test_no_budget(self, parser):
        query = "Visit Goa"
        intent = parser.parse(query)
        assert intent.budget_per_person is None


class TestGroupTypeExtraction:
    """Test group type extraction"""
    
    def test_solo_trip(self, parser):
        query = "Solo trip to Ladakh"
        intent = parser.parse(query)
        assert intent.group_type == GroupType.SOLO
    
    def test_couple_trip(self, parser):
        query = "Honeymoon package to Maldives"
        intent = parser.parse(query)
        assert intent.group_type == GroupType.COUPLE
    
    def test_family_trip(self, parser):
        query = "Family vacation with kids"
        intent = parser.parse(query)
        assert intent.group_type == GroupType.FAMILY
    
    def test_friends_trip(self, parser):
        query = "Trip with friends"
        intent = parser.parse(query)
        assert intent.group_type == GroupType.FRIENDS


class TestTripTypeDetection:
    """Test trip type detection"""
    
    def test_domestic_trip(self, parser):
        query = "Manali Kasol 7 days"
        intent = parser.parse(query)
        assert intent.trip_type == TripType.DOMESTIC
    
    def test_international_trip(self, parser):
        query = "Dubai vacation"
        intent = parser.parse(query)
        assert intent.trip_type == TripType.INTERNATIONAL
    
    def test_multi_country_trip(self, parser):
        query = "India to Dubai to Abu Dhabi"
        intent = parser.parse(query)
        assert intent.trip_type == TripType.MULTI_COUNTRY


class TestPreferencesExtraction:
    """Test preferences extraction"""
    
    def test_adventure_preference(self, parser):
        query = "Adventure trekking trip"
        intent = parser.parse(query)
        assert "adventure" in intent.preferences
    
    def test_luxury_preference(self, parser):
        query = "Luxury 5-star hotel package"
        intent = parser.parse(query)
        assert "luxury" in intent.preferences
    
    def test_budget_preference(self, parser):
        query = "Budget affordable trip"
        intent = parser.parse(query)
        assert "budget" in intent.preferences
    
    def test_beach_preference(self, parser):
        query = "Beach vacation in Goa"
        intent = parser.parse(query)
        assert "beach" in intent.preferences


class TestMustInclude:
    """Test must-include extraction"""
    
    def test_flights_included(self, parser):
        query = "Package with flights"
        intent = parser.parse(query)
        assert "flights" in intent.must_include
    
    def test_meals_included(self, parser):
        query = "Hotel with breakfast and dinner"
        intent = parser.parse(query)
        assert "meals" in intent.must_include
    
    def test_visa_included(self, parser):
        query = "Dubai package with visa"
        intent = parser.parse(query)
        assert "visa" in intent.must_include


class TestCompleteQueries:
    """Test complete real-world queries"""
    
    def test_complex_domestic_query(self, parser):
        query = "I want to go Manali-Kasol-Amritsar for 7 days, budget 15000 per person, with friends"
        intent = parser.parse(query)
        
        assert "Manali" in intent.destinations
        assert "Kasol" in intent.destinations
        assert "Amritsar" in intent.destinations
        assert intent.duration_days == 7
        assert intent.budget_per_person == 15000
        assert intent.group_type == GroupType.FRIENDS
        assert intent.trip_type == TripType.DOMESTIC
    
    def test_complex_international_query(self, parser):
        query = "India → Abu Dhabi → Dubai → India, 8 days, budget 80000 INR, with friends"
        intent = parser.parse(query)
        
        assert "Abu Dhabi" in intent.destinations
        assert "Dubai" in intent.destinations
        assert intent.duration_days == 8
        assert intent.budget_per_person == 80000
        assert intent.group_type == GroupType.FRIENDS
        assert intent.trip_type == TripType.MULTI_COUNTRY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])