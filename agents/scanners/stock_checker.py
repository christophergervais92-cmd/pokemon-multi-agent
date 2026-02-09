#!/usr/bin/env python3
"""
Unified Stock Checker - Optimized Multi-Retailer Scanner

Checks stock from multiple sources:
1. Target (Redsky API) - Real stock data
2. Walmart (Search API) - Real stock data
3. Best Buy (API/Scrape) - Real stock data
4. GameStop (Scrape) - Real stock data
5. Pokemon Center (Scrape) - Real stock data
6. TCGPlayer (Scrape) - Card singles availability
7. Pokemon TCG API - Card data + TCGPlayer prices

All individual scanner files have been consolidated here.
Optimized with parallel scanning, connection pooling, and retry logic.
"""
import json
import os
import sys
import time
import random
import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

CACHE_DIR = Path(__file__).parent.parent.parent / ".stock_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 180  # 3 minute cache for better performance

# Pokemon TCG API Key (get free key at https://dev.pokemontcg.io)
# Without key: 1000 requests/day, 30/minute - WITH key: 20,000/day
POKEMON_TCG_API_KEY = os.environ.get("POKEMON_TCG_API_KEY", "")

# Fast mode - minimal delays, higher risk of blocks
FAST_MODE = os.environ.get("FAST_SCAN", "true").lower() == "true"
MIN_DELAY = 0.05 if FAST_MODE else 0.3
MAX_DELAY = 0.15 if FAST_MODE else 1.0

# Parallel scanning config
MAX_WORKERS = 6  # Scan up to 6 retailers simultaneously
REQUEST_TIMEOUT = 12  # Seconds

# Retry configuration
MAX_RETRIES = 2
RETRY_BACKOFF = 0.5  # Seconds between retries

# Stealth utilities
try:
    from stealth.anti_detect import get_stealth_headers, get_random_delay
except ImportError:
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ]
    def get_stealth_headers():
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
    def get_random_delay():
        return random.uniform(MIN_DELAY, MAX_DELAY)


# =============================================================================
# SESSION POOL - Connection Reuse
# =============================================================================

_session_pool: Dict[str, requests.Session] = {}

def get_session(retailer: str = "default") -> requests.Session:
    """Get or create a session with retry logic for a retailer."""
    global _session_pool
    
    if retailer not in _session_pool:
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        _session_pool[retailer] = session
    
    return _session_pool[retailer]


def close_sessions():
    """Close all sessions (call on shutdown)."""
    global _session_pool
    for session in _session_pool.values():
        session.close()
    _session_pool = {}


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
    relevance_score: int = 0  # For sorting by relevance
    
    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# CACHE - With TTL Support
# =============================================================================

class Cache:
    @staticmethod
    def key(retailer: str, query: str = "") -> str:
        return hashlib.md5(f"{retailer}_{query}".lower().encode()).hexdigest()
    
    @staticmethod
    def get(retailer: str, query: str = "", ttl_override: int = None) -> Optional[List[Dict]]:
        """Get cached data if not expired."""
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file) as f:
                data = json.load(f)
            ttl = ttl_override if ttl_override is not None else CACHE_TTL_SECONDS
            if datetime.now() - datetime.fromisoformat(data["ts"]) > timedelta(seconds=ttl):
                return None
            return data["products"]
        except Exception:
            return None
    
    @staticmethod
    def set(retailer: str, query: str, products: List[Dict]):
        """Cache products with timestamp."""
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({"ts": datetime.now().isoformat(), "products": products}, f)
        except Exception:
            pass
    
    @staticmethod
    def clear(retailer: str = None):
        """Clear cache for retailer or all."""
        try:
            if retailer:
                for f in CACHE_DIR.glob(f"*{retailer}*.json"):
                    f.unlink()
            else:
                for f in CACHE_DIR.glob("*.json"):
                    f.unlink()
        except Exception:
            pass


# =============================================================================
# TARGET - REDSKY API (WORKING)
# =============================================================================

TARGET_REDSKY_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"

_target_store_cache: Dict[str, Tuple[str, float]] = {}  # zip -> (store_id, ts)
_TARGET_STORE_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h

