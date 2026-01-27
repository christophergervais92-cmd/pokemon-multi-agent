#!/usr/bin/env python3
"""
AI Photo Card Scanner

Identifies Pokemon cards from photos using AI vision.
Returns card identification, market prices, and grade estimation.

Supports:
- OpenAI GPT-4 Vision
- Anthropic Claude Vision
- Demo mode (no API key)

Usage:
    from vision.card_scanner import CardScanner
    
    scanner = CardScanner()
    result = scanner.scan_card(image_url="https://...")
    # or
    result = scanner.scan_card(image_base64="...")
"""
import os
import sys
import json
import base64
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add parent for imports
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Price API
PRICE_API_URL = os.environ.get("POKEMON_PRICE_API_URL", "")
PRICE_API_KEY = os.environ.get("POKEMON_PRICE_API_KEY", "")

# Pokemon TCG API
# Without key: 1000 requests/day, 30/minute - WITH key: 20,000/day
POKEMON_TCG_API = "https://api.pokemontcg.io/v2"
POKEMON_TCG_API_KEY = os.environ.get("POKEMON_TCG_API_KEY", "")


# =============================================================================
# CARD DATABASE (for quick lookups)
# =============================================================================

# Common valuable cards for demo mode
KNOWN_CARDS = {
    "charizard": {
        "base_set": {"name": "Charizard", "set": "Base Set", "number": "4/102", "rarity": "Holo Rare", 
                     "raw_price": 350, "psa_9": 2500, "psa_10": 50000},
        "vmax": {"name": "Charizard VMAX", "set": "Champion's Path", "number": "074/073", "rarity": "Secret Rare",
                "raw_price": 150, "psa_9": 350, "psa_10": 800},
        "ex": {"name": "Charizard ex", "set": "Obsidian Flames", "number": "223/197", "rarity": "Special Art Rare",
              "raw_price": 85, "psa_9": 180, "psa_10": 400},
    },
    "pikachu": {
        "illustrator": {"name": "Pikachu Illustrator", "set": "Promo", "number": "PROMO", "rarity": "Promo",
                       "raw_price": 500000, "psa_9": 2000000, "psa_10": 5000000},
        "vmax": {"name": "Pikachu VMAX", "set": "Vivid Voltage", "number": "044/185", "rarity": "Ultra Rare",
                "raw_price": 25, "psa_9": 60, "psa_10": 150},
    },
    "mewtwo": {
        "base_set": {"name": "Mewtwo", "set": "Base Set", "number": "10/102", "rarity": "Holo Rare",
                   "raw_price": 80, "psa_9": 400, "psa_10": 2000},
    },
    "mew": {
        "151": {"name": "Mew ex", "set": "151", "number": "205/165", "rarity": "Special Art Rare",
               "raw_price": 120, "psa_9": 280, "psa_10": 600},
    },
}


# =============================================================================
# VISION PROMPT
# =============================================================================

CARD_IDENTIFICATION_PROMPT = """You are an expert Pokemon card identifier. Analyze this image of a Pokemon card and provide:

1. **Card Name**: The Pokemon's name
2. **Set Name**: Which set/expansion it's from
3. **Card Number**: The card number (e.g., "4/102")
4. **Rarity**: Common, Uncommon, Rare, Holo Rare, Ultra Rare, Secret Rare, etc.
5. **Edition**: 1st Edition, Unlimited, or modern
6. **Condition Assessment**:
   - Centering (1-10): How centered is the card art?
   - Corners (1-10): Sharpness of corners
   - Edges (1-10): Condition of edges
   - Surface (1-10): Scratches, print lines, whitening
7. **Estimated Grade**: What PSA grade would this likely receive? (1-10)
8. **Notable Features**: Holographic, special art, error card, etc.

Respond in JSON format:
{
  "card_name": "...",
  "pokemon": "...",
  "set_name": "...",
  "card_number": "...",
  "rarity": "...",
  "edition": "...",
  "condition": {
    "centering": 8,
    "corners": 9,
    "edges": 8,
    "surface": 9
  },
  "estimated_grade": 8.5,
  "notable_features": ["holographic", "..."],
  "confidence": 0.95,
  "notes": "..."
}

If you cannot identify the card or the image is not a Pokemon card, return:
{"error": "Could not identify card", "reason": "..."}
"""


