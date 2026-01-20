"""
Test Ranking Script
Runs ranking engine on sample queries and prints top results
"""

from agents.intent_parser import IntentParser
from agents.planner import TripPlanner
from agents.ranker import PackageRanker  # ✅ Make sure this exists
from db.sessions import SessionLocal
from db.crud import search_packages


def run_ranking_tests():
    print("=" * 80)
    print("🧪 TESTING RANKING ENGINE")
    print("=" * 80)

    # ✅ FIX: Define test_queries first
    test_queries = [
        "Manali Kasol 5 days budget 20000 with friends",
        "Rajasthan tour 7 days budget 30000 with family",
        "Goa beach trip 4 days budget 15000 couple",
        "Dubai Abu Dhabi 6 days budget 80000 with friends",
    ]

    parser = IntentParser()
    planner = TripPlanner()
    ranker = PackageRanker()

    db = SessionLocal()

    for i, query in enumerate(test_queries, 1):
        print("\n" + "-" * 80)
        print(f"🔍 Test Query {i}: {query}")

        # Step 1: Parse Intent
        intent = parser.parse(query)
        print(f"✅ Intent: destinations={intent.destinations}, duration={intent.duration_days}, budget={intent.budget_per_person}")

        # Step 2: Create Plan
        trip_plan = planner.create_plan(intent)
        print(f"✅ Plan: total_days={trip_plan.total_days}, legs={len(trip_plan.legs)}")

        # Step 3: Fetch packages from DB (basic search)
        packages = search_packages(
            db=db,
            destinations=intent.destinations,
            min_price=0,
            max_price=intent.budget_per_person,
            min_days=max(1, intent.duration_days - 3),
            max_days=intent.duration_days + 3,
            limit=20
)


        print(f"📦 Packages found in DB: {len(packages)}")

        if not packages:
            print("⚠️ No packages available to rank for this query.")
            continue

        # Step 4: Rank packages
        ranked = ranker.rank_packages(intent, packages)

        print("\n🏆 Top 5 Ranked Packages:")
        for j, pkg in enumerate(ranked[:5], 1):
            print(
                f"{j}. ⭐ {pkg.package.package_title} | "
                f"₹{pkg.package.price_in_inr} | "
                f"{pkg.package.duration_days} days | "
                f"Score={pkg.total_score}"
            )


    db.close()

    print("\n" + "=" * 80)
    print("✅ RANKING TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_ranking_tests()