def _get_target_store_id(zip_code: str, session: requests.Session) -> str:
    """
    Resolve a physical Target store_id near the given ZIP.
    Needed for fulfillment lookups (digital store_ids are rejected).
    """
    zip_code = (zip_code or "").strip() or "90210"
    now = time.time()
    cached = _target_store_cache.get(zip_code)
    if cached and (now - cached[1]) < _TARGET_STORE_CACHE_TTL_SECONDS:
        return cached[0]

    try:
        url = "https://redsky.target.com/redsky_aggregations/v1/web/nearby_stores_v1"
        params = {
            "key": TARGET_REDSKY_KEY,
            "place": zip_code,
            "limit": 1,
            "within": 50,
        }
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        resp = session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            stores = (data.get("data", {}) or {}).get("nearby_stores", {}).get("stores", []) or []
            store_id = str(stores[0].get("store_id")) if stores else ""
            if store_id:
                _target_store_cache[zip_code] = (store_id, now)
                return store_id
    except Exception as e:
        print(f"Target store lookup error: {e}")

    # Fallback: commonly-used store id (kept for backward compatibility)
    _target_store_cache[zip_code] = ("911", now)
    return "911"


def _get_target_fulfillment(tcins: List[str], store_id: str, zip_code: str, session: requests.Session) -> Dict[str, Dict]:
    """
    Fetch fulfillment (ship/pickup/in-store) status for multiple tcins.
    """
    tcins = [str(t).strip() for t in (tcins or []) if str(t).strip()]
    if not tcins:
        return {}

    try:
        url = "https://redsky.target.com/redsky_aggregations/v1/web/product_summary_with_fulfillment_v1"
        params = {
            "key": TARGET_REDSKY_KEY,
            "tcins": ",".join(tcins[:24]),
            "store_id": str(store_id or "911"),
            "zip": str(zip_code or "90210"),
        }
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        resp = session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return {}

        data = resp.json()
        summaries = (data.get("data", {}) or {}).get("product_summaries", []) or []
        out: Dict[str, Dict] = {}
        for s in summaries:
            tcin = str(s.get("tcin") or "").strip()
            if not tcin:
                continue
            out[tcin] = s.get("fulfillment") or {}
        return out
    except Exception as e:
        print(f"Target fulfillment lookup error: {e}")
        return {}


