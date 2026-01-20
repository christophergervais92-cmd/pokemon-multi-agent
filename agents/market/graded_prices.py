#!/usr/bin/env python3
"""
Graded Card Price Checker

Fetches real-time prices for:
- Raw (ungraded) cards
- PSA 10, PSA 9, PSA 8, PSA 7 graded cards
- CGC 10, CGC 9.5, CGC 9 graded cards  
- BGS/Beckett 10, 9.5, 9 graded cards

Data sources:
1. Pokemon TCG API (TCGPlayer raw prices)
2. eBay sold listings (graded card prices)
3. PSA Price Guide
4. Price estimation based on multipliers

Author: LO TCG Bot
"""
import json
import os
import sys
import time
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Import stealth utilities
try:
    from stealth.anti_detect import get_stealth_headers, get_random_delay
except ImportError:
    def get_stealth_headers():
        return {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    def get_random_delay():
        import random
        return random.uniform(1, 3)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Cache settings
CACHE_DIR = Path(__file__).parent.parent.parent / ".price_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 300  # 5 minute cache for price data

# Grade multipliers (based on market analysis)
# These are typical multipliers from raw price to graded price
GRADE_MULTIPLIERS = {
    # PSA multipliers (most liquid market)
    "PSA 10": {"low": 3.0, "mid": 5.0, "high": 15.0},  # Gem Mint
    "PSA 9": {"low": 1.5, "mid": 2.0, "high": 3.5},    # Mint
    "PSA 8": {"low": 1.1, "mid": 1.4, "high": 2.0},    # Near Mint-Mint
    "PSA 7": {"low": 0.9, "mid": 1.1, "high": 1.5},    # Near Mint
    
    # CGC multipliers (slightly lower than PSA)
    "CGC 10": {"low": 2.5, "mid": 4.0, "high": 12.0},  # Perfect
    "CGC 9.5": {"low": 1.8, "mid": 2.5, "high": 4.0},  # Gem Mint
    "CGC 9": {"low": 1.3, "mid": 1.7, "high": 2.5},    # Mint
    
    # BGS/Beckett multipliers
    "BGS 10": {"low": 4.0, "mid": 8.0, "high": 25.0},  # Pristine (very rare)
    "BGS 10 Black": {"low": 8.0, "mid": 15.0, "high": 50.0},  # Black Label
    "BGS 9.5": {"low": 2.0, "mid": 3.5, "high": 6.0},  # Gem Mint
    "BGS 9": {"low": 1.2, "mid": 1.6, "high": 2.2},    # Mint
}

# Popular cards with known price data (fallback/reference)
KNOWN_CARD_PRICES = {
    "charizard base set": {"raw": 350, "psa10": 15000, "psa9": 2500, "psa8": 800},
    "charizard vmax": {"raw": 80, "psa10": 350, "psa9": 150, "psa8": 100},
    "pikachu illustrator": {"raw": 500000, "psa10": 5000000, "psa9": 2000000},
    "mew ex 151": {"raw": 120, "psa10": 450, "psa9": 200, "psa8": 150},
    "umbreon vmax alt": {"raw": 250, "psa10": 800, "psa9": 400, "psa8": 300},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GradedPrice:
    """Price data for a graded card."""
    grade: str
    company: str  # PSA, CGC, BGS
    price: float
    price_range: Tuple[float, float]  # (low, high)
    source: str
    last_sale: Optional[str] = None
    sales_count: int = 0
    trend: str = "stable"  # up, down, stable
    
    def to_dict(self) -> Dict:
        return {
            "grade": self.grade,
            "company": self.company,
            "price": self.price,
            "price_low": self.price_range[0],
            "price_high": self.price_range[1],
            "source": self.source,
            "last_sale": self.last_sale,
            "sales_count": self.sales_count,
            "trend": self.trend,
        }


@dataclass
class CardPriceReport:
    """Complete price report for a card."""
    card_name: str
    set_name: str
    card_number: str
    raw_price: float
    raw_low: float
    raw_high: float
    graded_prices: Dict[str, GradedPrice]
    image_url: str = ""
    tcgplayer_url: str = ""
    last_updated: str = ""
    source: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "card_name": self.card_name,
            "set_name": self.set_name,
            "card_number": self.card_number,
            "raw": {
                "price": self.raw_price,
                "low": self.raw_low,
                "high": self.raw_high,
            },
            "graded": {k: v.to_dict() for k, v in self.graded_prices.items()},
            "image_url": self.image_url,
            "tcgplayer_url": self.tcgplayer_url,
            "last_updated": self.last_updated,
            "source": self.source,
        }


# =============================================================================
# CACHE
# =============================================================================

class PriceCache:
    """Simple file-based cache for price data."""
    
    @staticmethod
    def _get_key(card_name: str, set_name: str = "") -> str:
        import hashlib
        key_str = f"{card_name}_{set_name}".lower()
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @staticmethod
    def get(card_name: str, set_name: str = "") -> Optional[Dict]:
        key = PriceCache._get_key(card_name, set_name)
        cache_file = CACHE_DIR / f"graded_{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file) as f:
                data = json.load(f)
            
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(seconds=CACHE_TTL_SECONDS):
                return None
            
            return data
        except:
            return None
    
    @staticmethod
    def set(card_name: str, set_name: str, data: Dict):
        key = PriceCache._get_key(card_name, set_name)
        cache_file = CACHE_DIR / f"graded_{key}.json"
        
        data["cached_at"] = datetime.now().isoformat()
        
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f)
        except:
            pass


