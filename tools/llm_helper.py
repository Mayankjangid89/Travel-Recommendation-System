"""
LLM Helper - Google Gemini integration for extraction and response generation
FREE alternative to OpenAI GPT
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiLLM:
    """
    Google Gemini LLM wrapper
    Handles extraction, generation, and structured outputs
    """
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        
        self.model_name = os.getenv("LLM_MODEL", "models/gemini-2.5-flash-lite")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": self.temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        
        logger.info(f"✅ Gemini LLM initialized: {self.model_name}")
    
    def extract_packages_from_html(self, html_content: str, agency_url: str) -> List[Dict[str, Any]]:
        """
        Extract travel packages from HTML using Gemini
        
        Args:
            html_content: Full HTML content of the page
            agency_url: URL of the agency website
            
        Returns:
            List of extracted packages as dictionaries
        """
        # Truncate HTML if too long (Gemini can handle large context but let's be safe)
        if len(html_content) > 100000:
            html_content = html_content[:100000]
        
        prompt = f"""
You are an expert at extracting travel package information from websites.

TASK: Extract ALL travel packages from this HTML content.

URL: {agency_url}

HTML CONTENT:
{html_content}

INSTRUCTIONS:
1. Find all travel packages/tour packages on this page
2. Extract: package name, price (in INR), duration (days), destinations, inclusions
3. If price is not in INR, skip that package
4. If duration is not clear, estimate from the itinerary
5. Return ONLY valid JSON (no markdown, no explanations)

OUTPUT FORMAT (JSON):
{{
  "packages": [
    {{
      "title": "Package name",
      "price_inr": 15999,
      "duration_days": 5,
      "destinations": ["Manali", "Kullu"],
      "inclusions": ["Hotel", "Meals", "Transport"],
      "exclusions": ["Flight", "Visa"],
      "highlights": ["Key selling points"],
      "url": "full package URL or {agency_url}"
    }}
  ]
}}

If NO packages found, return: {{"packages": []}}

EXTRACT NOW:
"""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            packages = data.get("packages", [])     

            # ✅ Normalize keys to match your DB schema
            normalized_packages = []
            for p in packages:
                normalized_packages.append({
                    "package_title": p.get("title"),
                    "price_in_inr": p.get("price_inr"),
                    "duration_days": p.get("duration_days"),
                    "destinations": p.get("destinations", []),
                    "inclusions": p.get("inclusions", []),
                    "exclusions": p.get("exclusions", []),
                    "highlights": p.get("highlights", []),
                    "url": p.get("url", agency_url),
                })

            logger.info(f"✅ Extracted {len(normalized_packages)} packages from {agency_url}")
            return normalized_packages
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"❌ Gemini extraction error: {e}")
            return []
    
    def generate_recommendation_response(
        self, 
        query: str,
        packages: List[Dict[str, Any]],
        top_packages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate friendly AI response explaining recommendations
        
        Args:
            query: Original user query
            packages: All packages found
            top_packages: Top ranked packages
            
        Returns:
            Human-friendly explanation
        """
        packages_summary = []
        for i, pkg in enumerate(top_packages[:5], 1):
            packages_summary.append(f"""
Package {i}: {pkg['package_title']}
- Price: ₹{pkg['price_in_inr']:,.0f}
- Duration: {pkg['duration_days']} days
- Destinations: {', '.join(pkg['destinations'])}
- Agency: {pkg['agency_name']}
""")
        
        prompt = f"""
You are a friendly travel assistant helping someone plan their trip.

USER QUERY: "{query}"

We found {len(packages)} packages and selected the top {len(top_packages)} matches.

TOP PACKAGES:
{"".join(packages_summary)}

TASK:
Write a friendly, helpful response (2-3 paragraphs) that:
1. Acknowledges their query
2. Highlights the BEST package (#1) and why it's perfect for them
3. Briefly mentions 1-2 other good alternatives
4. Encourages them to check the links

TONE: Friendly, professional, enthusiastic but not pushy

WRITE RESPONSE:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Response generation error: {e}")
            return f"Found {len(top_packages)} great packages for your {query}. Check out the top recommendations below!"
    
    def enhance_package_data(self, raw_package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini to enhance/clean extracted package data
        Useful when scraped data is messy
        
        Args:
            raw_package: Raw extracted package data
            
        Returns:
            Enhanced package data
        """
        prompt = f"""
Clean and enhance this travel package data:

RAW DATA:
{json.dumps(raw_package, indent=2)}

TASKS:
1. Standardize destination names (proper capitalization)
2. Parse duration into days (e.g., "5D/4N" → 5)
3. Clean price (remove currency symbols, get numeric value)
4. Standardize inclusions/exclusions
5. Fix any obvious errors

Return ONLY valid JSON in this format:
{{
  "title": "cleaned title",
  "price_inr": numeric,
  "duration_days": numeric,
  "destinations": ["City1", "City2"],
  "inclusions": ["Hotel", "Meals"],
  "exclusions": ["Flights"],
  "highlights": ["key points"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            return json.loads(response_text.strip())
        except Exception as e:
            logger.error(f"❌ Enhancement error: {e}")
            return raw_package


# Singleton instance
_llm_instance: Optional[GeminiLLM] = None

def get_llm() -> GeminiLLM:
    """Get or create LLM singleton instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = GeminiLLM()
    return _llm_instance


# Example usage
if __name__ == "__main__":
    # Test Gemini connection
    llm = get_llm()
    
    # Test HTML extraction
    test_html = """
    <div class="package">
        <h2>Manali Kullu Package</h2>
        <p>Duration: 5 Days / 4 Nights</p>
        <p>Price: ₹15,999 per person</p>
        <p>Visit: Manali, Kullu, Solang Valley</p>
        <p>Includes: Hotel, Breakfast, Transport</p>
    </div>
    """
    
    packages = llm.extract_packages_from_html(test_html, "https://example-agency.com")
    print("📦 Extracted packages:")
    print(json.dumps(packages, indent=2))