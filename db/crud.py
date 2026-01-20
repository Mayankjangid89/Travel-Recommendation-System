"""
CRUD Operations - Create, Read, Update, Delete for database
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import logging

from db.models import Agency, TravelPackage, ScrapingJob, UserQuery

logger = logging.getLogger(__name__)


# ============================================================================
# AGENCY CRUD OPERATIONS
# ============================================================================

def create_agency(
    db: Session,
    name: str,
    domain: str,
    url: str,
    **kwargs
) -> Agency:
    """
    Create a new agency
    
    Args:
        db: Database session
        name: Agency name
        domain: Domain name (e.g., 'example.com')
        url: Full URL
        **kwargs: Additional fields (country, city, trust_score, etc.)
    
    Returns:
        Created Agency object
    """
    agency = Agency(
        name=name,
        domain=domain,
        url=url,
        **kwargs
    )
    db.add(agency)
    db.commit()
    db.refresh(agency)
    
    logger.info(f"✅ Created agency: {name} ({domain})")
    return agency


def get_agency_by_domain(db: Session, domain: str) -> Optional[Agency]:
    """Get agency by domain"""
    return db.query(Agency).filter(Agency.domain == domain).first()


def get_agency_by_id(db: Session, agency_id: int) -> Optional[Agency]:
    """Get agency by ID"""
    return db.query(Agency).filter(Agency.id == agency_id).first()


def get_all_agencies(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> List[Agency]:
    """
    Get all agencies with pagination
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return
        active_only: Only return active agencies
    
    Returns:
        List of Agency objects
    """
    query = db.query(Agency)
    
    if active_only:
        query = query.filter(Agency.is_active == True)
    
    return query.offset(skip).limit(limit).all()


def update_agency_scrape_status(
    db: Session,
    agency_id: int,
    success: bool,
    packages_found: int = 0
) -> Optional[Agency]:
    """
    Update agency scraping statistics
    
    Args:
        db: Database session
        agency_id: Agency ID
        success: Whether scraping was successful
        packages_found: Number of packages found
    
    Returns:
        Updated Agency object
    """
    agency = get_agency_by_id(db, agency_id)
    if not agency:
        return None
    
    agency.last_scraped_at = datetime.utcnow()
    
    if success:
        agency.scrape_success_count += 1
    else:
        agency.scrape_failure_count += 1
    
    db.commit()
    db.refresh(agency)
    
    logger.info(f"✅ Updated scrape status for {agency.name}: success={success}, packages={packages_found}")
    return agency


def get_agencies_needing_scrape(
    db: Session,
    hours_since_last_scrape: int = 24
) -> List[Agency]:
    """
    Get agencies that need to be scraped
    
    Args:
        db: Database session
        hours_since_last_scrape: Minimum hours since last scrape
    
    Returns:
        List of agencies needing scrape
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_since_last_scrape)
    
    return db.query(Agency).filter(
        and_(
            Agency.is_active == True,
            Agency.scraping_enabled == True,
            or_(
                Agency.last_scraped_at == None,
                Agency.last_scraped_at < cutoff_time
            )
        )
    ).all()


# ============================================================================
# PACKAGE CRUD OPERATIONS
# ============================================================================

