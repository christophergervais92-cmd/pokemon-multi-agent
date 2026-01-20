#!/usr/bin/env python3
"""
Unified Stock Checker - Optimized Multi-Retailer Scanner

Checks stock from multiple sources:
1. Target (Redsky API) - Real stock data
2. Best Buy (API/Scrape) - Real stock data
3. GameStop (Scrape) - Real stock data
4. Pokemon Center (Scrape) - Real stock data
5. TCGPlayer (Scrape) - Card singles availability
6. Pokemon TCG API - Card data + TCGPlayer prices

All individual scanner files have been consolidated here.
"""
import json
import os
import sys
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
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

# Stealth utilities
try:
    from stealth.anti_detect import get_stealth_headers, get_random_delay
except ImportError:
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    def get_stealth_headers():
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    def get_random_delay():
        return random.uniform(MIN_DELAY, MAX_DELAY)


# =============================================================================
# CONFIGURATION
# =============================================================================

CACHE_DIR = Path(__file__).parent.parent.parent / ".stock_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 30  # 30 second cache for faster updates

# Fast mode - minimal delays, higher risk of blocks
FAST_MODE = os.environ.get("FAST_SCAN", "true").lower() == "true"
MIN_DELAY = 0.1 if FAST_MODE else 0.5
MAX_DELAY = 0.3 if FAST_MODE else 2.0


@dataclass
class Product:
    """Standardized product data."""
    name: str
    retailer: str
    price: float
    url: str
    sku: str = ""
    stock: bool = False
    stock_status: str = "Unknown"
    image_url: str = ""
    category: str = "TCG"
    last_checked: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# CACHE
# =============================================================================

class Cache:
    @staticmethod
    def key(retailer: str, query: str = "") -> str:
        return hashlib.md5(f"{retailer}_{query}".lower().encode()).hexdigest()
    
    @staticmethod
    def get(retailer: str, query: str = "") -> Optional[List[Dict]]:
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file) as f:
                data = json.load(f)
            if datetime.now() - datetime.fromisoformat(data["ts"]) > timedelta(seconds=CACHE_TTL_SECONDS):
                return None
            return data["products"]
        except:
            return None
    
    @staticmethod
    def set(retailer: str, query: str, products: List[Dict]):
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({"ts": datetime.now().isoformat(), "products": products}, f)
        except:
            pass


# =============================================================================
# TARGET - REDSKY API (WORKING)
# =============================================================================

