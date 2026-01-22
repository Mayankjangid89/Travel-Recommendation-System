"""
Ranking Engine - Scores and ranks travel packages
Uses weighted scoring algorithm to find best matches
"""

from typing import List, Dict, Any, Union
from datetime import datetime
import os
import logging

from agents.models import ParsedIntent, TravelPackageSchema, RankedPackage

logger = logging.getLogger(__name__)


class PackageRanker:
    """
    Intelligent package ranking system
    Scores packages based on multiple weighted factors
    """

    def __init__(self):
        self.weights = {
            "destination_match": float(os.getenv("WEIGHT_DESTINATION_MATCH", "0.30")),
            "duration_match": float(os.getenv("WEIGHT_DURATION_MATCH", "0.20")),
            "budget_match": float(os.getenv("WEIGHT_BUDGET_MATCH", "0.25")),
            "trust_score": float(os.getenv("WEIGHT_TRUST_SCORE", "0.10")),
            "reviews": float(os.getenv("WEIGHT_REVIEWS", "0.10")),
            "inclusions": float(os.getenv("WEIGHT_INCLUSIONS", "0.05")),
        }

        logger.info(f"✅ Ranker initialized with weights: {self.weights}")

    # ----------------------------
    # Public
    # ----------------------------
    def rank_packages(
    self,
    packages: list,
    intent: ParsedIntent,
    max_results: int = 5
    ) -> List[RankedPackage]:
        """
        Rank packages based on intent match.

        IMPORTANT:
        packages can be:
        - dict from scraper
        - SQLAlchemy TravelPackage object from DB
        So we normalize both into dict.
        """

        if not packages:
            logger.warning("⚠️ No packages to rank")
            return []

        normalized_packages = [self._to_dict(p) for p in packages]

        logger.info(
            f"🎯 Ranking {len(normalized_packages)} packages for intent: {intent.destinations}"
        )

        scored_packages = []
        for pkg in normalized_packages:
            scores = self._calculate_scores(pkg, intent)
            total_score = self._calculate_total_score(scores)

            scored_packages.append(
                {
                    "package": pkg,
                    "total_score": total_score,
                    "score_breakdown": scores,
                }
            )

        scored_packages.sort(key=lambda x: x["total_score"], reverse=True)
        top_packages = scored_packages[:max_results]

        ranked: List[RankedPackage] = []

        for i, scored in enumerate(top_packages, start=1):
            ranked_pkg = self._create_ranked_package(
                package=scored["package"],
                rank=i,
                total_score=scored["total_score"],
                score_breakdown=scored["score_breakdown"],
                intent=intent,
            )
            ranked.append(ranked_pkg)

        if ranked:
            logger.info(f"✅ Ranked {len(ranked)} packages, top score: {ranked[0].total_score:.2f}")

        return ranked

    # ----------------------------
    # Helpers
    # ----------------------------
    def _to_dict(self, package: Any) -> Dict[str, Any]:
        """
        Convert SQLAlchemy model OR dict into a common dictionary format
        so scoring functions work safely.
        """
        if isinstance(package, dict):
            return package

        # SQLAlchemy object conversion
        return {
            "agency_name": getattr(package, "agency_name", None) or "Unknown Agency",
            "package_title": getattr(package, "package_title", "") or "",
            "url": getattr(package, "url", "") or "",
            "price_in_inr": getattr(package, "price_in_inr", 0) or 0,
            "duration_days": getattr(package, "duration_days", 0) or 0,
            "destinations": getattr(package, "destinations", []) or [],
            "inclusions": getattr(package, "inclusions", []) or [],
            "exclusions": getattr(package, "exclusions", []) or [],
            "highlights": getattr(package, "highlights", []) or [],
            "rating": getattr(package, "rating", None),
            "reviews_count": getattr(package, "reviews_count", 0) or 0,
            "agency_trust_score": getattr(package, "agency_trust_score", 0.5) or 0.5,
            "source_confidence_score": getattr(package, "source_confidence_score", 0.5)
            or 0.5,
            "scraped_at": getattr(package, "scraped_at", datetime.utcnow()),
        }

    def _calculate_scores(self, package: Dict[str, Any], intent: ParsedIntent) -> Dict[str, float]:
        return {
            "destination_match": self._score_destination_match(package, intent),
            "duration_match": self._score_duration_match(package, intent),
            "budget_match": self._score_budget_match(package, intent),
            "trust_score": self._score_trust(package),
            "reviews": self._score_reviews(package),
            "inclusions": self._score_inclusions(package, intent),
        }

    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        total = 0.0
        for factor, score in scores.items():
            total += score * self.weights.get(factor, 0.0)
        return round(total, 3)

    # ----------------------------
    # Scoring
    # ----------------------------
    def _score_destination_match(self, package: Dict[str, Any], intent: ParsedIntent) -> float:
        if not intent.destinations:
            return 0.5

        pkg_destinations = set(d.lower() for d in package.get("destinations", []))
        intent_destinations = set(d.lower() for d in intent.destinations)

        if not pkg_destinations:
            return 0.0

        overlap = pkg_destinations & intent_destinations
        if not overlap:
            return 0.0

        coverage = len(overlap) / len(intent_destinations)
        if pkg_destinations == intent_destinations:
            coverage = 1.0

        return min(coverage, 1.0)

    def _score_duration_match(self, package: Dict[str, Any], intent: ParsedIntent) -> float:
        if not intent.duration_days:
            return 0.5

        pkg_days = package.get("duration_days", 0)
        intent_days = intent.duration_days
        flexibility = intent.flexibility_days

        if not pkg_days:
            return 0.0

        diff = abs(pkg_days - intent_days)

        if diff == 0:
            return 1.0

        if diff <= flexibility:
            return 1.0 - (diff / (flexibility + 1)) * 0.2

        max_diff = flexibility * 2
        if diff >= max_diff:
            return 0.0

        return 1.0 - (diff / max_diff)

    def _score_budget_match(self, package: Dict[str, Any], intent: ParsedIntent) -> float:
        if not intent.budget_per_person:
            return 0.5

        pkg_price = package.get("price_in_inr", 0)
        budget = intent.budget_per_person

        if not pkg_price:
            return 0.0

        if abs(pkg_price - budget) / budget <= 0.05:
            return 1.0

        if pkg_price < budget:
            ratio = pkg_price / budget
            return 0.8 + (ratio * 0.2)

        over_ratio = (pkg_price - budget) / budget

        if over_ratio <= 0.10:
            return 0.9 - (over_ratio * 5)

        if over_ratio <= 0.30:
            return 0.6 - ((over_ratio - 0.10) * 2)

        if over_ratio <= 0.50:
            return 0.3 - ((over_ratio - 0.30) * 1.5)

        return 0.0

    def _score_trust(self, package: Dict[str, Any]) -> float:
        trust = float(package.get("agency_trust_score", 0.5) or 0.5)
        confidence = float(package.get("source_confidence_score", 0.5) or 0.5)
        return (trust + confidence) / 2

    def _score_reviews(self, package: Dict[str, Any]) -> float:
        rating = package.get("rating")
        reviews_count = int(package.get("reviews_count", 0) or 0)

        if rating is None:
            return 0.5

        rating_score = float(rating) / 5.0

        if reviews_count >= 100:
            bonus = 0.10
        elif reviews_count >= 50:
            bonus = 0.05
        elif reviews_count >= 10:
            bonus = 0.02
        else:
            bonus = 0.0

        return min(rating_score + bonus, 1.0)

    def _score_inclusions(self, package: Dict[str, Any], intent: ParsedIntent) -> float:
        pkg_inclusions = set(i.lower() for i in package.get("inclusions", []))
        must_include = set(m.lower() for m in intent.must_include)

        base = min(len(pkg_inclusions) / 10, 0.7)

        if must_include:
            matches = pkg_inclusions & must_include
            bonus = (len(matches) / len(must_include)) * 0.3
        else:
            bonus = 0.0

        return min(base + bonus, 1.0)

    # ----------------------------
    # Output formatting
    # ----------------------------
    def _create_ranked_package(
        self,
        package: Dict[str, Any],
        rank: int,
        total_score: float,
        score_breakdown: Dict[str, float],
        intent: ParsedIntent,
    ) -> RankedPackage:

        explanation = self._generate_explanation(package, score_breakdown, intent)

        pkg_schema = TravelPackageSchema(
            agency_name=package.get("agency_name", "Unknown Agency"),
            package_title=package.get("package_title", ""),
            url=package.get("url", ""),
            price_in_inr=float(package.get("price_in_inr", 0) or 0),
            duration_days=int(package.get("duration_days", 0) or 0),
            destinations=package.get("destinations", []),
            inclusions=package.get("inclusions", []),
            exclusions=package.get("exclusions", []),
            rating=package.get("rating"),
            reviews_count=int(package.get("reviews_count", 0) or 0),
            scraped_at=package.get("scraped_at", datetime.utcnow()),
        )

        return RankedPackage(
            package=pkg_schema,
            rank=rank,
            total_score=total_score,
            score_breakdown=score_breakdown,
            match_explanation=explanation,
            booking_url=package.get("url", ""),
        )

    def _generate_explanation(
        self,
        package: Dict[str, Any],
        scores: Dict[str, float],
        intent: ParsedIntent,
    ) -> str:

        reasons = []

        if scores["destination_match"] >= 0.8:
            dest_str = ", ".join(package.get("destinations", [])[:3])
            reasons.append(f"Perfect match for {dest_str}")
        elif scores["destination_match"] >= 0.5:
            reasons.append("Good destination coverage")

        price = package.get("price_in_inr", 0)
        if intent.budget_per_person and scores["budget_match"] >= 0.8:
            if price <= intent.budget_per_person:
                reasons.append(f"Within budget at ₹{price:,.0f}")
            else:
                reasons.append("Slightly over budget but great value")

        if scores["duration_match"] >= 0.9:
            days = package.get("duration_days", 0)
            reasons.append(f"Perfect {days}-day duration")

        if scores["trust_score"] >= 0.8:
            reasons.append("Highly trusted agency")

        if scores["reviews"] >= 0.8:
            rating = package.get("rating", 0)
            reasons.append(f"Excellent {rating}★ rating")

        if not reasons:
            reasons.append("Matches your criteria")

        return "; ".join(reasons)