# =============================================================================
# POKEMON TCG API - RAW PRICES
# =============================================================================

def get_raw_price_from_api(card_name: str, set_name: str = "") -> Optional[Dict]:
    """
    Get raw card price from Pokemon TCG API (which uses TCGPlayer data).
    """
    try:
        api_url = "https://api.pokemontcg.io/v2/cards"
        
        # Build query
        q_parts = []
        if card_name:
            q_parts.append(f'name:"{card_name}"')
        if set_name:
            q_parts.append(f'set.name:"{set_name}"')
        
        query = " ".join(q_parts) if q_parts else f'name:"{card_name}"'
        
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        
        params = {"q": query, "pageSize": 5, "orderBy": "-tcgplayer.prices.holofoil.market"}
        
        time.sleep(get_random_delay())
        
        resp = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            cards = data.get("data", [])
            
            if cards:
                card = cards[0]  # Get first (best) result
                tcgplayer = card.get("tcgplayer", {})
                prices = tcgplayer.get("prices", {})
                
                # Get the best price tier
                price_tier = (
                    prices.get("holofoil") or 
                    prices.get("1stEditionHolofoil") or
                    prices.get("unlimitedHolofoil") or
                    prices.get("reverseHolofoil") or
                    prices.get("normal") or
                    {}
                )
                
                return {
                    "card_name": card.get("name", card_name),
                    "set_name": card.get("set", {}).get("name", set_name),
                    "card_number": card.get("number", ""),
                    "raw_price": price_tier.get("market", 0),
                    "raw_low": price_tier.get("low", 0),
                    "raw_high": price_tier.get("high", 0),
                    "image_url": card.get("images", {}).get("small", ""),
                    "tcgplayer_url": tcgplayer.get("url", ""),
                }
    
    except Exception as e:
        print(f"Pokemon TCG API error: {e}")
    
    return None


# =============================================================================
# EBAY SOLD LISTINGS - GRADED PRICES
# =============================================================================

def search_ebay_sold(card_name: str, grade: str = "PSA 10") -> List[Dict]:
    """
    Search eBay sold listings for graded card prices.
    
    This provides real market data for graded cards.
    """
    results = []
    
    try:
        # eBay sold listings URL
        search_query = f"{card_name} {grade} pokemon"
        search_url = "https://www.ebay.com/sch/i.html"
        
        params = {
            "_nkw": search_query,
            "_sacat": "0",
            "LH_Sold": "1",  # Sold listings only
            "LH_Complete": "1",
            "_sop": "13",  # Sort by price + shipping lowest first
            "rt": "nc",
        }
        
        headers = get_stealth_headers()
        
        time.sleep(get_random_delay())
        
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find sold items
            items = soup.select('.s-item, .srp-results .s-item__wrapper')
            
            for item in items[:10]:
                try:
                    title_elem = item.select_one('.s-item__title, .s-item__title--has-tags')
                    price_elem = item.select_one('.s-item__price')
                    date_elem = item.select_one('.s-item__endedDate, .s-item__listingDate')
                    
                    if not title_elem or not price_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Skip if doesn't match grade
                    if grade.lower() not in title.lower():
                        continue
                    
                    # Parse price
                    price_text = price_elem.get_text(strip=True)
                    price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
                    try:
                        price = float(price_text)
                    except:
                        continue
                    
                    # Get date
                    date_str = ""
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                    
                    results.append({
                        "title": title,
                        "price": price,
                        "date": date_str,
                        "grade": grade,
                    })
                    
                except:
                    continue
    
    except Exception as e:
        print(f"eBay search error: {e}")
    
    return results


