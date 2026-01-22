"""
Database CRUD operations (Agencies, Packages, Stats, Scrape Jobs)
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from db.models import Agency, TravelPackage, ScrapingJob
from typing import Optional, List     
from sqlalchemy import or_

# =============================================================================
# AGENCY CRUD
# =============================================================================

def create_agency(
    db: Session,
    name: str,
    domain: str,
    url: str,
    country: str = "India",
    city: str = "",
    agency_type: str = "private",
    trust_score: float = 0.6,
    is_verified: bool = False,
    scraping_enabled: bool = True,
):
    agency = Agency(
        name=name,
        domain=domain,
        url=url,
        country=country,
        city=city,
        agency_type=agency_type,
        trust_score=trust_score,
        is_verified=is_verified,
        scraping_enabled=scraping_enabled,
        created_at=datetime.utcnow(),
    )

    db.add(agency)
    db.commit()
    db.refresh(agency)
    return agency


def get_agency_by_domain(db: Session, domain: str) -> Optional[Agency]:
    return db.query(Agency).filter(Agency.domain == domain).first()


def get_all_agencies(db: Session, limit: int = 100, active_only: bool = True) -> List[Agency]:
    query = db.query(Agency)

    if active_only:
        query = query.filter(Agency.scraping_enabled == True)

    return query.limit(limit).all()


# =============================================================================
# PACKAGE CRUD
# =============================================================================

def create_package(db: Session, agency_id: int, pkg_data: Dict[str, Any]) -> TravelPackage:
    """
    Create ONE travel package row linked to an agency.
    """

    pkg_data = dict(pkg_data)  # safe copy

    # ✅ Ensure agency_id exists
    pkg_data.pop("agency_id", None)

    package = TravelPackage(
        agency_id=agency_id,
        package_title=pkg_data.get("package_title", ""),
        url=pkg_data.get("url", ""),
        price_in_inr=pkg_data.get("price_in_inr", 0.0) or 0.0,
        duration_days=pkg_data.get("duration_days", 0) or 0,
        duration_nights=pkg_data.get("duration_nights", 0) or 0,
        destinations=pkg_data.get("destinations", []) or [],
        countries=pkg_data.get("countries", ["India"]) or ["India"],
        inclusions=pkg_data.get("inclusions", []) or [],
        exclusions=pkg_data.get("exclusions", []) or [],
        highlights=pkg_data.get("highlights", []) or [],
        rating=pkg_data.get("rating", None),
        reviews_count=pkg_data.get("reviews_count", 0) or 0,
        source_confidence_score=pkg_data.get("source_confidence_score", 0.6) or 0.6,
        scraped_at=pkg_data.get("scraped_at", datetime.utcnow()),
        is_active=pkg_data.get("is_active", True),
        created_at=datetime.utcnow(),
    )

    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def bulk_create_packages(db: Session, agency_id: int, packages: List[Dict[str, Any]]) -> int:
    """
    Bulk insert packages (fast)
    Returns count stored.
    """

    if not packages:
        return 0

    count = 0

    for pkg_data in packages:
        try:
            pkg_data = dict(pkg_data)
            pkg_data.pop("agency_id", None)

            package = TravelPackage(
                agency_id=agency_id,
                package_title=pkg_data.get("package_title", ""),
                url=pkg_data.get("url", ""),
                price_in_inr=pkg_data.get("price_in_inr", 0.0) or 0.0,
                duration_days=pkg_data.get("duration_days", 0) or 0,
                duration_nights=pkg_data.get("duration_nights", 0) or 0,
                destinations=pkg_data.get("destinations", []) or [],
                countries=pkg_data.get("countries", ["India"]) or ["India"],
                inclusions=pkg_data.get("inclusions", []) or [],
                exclusions=pkg_data.get("exclusions", []) or [],
                highlights=pkg_data.get("highlights", []) or [],
                rating=pkg_data.get("rating", None),
                reviews_count=pkg_data.get("reviews_count", 0) or 0,
                source_confidence_score=pkg_data.get("source_confidence_score", 0.6) or 0.6,
                scraped_at=pkg_data.get("scraped_at", datetime.utcnow()),
                is_active=pkg_data.get("is_active", True),
                created_at=datetime.utcnow(),
            )

            db.add(package)
            count += 1

        except Exception as e:
            # skip bad package
            print(f"⚠️ Skipping bad package: {e}")

    db.commit()
    return count


def search_packages(
    db: Session,
    destinations: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_days: Optional[int] = None,
    max_days: Optional[int] = None,
    skip: int = 0,
    limit: int = 50
):
    query = db.query(TravelPackage)

    # ✅ Destination filter (works for JSON/List columns OR string-based columns)
    if destinations:
        # Destination list ko lowercase
        dests = [d.lower().strip() for d in destinations if d]

        # If destinations stored as JSON list in DB
        # We'll match ANY of them using LIKE fallback (safe)
        destination_filters = []
        for d in dests:
            destination_filters.append(
                TravelPackage.destinations.ilike(f"%{d}%")
            )

        query = query.filter(or_(*destination_filters))

    # ✅ Price filters
    if min_price is not None:
        query = query.filter(TravelPackage.price_in_inr >= min_price)

    if max_price is not None:
        query = query.filter(TravelPackage.price_in_inr <= max_price)

    # ✅ Duration filters
    if min_days is not None:
        query = query.filter(TravelPackage.duration_days >= min_days)

    if max_days is not None:
        query = query.filter(TravelPackage.duration_days <= max_days)

    return query.offset(skip).limit(limit).all()



# =============================================================================
# UPDATE AGENCY SCRAPE STATUS
# =============================================================================

def update_agency_scrape_status(db, agency_id: int, success: bool, packages_found: int = 0):
    """
    Update scraping status of agency safely (works even if model doesn't have counters)
    """
    agency = db.query(Agency).filter(Agency.id == agency_id).first()

    if not agency:
        return None

    # ✅ basic status fields
    agency.last_scraped_at = datetime.utcnow()
    agency.last_scrape_success = success
    agency.last_scrape_packages_found = packages_found

    # ✅ optional counters (only if they exist in model)
    if success:
        if hasattr(agency, "success_count"):
            agency.success_count = (agency.success_count or 0) + 1
    else:
        if hasattr(agency, "fail_count"):
            agency.fail_count = (agency.fail_count or 0) + 1

    db.commit()
    db.refresh(agency)

    print(
        f"INFO:db.crud:✅ Updated scrape status for {agency.name}: "
        f"success={success}, packages={packages_found}"
    )

    return agency


# =============================================================================
# DATABASE STATS
# =============================================================================

def get_database_stats(db: Session) -> Dict[str, Any]:
    agencies_total = db.query(Agency).count()
    agencies_active = db.query(Agency).filter(Agency.scraping_enabled == True).count()

    packages_total = db.query(TravelPackage).count()
    packages_active = db.query(TravelPackage).filter(TravelPackage.is_active == True).count()

    return {
        "agencies_total": agencies_total,
        "agencies_active": agencies_active,
        "packages_total": packages_total,
        "packages_active": packages_active,
    }


# =============================================================================
# SCRAPING JOB TRACKING (OPTIONAL - but your test_db_ops uses it)
# =============================================================================

def create_scrape_job(
    db: Session,
    job_id: str,
    agency_id: int,
    status: str = "pending",
    started_at: Optional[datetime] = None,
):
    job = ScrapeJob(
        job_id=job_id,
        agency_id=agency_id,
        status=status,
        started_at=started_at or datetime.utcnow(),
        created_at=datetime.utcnow(),
    )

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_scrape_job_status(
    db: Session,
    job_id: str,
    status: str,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
):
    job = db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
    if not job:
        return None

    job.status = status
    job.finished_at = finished_at or datetime.utcnow()
    job.error_message = error_message

    db.commit()
    db.refresh(job)
    return job


def get_scrape_job(db: Session, job_id: str) -> Optional[ScrapeJob]:
    return db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