def scan_target(query: str = "pokemon trading cards", zip_code: str = "90210") -> List[Product]:
    """
    Scan Target using Redsky API.
    
    This API is still functional as of 2026.
    Requires: key, channel, keyword, page, pricing_store_id
    """
    products = []
    
    cached = Cache.get("target", query)
    if cached:
        return [Product(**p) for p in cached]
    
    try:
        api_url = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
        
        params = {
            "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
            "channel": "WEB",
            "count": 24,
            "default_purchasability_filter": "true",
            "keyword": query,
            "offset": 0,
            "page": f"/s/{query.replace(' ', '+')}",
            "platform": "desktop",
            "pricing_store_id": "911",
            "visitor_id": f"PKM_{int(time.time())}",
            "zip": zip_code,
        }
        
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        
        time.sleep(get_random_delay())
        resp = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("search", {}).get("products", [])
            
            for item in items:
                p = item.get("item", {})
                title = p.get("product_description", {}).get("title", "")
                
                if "pokemon" not in title.lower():
                    continue
                
                price_data = p.get("price", {})
                fulfillment = p.get("fulfillment", {})
                
                # Check stock
                ship_ok = fulfillment.get("shipping_options", {}).get("availability_status", "") == "IN_STOCK"
                pickup_ok = "IN_STOCK" in str(fulfillment.get("store_options", []))
                in_stock = ship_ok or pickup_ok
                
                # Get URL - handle both relative and absolute URLs
                buy_url = p.get('enrichment', {}).get('buy_url', '')
                if buy_url.startswith('http'):
                    product_url = buy_url
                elif buy_url:
                    product_url = f"https://www.target.com{buy_url}"
                else:
                    tcin = p.get("tcin", "")
                    product_url = f"https://www.target.com/p/-/A-{tcin}" if tcin else ""
                
                products.append(Product(
                    name=title,
                    retailer="Target",
                    price=price_data.get("current_retail", 0) or price_data.get("reg_retail", 0) or price_data.get("formatted_current_price_default_message", "").replace("$", "").replace(",", "") or 0,
                    url=product_url,
                    sku=p.get("tcin", ""),
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    image_url=p.get("enrichment", {}).get("images", {}).get("primary_image_url", ""),
                    last_checked=datetime.now().isoformat(),
                ))
        
        if products:
            Cache.set("target", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Target error: {e}")
    
    return products


# =============================================================================
# BEST BUY - API/SCRAPE
# =============================================================================

def scan_bestbuy(query: str = "pokemon trading cards") -> List[Product]:
    """
    Scan Best Buy.
    
    Uses their API if key available, otherwise scrapes.
    """
    products = []
    
    cached = Cache.get("bestbuy", query)
    if cached:
        return [Product(**p) for p in cached]
    
    api_key = os.environ.get("BESTBUY_API_KEY", "")
    
    try:
        if api_key:
            # Use official API
            url = f"https://api.bestbuy.com/v1/products((search={query}))"
            params = {
                "apiKey": api_key,
                "format": "json",
                "show": "sku,name,salePrice,url,inStoreAvailability,onlineAvailability,image",
                "pageSize": 20,
            }
            
            time.sleep(get_random_delay())
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("products", []):
                    if "pokemon" in item.get("name", "").lower():
                        in_stock = item.get("onlineAvailability", False)
                        products.append(Product(
                            name=item.get("name", ""),
                            retailer="Best Buy",
                            price=item.get("salePrice", 0),
                            url=item.get("url", ""),
                            sku=str(item.get("sku", "")),
                            stock=in_stock,
                            stock_status="In Stock" if in_stock else "Out of Stock",
                            image_url=item.get("image", ""),
                            last_checked=datetime.now().isoformat(),
                        ))
        else:
            # Scrape fallback
            search_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={query.replace(' ', '+')}"
            headers = get_stealth_headers()
            
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
            
            if resp.status_code == 200 and BS4_AVAILABLE:
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select('.sku-item, .list-item')
                
                for item in items[:20]:
                    name_elem = item.select_one('.sku-title a, .sku-header a')
                    price_elem = item.select_one('[data-price], .priceView-customer-price span')
                    
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True)
                    if "pokemon" not in name.lower():
                        continue
                    
                    price = 0
                    if price_elem:
                        price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                        try:
                            price = float(price_text) if price_text else 0
                        except:
                            pass
                    
                    url = name_elem.get('href', '')
                    if not url.startswith('http'):
                        url = f"https://www.bestbuy.com{url}"
                    
                    # Check for add to cart button
                    cart_btn = item.select_one('.add-to-cart-button:not(.btn-disabled)')
                    in_stock = cart_btn is not None
                    
                    products.append(Product(
                        name=name,
                        retailer="Best Buy",
                        price=price,
                        url=url,
                        stock=in_stock,
                        stock_status="In Stock" if in_stock else "Out of Stock",
                        last_checked=datetime.now().isoformat(),
                    ))
        
        if products:
            Cache.set("bestbuy", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Best Buy error: {e}")
    
    return products


# =============================================================================
# GAMESTOP - SCRAPE
# =============================================================================

def scan_gamestop(query: str = "pokemon cards") -> List[Product]:
    """Scan GameStop by scraping."""
    products = []
    
    cached = Cache.get("gamestop", query)
    if cached:
        return [Product(**p) for p in cached]
    
    try:
        search_url = f"https://www.gamestop.com/search/?q={query.replace(' ', '+')}"
        headers = get_stealth_headers()
        
        time.sleep(get_random_delay())
        resp = requests.get(search_url, headers=headers, timeout=15)
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.product-tile, [data-product-tile]')
            
            for item in items[:20]:
                name_elem = item.select_one('.product-name a, .product-tile-name a, h3 a')
                price_elem = item.select_one('.actual-price, .price-sales')
                
                if not name_elem:
                    continue
                
                name = name_elem.get_text(strip=True)
                if "pokemon" not in name.lower():
                    continue
                
                price = 0
                if price_elem:
                    price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                    try:
                        price = float(price_text) if price_text else 0
                    except:
                        pass
                
                url = name_elem.get('href', '')
                if not url.startswith('http'):
                    url = f"https://www.gamestop.com{url}"
                
                # Check availability
                avail_elem = item.select_one('.add-to-cart, .availability-message')
                in_stock = avail_elem is not None and 'unavailable' not in (avail_elem.get_text() or '').lower()
                
                products.append(Product(
                    name=name,
                    retailer="GameStop",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    last_checked=datetime.now().isoformat(),
                ))
        
        if products:
            Cache.set("gamestop", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"GameStop error: {e}")
    
    return products


# =============================================================================
# POKEMON CENTER - SCRAPE
# =============================================================================

def scan_pokemoncenter(query: str = "trading cards") -> List[Product]:
    """Scan Pokemon Center official store."""
    products = []
    
    cached = Cache.get("pokemoncenter", query)
    if cached:
        return [Product(**p) for p in cached]
    
    try:
        search_url = f"https://www.pokemoncenter.com/search/{query.replace(' ', '%20')}"
        headers = get_stealth_headers()
        headers["Accept"] = "text/html,application/xhtml+xml"
        
        time.sleep(get_random_delay())
        resp = requests.get(search_url, headers=headers, timeout=15)
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('[data-testid="product-card"], .product-card, .product-tile')
            
            for item in items[:20]:
                name_elem = item.select_one('h2, h3, .product-name, [data-testid="product-name"]')
                price_elem = item.select_one('[data-testid="price"], .price, .product-price')
                link_elem = item.select_one('a[href*="/product/"]')
                
                if not name_elem:
                    continue
                
                name = name_elem.get_text(strip=True)
                
                price = 0
                if price_elem:
                    price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                    try:
                        price = float(price_text) if price_text else 0
                    except:
                        pass
                
                url = "https://www.pokemoncenter.com"
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        url = f"https://www.pokemoncenter.com{href}"
                    elif href.startswith('http'):
                        url = href
                
                # Check stock
                oos_elem = item.select_one('.out-of-stock, [data-testid="out-of-stock"]')
                in_stock = oos_elem is None and price > 0
                
                products.append(Product(
                    name=name,
                    retailer="Pokemon Center",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    last_checked=datetime.now().isoformat(),
                ))
        
        if products:
            Cache.set("pokemoncenter", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Pokemon Center error: {e}")
    
    return products


# =============================================================================
# POKEMON TCG API - CARD DATA + TCGPLAYER PRICES
# =============================================================================

def scan_cards(card_name: str = "", set_name: str = "") -> List[Product]:
    """
    Get card data from Pokemon TCG API.
    
    This is free and reliable for card information and TCGPlayer prices.
    """
    products = []
    
    query = f"{card_name}_{set_name}"
    cached = Cache.get("pokemontcgapi", query)
    if cached:
        return [Product(**p) for p in cached]
    
    try:
        api_url = "https://api.pokemontcg.io/v2/cards"
        
        q_parts = []
        if card_name:
            q_parts.append(f'name:"{card_name}"')
        if set_name:
            q_parts.append(f'set.name:"{set_name}"')
        
        q = " ".join(q_parts) if q_parts else "supertype:pokemon"
        
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        
        params = {"q": q, "pageSize": 20, "orderBy": "-tcgplayer.prices.holofoil.market"}
        
        time.sleep(get_random_delay())
        resp = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            
            for card in data.get("data", []):
                tcgplayer = card.get("tcgplayer", {})
                prices = tcgplayer.get("prices", {})
                
                # Get best price tier
                price_tier = prices.get("holofoil") or prices.get("normal") or prices.get("reverseHolofoil") or {}
                market_price = price_tier.get("market", 0)
                
                products.append(Product(
                    name=f"{card.get('name', '')} - {card.get('set', {}).get('name', '')}",
                    retailer="TCGPlayer",
                    price=market_price,
                    url=tcgplayer.get("url", ""),
                    sku=card.get("id", ""),
                    stock=market_price > 0,
                    stock_status="Available" if market_price > 0 else "Check Site",
                    image_url=card.get("images", {}).get("small", ""),
                    category="Singles",
                    last_checked=datetime.now().isoformat(),
                ))
        
        if products:
            Cache.set("pokemontcgapi", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Pokemon TCG API error: {e}")
    
    return products


# =============================================================================
# UNIFIED SCANNER
# =============================================================================

class StockChecker:
    """Unified stock checker for all retailers."""
    
    RETAILERS = {
        "target": scan_target,
        "bestbuy": scan_bestbuy,
        "gamestop": scan_gamestop,
        "pokemoncenter": scan_pokemoncenter,
        "tcgplayer": scan_cards,
    }
    
    def __init__(self, zip_code: str = "90210"):
        self.zip_code = zip_code
    
    def scan_all(self, query: str = "pokemon trading cards") -> Dict[str, Any]:
        """Scan all retailers for Pokemon products."""
        all_products = []
        results = {}
        errors = []
        
        for name, scan_func in self.RETAILERS.items():
            try:
                if name == "target":
                    products = scan_func(query, self.zip_code)
                elif name == "tcgplayer":
                    # For cards, extract card name from query
                    card_query = query.replace("pokemon", "").replace("trading cards", "").strip()
                    products = scan_func(card_query or "charizard")
                else:
                    products = scan_func(query)
                
                results[name] = {
                    "count": len(products),
                    "in_stock": len([p for p in products if p.stock]),
                }
                all_products.extend([p.to_dict() for p in products])
                
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        # Deduplicate
        seen = set()
        unique = []
        for p in all_products:
            key = p["name"].lower()[:40]
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        in_stock = [p for p in unique if p.get("stock")]
        
        return {
            "success": True,
            "query": query,
            "zip_code": self.zip_code,
            "total": len(unique),
            "in_stock_count": len(in_stock),
            "by_retailer": results,
            "products": unique,
            "in_stock_only": in_stock,
            "errors": errors if errors else None,
            "checked_at": datetime.now().isoformat(),
        }
    
    def scan_retailer(self, retailer: str, query: str) -> Dict[str, Any]:
        """Scan specific retailer."""
        retailer_key = retailer.lower().replace(" ", "")
        
        if retailer_key not in self.RETAILERS:
            return {"error": f"Unknown retailer: {retailer}", "available": list(self.RETAILERS.keys())}
        
        try:
            scan_func = self.RETAILERS[retailer_key]
            if retailer_key == "target":
                products = scan_func(query, self.zip_code)
            else:
                products = scan_func(query)
            
            return {
                "success": True,
                "retailer": retailer,
                "query": query,
                "total": len(products),
                "in_stock": len([p for p in products if p.stock]),
                "products": [p.to_dict() for p in products],
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def scan_all(query: str = "pokemon trading cards", zip_code: str = "90210") -> Dict[str, Any]:
    """Main entry point - scan all retailers."""
    return StockChecker(zip_code).scan_all(query)


def scan_retailer(retailer: str, query: str, zip_code: str = "90210") -> Dict[str, Any]:
    """Scan specific retailer."""
    return StockChecker(zip_code).scan_retailer(retailer, query)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "pokemon elite trainer box"
    result = scan_all(query)
    print(json.dumps(result, indent=2))
