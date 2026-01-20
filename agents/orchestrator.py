"""
Orchestrator - Coordinates the complete recommendation workflow
Ties together: parsing → planning → searching → ranking → responding
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import logging

from agents.intent_parser import IntentParser
from agents.planner import TripPlanner
from agents.ranker import PackageRanker
from agents.responder import ResponseGenerator
from agents.models import ParsedIntent, RecommendationResponse, RankedPackage
from db.sessions import SessionLocal
from db.crud import search_packages, log_user_query

logger = logging.getLogger(__name__)


class RecommendationOrchestrator:
    """
    Orchestrates the complete recommendation workflow
    This is the main entry point for getting package recommendations
    """
    
    def __init__(self):
        self.parser = IntentParser()
        self.planner = TripPlanner()
        self.ranker = PackageRanker()
        self.responder = ResponseGenerator()
        
        logger.info("✅ Orchestrator initialized")
    
    def get_recommendations(
        self,
        query: str,
        max_results: int = 5,
        include_explanation: bool = True
    ) -> RecommendationResponse:
        """
        Complete recommendation workflow
        
        Args:
            query: Natural language query
            max_results: Maximum packages to return
            include_explanation: Whether to generate AI explanation
        
        Returns:
            RecommendationResponse with ranked packages
        """
        start_time = time.time()
        query_id = f"q_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"🚀 Starting recommendation for query: {query}")
        
        # Step 1: Parse Intent
        logger.info("📝 Step 1: Parsing intent...")
        intent = self.parser.parse(query)
        logger.info(f"   ✅ Parsed: {intent.destinations}, {intent.duration_days} days, ₹{intent.budget_per_person}")
        
        # Step 2: Create Trip Plan
        logger.info("🗺️  Step 2: Creating trip plan...")
        trip_plan = self.planner.create_plan(intent)
        logger.info(f"   ✅ Plan: {trip_plan.total_days} days, {len(trip_plan.legs)} legs")
        
        # Step 3: Search Database for Packages
        logger.info("🔍 Step 3: Searching database...")
        packages = self._search_packages(intent)
        logger.info(f"   ✅ Found {len(packages)} packages")
        
        # Step 4: Rank Packages
        logger.info("🏆 Step 4: Ranking packages...")
        ranked_packages = self.ranker.rank_packages(packages, intent, max_results)
        logger.info(f"   ✅ Top {len(ranked_packages)} ranked")
        
        # Step 5: Generate AI Response
        assistant_message = ""
        if include_explanation and ranked_packages:
            logger.info("💬 Step 5: Generating response...")
            assistant_message = self.responder.generate_recommendation_response(
                intent, ranked_packages, len(packages)
            )
            logger.info("   ✅ Response generated")
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log query to database
        self._log_query(
            query_id=query_id,
            raw_query=query,
            intent=intent,
            packages_returned=len(ranked_packages),
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"✅ Completed in {processing_time_ms:.0f}ms")
        
        # Build response
        response = RecommendationResponse(
            query_id=query_id,
            parsed_intent=intent,
            trip_plan=trip_plan,
            ranked_packages=ranked_packages,
            total_found=len(packages),
            assistant_message=assistant_message,
            processing_time_ms=processing_time_ms
        )
        
        return response
    
    def _search_packages(self, intent: ParsedIntent) -> List[Dict[str, Any]]:
        """
        Search database for matching packages
        
        Args:
            intent: Parsed user intent
        
        Returns:
            List of package dicts
        """
        db = SessionLocal()
        
        try:
            # Calculate price range (allow 30% flexibility)
            min_price = None
            max_price = None
            if intent.budget_per_person:
                min_price = intent.budget_per_person * 0.5  # 50% below budget
                max_price = intent.budget_per_person * 1.3  # 30% over budget
            
            # Calculate duration range
            min_days = None
            max_days = None
            if intent.duration_days:
                flexibility = intent.flexibility_days
                min_days = max(1, intent.duration_days - flexibility)
                max_days = intent.duration_days + flexibility
            
            # Search database
            packages = search_packages(
                db,
                destinations=intent.destinations if intent.destinations else None,
                min_price=min_price,
                max_price=max_price,
                min_days=min_days,
                max_days=max_days,
                limit=100  # Get more results for better ranking
            )
            
            # Convert SQLAlchemy objects to dicts
            package_dicts = []
            for pkg in packages:
                pkg_dict = {
                    "id": pkg.id,
                    "agency_name": pkg.agency.name if pkg.agency else "Unknown",
                    "package_title": pkg.package_title,
                    "url": pkg.url,
                    "price_in_inr": pkg.price_in_inr,
                    "duration_days": pkg.duration_days,
                    "destinations": pkg.destinations,
                    "inclusions": pkg.inclusions or [],
                    "exclusions": pkg.exclusions or [],
                    "rating": pkg.rating,
                    "reviews_count": pkg.reviews_count,
                    "agency_trust_score": pkg.agency.trust_score if pkg.agency else 0.5,
                    "source_confidence_score": pkg.source_confidence_score,
                    "scraped_at": pkg.scraped_at
                }
                package_dicts.append(pkg_dict)
            
            return package_dicts
            
        finally:
            db.close()
    
    def _log_query(
        self,
        query_id: str,
        raw_query: str,
        intent: ParsedIntent,
        packages_returned: int,
        processing_time_ms: float
    ):
        """Log query for analytics"""
        db = SessionLocal()
        
        try:
            log_user_query(
                db,
                query_id=query_id,
                raw_query=raw_query,
                parsed_intent=intent.model_dump(),
                packages_returned=packages_returned,
                response_time_ms=processing_time_ms
            )
        except Exception as e:
            logger.error(f"❌ Failed to log query: {e}")
        finally:
            db.close()