# =============================================================================
# CARD SCANNER CLASS
# =============================================================================

class CardScanner:
    """
    AI-powered Pokemon card scanner.
    
    Identifies cards from photos and provides pricing information.
    """
    
    def __init__(self):
        """Initialize the scanner with available AI providers."""
        self.provider = self._detect_provider()
    
    def _detect_provider(self) -> str:
        """Detect which AI provider is available."""
        if ANTHROPIC_API_KEY:
            return "anthropic"
        elif OPENAI_API_KEY:
            return "openai"
        else:
            return "demo"
    
    def scan_card(
        self,
        image_url: str = None,
        image_base64: str = None,
        image_path: str = None,
    ) -> Dict[str, Any]:
        """
        Scan a Pokemon card image and identify it.
        
        Args:
            image_url: URL to the card image
            image_base64: Base64 encoded image data
            image_path: Local file path to image
        
        Returns:
            Dict with card identification, pricing, and grade estimate
        """
        # Convert local file to base64 if provided
        if image_path and not image_base64:
            try:
                with open(image_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()
            except Exception as e:
                return {"error": f"Could not read image file: {e}"}
        
        # If no image provided, use demo mode
        if not image_url and not image_base64:
            identification = self._scan_demo_mode(None, None)
        # Get card identification from AI
        elif self.provider == "anthropic":
            identification = self._scan_with_anthropic(image_url, image_base64)
            # Fallback to demo if API fails
            if "error" in identification:
                demo = self._scan_demo_mode(image_url, image_base64)
                demo["api_error"] = identification.get("error")
                identification = demo
        elif self.provider == "openai":
            identification = self._scan_with_openai(image_url, image_base64)
            # Fallback to demo if API fails
            if "error" in identification:
                demo = self._scan_demo_mode(image_url, image_base64)
                demo["api_error"] = identification.get("error")
                identification = demo
        else:
            identification = self._scan_demo_mode(image_url, image_base64)
        
        if "error" in identification:
            return identification
        
        # Enrich with pricing data
        enriched = self._enrich_with_pricing(identification)
        
        # Calculate grade value analysis
        enriched = self._add_grade_analysis(enriched)
        
        return enriched
    
    def _scan_with_anthropic(
        self,
        image_url: str = None,
        image_base64: str = None,
    ) -> Dict[str, Any]:
        """Scan using Anthropic Claude Vision."""
        if not requests:
            return {"error": "requests library not available"}
        
        try:
            # Build content
            content = []
            
            if image_url:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": image_url,
                    }
                })
            elif image_base64:
                # Detect media type
                media_type = "image/jpeg"
                if image_base64.startswith("/9j/"):
                    media_type = "image/jpeg"
                elif image_base64.startswith("iVBOR"):
                    media_type = "image/png"
                
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64,
                    }
                })
            
            content.append({
                "type": "text",
                "text": CARD_IDENTIFICATION_PROMPT
            })
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [{
                        "role": "user",
                        "content": content,
                    }]
                },
                timeout=30,
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract JSON from response
            text = data["content"][0]["text"]
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return {"error": "Could not parse AI response"}
            
        except Exception as e:
            return {"error": f"Anthropic API error: {str(e)}"}
    
    def _scan_with_openai(
        self,
        image_url: str = None,
        image_base64: str = None,
    ) -> Dict[str, Any]:
        """Scan using OpenAI GPT-4 Vision."""
        if not requests:
            return {"error": "requests library not available"}
        
        try:
            # Build content
            content = [{"type": "text", "text": CARD_IDENTIFICATION_PROMPT}]
            
            if image_url:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
            elif image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                })
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [{
                        "role": "user",
                        "content": content,
                    }],
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract JSON from response
            text = data["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return {"error": "Could not parse AI response"}
            
        except Exception as e:
            return {"error": f"OpenAI API error: {str(e)}"}
    
    def _scan_demo_mode(
        self,
        image_url: str = None,
        image_base64: str = None,
    ) -> Dict[str, Any]:
        """Demo mode - returns sample data when no API key is available."""
        # Return a realistic demo response
        return {
            "card_name": "Charizard ex",
            "pokemon": "Charizard",
            "set_name": "Obsidian Flames",
            "card_number": "223/197",
            "rarity": "Special Art Rare",
            "edition": "Modern",
            "condition": {
                "centering": 8,
                "corners": 9,
                "edges": 8,
                "surface": 9,
            },
            "estimated_grade": 8.5,
            "notable_features": ["Special Art", "Full Art", "Holographic"],
            "confidence": 0.85,
            "notes": "DEMO MODE - Set ANTHROPIC_API_KEY or OPENAI_API_KEY for real scanning",
            "demo_mode": True,
        }
    
    def _enrich_with_pricing(self, identification: Dict[str, Any]) -> Dict[str, Any]:
        """Add pricing data to the identification."""
        result = identification.copy()
        
        card_name = identification.get("card_name", "").lower()
        pokemon = identification.get("pokemon", "").lower()
        set_name = identification.get("set_name", "").lower()
        
        # Try to get pricing from external API
        if PRICE_API_URL and PRICE_API_KEY:
            try:
                response = requests.get(
                    PRICE_API_URL,
                    params={
                        "name": identification.get("card_name"),
                        "set_name": identification.get("set_name"),
                    },
                    headers={"Authorization": f"Bearer {PRICE_API_KEY}"},
                    timeout=10,
                )
                if response.status_code == 200:
                    price_data = response.json()
                    result["pricing"] = {
                        "raw": price_data.get("market_price", 0),
                        "psa_9": price_data.get("psa_9_price", 0),
                        "psa_10": price_data.get("psa_10_price", 0),
                        "source": "PokemonPriceTracker",
                        "last_updated": datetime.now().isoformat(),
                    }
                    return result
            except:
                pass
        
        # Try Pokemon TCG API for basic info
        try:
            search_name = identification.get("card_name", "").replace(" ", "+")
            headers = {"Accept": "application/json"}
            if POKEMON_TCG_API_KEY:
                headers["X-Api-Key"] = POKEMON_TCG_API_KEY
            response = requests.get(
                f"{POKEMON_TCG_API}/cards",
                params={"q": f"name:{search_name}"},
                headers=headers,
                timeout=10,
            )
            if response.status_code == 200:
                cards = response.json().get("data", [])
                if cards:
                    tcg_data = cards[0]
                    tcgplayer = tcg_data.get("tcgplayer", {})
                    prices = tcgplayer.get("prices", {})
                    
                    # Get holofoil or normal prices
                    price_tier = prices.get("holofoil") or prices.get("normal") or {}
                    
                    result["pricing"] = {
                        "raw": price_tier.get("market", 0),
                        "low": price_tier.get("low", 0),
                        "high": price_tier.get("high", 0),
                        "source": "TCGPlayer via Pokemon TCG API",
                        "tcgplayer_url": tcgplayer.get("url"),
                        "last_updated": tcgplayer.get("updatedAt"),
                    }
                    
                    # Add card images
                    result["images"] = tcg_data.get("images", {})
                    
                    return result
        except:
            pass
        
        # Fallback to known cards database
        for known_pokemon, variants in KNOWN_CARDS.items():
            if known_pokemon in pokemon or known_pokemon in card_name:
                for variant_name, variant_data in variants.items():
                    if variant_name in set_name or variant_name in card_name:
                        result["pricing"] = {
                            "raw": variant_data["raw_price"],
                            "psa_9": variant_data["psa_9"],
                            "psa_10": variant_data["psa_10"],
                            "source": "Known Cards Database",
                        }
                        return result
                # Default to first variant
                first_variant = list(variants.values())[0]
                result["pricing"] = {
                    "raw": first_variant["raw_price"],
                    "psa_9": first_variant["psa_9"],
                    "psa_10": first_variant["psa_10"],
                    "source": "Known Cards Database (estimated)",
                }
                return result
        
        # Default pricing
        result["pricing"] = {
            "raw": 5.00,
            "psa_9": 15.00,
            "psa_10": 50.00,
            "source": "Estimated (card not found in database)",
        }
        
        return result
    
    def _add_grade_analysis(self, identification: Dict[str, Any]) -> Dict[str, Any]:
        """Add grade-based value analysis."""
        result = identification.copy()
        
        pricing = result.get("pricing", {})
        raw_price = pricing.get("raw", 0)
        psa_9_price = pricing.get("psa_9", raw_price * 2.5)
        psa_10_price = pricing.get("psa_10", raw_price * 10)
        
        estimated_grade = result.get("estimated_grade", 8)
        
        # Grading costs
        PSA_COST = 25  # Standard tier
        CGC_COST = 20
        BGS_COST = 30
        
        # Estimate value based on grade
        if estimated_grade >= 9.5:
            expected_value = psa_10_price * 0.7  # 70% chance of 10
        elif estimated_grade >= 9.0:
            expected_value = psa_9_price
        elif estimated_grade >= 8.5:
            expected_value = psa_9_price * 0.8
        else:
            expected_value = raw_price * 1.5
        
        result["grade_analysis"] = {
            "estimated_grade": estimated_grade,
            "raw_value": raw_price,
            "graded_value_estimate": round(expected_value, 2),
            "grading_cost": PSA_COST,
            "potential_profit": round(expected_value - raw_price - PSA_COST, 2),
            "worth_grading": expected_value > (raw_price + PSA_COST + 20),  # $20 buffer
            "recommendation": self._get_grading_recommendation(
                estimated_grade, raw_price, psa_9_price, psa_10_price, PSA_COST
            ),
        }
        
        return result
    
    def _get_grading_recommendation(
        self,
        grade: float,
        raw: float,
        psa_9: float,
        psa_10: float,
        cost: float,
    ) -> str:
        """Generate a human-readable grading recommendation."""
        if grade >= 9.5 and (psa_10 - raw - cost) > 50:
            return f"🌟 HIGHLY RECOMMENDED - Potential PSA 10! Could be worth ${psa_10}"
        elif grade >= 9.0 and (psa_9 - raw - cost) > 30:
            return f"✅ RECOMMENDED - Likely PSA 9 worth ${psa_9}"
        elif grade >= 8.5:
            return f"🤔 MAYBE - Grade could go either way. PSA 9: ${psa_9}"
        elif grade >= 8.0:
            return f"⚠️ RISKY - May only get PSA 8. Consider keeping raw."
        else:
            return f"❌ NOT RECOMMENDED - Condition issues detected. Keep raw at ${raw}"
    
    def batch_scan(self, images: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Scan multiple cards.
        
        Args:
            images: List of {"url": "..."} or {"base64": "..."} or {"path": "..."}
        
        Returns:
            List of scan results
        """
        results = []
        
        for img in images:
            result = self.scan_card(
                image_url=img.get("url"),
                image_base64=img.get("base64"),
                image_path=img.get("path"),
            )
            results.append(result)
        
        return results


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing card scanner."""
    import sys
    
    scanner = CardScanner()
    
    if len(sys.argv) > 1:
        # Scan provided URL or file
        arg = sys.argv[1]
        if arg.startswith("http"):
            result = scanner.scan_card(image_url=arg)
        else:
            result = scanner.scan_card(image_path=arg)
    else:
        # Demo scan
        result = scanner.scan_card()
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
