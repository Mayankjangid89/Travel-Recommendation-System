"""
Database models for Travel AI Agent
Stores agencies, packages, and scraping metadata
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    JSON, Text, Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Agency(Base):
    """Travel agency information"""
    __tablename__ = "agencies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    url = Column(Text, nullable=False)
    
    # Agency metadata
    country = Column(String(100))
    city = Column(String(100))
    agency_type = Column(String(50))  # 'local', 'national', 'international'
    
    # Trust signals
    is_verified = Column(Boolean, default=False)
    trust_score = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Discovery metadata
    discovery_source = Column(String(100))  # 'manual', 'google', 'directory'
    discovery_date = Column(DateTime, default=datetime.utcnow)
    
    # Scraping configuration
    scraping_enabled = Column(Boolean, default=True)
    requires_js = Column(Boolean, default=False)
    last_scraped_at = Column(DateTime, nullable=True)
    scrape_success_count = Column(Integer, default=0)
    scrape_failure_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    packages = relationship("TravelPackage", back_populates="agency", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_agency_active_domain', 'is_active', 'domain'),
    )


class TravelPackage(Base):
    """Normalized travel package data"""
    __tablename__ = "travel_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'), nullable=False, index=True)
    
    # Package details
    package_title = Column(String(500), nullable=False)
    package_id_external = Column(String(255))  # ID from source website
    url = Column(Text, nullable=False)
    
    # Pricing
    price_in_inr = Column(Float, nullable=False, index=True)
    original_price = Column(Float, nullable=True)
    currency = Column(String(10), default='INR')
    price_per_person = Column(Boolean, default=True)
    
    # Trip details
    duration_days = Column(Integer, nullable=False, index=True)
    duration_nights = Column(Integer, nullable=True)
    
    # Destinations (JSON array of cities/places)
    destinations = Column(JSON, nullable=False)  # ["Manali", "Kasol", "Amritsar"]
    countries = Column(JSON, nullable=True)  # ["India", "UAE"]
    
    # Package features
    inclusions = Column(JSON, nullable=True)  # ["Hotel", "Meals", "Transport"]
    exclusions = Column(JSON, nullable=True)  # ["Flights", "Visa"]
    highlights = Column(JSON, nullable=True)  # Key selling points
    
    # Itinerary (day-wise breakdown)
    itinerary_daywise = Column(JSON, nullable=True)
    # Format: [{"day": 1, "title": "Arrival", "activities": [...], "meals": [...]}]
    
    # Quality signals
    rating = Column(Float, nullable=True)  # 0.0 to 5.0
    reviews_count = Column(Integer, default=0)
    hotel_star = Column(String(10), nullable=True)  # "3-star", "4-star"
    transport_type = Column(String(100), nullable=True)  # "Private Car", "Flight"
    
    # Additional metadata
    group_size_min = Column(Integer, nullable=True)
    group_size_max = Column(Integer, nullable=True)
    best_for = Column(JSON, nullable=True)  # ["couples", "families", "friends"]
    
    # Scraping metadata
    source_confidence_score = Column(Float, default=0.5)  # Data quality confidence
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agency = relationship("Agency", back_populates="packages")
    
    __table_args__ = (
        Index('idx_package_destinations', 'destinations', postgresql_using='gin'),
        Index('idx_package_price_duration', 'price_in_inr', 'duration_days'),
        Index('idx_package_active_scraped', 'is_active', 'scraped_at'),
        UniqueConstraint('agency_id', 'package_id_external', name='uq_agency_package'),
    )


class ScrapingJob(Base):
    """Track scraping job execution"""
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    
    agency_id = Column(Integer, ForeignKey('agencies.id'), nullable=True)
    job_type = Column(String(50), nullable=False)  # 'agency_discovery', 'package_scrape'
    
    status = Column(String(50), nullable=False, index=True)  # 'pending', 'running', 'completed', 'failed'
    
    # Execution details
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results
    packages_found = Column(Integer, default=0)
    packages_stored = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_job_status_created', 'status', 'created_at'),
    )


class UserQuery(Base):
    """Store user queries for analytics and improvement"""
    __tablename__ = "user_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Query details
    raw_query = Column(Text, nullable=False)
    parsed_intent = Column(JSON, nullable=True)
    
    # Results
    packages_returned = Column(Integer, default=0)
    response_time_ms = Column(Float, nullable=True)
    
    # User feedback (if available)
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_query_created', 'created_at'),
    )