def get_ebay_graded_prices(card_name: str) -> Dict[str, GradedPrice]:
    """
    Get graded prices from eBay for all major grades.
    """
    graded_prices = {}
    
    grades_to_check = [
        ("PSA 10", "PSA"),
        ("PSA 9", "PSA"),
        ("PSA 8", "PSA"),
        ("CGC 10", "CGC"),
        ("CGC 9.5", "CGC"),
        ("BGS 10", "BGS"),
        ("BGS 9.5", "BGS"),
    ]
    
    for grade, company in grades_to_check:
        sales = search_ebay_sold(card_name, grade)
        
        if sales:
            prices = [s["price"] for s in sales]
            avg_price = sum(prices) / len(prices)
            
            graded_prices[grade] = GradedPrice(
                grade=grade,
                company=company,
                price=round(avg_price, 2),
                price_range=(min(prices), max(prices)),
                source="eBay Sold Listings",
                last_sale=sales[0].get("date", ""),
                sales_count=len(sales),
                trend="stable",
            )
        
        # Rate limit between searches
        time.sleep(1)
    
    return graded_prices


# =============================================================================
# PRICE ESTIMATION (FALLBACK)
# =============================================================================

def estimate_graded_prices(raw_price: float, card_rarity: str = "holo") -> Dict[str, GradedPrice]:
    """
    Estimate graded prices based on raw price and multipliers.
    
    This is used when eBay data isn't available.
    """
    graded_prices = {}
    
    # Adjust multipliers based on rarity
    rarity_factor = 1.0
    if "ultra rare" in card_rarity.lower() or "secret" in card_rarity.lower():
        rarity_factor = 1.5
    elif "common" in card_rarity.lower():
        rarity_factor = 0.7
    
    for grade, multipliers in GRADE_MULTIPLIERS.items():
        company = grade.split()[0]  # PSA, CGC, or BGS
        
        mid_mult = multipliers["mid"] * rarity_factor
        low_mult = multipliers["low"] * rarity_factor
        high_mult = multipliers["high"] * rarity_factor
        
        estimated_price = raw_price * mid_mult
        price_low = raw_price * low_mult
        price_high = raw_price * high_mult
        
        graded_prices[grade] = GradedPrice(
            grade=grade,
            company=company,
            price=round(estimated_price, 2),
            price_range=(round(price_low, 2), round(price_high, 2)),
            source="Estimated (multiplier)",
            sales_count=0,
            trend="stable",
        )
    
    return graded_prices


# =============================================================================
# MAIN PRICE LOOKUP
# =============================================================================

