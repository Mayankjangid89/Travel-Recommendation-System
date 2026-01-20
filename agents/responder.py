"""
Response Generator - Creates friendly AI responses
Uses LLM to generate natural language explanations
"""
from typing import List, Dict, Any
from agents.models import ParsedIntent, RankedPackage
from tools.llm_helper import get_llm
import logging

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates natural language responses using LLM
    Creates friendly, helpful explanations of recommendations
    """
    
    def __init__(self):
        self.llm = get_llm()
        logger.info("✅ Response Generator initialized")
    
    def generate_recommendation_response(
        self,
        intent: ParsedIntent,
        ranked_packages: List[RankedPackage],
        total_found: int
    ) -> str:
        """
        Generate friendly response explaining recommendations
        
        Args:
            intent: User's parsed intent
            ranked_packages: Top ranked packages
            total_found: Total packages found before ranking
        
        Returns:
            Natural language response
        """
        if not ranked_packages:
            return self._generate_no_results_response(intent)
        
        # Prepare package summaries for LLM
        packages_summary = self._prepare_packages_summary(ranked_packages[:5])
        
        # Generate response using LLM
        prompt = f"""
You are a friendly travel assistant helping someone plan their trip.

USER QUERY: "{intent.raw_query}"

PARSED INTENT:
- Destinations: {', '.join(intent.destinations) if intent.destinations else 'Any'}
- Duration: {intent.duration_days or 'Flexible'} days
- Budget: ₹{intent.budget_per_person:,.0f} per person
- Group: {intent.group_type or 'Not specified'}

SEARCH RESULTS:
We found {total_found} packages and selected the top {len(ranked_packages)} matches.

TOP PACKAGES:
{packages_summary}

TASK:
Write a friendly, helpful response (2-3 paragraphs) that:
1. Acknowledges their query warmly
2. Highlights the #1 package and why it's perfect for them (mention price, duration, destinations)
3. Briefly mentions 1-2 other good alternatives
4. Encourages them to check the packages

TONE: Friendly, enthusiastic, professional (not pushy)
LENGTH: 2-3 short paragraphs
FORMAT: Plain text, no bullet points

WRITE RESPONSE:
"""
        
        try:
            response = self.llm.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ LLM response generation failed: {e}")
            return self._generate_fallback_response(intent, ranked_packages)
    
    def _prepare_packages_summary(self, packages: List[RankedPackage]) -> str:
        """Prepare concise package summaries for LLM"""
        summaries = []
        
        for i, ranked_pkg in enumerate(packages, 1):
            pkg = ranked_pkg.package
            summary = f"""
Package #{i}: {pkg.package_title}
- Agency: {pkg.agency_name}
- Price: ₹{pkg.price_in_inr:,.0f}
- Duration: {pkg.duration_days} days
- Destinations: {', '.join(pkg.destinations[:3])}
- Match Score: {ranked_pkg.total_score:.2f}
- Why it matches: {ranked_pkg.match_explanation}
"""
            summaries.append(summary.strip())
        
        return "\n\n".join(summaries)
    
    def _generate_no_results_response(self, intent: ParsedIntent) -> str:
        """Generate response when no packages found"""
        destinations = ', '.join(intent.destinations) if intent.destinations else "your destination"
        
        return f"""
I searched for packages matching your query for {destinations}, but unfortunately, I couldn't find any packages that perfectly match your criteria right now.

Here are a few suggestions:
1. Try adjusting your budget range
2. Consider being flexible with travel dates
3. Check back later as we're constantly adding new packages

Would you like to modify your search criteria?
"""
    
    def _generate_fallback_response(
        self,
        intent: ParsedIntent,
        ranked_packages: List[RankedPackage]
    ) -> str:
        """Generate simple response if LLM fails"""
        if not ranked_packages:
            return self._generate_no_results_response(intent)
        
        top_pkg = ranked_packages[0].package
        
        return f"""
Great news! I found {len(ranked_packages)} excellent packages for your {', '.join(intent.destinations)} trip.

The best match is "{top_pkg.package_title}" by {top_pkg.agency_name} - a {top_pkg.duration_days}-day package for ₹{top_pkg.price_in_inr:,.0f}. This package covers {', '.join(top_pkg.destinations[:3])} and matches your requirements perfectly!

Check out the top {len(ranked_packages)} recommendations below and choose the one that fits you best. Happy travels! 🌍
"""


class ComparisonGenerator:
    """
    Generates package comparisons
    Helps users choose between similar packages
    """
    
    def __init__(self):
        self.llm = get_llm()
    
    def compare_packages(
        self,
        packages: List[RankedPackage],
        comparison_factors: List[str] = None
    ) -> str:
        """
        Generate detailed comparison of packages
        
        Args:
            packages: List of packages to compare (2-5)
            comparison_factors: Specific factors to compare
        
        Returns:
            Comparison text
        """
        if not packages or len(packages) < 2:
            return "Need at least 2 packages to compare."
        
        if comparison_factors is None:
            comparison_factors = ["price", "duration", "destinations", "inclusions", "rating"]
        
        # Prepare comparison data
        comparison_data = []
        for i, ranked_pkg in enumerate(packages[:5], 1):
            pkg = ranked_pkg.package
            comparison_data.append({
                "number": i,
                "title": pkg.package_title,
                "agency": pkg.agency_name,
                "price": pkg.price_in_inr,
                "days": pkg.duration_days,
                "destinations": pkg.destinations,
                "inclusions": pkg.inclusions,
                "rating": pkg.rating or "Not rated"
            })
        
        prompt = f"""
Compare these {len(comparison_data)} travel packages:

{self._format_comparison_data(comparison_data)}

Create a helpful comparison focusing on:
{', '.join(comparison_factors)}

Write a clear 2-3 paragraph comparison highlighting:
1. Key differences between packages
2. Best value option
3. Best overall option
4. Who each package is best suited for

Keep it concise and actionable.
"""
        
        try:
            response = self.llm.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Comparison generation failed: {e}")
            return self._generate_simple_comparison(comparison_data)
    
    def _format_comparison_data(self, data: List[Dict]) -> str:
        """Format comparison data for LLM"""
        formatted = []
        for pkg in data:
            formatted.append(f"""
Package {pkg['number']}: {pkg['title']}
- Agency: {pkg['agency']}
- Price: ₹{pkg['price']:,.0f}
- Duration: {pkg['days']} days
- Destinations: {', '.join(pkg['destinations'][:3])}
- Inclusions: {', '.join(pkg['inclusions'][:5])}
- Rating: {pkg['rating']}
""")
        return "\n".join(formatted)
    
    def _generate_simple_comparison(self, data: List[Dict]) -> str:
        """Simple comparison if LLM fails"""
        lines = ["Package Comparison:\n"]
        
        for pkg in data:
            lines.append(f"{pkg['number']}. {pkg['title']} - ₹{pkg['price']:,.0f} ({pkg['days']} days)")
        
        cheapest = min(data, key=lambda x: x['price'])
        lines.append(f"\n💰 Best Value: {cheapest['title']} at ₹{cheapest['price']:,.0f}")
        
        return "\n".join(lines)