def create_package(
    db: Session,
    agency_id: int,
    package_data: Dict[str, Any]
) -> TravelPackage:
    """
    Create a new travel package
    
    Args:
        db: Database session
        agency_id: Agency ID
        package_data: Package information dict
    
    Returns:
        Created TravelPackage object
    """
    package = TravelPackage(
        agency_id=agency_id,
        **package_data
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    logger.info(f"✅ Created package: {package.package_title} (₹{package.price_in_inr})")
    return package


def bulk_create_packages(db, agency_id: int, packages: list[dict]) -> int:
    created = 0

    for pkg_data in packages:
        # ✅ remove duplicate agency_id if present
        pkg_data.pop("agency_id", None)

        # ✅ Check for duplicates (Phase 3 Fix)
        # Strategy: agency_id + url OR agency_id + package_title + duration_days
        
        query = db.query(TravelPackage).filter(TravelPackage.agency_id == agency_id)
        
        # 1. Check by URL
        if pkg_data.get("url") and len(pkg_data["url"]) > 10:
             existing_url = query.filter(TravelPackage.url == pkg_data["url"]).first()
             if existing_url:
                 continue

        # 2. Check by Title + Duration
        if pkg_data.get("package_title"):
            existing_title = query.filter(
                TravelPackage.package_title == pkg_data["package_title"],
                TravelPackage.duration_days == pkg_data.get("duration_days", 0)
            ).first()
            if existing_title:
                continue

        # ✅ create package properly
        package = TravelPackage(
            agency_id=agency_id,
            **pkg_data
        )

        db.add(package)
        created += 1

    if created > 0:
        db.commit()
    
    return created
    

def search_packages(
    db: Session,
    destinations: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_days: Optional[int] = None,
    max_days: Optional[int] = None,
    skip: int = 0,
    limit: int = 50
) -> List[TravelPackage]:
    """
    Search packages with filters
    
    Args:
        db: Database session
        destinations: List of destination cities
        min_price: Minimum price in INR
        max_price: Maximum price in INR
        min_days: Minimum duration
        max_days: Maximum duration
        skip: Pagination offset
        limit: Maximum results
    
    Returns:
        List of matching packages
    """
    query = db.query(TravelPackage).filter(TravelPackage.is_active == True)
    
    # Filter by destinations (check if any destination matches)
    if destinations:
        # For JSON column, we need to check if array contains any of the destinations
        # This is database-specific; for SQLite we'll do a simple text search
        destination_filters = []
        for dest in destinations:
            destination_filters.append(
                TravelPackage.destinations.contains([dest])
            )
        if destination_filters:
            query = query.filter(or_(*destination_filters))
    
    # Price filters
    if min_price is not None:
        query = query.filter(TravelPackage.price_in_inr >= min_price)
    if max_price is not None:
        query = query.filter(TravelPackage.price_in_inr <= max_price)
    
    # Duration filters
    if min_days is not None:
        query = query.filter(TravelPackage.duration_days >= min_days)
    if max_days is not None:
        query = query.filter(TravelPackage.duration_days <= max_days)
    
    # Sort by price (cheapest first)
    query = query.order_by(TravelPackage.price_in_inr)
    
    return query.offset(skip).limit(limit).all()


def get_package_by_id(db: Session, package_id: int) -> Optional[TravelPackage]:
    """Get package by ID"""
    return db.query(TravelPackage).filter(TravelPackage.id == package_id).first()


def get_packages_by_agency(
    db: Session,
    agency_id: int,
    active_only: bool = True
) -> List[TravelPackage]:
    """Get all packages from a specific agency"""
    query = db.query(TravelPackage).filter(TravelPackage.agency_id == agency_id)
    
    if active_only:
        query = query.filter(TravelPackage.is_active == True)
    
    return query.all()


def deactivate_old_packages(
    db: Session,
    agency_id: int,
    days_old: int = 30
) -> int:
    """
    Deactivate packages older than X days
    
    Args:
        db: Database session
        agency_id: Agency ID
        days_old: Age threshold in days
    
    Returns:
        Number of packages deactivated
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    updated = db.query(TravelPackage).filter(
        and_(
            TravelPackage.agency_id == agency_id,
            TravelPackage.scraped_at < cutoff_date,
            TravelPackage.is_active == True
        )
    ).update({"is_active": False})
    
    db.commit()
    
    logger.info(f"✅ Deactivated {updated} old packages for agency {agency_id}")
    return updated


# ============================================================================
# SCRAPING JOB OPERATIONS
# ============================================================================

def create_scraping_job(
    db: Session,
    job_id: str,
    agency_id: Optional[int] = None,
    job_type: str = "package_scrape"
) -> ScrapingJob:
    """Create a new scraping job"""
    job = ScrapingJob(
        job_id=job_id,
        agency_id=agency_id,
        job_type=job_type,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return job


def update_scraping_job(
    db: Session,
    job_id: str,
    status: str,
    packages_found: int = 0,
    packages_stored: int = 0,
    error_message: Optional[str] = None
) -> Optional[ScrapingJob]:
    """Update scraping job status"""
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    
    if not job:
        return None
    
    job.status = status
    job.packages_found = packages_found
    job.packages_stored = packages_stored
    
    if error_message:
        job.error_message = error_message
    
    if status == "running" and not job.started_at:
        job.started_at = datetime.utcnow()
    
    if status in ["completed", "failed"]:
        job.completed_at = datetime.utcnow()
        if job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            job.duration_seconds = duration
    
    db.commit()
    db.refresh(job)
    
    return job


# ============================================================================
# USER QUERY OPERATIONS
# ============================================================================

def log_user_query(
    db: Session,
    query_id: str,
    raw_query: str,
    parsed_intent: Optional[Dict] = None,
    packages_returned: int = 0,
    response_time_ms: Optional[float] = None
) -> UserQuery:
    """Log a user query for analytics"""
    user_query = UserQuery(
        query_id=query_id,
        raw_query=raw_query,
        parsed_intent=parsed_intent,
        packages_returned=packages_returned,
        response_time_ms=response_time_ms
    )
    db.add(user_query)
    db.commit()
    db.refresh(user_query)
    
    return user_query


# ============================================================================
# STATISTICS & ANALYTICS
# ============================================================================


def get_db_stats(db: Session) -> Dict[str, Any]:
    """
    Returns quick database stats for health check API
    """
    return {
        "total_agencies": db.query(Agency).count(),
        "active_agencies": db.query(Agency).filter(Agency.is_active == True).count(),
        "total_packages": db.query(TravelPackage).count(),
        "active_packages": db.query(TravelPackage).filter(TravelPackage.is_active == True).count(),
        "total_jobs": db.query(ScrapingJob).count()
    }

# ---------------------------
# AGENCY READ OPERATIONS
# ---------------------------

def get_agencies(db: Session, skip: int = 0, limit: int = 50) -> List[Agency]:
    """
    Fetch all agencies
    """
    return (
        db.query(Agency)
        .offset(skip)
        .limit(limit)
        .all()
    )