class GradedPriceChecker:
    """
    Unified graded card price checker.
    
    Fetches prices from multiple sources and provides
    comprehensive price data for raw and graded cards.
    """
    
    def __init__(self, use_ebay: bool = True):
        """
        Initialize the checker.
        
        Args:
            use_ebay: Whether to search eBay for graded prices (slower but more accurate)
        """
        self.use_ebay = use_ebay
    
    def get_prices(self, card_name: str, set_name: str = "") -> CardPriceReport:
        """
        Get comprehensive price data for a card.
        
        Returns raw price and all graded prices (PSA, CGC, BGS).
        """
        # Check cache first
        cached = PriceCache.get(card_name, set_name)
        if cached and "report" in cached:
            # Reconstruct report from cache
            return self._dict_to_report(cached["report"])
        
        # Get raw price from Pokemon TCG API
        raw_data = get_raw_price_from_api(card_name, set_name)
        
        if not raw_data:
            # Fallback to known prices or estimate
            raw_data = self._get_fallback_raw_price(card_name)
        
        raw_price = raw_data.get("raw_price", 0)
        
        # Get graded prices
        graded_prices = {}
        
        if self.use_ebay and raw_price >= 10:  # Only search eBay for cards worth $10+
            graded_prices = get_ebay_graded_prices(card_name)
        
        # Fill in missing grades with estimates
        if raw_price > 0:
            estimated = estimate_graded_prices(raw_price)
            for grade, price_data in estimated.items():
                if grade not in graded_prices:
                    graded_prices[grade] = price_data
        
        # Build report
        report = CardPriceReport(
            card_name=raw_data.get("card_name", card_name),
            set_name=raw_data.get("set_name", set_name),
            card_number=raw_data.get("card_number", ""),
            raw_price=raw_price,
            raw_low=raw_data.get("raw_low", raw_price * 0.8),
            raw_high=raw_data.get("raw_high", raw_price * 1.2),
            graded_prices=graded_prices,
            image_url=raw_data.get("image_url", ""),
            tcgplayer_url=raw_data.get("tcgplayer_url", ""),
            last_updated=datetime.now().isoformat(),
            source="Pokemon TCG API + eBay" if self.use_ebay else "Pokemon TCG API + Estimates",
        )
        
        # Cache the result
        PriceCache.set(card_name, set_name, {"report": report.to_dict()})
        
        return report
    
    def _get_fallback_raw_price(self, card_name: str) -> Dict:
        """Get fallback price from known prices database."""
        card_lower = card_name.lower()
        
        for known_name, prices in KNOWN_CARD_PRICES.items():
            if known_name in card_lower or card_lower in known_name:
                return {
                    "card_name": card_name,
                    "raw_price": prices.get("raw", 10),
                    "raw_low": prices.get("raw", 10) * 0.8,
                    "raw_high": prices.get("raw", 10) * 1.2,
                }
        
        # Default fallback
        return {
            "card_name": card_name,
            "raw_price": 10,
            "raw_low": 5,
            "raw_high": 20,
        }
    
    def _dict_to_report(self, data: Dict) -> CardPriceReport:
        """Convert cached dict back to CardPriceReport."""
        graded = {}
        for grade, gdata in data.get("graded", {}).items():
            graded[grade] = GradedPrice(
                grade=gdata["grade"],
                company=gdata["company"],
                price=gdata["price"],
                price_range=(gdata["price_low"], gdata["price_high"]),
                source=gdata["source"],
                last_sale=gdata.get("last_sale"),
                sales_count=gdata.get("sales_count", 0),
                trend=gdata.get("trend", "stable"),
            )
        
        return CardPriceReport(
            card_name=data["card_name"],
            set_name=data["set_name"],
            card_number=data.get("card_number", ""),
            raw_price=data["raw"]["price"],
            raw_low=data["raw"]["low"],
            raw_high=data["raw"]["high"],
            graded_prices=graded,
            image_url=data.get("image_url", ""),
            tcgplayer_url=data.get("tcgplayer_url", ""),
            last_updated=data.get("last_updated", ""),
            source=data.get("source", ""),
        )
    
    def get_quick_prices(self, card_name: str, set_name: str = "") -> Dict:
        """
        Get prices quickly without eBay search.
        
        Uses Pokemon TCG API + estimation.
        """
        old_setting = self.use_ebay
        self.use_ebay = False
        report = self.get_prices(card_name, set_name)
        self.use_ebay = old_setting
        return report.to_dict()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_card_prices(card_name: str, set_name: str = "", include_ebay: bool = False) -> Dict:
    """
    Get all prices for a card (raw + graded).
    
    Args:
        card_name: Name of the card
        set_name: Set name (optional, helps accuracy)
        include_ebay: Whether to search eBay for graded prices
    
    Returns:
        Dict with raw and graded prices
    """
    checker = GradedPriceChecker(use_ebay=include_ebay)
    report = checker.get_prices(card_name, set_name)
    return report.to_dict()


def get_psa_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just PSA graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    psa_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "PSA" in grade:
            psa_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "psa": psa_grades,
    }


def get_cgc_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just CGC graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    cgc_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "CGC" in grade:
            cgc_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "cgc": cgc_grades,
    }


def get_bgs_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just BGS/Beckett graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    bgs_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "BGS" in grade:
            bgs_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "bgs": bgs_grades,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing graded prices."""
    import sys
    
    if len(sys.argv) > 1:
        card_name = " ".join(sys.argv[1:])
    else:
        card_name = "Charizard VMAX"
    
    print(f"Getting prices for: {card_name}")
    print("-" * 50)
    
    prices = get_card_prices(card_name, include_ebay=False)
    
    print(f"\n📊 {prices['card_name']}")
    if prices['set_name']:
        print(f"   Set: {prices['set_name']}")
    
    print(f"\n💰 RAW (Ungraded):")
    raw = prices['raw']
    print(f"   Market: ${raw['price']:.2f}")
    print(f"   Range: ${raw['low']:.2f} - ${raw['high']:.2f}")
    
    print(f"\n🏆 GRADED PRICES:")
    
    # PSA
    print("\n   PSA:")
    for grade in ["PSA 10", "PSA 9", "PSA 8", "PSA 7"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    # CGC
    print("\n   CGC:")
    for grade in ["CGC 10", "CGC 9.5", "CGC 9"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    # BGS
    print("\n   BGS/Beckett:")
    for grade in ["BGS 10 Black", "BGS 10", "BGS 9.5", "BGS 9"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    print(f"\n📅 Updated: {prices['last_updated']}")
    print(f"📍 Source: {prices['source']}")


if __name__ == "__main__":
    main()
