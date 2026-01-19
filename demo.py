"""
Complete Demo - End-to-end flow demonstration
Shows: Query → Parse → Discover → Scrape → Match → Rank → Response
"""

import asyncio
import json
from datetime import datetime, timezone
from urllib.parse import urljoin

# Import all our modules
from agents.intent_parser import IntentParser
from agents.planner import TripPlanner
from tools.llm_helper import get_llm
from tools.scraper_engine import ScraperEngine


async def demo_complete_flow():
    """
    Demonstrate the complete workflow
    """
    print("=" * 80)
    print("🚀 TRAVEL AI AGENT - COMPLETE FLOW DEMONSTRATION")
    print("=" * 80)
    print()

    # ✅ MUST be initialized here
    all_packages = []

    # ========================================
    # STEP 1: USER QUERY
    # ========================================
    user_query = "I want to go Manali-Kasol for 5 days, budget 20000 per person, with friends"

    print("📝 STEP 1: User Query")
    print(f"   Query: {user_query}")
    print()

    # ========================================
    # STEP 2: PARSE INTENT
    # ========================================
    print("🧠 STEP 2: Parse Intent")
    parser = IntentParser()
    intent = parser.parse(user_query)

    print(f"   Destinations: {intent.destinations}")
    print(f"   Duration: {intent.duration_days} days")
    print(f"   Budget: ₹{intent.budget_per_person:,.0f}")
    print(f"   Group Type: {intent.group_type}")
    print(f"   Trip Type: {intent.trip_type}")
    print()

    # ========================================
    # STEP 3: CREATE TRIP PLAN
    # ========================================
    print("🗺️  STEP 3: Create Trip Plan")
    planner = TripPlanner()
    trip_plan = planner.create_plan(intent)

    print(f"   Total Days: {trip_plan.total_days}")
    print(f"   Legs: {len(trip_plan.legs)}")
    for i, leg in enumerate(trip_plan.legs, 1):
        print(f"      Leg {i}: {leg['cities']} - {leg['days']} days")
    print()

    # ========================================
    # STEP 4: DISCOVER AGENCIES (DEMO STATIC)
    # ========================================
    print("🔍 STEP 4: Discover Local Agencies")
    print("   (In production, this runs as a background job)")

    agencies = [
        {
            "name": "Youth Camping",
            "url": "https://www.youthcamping.in/",
            "trust_score": 0.9
        }
    ]

    print(f"   Found {len(agencies)} agencies")
    for agency in agencies:
        print(f"      - {agency['name']}")
    print()

    # ========================================
    # STEP 5: SCRAPE PACKAGES
    # ========================================
    print("📦 STEP 5: Scrape Packages from Agencies")
    print("   Using Playwright + Gemini extraction...")

    async with ScraperEngine() as scraper:
        for agency in agencies:
            print(f"   Scraping: {agency['name']}...")

            result = await scraper.scrape_agency(
                agency["url"],
                agency["name"],
                extract_packages=True
            )

            if result.get("success"):
                for pkg in result.get("packages", []):
                    # ✅ attach agency metadata
                    pkg["agency_name"] = agency["name"]
                    pkg["agency_trust_score"] = agency.get("trust_score", 0.5)

                    # ✅ convert relative URL to full URL
                    pkg_url = pkg.get("url", "")
                    pkg["url"] = urljoin(agency["url"], pkg_url)

                    # ✅ save scrape time
                    pkg["scraped_at"] = datetime.now(timezone.utc).isoformat()

                    all_packages.append(pkg)

                print(f"      ✅ Found {len(result.get('packages', []))} packages")
            else:
                print(f"      ❌ Scraping failed: {result.get('error')}")

    print(f"   Total packages collected: {len(all_packages)}")
    print()

    # ========================================
    # STEP 6: FILTER & MATCH PACKAGES
    # ========================================
    print("🎯 STEP 6: Filter Packages by Intent")

    matched_packages = []

    intent_destinations = set([d.lower() for d in intent.destinations])
    intent_days = intent.duration_days
    intent_budget = intent.budget_per_person

    for pkg in all_packages:
        pkg_destinations = set([d.lower() for d in pkg.get("destinations", [])])

        # ✅ destination match: at least 1 common destination
        common = intent_destinations.intersection(pkg_destinations)
        destination_match = len(common) > 0

        # ✅ budget match: allow +20%
        pkg_price = float(pkg.get("price_in_inr", 999999))
        budget_ok = pkg_price <= (intent_budget * 1.2)

        # ✅ duration match: allow +-5 days
        pkg_days = int(pkg.get("duration_days", 0))
        duration_ok = True
        if intent_days:
            duration_ok = abs(pkg_days - intent_days) <= 5

        if destination_match and budget_ok and duration_ok:
            matched_packages.append(pkg)

    print(f"   Matched packages: {len(matched_packages)}/{len(all_packages)}")
    print()

    # ========================================
    # STEP 7: RANK PACKAGES
    # ========================================
    print("🏆 STEP 7: Rank Packages (Simple Scoring)")

    def calculate_score(pkg):
        score = 0

        pkg_dest = set([d.lower() for d in pkg.get("destinations", [])])
        common_dest = intent_destinations.intersection(pkg_dest)

        # ✅ Destination score
        score += len(common_dest) * 50

        # ✅ Budget score
        pkg_price = float(pkg.get("price_in_inr", 999999))
        if intent_budget:
            if pkg_price <= intent_budget:
                score += 50
            elif pkg_price <= intent_budget * 1.2:
                score += 20

        # ✅ Duration score
        pkg_days = int(pkg.get("duration_days", 0))
        if intent_days:
            diff = abs(pkg_days - intent_days)
            if diff == 0:
                score += 30
            elif diff <= 2:
                score += 15
            elif diff <= 5:
                score += 5

        # ✅ Trust score bonus
        score += int(pkg.get("agency_trust_score", 0.5) * 20)

        return score

    for pkg in matched_packages:
        pkg["match_score"] = calculate_score(pkg)

    ranked_packages = sorted(matched_packages, key=lambda x: x["match_score"], reverse=True)
    top_packages = ranked_packages[:3]

    print("   Top 3 packages:")
    for pkg in top_packages:
        print(
            f"   ⭐ {pkg.get('package_title')} | ₹{pkg.get('price_in_inr')} | "
            f"{pkg.get('duration_days')} days | {pkg.get('destinations')} | "
            f"Score={pkg.get('match_score')}"
        )
    print()

    # ========================================
    # STEP 8: GENERATE AI RESPONSE
    # ========================================
    print("💬 STEP 8: Generate AI Response")

    llm = get_llm()

    if ranked_packages:
        ai_response = llm.generate_recommendation_response(
            query=user_query,
            packages=all_packages,
            top_packages=ranked_packages[:5]
        )

        print("   AI Assistant says:")
        print("   " + "-" * 70)
        print("   " + ai_response.replace("\n", "\n   "))
        print("   " + "-" * 70)
    else:
        print("   ❌ No packages found matching criteria")

    print()

    # ========================================
    # STEP 9: FINAL RESPONSE JSON
    # ========================================
    print("📋 STEP 9: Final Response JSON")

    response = {
        "query_id": f"q_{int(datetime.now(timezone.utc).timestamp())}",
        "parsed_intent": {
            "destinations": intent.destinations,
            "duration_days": intent.duration_days,
            "budget_per_person": intent.budget_per_person,
            "group_type": str(intent.group_type),
            "trip_type": str(intent.trip_type)
        },
        "trip_plan": {
            "total_days": trip_plan.total_days,
            "legs": trip_plan.legs
        },
        "total_found": len(all_packages),
        "matched": len(matched_packages),
        "top_packages": [
            {
                "title": pkg.get("package_title"),
                "price_inr": pkg.get("price_in_inr"),
                "duration_days": pkg.get("duration_days"),
                "destinations": pkg.get("destinations"),
                "agency": pkg.get("agency_name"),
                "match_score": pkg.get("match_score"),
                "url": pkg.get("url")
            }
            for pkg in ranked_packages[:5]
        ],
        "processing_time_ms": 1234.5
    }

    print(json.dumps(response, indent=2))
    print()

    print("=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print()
    print("📌 Next Steps:")
    print("   1. Store agencies in PostgreSQL database")
    print("   2. Run background workers to scrape daily")
    print("   3. Create FastAPI endpoints")
    print("   4. Add caching layer (Redis)")
    print("   5. Deploy to production")
    print()


if __name__ == "__main__":
    print("\n🎬 Starting Complete Flow Demo...\n")
    asyncio.run(demo_complete_flow())
