from agents.orchestrator import RecommendationOrchestrator

orchestrator = RecommendationOrchestrator()

# Test Manali query
response = orchestrator.get_recommendations(
    query="I want to go Manali",
    max_results=5
)

print(f"✅ Found {response.total_found} packages")
print(f"✅ Top {len(response.ranked_packages)} recommendations:")

for ranked_pkg in response.ranked_packages:
    pkg = ranked_pkg.package
    print(f"\n#{ranked_pkg.rank}. {pkg.package_title}")
    print(f"   Price: ₹{pkg.price_in_inr:,.0f} | {pkg.duration_days} days")
    print(f"   Score: {ranked_pkg.total_score:.2f}")