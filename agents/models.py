"""
Pydantic models for API requests/responses and internal data structures
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class TripType(str, Enum):
    """Type of trip"""
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    MULTI_COUNTRY = "multi_country"


class GroupType(str, Enum):
    """Who is traveling"""
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    FRIENDS = "friends"
    GROUP = "group"


class ParsedIntent(BaseModel):
    """
    Structured intent extracted from user query
    """
    raw_query: str
    destinations: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    duration_days: Optional[int] = None
    budget_per_person: Optional[float] = None
    currency: str = "INR"
    group_type: Optional[GroupType] = None
    group_size: Optional[int] = None
    trip_type: TripType = TripType.DOMESTIC
    preferences: List[str] = Field(default_factory=list)  # ["adventure", "luxury", "budget"]
    must_include: List[str] = Field(default_factory=list)  # ["hotel", "meals", "visa"]
    flexibility_days: int = 2  # +/- days flexibility


class TripPlan(BaseModel):
    """
    Multi-city trip structure
    """
    total_days: int
    legs: List[Dict[str, Any]] = Field(default_factory=list)
    # Format: [{"cities": ["Manali", "Kasol"], "days": 4}, {"cities": ["Amritsar"], "days": 3}]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_days": 7,
                "legs": [
                    {"cities": ["Manali", "Kasol"], "days": 4},
                    {"cities": ["Amritsar"], "days": 3}
                ]
            }
        }


class PackageInclusion(BaseModel):
    """What's included in package"""
    category: str  # "accommodation", "meals", "transport", "activities", "visa"
    details: str
    included: bool = True


class DayItinerary(BaseModel):
    """Single day itinerary"""
    day: int
    title: str
    description: Optional[str] = None
    activities: List[str] = Field(default_factory=list)
    meals: List[str] = Field(default_factory=list)
    accommodation: Optional[str] = None


class TravelPackageSchema(BaseModel):
    """
    Normalized travel package (matches DB model)
    """
    id: Optional[int] = None
    agency_name: str
    package_title: str
    url: str
    
    # Pricing
    price_in_inr: float
    original_price: Optional[float] = None
    currency: str = "INR"
    price_per_person: bool = True
    
    # Trip details
    duration_days: int
    duration_nights: Optional[int] = None
    destinations: List[str]
    countries: List[str] = Field(default_factory=list)
    
    # Features
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    
    # Itinerary
    itinerary_daywise: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Quality signals
    rating: Optional[float] = None
    reviews_count: int = 0
    hotel_star: Optional[str] = None
    transport_type: Optional[str] = None
    
    # Metadata
    source_confidence_score: float = 0.5
    scraped_at: datetime
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v
    
    class Config:
        from_attributes = True


class RankedPackage(BaseModel):
    """
    Package with ranking score and explanation
    """
    package: TravelPackageSchema
    rank: int
    total_score: float
    score_breakdown: Dict[str, float]
    match_explanation: str
    booking_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "total_score": 0.87,
                "score_breakdown": {
                    "destination_match": 0.95,
                    "duration_match": 0.85,
                    "budget_match": 0.90,
                    "trust_score": 0.80,
                    "reviews": 0.75
                },
                "match_explanation": "Perfect match for Manali-Kasol trip with your budget"
            }
        }


class RecommendationRequest(BaseModel):
    """
    API request for package recommendations
    """
    query: str = Field(..., min_length=10, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)
    include_explanation: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "I want to go Manali-Kasol-Amritsar for 7 days, budget 15000 per person, with friends",
                "max_results": 5,
                "include_explanation": True
            }
        }


class RecommendationResponse(BaseModel):
    """
    API response with ranked packages
    """
    query_id: str
    parsed_intent: ParsedIntent
    trip_plan: TripPlan
    ranked_packages: List[RankedPackage]
    total_found: int
    assistant_message: str
    processing_time_ms: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "q_1234567890",
                "total_found": 42,
                "assistant_message": "I found 5 excellent packages for your Manali-Kasol-Amritsar trip...",
                "processing_time_ms": 234.5
            }
        }


class AgencySchema(BaseModel):
    """Agency information"""
    id: Optional[int] = None
    name: str
    domain: str
    url: str
    country: Optional[str] = None
    city: Optional[str] = None
    trust_score: float = 0.5
    is_verified: bool = False
    scraping_enabled: bool = True
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    database: str
    redis: str
    total_agencies: int
    total_packages: int
    last_scrape: Optional[datetime] = None
    