def scan_target(query: str = "pokemon trading cards", zip_code: str = "90210") -> List[Product]:
    """
    Scan Target using Redsky API.
    Uses session pooling and retry logic.
    """
    products = []
    
    cached = Cache.get("target", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("target")
    
    try:
        api_url = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
        
        params = {
            "key": TARGET_REDSKY_KEY,
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
        resp = session.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("search", {}).get("products", [])

            tcins: List[str] = []
            raw_rows: List[Dict[str, Any]] = []

            for item in items:
                p = item.get("item", {})
                title = p.get("product_description", {}).get("title", "")
                
                if "pokemon" not in title.lower() and "pokémon" not in title.lower():
                    continue
                
                tcin = str(item.get("tcin") or "").strip()
                if tcin:
                    tcins.append(tcin)
                
                # Get URL
                buy_url = p.get('enrichment', {}).get('buy_url', '')
                if buy_url.startswith('http'):
                    product_url = buy_url
                elif buy_url:
                    product_url = f"https://www.target.com{buy_url}"
                else:
                    tcin = p.get("tcin", "")
                    product_url = f"https://www.target.com/p/-/A-{tcin}" if tcin else ""
                
                # Price lives on the top-level product record (not inside item)
                price_data = item.get("price", {}) or {}
                price_val = price_data.get("current_retail", 0) or price_data.get("reg_retail", 0)
                if not price_val:
                    price_str = price_data.get("formatted_current_price_default_message", "")
                    price_val = float(''.join(c for c in price_str if c.isdigit() or c == '.') or '0')

                raw_rows.append({
                    "tcin": tcin,
                    "title": title,
                    "price": float(price_val) if price_val else 0,
                    "url": product_url,
                    "image_url": p.get("enrichment", {}).get("images", {}).get("primary_image_url", ""),
                })

            # Enrich with fulfillment (ship/pickup) data.
            store_id = _get_target_store_id(zip_code, session)
            fulfillment_map = _get_target_fulfillment(tcins, store_id=store_id, zip_code=zip_code, session=session)

            for row in raw_rows:
                tcin = row.get("tcin", "")
                fulfillment = fulfillment_map.get(tcin, {}) or {}
                ship_status = (fulfillment.get("shipping_options") or {}).get("availability_status", "")
                sold_out = bool(fulfillment.get("sold_out", False))
                store_options = fulfillment.get("store_options") or []

                pickup_statuses = []
                in_store_statuses = []
                for opt in store_options:
                    pickup_statuses.append(((opt.get("order_pickup") or {}).get("availability_status") or ""))
                    in_store_statuses.append(((opt.get("in_store_only") or {}).get("availability_status") or ""))

                in_stock_ship = ship_status == "IN_STOCK"
                in_stock_pickup = any(s == "IN_STOCK" for s in pickup_statuses)
                in_stock_in_store = any(s == "IN_STOCK" for s in in_store_statuses)
                in_stock = (not sold_out) and (in_stock_ship or in_stock_pickup or in_stock_in_store)

                if sold_out:
                    stock_status = "Sold Out"
                elif in_stock_ship:
                    stock_status = "In Stock (Ship)"
                elif in_stock_pickup:
                    stock_status = "In Stock (Pickup)"
                elif in_stock_in_store:
                    stock_status = "In Stock (In Store)"
                else:
                    stock_status = "Out of Stock"

                products.append(Product(
                    name=row.get("title") or "",
                    retailer="Target",
                    price=row.get("price") or 0,
                    url=row.get("url") or "",
                    sku=tcin,
                    stock=in_stock,
                    stock_status=stock_status,
                    image_url=row.get("image_url") or "",
                    last_checked=datetime.now().isoformat(),
                ))
        
        if products:
            Cache.set("target", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Target error: {e}")
    
    return products


# =============================================================================
# WALMART - SEARCH API
# =============================================================================

def scan_walmart(query: str = "pokemon trading cards") -> List[Product]:
    """
    Scan Walmart using their search endpoint.
    Uses session pooling and retry logic.
    """
    products = []
    
    cached = Cache.get("walmart", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("walmart")
    
    try:
        # Walmart's search API endpoint
        search_url = "https://www.walmart.com/orchestra/home/graphql"
        
        headers = get_stealth_headers()
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-O-CORRELATION-ID": f"pkm-{int(time.time())}",
            "X-O-SEGMENT": "oaoh",
            "Referer": f"https://www.walmart.com/search?q={query.replace(' ', '+')}",
        })
        
        # GraphQL query for search
        payload = {
            "query": """query Search($query: String!, $page: Int, $prg: Prg!, $facet: String) {
                search(query: $query, page: $page, prg: $prg, facet: $facet) {
                    searchResult {
                        itemStacks {
                            items {
                                name
                                canonicalUrl
                                usItemId
                                priceInfo { currentPrice { price } }
                                availabilityStatusV2 { value }
                                imageInfo { thumbnailUrl }
                            }
                        }
                    }
                }
            }""",
            "variables": {
                "query": query,
                "page": 1,
                "prg": "desktop",
                "facet": ""
            }
        }
        
        time.sleep(get_random_delay())
        resp = session.post(search_url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if resp.status_code == 200:
            data = resp.json()
            stacks = data.get("data", {}).get("search", {}).get("searchResult", {}).get("itemStacks", [])
            
            for stack in stacks:
                for item in stack.get("items", [])[:24]:
                    name = item.get("name", "")
                    
                    if "pokemon" not in name.lower() and "pokémon" not in name.lower():
                        continue
                    
                    price_info = item.get("priceInfo", {}).get("currentPrice", {})
                    avail = item.get("availabilityStatusV2", {}).get("value", "")
                    in_stock = avail.upper() in ["IN_STOCK", "AVAILABLE"]
                    
                    url = item.get("canonicalUrl", "")
                    if url and not url.startswith("http"):
                        url = f"https://www.walmart.com{url}"
                    
                    products.append(Product(
                        name=name,
                        retailer="Walmart",
                        price=price_info.get("price", 0) or 0,
                        url=url,
                        sku=item.get("usItemId", ""),
                        stock=in_stock,
                        stock_status="In Stock" if in_stock else "Out of Stock",
                        image_url=item.get("imageInfo", {}).get("thumbnailUrl", ""),
                        last_checked=datetime.now().isoformat(),
                    ))
        
        # Fallback to scraping if GraphQL fails
        if not products:
            products = _scan_walmart_scrape(query, session)
        
        if products:
            Cache.set("walmart", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Walmart error: {e}")
        # Try scrape fallback
        try:
            products = _scan_walmart_scrape(query, session)
            if products:
                Cache.set("walmart", query, [p.to_dict() for p in products])
        except Exception as e2:
            print(f"Walmart scrape fallback error: {e2}")
    
    return products


def _scan_walmart_scrape(query: str, session: requests.Session) -> List[Product]:
    """Fallback scraping for Walmart."""
    products = []
    
    if not BS4_AVAILABLE:
        return products
    
    try:
        search_url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
        headers = get_stealth_headers()
        
        time.sleep(get_random_delay())
        resp = session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for product data in script tags
            for script in soup.find_all('script', type='application/json'):
                try:
                    data = json.loads(script.string or '{}')
                    # Parse Walmart's embedded JSON data
                    items = _extract_walmart_items(data)
                    for item in items:
                        if "pokemon" in item.get("name", "").lower():
                            products.append(Product(
                                name=item.get("name", ""),
                                retailer="Walmart",
                                price=item.get("price", 0),
                                url=item.get("url", ""),
                                sku=item.get("sku", ""),
                                stock=item.get("in_stock", False),
                                stock_status="In Stock" if item.get("in_stock") else "Out of Stock",
                                image_url=item.get("image", ""),
                                last_checked=datetime.now().isoformat(),
                            ))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Walmart scrape error: {e}")
    
    return products


def _extract_walmart_items(data: dict, items: list = None) -> list:
    """Recursively extract product items from Walmart's JSON."""
    if items is None:
        items = []
    
    if isinstance(data, dict):
        # Check if this looks like a product
        if "name" in data and ("usItemId" in data or "canonicalUrl" in data):
            price = 0
            if "priceInfo" in data:
                price = data["priceInfo"].get("currentPrice", {}).get("price", 0)
            elif "price" in data:
                price = data.get("price", 0)
            
            items.append({
                "name": data.get("name", ""),
                "price": price,
                "url": f"https://www.walmart.com{data.get('canonicalUrl', '')}" if data.get('canonicalUrl') else "",
                "sku": data.get("usItemId", ""),
                "in_stock": data.get("availabilityStatusV2", {}).get("value", "").upper() in ["IN_STOCK", "AVAILABLE"],
                "image": data.get("imageInfo", {}).get("thumbnailUrl", ""),
            })
        
        # Recurse into dict values
        for v in data.values():
            _extract_walmart_items(v, items)
    
    elif isinstance(data, list):
        for item in data:
            _extract_walmart_items(item, items)
    
    return items[:24]  # Limit results


# =============================================================================
# BEST BUY - API/SCRAPE
# =============================================================================

def scan_bestbuy(query: str = "pokemon trading cards") -> List[Product]:
    """
    Scan Best Buy using API or scraping fallback.
    Uses session pooling.
    
    NOTE: Best Buy blocks cloud server IPs (Render, AWS, etc.).
    Disabled to prevent timeout spam. Re-enable with BESTBUY_API_KEY or proxy.
    """
    # Check if Best Buy scanning is explicitly enabled (API key or proxy configured)
    api_key = os.environ.get("BESTBUY_API_KEY", "")
    proxy_url = os.environ.get("PROXY_SERVICE_URL", "")
    
    if not api_key and not proxy_url:
        # Skip Best Buy - blocked without API key or proxy
        return []
    
    products = []
    
    cached = Cache.get("bestbuy", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("bestbuy")
    api_key = os.environ.get("BESTBUY_API_KEY", "")
    
    try:
        if api_key:
            # Use official API
            url = f"https://api.bestbuy.com/v1/products((search={query}))"
            params = {
                "apiKey": api_key,
                "format": "json",
                "show": "sku,name,salePrice,url,inStoreAvailability,onlineAvailability,image",
                "pageSize": 24,
            }
            
            time.sleep(get_random_delay())
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            
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
            resp = session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
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
    """Scan GameStop by scraping. Uses session pooling."""
    products = []
    
    cached = Cache.get("gamestop", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("gamestop")
    
    try:
        search_url = f"https://www.gamestop.com/search/?q={query.replace(' ', '+')}"
        headers = get_stealth_headers()
        
        time.sleep(get_random_delay())
        resp = session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
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
    """Scan Pokemon Center official store. Uses session pooling."""
    products = []
    
    cached = Cache.get("pokemoncenter", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("pokemoncenter")
    
    try:
        search_url = f"https://www.pokemoncenter.com/search/{query.replace(' ', '%20')}"
        headers = get_stealth_headers()
        headers["Accept"] = "text/html,application/xhtml+xml"
        
        time.sleep(get_random_delay())
        resp = session.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
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
    Free and reliable for card information and TCGPlayer prices.
    Uses session pooling.
    """
    products = []
    
    query = f"{card_name}_{set_name}"
    cached = Cache.get("pokemontcgapi", query)
    if cached:
        return [Product(**p) for p in cached]
    
    session = get_session("pokemontcgapi")
    
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
        # Add API key if available (increases rate limit from 1000/day to 20000/day)
        if POKEMON_TCG_API_KEY:
            headers["X-Api-Key"] = POKEMON_TCG_API_KEY
        
        params = {"q": q, "pageSize": 24, "orderBy": "-tcgplayer.prices.holofoil.market"}
        
        time.sleep(get_random_delay())
        resp = session.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        
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
# SEARCH RELEVANCE HELPER
# =============================================================================

_MATCH_SYNONYMS = {
    "etb": "elite trainer box",
    "upc": "ultra premium collection",
    "bb": "booster box",
    "b&b": "build and battle",
}

def _normalize_for_match(text: str) -> str:
    """Lowercase + expand common abbreviations so short queries still match product names."""
    t = (text or "").lower()
    # Replace punctuation with spaces, keep alphanumerics.
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    if not t:
        return ""

    words = t.split()
    expanded: List[str] = []
    for w in words:
        if w in _MATCH_SYNONYMS:
            expanded.extend(_MATCH_SYNONYMS[w].split())
        else:
            expanded.append(w)
    return " ".join(expanded)


def matches_query(product_name: str, query: str) -> tuple[bool, int]:
    """
    Check if a product name matches the search query.
    Returns (matches, score) where higher score = better match.
    """
    name_lower = _normalize_for_match(product_name)
    query_lower = _normalize_for_match(query)
    
    # Extract key search terms (ignore common words)
    ignore_words = {'pokemon', 'trading', 'cards', 'card', 'tcg', 'the', 'and', 'of', 'a'}
    query_terms = [w for w in query_lower.split() if w not in ignore_words and len(w) > 2]
    
    # If no specific terms, do not over-filter (scanners already filter to Pokemon items).
    if not query_terms:
        return (True, 1)
    
    # Score based on how many query terms match
    score = 0
    matched_terms = 0
    
    for term in query_terms:
        if term in name_lower:
            matched_terms += 1
            # Exact word match scores higher
            if f" {term} " in f" {name_lower} ":
                score += 10
            else:
                score += 5
    
    # Check for set name patterns (e.g., "destined rivals" should match "Destined Rivals")
    # Handle multi-word set names
    if len(query_terms) >= 2:
        # Check if consecutive terms match as a phrase
        query_phrase = ' '.join(query_terms)
        if query_phrase in name_lower:
            score += 50  # Big bonus for exact phrase match
            matched_terms = len(query_terms)
    
    # Require at least half the terms to match (or all if only 1-2 terms)
    min_matches = max(1, len(query_terms) // 2) if len(query_terms) > 2 else len(query_terms)
    matches = matched_terms >= min_matches
    
    return (matches, score)


def filter_by_relevance(products: List[Product], query: str) -> List[Product]:
    """Filter and sort products by relevance to search query."""
    scored = []
    
    for p in products:
        matches, score = matches_query(p.name, query)
        if matches:
            p.relevance_score = score  # Store score on product
            scored.append((p, score))
    
    # Sort by score (highest first)
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return [p for p, _ in scored]


# =============================================================================
# UNIFIED SCANNER - With Parallel Execution
# =============================================================================

class StockChecker:
    """
    Unified stock checker for all retailers.
    
    Features:
    - Parallel scanning (3-4x faster)
    - Session pooling for connection reuse
    - Automatic retry with backoff
    - Smart caching
    """
    
    RETAILERS = {
        "target": scan_target,
        "walmart": scan_walmart,
        "bestbuy": scan_bestbuy,
        "gamestop": scan_gamestop,
        "pokemoncenter": scan_pokemoncenter,
        "tcgplayer": scan_cards,
    }
    
    def __init__(self, zip_code: str = "90210"):
        self.zip_code = zip_code
    
    def _scan_single_retailer(self, name: str, query: str) -> Tuple[str, List[Product], Optional[str]]:
        """Scan a single retailer. Returns (name, products, error)."""
        try:
            scan_func = self.RETAILERS[name]
            
            if name == "target":
                products = scan_func(query, self.zip_code)
            elif name == "tcgplayer":
                # For cards, extract card name from query
                card_query = query.replace("pokemon", "").replace("trading cards", "").strip()
                products = scan_func(card_query or "charizard")
            else:
                products = scan_func(query)
            
            return (name, products, None)
            
        except Exception as e:
            return (name, [], str(e))
    
    def scan_all(self, query: str = "pokemon trading cards", parallel: bool = True) -> Dict[str, Any]:
        """
        Scan all retailers for Pokemon products.
        
        Args:
            query: Search query
            parallel: If True, scan retailers in parallel (faster)
        """
        all_products = []
        results = {}
        errors = []
        start_time = time.time()
        
        if parallel:
            # Parallel scanning - up to 6 retailers at once
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(self._scan_single_retailer, name, query): name 
                    for name in self.RETAILERS
                }
                
                for future in as_completed(futures):
                    name, products, error = future.result()
                    
                    if error:
                        errors.append(f"{name}: {error}")
                        results[name] = {"count": 0, "in_stock": 0, "error": error}
                    else:
                        # Filter by relevance
                        relevant_products = filter_by_relevance(products, query)
                        results[name] = {
                            "count": len(relevant_products),
                            "in_stock": len([p for p in relevant_products if p.stock]),
                        }
                        all_products.extend([p.to_dict() for p in relevant_products])
        else:
            # Sequential scanning (fallback)
            for name in self.RETAILERS:
                _, products, error = self._scan_single_retailer(name, query)
                
                if error:
                    errors.append(f"{name}: {error}")
                    results[name] = {"count": 0, "in_stock": 0, "error": error}
                else:
                    relevant_products = filter_by_relevance(products, query)
                    results[name] = {
                        "count": len(relevant_products),
                        "in_stock": len([p for p in relevant_products if p.stock]),
                    }
                    all_products.extend([p.to_dict() for p in relevant_products])
        
        # Deduplicate by name similarity
        seen = set()
        unique = []
        for p in all_products:
            # Create normalized key for deduplication
            key = ''.join(c.lower() for c in p["name"] if c.isalnum())[:50]
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        # Sort by stock status (in stock first), then by relevance score
        unique.sort(key=lambda x: (not x.get("stock", False), -x.get("relevance_score", 0)))
        
        in_stock = [p for p in unique if p.get("stock")]
        scan_time = round(time.time() - start_time, 2)
        
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
            "scan_time_seconds": scan_time,
            "parallel": parallel,
        }
    
    def scan_retailer(self, retailer: str, query: str) -> Dict[str, Any]:
        """Scan specific retailer."""
        retailer_key = retailer.lower().replace(" ", "")
        
        if retailer_key not in self.RETAILERS:
            return {"error": f"Unknown retailer: {retailer}", "available": list(self.RETAILERS.keys())}
        
        start_time = time.time()
        
        try:
            _, products, error = self._scan_single_retailer(retailer_key, query)
            
            if error:
                return {"error": error}
            
            # Filter by relevance
            relevant_products = filter_by_relevance(products, query)
            scan_time = round(time.time() - start_time, 2)
            
            return {
                "success": True,
                "retailer": retailer,
                "query": query,
                "total": len(relevant_products),
                "in_stock": len([p for p in relevant_products if p.stock]),
                "products": [p.to_dict() for p in relevant_products],
                "scan_time_seconds": scan_time,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def scan_multiple(self, retailers: List[str], query: str) -> Dict[str, Any]:
        """Scan specific retailers in parallel."""
        all_products = []
        results = {}
        errors = []
        start_time = time.time()
        
        # Validate retailers
        valid_retailers = [r.lower().replace(" ", "") for r in retailers if r.lower().replace(" ", "") in self.RETAILERS]
        
        if not valid_retailers:
            return {"error": "No valid retailers specified", "available": list(self.RETAILERS.keys())}
        
        with ThreadPoolExecutor(max_workers=len(valid_retailers)) as executor:
            futures = {
                executor.submit(self._scan_single_retailer, name, query): name 
                for name in valid_retailers
            }
            
            for future in as_completed(futures):
                name, products, error = future.result()
                
                if error:
                    errors.append(f"{name}: {error}")
                    results[name] = {"count": 0, "in_stock": 0, "error": error}
                else:
                    relevant_products = filter_by_relevance(products, query)
                    results[name] = {
                        "count": len(relevant_products),
                        "in_stock": len([p for p in relevant_products if p.stock]),
                    }
                    all_products.extend([p.to_dict() for p in relevant_products])
        
        scan_time = round(time.time() - start_time, 2)
        
        return {
            "success": True,
            "retailers": valid_retailers,
            "query": query,
            "total": len(all_products),
            "in_stock_count": len([p for p in all_products if p.get("stock")]),
            "by_retailer": results,
            "products": all_products,
            "errors": errors if errors else None,
            "scan_time_seconds": scan_time,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def scan_all(query: str = "pokemon trading cards", zip_code: str = "90210", parallel: bool = True) -> Dict[str, Any]:
    """Main entry point - scan all retailers in parallel."""
    return StockChecker(zip_code).scan_all(query, parallel=parallel)


def scan_retailer(retailer: str, query: str, zip_code: str = "90210") -> Dict[str, Any]:
    """Scan specific retailer."""
    return StockChecker(zip_code).scan_retailer(retailer, query)


def scan_multiple(retailers: List[str], query: str, zip_code: str = "90210") -> Dict[str, Any]:
    """Scan specific retailers in parallel."""
    return StockChecker(zip_code).scan_multiple(retailers, query)


def clear_cache(retailer: str = None):
    """Clear cache for retailer or all retailers."""
    Cache.clear(retailer)


def get_available_retailers() -> List[str]:
    """Get list of available retailers."""
    return list(StockChecker.RETAILERS.keys())


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Pokemon Stock Checker")
    parser.add_argument("query", nargs="*", default=["pokemon", "elite", "trainer", "box"], help="Search query")
    parser.add_argument("--retailer", "-r", help="Specific retailer to scan")
    parser.add_argument("--zip", "-z", default="90210", help="ZIP code for local stock")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel scanning")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cache before scanning")
    
    args = parser.parse_args()
    query = " ".join(args.query)
    
    if args.clear_cache:
        clear_cache()
        print("Cache cleared.")
    
    print(f"Scanning for: {query}")
    print(f"Available retailers: {', '.join(get_available_retailers())}")
    print("-" * 50)
    
    if args.retailer:
        result = scan_retailer(args.retailer, query, args.zip)
    else:
        result = scan_all(query, args.zip, parallel=not args.no_parallel)
    
    print(json.dumps(result, indent=2))
    
    if result.get("scan_time_seconds"):
        print(f"\nScan completed in {result['scan_time_seconds']} seconds")
