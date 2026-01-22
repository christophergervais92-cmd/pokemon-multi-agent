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
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

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
    from stealth.anti_detect import get_stealth_headers, get_random_delay, StealthSession, AdaptiveRateLimiter, get_stealth_session
    STEALTH_AVAILABLE = True
    # Force proxy usage if configured
    _stealth_session = None
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
    def get_random_delay(fast_mode=False):
        if fast_mode:
            return random.uniform(INITIAL_SCAN_MIN_DELAY, INITIAL_SCAN_MAX_DELAY)
        return random.uniform(MIN_DELAY, MAX_DELAY)
    def get_stealth_session():
        return None
    STEALTH_AVAILABLE = False

# Advanced stealth (optional - may not be installed)
try:
    from stealth.advanced_anti_detect import AdvancedStealthSession, BrowsingPattern
    ADVANCED_STEALTH_AVAILABLE = True
except ImportError:
    AdvancedStealthSession = None
    BrowsingPattern = None
    ADVANCED_STEALTH_AVAILABLE = False

# Global flag for fast initial scan mode
_fast_initial_scan = False

def set_fast_initial_scan(enabled: bool):
    """Enable/disable fast initial scan mode (reduced delays, no warm-ups)."""
    global _fast_initial_scan
    _fast_initial_scan = enabled

def get_fast_initial_scan() -> bool:
    """Check if fast initial scan mode is enabled."""
    return _fast_initial_scan

# Global rate limiter per retailer
_retailer_rate_limiters = {}

# =============================================================================
# RETRY DECORATOR
# =============================================================================

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.1)
                        time.sleep(delay + jitter)
                    else:
                        # Last attempt failed
                        print(f"⚠️ {func.__name__} failed after {max_retries} attempts: {e}")
            return []  # Return empty list on failure
        return wrapper
    return decorator


# =============================================================================
# CONFIGURATION
# =============================================================================

CACHE_DIR = Path(__file__).parent.parent.parent / ".stock_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Aggressive caching - longer TTL for better performance
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))  # 5 minutes default (was 30s)
CACHE_TTL_STABLE = int(os.environ.get("CACHE_TTL_STABLE", "900"))  # 15 minutes for stable data (sets, card info)
CACHE_TTL_ERROR = int(os.environ.get("CACHE_TTL_ERROR", "60"))  # 1 minute for error responses (avoid hammering)

# Balanced delays - not too slow, but safe from blocks
FAST_MODE = os.environ.get("FAST_SCAN", "false").lower() == "true"
MIN_DELAY = float(os.environ.get("SCAN_MIN_DELAY", "2.0"))  # 2 seconds minimum
MAX_DELAY = float(os.environ.get("SCAN_MAX_DELAY", "4.0"))  # 4 seconds maximum

# Time-of-day awareness multiplier
try:
    from stealth.advanced_blocking_prevention import get_time_awareness
    _time_awareness = get_time_awareness()
    TIME_MULTIPLIER = _time_awareness.get_delay_multiplier()
    # Adjust delays based on time of day
    MIN_DELAY = MIN_DELAY * TIME_MULTIPLIER
    MAX_DELAY = MAX_DELAY * TIME_MULTIPLIER
except ImportError:
    TIME_MULTIPLIER = 1.0

# Fast initial scan delays (reduced for first scan, but still safe)
# Increased from 0.5-1.0s to 1.0-2.0s to reduce blocking risk
INITIAL_SCAN_MIN_DELAY = float(os.environ.get("INITIAL_SCAN_MIN_DELAY", "1.0"))  # 1 second minimum for initial
INITIAL_SCAN_MAX_DELAY = float(os.environ.get("INITIAL_SCAN_MAX_DELAY", "2.0"))  # 2 seconds maximum for initial

# High-risk retailers that should always use normal delays and warm-ups
HIGH_RISK_RETAILERS = {
    "pokemoncenter",  # Very aggressive bot detection
    "gamestop",      # Moderate bot detection
    "amazon",        # Very aggressive bot detection
}

# =============================================================================
# BLOCKING TRACKER - Skip retailers that are consistently blocked
# =============================================================================

BLOCKED_RETAILERS_FILE = CACHE_DIR / "blocked_retailers.json"

def load_blocked_retailers() -> Dict[str, datetime]:
    """Load list of blocked retailers and when they were blocked."""
    if not BLOCKED_RETAILERS_FILE.exists():
        return {}
    try:
        with open(BLOCKED_RETAILERS_FILE) as f:
            data = json.load(f)
            # Convert ISO strings back to datetime
            return {
                k: datetime.fromisoformat(v) 
                for k, v in data.items()
            }
    except:
        return {}

def save_blocked_retailers(blocked: Dict[str, datetime]):
    """Save blocked retailers list."""
    try:
        with open(BLOCKED_RETAILERS_FILE, 'w') as f:
            # Convert datetime to ISO string
            data = {
                k: v.isoformat() 
                for k, v in blocked.items()
            }
            json.dump(data, f)
    except:
        pass

def mark_retailer_blocked(retailer: str):
    """Mark a retailer as blocked."""
    blocked = load_blocked_retailers()
    blocked[retailer] = datetime.now()
    save_blocked_retailers(blocked)
    print(f"🚫 Marked {retailer} as blocked (will skip for 1 hour)")

def is_retailer_blocked(retailer: str, retry_after_hours: int = 1) -> bool:
    """
    Check if a retailer is currently blocked.
    
    Args:
        retailer: Retailer name
        retry_after_hours: How many hours to wait before retrying
    
    Returns:
        True if blocked and should be skipped
    """
    blocked = load_blocked_retailers()
    if retailer not in blocked:
        return False
    
    blocked_time = blocked[retailer]
    hours_since_block = (datetime.now() - blocked_time).total_seconds() / 3600
    
    if hours_since_block >= retry_after_hours:
        # Unblock after retry period
        blocked.pop(retailer, None)
        save_blocked_retailers(blocked)
        print(f"✅ {retailer} unblocked (retrying after {hours_since_block:.1f} hours)")
        return False
    
    return True

def check_response_for_blocks(resp, retailer_name: str) -> bool:
    """Check if response indicates blocking and mark retailer if so."""
    if resp is None:
        return True  # Timeout/connection error = likely blocked
    
    # Check status codes
    if resp.status_code in [403, 429]:
        mark_retailer_blocked(retailer_name)
        return True
    
    # Check for CAPTCHA/blocking in content
    if resp.status_code == 200 and BS4_AVAILABLE:
        text_lower = resp.text.lower()
        blocking_indicators = [
            "captcha", "cloudflare", "checking your browser",
            "access denied", "blocked", "i'm not a robot"
        ]
        if any(indicator in text_lower for indicator in blocking_indicators):
            mark_retailer_blocked(retailer_name)
            return True
    
    return False


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
    confidence: float = 0.0  # Stock confidence score (0-100)
    detection_method: str = "single"  # How stock was detected
    
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
    def get(retailer: str, query: str = "", ttl: Optional[int] = None) -> Optional[Dict]:
        """
        Get cached results with metadata.
        
        Returns:
            Dict with 'products', 'ts', 'error' or None if expired/missing
        """
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file) as f:
                data = json.load(f)
            
            # Use provided TTL or default
            cache_ttl = ttl or CACHE_TTL_SECONDS
            
            # Check if expired
            cache_time = datetime.fromisoformat(data.get("ts", datetime.now().isoformat()))
            if datetime.now() - cache_time > timedelta(seconds=cache_ttl):
                return None
            
            return data
        except:
            return None
    
    @staticmethod
    def get_products(retailer: str, query: str = "", ttl: Optional[int] = None) -> Optional[List[Dict]]:
        """Get just the products list from cache."""
        cached = Cache.get(retailer, query, ttl)
        return cached.get("products") if cached else None
    
    @staticmethod
    def set(retailer: str, query: str, products: List[Dict], error: Optional[str] = None, ttl_override: Optional[int] = None):
        """
        Cache results with metadata.
        
        Args:
            retailer: Retailer name
            query: Search query
            products: List of products
            error: Optional error message (cached for shorter time)
            ttl_override: Override default TTL
        """
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        try:
            # Use shorter TTL for errors
            if error:
                ttl = ttl_override or CACHE_TTL_ERROR
            else:
                ttl = ttl_override or CACHE_TTL_SECONDS
            
            data = {
                "ts": datetime.now().isoformat(),
                "products": products,
                "ttl": ttl,
            }
            if error:
                data["error"] = error
            
            with open(cache_file, "w") as f:
                json.dump(data, f)
        except:
            pass
    
    @staticmethod
    def get_previous(retailer: str, query: str = "") -> Optional[List[Dict]]:
        """Get previous results for delta comparison (ignores TTL)."""
        cache_file = CACHE_DIR / f"{Cache.key(retailer, query)}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file) as f:
                data = json.load(f)
            return data.get("products", [])
        except:
            return None


# =============================================================================
# TARGET - REDSKY API (WORKING)
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_target(query: str = "pokemon trading cards", zip_code: str = "90210") -> List[Product]:
    """
    Scan Target using Redsky API.
    
    This API is still functional as of 2026.
    Requires: key, channel, keyword, page, pricing_store_id
    """
    products = []
    
    # Aggressive caching - check cache first
    cached_products = Cache.get_products("target", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
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
        
        # Use advanced stealth session if available (best anti-detection)
        if ADVANCED_STEALTH_AVAILABLE and AdvancedStealthSession:
            global _advanced_session
            if _advanced_session is None:
                _advanced_session = get_advanced_stealth_session(
                    use_residential_proxies=True,
                    enable_fingerprinting=True,
                    enable_human_timing=True,
                )
            
            # Use realistic browsing pattern (warm-up)
            browsing_seq = BrowsingPattern.get_browsing_sequence("target")
            for warmup_url in browsing_seq:
                _advanced_session.get(warmup_url)
                time.sleep(HumanTiming.get_reading_delay(50))  # Small page
            
            # Make main request
            resp = _advanced_session.get(api_url, params=params)
            if resp is None:
                raise Exception("Advanced stealth request failed")
        elif STEALTH_AVAILABLE:
            # Fallback to standard stealth session
            global _stealth_session
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(api_url, params=params, timeout=20)
            else:
                headers = get_stealth_headers()
                headers["Accept"] = "application/json"
                time.sleep(get_random_delay())
                resp = requests.get(api_url, params=params, headers=headers, timeout=15)
        else:
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
                
                # Check stock - multiple indicators for better accuracy
                ship_ok = fulfillment.get("shipping_options", {}).get("availability_status", "") == "IN_STOCK"
                pickup_ok = "IN_STOCK" in str(fulfillment.get("store_options", []))
                in_stock = ship_ok or pickup_ok
                
                # Calculate confidence based on number of indicators
                indicators = sum([ship_ok, pickup_ok])
                confidence = 0.5 + (indicators * 0.25)  # 0.5-1.0
                detection_method = "target_api"
                
                # Get URL - handle both relative and absolute URLs
                buy_url = p.get('enrichment', {}).get('buy_url', '')
                if buy_url.startswith('http'):
                    product_url = buy_url
                elif buy_url:
                    product_url = f"https://www.target.com{buy_url}"
                else:
                    tcin = p.get("tcin", "")
                    product_url = f"https://www.target.com/p/-/A-{tcin}" if tcin else ""
                
                # Calculate confidence (API = high confidence)
                confidence = 95.0 if in_stock else 5.0  # API data is reliable
                detection_method = "redsky_api"
                
                products.append(Product(
                    name=title,
                    retailer="Target",
                    price=price_data.get("current_retail", 0) or price_data.get("reg_retail", 0) or price_data.get("formatted_current_price_default_message", "").replace("$", "").replace(",", "") or 0,
                    url=product_url,
                    sku=p.get("tcin", ""),
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    image_url=p.get("enrichment", {}).get("images", {}).get("primary_image_url", ""),
                    confidence=confidence,
                    detection_method=detection_method,
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

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_bestbuy(query: str = "pokemon trading cards") -> List[Product]:
    """
    Scan Best Buy.
    
    Uses their API if key available, otherwise scrapes.
    """
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("bestbuy", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
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
            
            # Use advanced stealth if available
            if ADVANCED_STEALTH_AVAILABLE and AdvancedStealthSession:
                global _advanced_session
                if _advanced_session is None:
                    _advanced_session = get_advanced_stealth_session()
                resp = _advanced_session.get(url, params=params)
                if resp is None:
                    raise Exception("Advanced stealth request failed")
            else:
                time.sleep(get_random_delay())
                resp = requests.get(url, params=params, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("products", []):
                    if "pokemon" in item.get("name", "").lower():
                        in_stock = item.get("onlineAvailability", False)
                        # API = high confidence
                        confidence = 90.0 if in_stock else 10.0
                        detection_method = "bestbuy_api"
                        
                        products.append(Product(
                            name=item.get("name", ""),
                            retailer="Best Buy",
                            price=item.get("salePrice", 0),
                            url=item.get("url", ""),
                            sku=str(item.get("sku", "")),
                            stock=in_stock,
                            stock_status="In Stock" if in_stock else "Out of Stock",
                            image_url=item.get("image", ""),
                            confidence=confidence,
                            detection_method=detection_method,
                            last_checked=datetime.now().isoformat(),
                        ))
        else:
            # Scrape fallback - use StealthSession for better protection
            search_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={query.replace(' ', '+')}"
            
            if STEALTH_AVAILABLE:
                if _stealth_session is None:
                    _stealth_session = get_stealth_session(use_proxy=True)
                if _stealth_session:
                    resp = _stealth_session.get(search_url, timeout=20)
                else:
                    headers = get_stealth_headers()
                    time.sleep(get_random_delay())
                    resp = requests.get(search_url, headers=headers, timeout=15)
            else:
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
                    
                    # Scrape = medium confidence
                    confidence = 70.0 if in_stock else 30.0
                    detection_method = "bestbuy_scrape"
                    
                    products.append(Product(
                        name=name,
                        retailer="Best Buy",
                        price=price,
                        url=url,
                        stock=in_stock,
                        stock_status="In Stock" if in_stock else "Out of Stock",
                        confidence=confidence,
                        detection_method=detection_method,
                        last_checked=datetime.now().isoformat(),
                    ))
        
        # Aggressive caching - always cache (even empty results)
        Cache.set("bestbuy", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Best Buy error: {e}")
    
    return products


# =============================================================================
# GAMESTOP - SCRAPE
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_gamestop(query: str = "pokemon cards") -> List[Product]:
    """Scan GameStop by scraping."""
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("gamestop", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
    try:
        search_url = f"https://www.gamestop.com/search/?q={query.replace(' ', '+')}"
        
        # Use StealthSession for better protection
        if STEALTH_AVAILABLE:
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(search_url, timeout=20)
            else:
                headers = get_stealth_headers()
                time.sleep(get_random_delay())
                resp = requests.get(search_url, headers=headers, timeout=15)
        else:
            headers = get_stealth_headers()
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
        
        # Check for blocking
        if check_response_for_blocks(resp, "gamestop"):
            return products
        
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
                
                # Scrape = medium confidence
                confidence = 70.0 if in_stock else 30.0
                detection_method = "gamestop_scrape"
                
                products.append(Product(
                    name=name,
                    retailer="GameStop",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching
        Cache.set("gamestop", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"GameStop error: {e}")
    
    return products


# =============================================================================
# POKEMON CENTER - SCRAPE
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_pokemoncenter(query: str = "trading cards") -> List[Product]:
    """Scan Pokemon Center official store."""
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("pokemoncenter", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
    try:
        search_url = f"https://www.pokemoncenter.com/search/{query.replace(' ', '%20')}"
        
        # Use StealthSession for Pokemon Center (most likely to block)
        if STEALTH_AVAILABLE:
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(search_url, timeout=20)
            else:
                headers = get_stealth_headers()
                headers["Accept"] = "text/html,application/xhtml+xml"
                time.sleep(get_random_delay())
                resp = requests.get(search_url, headers=headers, timeout=15)
        else:
            headers = get_stealth_headers()
            headers["Accept"] = "text/html,application/xhtml+xml"
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
        
        # Check for blocking
        if check_response_for_blocks(resp, "pokemoncenter"):
            return products
        
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
                
                # Check stock - multiple methods for accuracy
                oos_elem = item.select_one('.out-of-stock, [data-testid="out-of-stock"], .sold-out, [aria-label*="out of stock"]')
                add_to_cart = item.select_one('button[data-testid="add-to-cart"], .add-to-cart, button:not([disabled]):has-text("Add")')
                stock_indicators = []
                
                # Method 1: Check for out-of-stock indicators
                if oos_elem:
                    stock_indicators.append(False)
                else:
                    stock_indicators.append(True)
                
                # Method 2: Check for add-to-cart button
                if add_to_cart and 'disabled' not in (add_to_cart.get('class', []) or []):
                    stock_indicators.append(True)
                else:
                    stock_indicators.append(False)
                
                # Method 3: Price availability
                if price > 0:
                    stock_indicators.append(True)
                else:
                    stock_indicators.append(False)
                
                # Vote-based: 2+ indicators = in stock
                in_stock = sum(stock_indicators) >= 2
                
                # Calculate confidence score (0-100)
                confidence = (sum(stock_indicators) / len(stock_indicators)) * 100
                detection_method = f"multi-indicator ({sum(stock_indicators)}/{len(stock_indicators)})"
                
                products.append(Product(
                    name=name,
                    retailer="Pokemon Center",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching
        Cache.set("pokemoncenter", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Pokemon Center error: {e}")
    
    return products


# WALMART - SCRAPE
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_walmart(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Walmart by scraping."""
    products = []
    
    if not requests or not BS4_AVAILABLE:
        return products
    
    cached = Cache.get("walmart", query)
    if cached:
        return [Product(**p) for p in cached]
    
    try:
        # Walmart search URL
        search_url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
        
        headers = get_stealth_headers()
        
        # Get proxy if available
        try:
            from stealth.anti_detect import get_random_proxy
            proxies = get_random_proxy()
        except:
            proxies = None
        
        time.sleep(get_random_delay())
        resp = requests.get(search_url, headers=headers, proxies=proxies, timeout=15)
        
        # Check for blocking
        if check_response_for_blocks(resp, "walmart"):
            return products
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Walmart product selectors (may need adjustment based on actual HTML)
            product_items = soup.select('[data-testid="item-stack"], .search-result-gridview-item, [data-automation-id="productTile"], [data-item-id]')
            
            for item in product_items[:20]:  # Limit to 20 products
                try:
                    # Product name
                    name_elem = item.select_one('[data-automation-id="product-title"], .product-title, h3 a, [data-testid="product-title"]')
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True)
                    if "pokemon" not in name.lower():
                        continue
                    
                    # Product URL
                    link_elem = item.select_one('a[href*="/ip/"], a[data-automation-id="product-title"], a[data-testid="product-title"]')
                    href = link_elem.get('href', '') if link_elem else ''
                    url = href if href.startswith('http') else f"https://www.walmart.com{href}"
                    
                    # Price
                    price_elem = item.select_one('[data-automation-id="product-price"], .price-current, .price, [data-testid="product-price"]')
                    price = 0
                    if price_elem:
                        price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                        try:
                            price = float(price_text) if price_text else 0
                        except:
                            pass
                    
                    # Stock status - Walmart shows "Add to Cart" if in stock
                    stock_elem = item.select_one('[data-automation-id="add-to-cart-button"], .prod-ProductCTA--primary, [data-testid="add-to-cart"]')
                    oos_elem = item.select_one('.out-of-stock, [aria-label*="out of stock"]')
                    in_stock = stock_elem is not None and oos_elem is None and 'disabled' not in (stock_elem.get('class', []) or [])
                    
                    # Image
                    img_elem = item.select_one('img[data-testid="product-image"], img.product-image, img[alt*="product"]')
                    image_url = img_elem.get('src', '') if img_elem else ''
                    
                    # SKU (if available)
                    sku = item.get('data-item-id', '') or item.get('data-product-id', '') or ''
                    
                    products.append(Product(
                        name=name,
                        retailer="Walmart",
                        price=price,
                        url=url,
                        sku=sku,
                        stock=in_stock,
                        stock_status="In Stock" if in_stock else "Out of Stock",
                        image_url=image_url,
                        last_checked=datetime.now().isoformat(),
                    ))
                except Exception as e:
                    continue
        
        # Cache results
        if products:
            Cache.set("walmart", query, [p.to_dict() for p in products])
        
    except Exception as e:
        print(f"Walmart error: {e}")
    
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
    # Aggressive caching for stable data (card info doesn't change often)
    cached_products = Cache.get_products("pokemontcgapi", query, ttl=CACHE_TTL_STABLE)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
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
                
                # API = high confidence
                confidence = 95.0 if market_price > 0 else 5.0
                detection_method = "pokemontcg_api"
                
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
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching for stable data (15 min TTL)
        Cache.set("pokemontcgapi", query, [p.to_dict() for p in products], ttl_override=CACHE_TTL_STABLE)
            
    except Exception as e:
        print(f"Pokemon TCG API error: {e}")
    
    return products


# =============================================================================
# COSTCO - SCRAPE
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_costco(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Costco by scraping."""
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("costco", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
    try:
        search_url = f"https://www.costco.com/CatalogSearch?keyword={query.replace(' ', '+')}"
        
        # Use StealthSession for better protection
        if STEALTH_AVAILABLE:
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(search_url, timeout=20)
            else:
                headers = get_stealth_headers()
                time.sleep(get_random_delay())
                resp = requests.get(search_url, headers=headers, timeout=15)
        else:
            headers = get_stealth_headers()
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
        
        # Check for blocking
        if check_response_for_blocks(resp, "costco"):
            return products
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('[data-automation-id="productTile"], .product-tile, .product')
            
            for item in items[:20]:
                name_elem = item.select_one('[data-automation-id="productTitle"], .product-title a, h3 a, .description a')
                price_elem = item.select_one('[data-automation-id="productPrice"], .price, .your-price')
                link_elem = item.select_one('a[href*="/product."]')
                
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
                
                url = ""
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        url = f"https://www.costco.com{href}"
                    elif href.startswith('http'):
                        url = href
                
                # Check stock - Costco shows "Add to Cart" if in stock
                add_to_cart = item.select_one('[data-automation-id="addToCartButton"], .add-to-cart, button')
                oos_elem = item.select_one('.out-of-stock, [aria-label*="out of stock"]')
                in_stock = add_to_cart is not None and oos_elem is None
                
                # Scrape = medium confidence
                confidence = 70.0 if in_stock else 30.0
                detection_method = "costco_scrape"
                
                products.append(Product(
                    name=name,
                    retailer="Costco",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching
        Cache.set("costco", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Costco error: {e}")
    
    return products


# =============================================================================
# BARNES & NOBLE - SCRAPE
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_barnesandnoble(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Barnes & Noble by scraping."""
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("barnesandnoble", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
    try:
        search_url = f"https://www.barnesandnoble.com/s/{query.replace(' ', '+')}"
        
        # Use StealthSession for better protection
        if STEALTH_AVAILABLE:
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(search_url, timeout=20)
            else:
                headers = get_stealth_headers()
                time.sleep(get_random_delay())
                resp = requests.get(search_url, headers=headers, timeout=15)
        else:
            headers = get_stealth_headers()
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
        
        # Check for blocking
        if check_response_for_blocks(resp, "barnesandnoble"):
            return products
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('[data-testid="productCard"], .product-shelf-item, .product-item')
            
            for item in items[:20]:
                name_elem = item.select_one('[data-testid="productTitle"], .product-title a, h3 a')
                price_elem = item.select_one('[data-testid="price"], .price, .product-price')
                link_elem = item.select_one('a[href*="/p/"]')
                
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
                
                url = ""
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        url = f"https://www.barnesandnoble.com{href}"
                    elif href.startswith('http'):
                        url = href
                
                # Check stock
                add_to_cart = item.select_one('[data-testid="addToCart"], .add-to-cart-button')
                oos_elem = item.select_one('.out-of-stock, [aria-label*="out of stock"]')
                in_stock = add_to_cart is not None and oos_elem is None
                
                # Scrape = medium confidence
                confidence = 70.0 if in_stock else 30.0
                detection_method = "barnesandnoble_scrape"
                
                products.append(Product(
                    name=name,
                    retailer="Barnes & Noble",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching
        Cache.set("barnesandnoble", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Barnes & Noble error: {e}")
    
    return products


# =============================================================================
# AMAZON - SCRAPE (Limited - Amazon has aggressive blocking)
# =============================================================================

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scan_amazon(query: str = "pokemon trading cards") -> List[Product]:
    """
    Scan Amazon by scraping.
    
    NOTE: Amazon has very aggressive bot detection.
    This may not work reliably without advanced proxies.
    """
    products = []
    
    # Aggressive caching
    cached_products = Cache.get_products("amazon", query)
    if cached_products:
        return [Product(**p) for p in cached_products]
    
    try:
        search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        
        # Use StealthSession for better protection (Amazon needs it most)
        if STEALTH_AVAILABLE:
            if _stealth_session is None:
                _stealth_session = get_stealth_session(use_proxy=True)
            if _stealth_session:
                resp = _stealth_session.get(search_url, timeout=20)
            else:
                headers = get_stealth_headers()
                time.sleep(get_random_delay())
                resp = requests.get(search_url, headers=headers, timeout=15)
        else:
            headers = get_stealth_headers()
            time.sleep(get_random_delay())
            resp = requests.get(search_url, headers=headers, timeout=15)
        
        # Check for blocking (Amazon is most likely to block)
        if check_response_for_blocks(resp, "amazon"):
            return products
        
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('[data-component-type="s-search-result"], .s-result-item')
            
            for item in items[:20]:
                name_elem = item.select_one('h2 a span, .s-title-instructions-style h2 a')
                price_elem = item.select_one('.a-price .a-offscreen, .a-price-whole')
                link_elem = item.select_one('h2 a, .s-title-instructions-style h2 a')
                
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
                
                url = ""
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        url = f"https://www.amazon.com{href}"
                    elif href.startswith('http'):
                        url = href
                
                # Check stock - Amazon shows "Add to Cart" if available
                add_to_cart = item.select_one('[aria-label*="Add to Cart"], .a-button-inner')
                unavailable = item.select_one('.a-color-state, [aria-label*="unavailable"]')
                in_stock = add_to_cart is not None and unavailable is None
                
                # Amazon scraping = lower confidence (aggressive blocking)
                confidence = 60.0 if in_stock else 20.0
                detection_method = "amazon_scrape"
                
                products.append(Product(
                    name=name,
                    retailer="Amazon",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Check Site",
                    confidence=confidence,
                    detection_method=detection_method,
                    last_checked=datetime.now().isoformat(),
                ))
        
        # Aggressive caching
        Cache.set("amazon", query, [p.to_dict() for p in products])
            
    except Exception as e:
        print(f"Amazon error: {e}")
    
    return products


# =============================================================================
# FUZZY MATCHING
# =============================================================================

try:
    from difflib import SequenceMatcher
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

def fuzzy_match(text1: str, text2: str, threshold: float = 0.6) -> float:
    """
    Calculate similarity between two strings (0-1).
    
    Args:
        text1: First string
        text2: Second string
        threshold: Minimum similarity to consider a match
    
    Returns:
        Similarity score (0-1)
    """
    if not FUZZY_AVAILABLE:
        # Fallback: simple substring check
        return 1.0 if text1.lower() in text2.lower() or text2.lower() in text1.lower() else 0.0
    
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    # Exact match
    if text1_lower == text2_lower:
        return 1.0
    
    # Calculate similarity
    similarity = SequenceMatcher(None, text1_lower, text2_lower).ratio()
    
    # Bonus for word matches
    words1 = set(text1_lower.split())
    words2 = set(text2_lower.split())
    if words1 and words2:
        word_overlap = len(words1 & words2) / max(len(words1), len(words2))
        similarity = max(similarity, word_overlap * 0.8)
    
    return similarity

def normalize_set_name(name: str) -> str:
    """Normalize set names for better matching."""
    # Common variations
    replacements = {
        "pokémon": "pokemon",
        "pokemon": "pokemon",
        "trading card game": "tcg",
        "trading cards": "tcg",
        "elite trainer box": "etb",
        "booster box": "bb",
        "booster bundle": "bundle",
    }
    
    normalized = name.lower()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    # Remove special characters
    normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
    
    return normalized.strip()

# =============================================================================
# SEARCH RELEVANCE HELPER
# =============================================================================

def matches_query(product_name: str, query: str) -> tuple[bool, int]:
    """
    Check if a product name matches the search query.
    Returns (matches, score) where higher score = better match.
    """
    name_lower = product_name.lower()
    query_lower = query.lower()
    
    # Extract key search terms (ignore common words)
    ignore_words = {'pokemon', 'trading', 'cards', 'card', 'tcg', 'the', 'and', 'of', 'a'}
    query_terms = [w for w in query_lower.split() if w not in ignore_words and len(w) > 2]
    
    # If no specific terms, match any Pokemon product
    if not query_terms:
        return ('pokemon' in name_lower or 'pokémon' in name_lower, 1)
    
    # Normalize for fuzzy matching
    normalized_query = normalize_set_name(query)
    normalized_name = normalize_set_name(product_name)
    
    # Try fuzzy matching first (handles typos)
    fuzzy_score = fuzzy_match(normalized_query, normalized_name, threshold=0.5)
    if fuzzy_score >= 0.7:
        return (True, int(fuzzy_score * 100))
    
    # Fallback to exact matching
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
            scored.append((p, score))
    
    # Sort by score (highest first)
    scored.sort(key=lambda x: x[1], reverse=True)
    
    filtered = [p for p, _ in scored]
    
    # Apply deduplication
    try:
        from scanners.stock_optimizations import get_deduplicator
        deduplicator = get_deduplicator()
        filtered = deduplicator.deduplicate(filtered)
    except:
        pass  # Fallback if optimizations not available
    
    return filtered


# =============================================================================
# DELTA LOGIC - Only return what changed
# =============================================================================

def compute_delta(current: List[Product], previous: List[Product]) -> Dict[str, Any]:
    """
    Compute delta between current and previous results.
    
    Returns:
        Dict with 'new', 'removed', 'changed', 'unchanged' products
    """
    # Convert to dicts for easier comparison (use URL or SKU as key)
    current_dict = {}
    previous_dict = {}
    
    for p in current:
        key = p.url or p.sku or p.name
        if key:
            current_dict[key] = p
    
    for p in previous:
        key = p.url or p.sku or p.name
        if key:
            previous_dict[key] = p
    
    new = []
    removed = []
    changed = []
    unchanged = []
    
    # Find new products
    for key, product in current_dict.items():
        if key not in previous_dict:
            new.append(product)
        else:
            prev = previous_dict[key]
            # Check if changed (price or stock status)
            if (product.price != prev.price or 
                product.stock != prev.stock or 
                product.stock_status != prev.stock_status):
                changed.append({
                    "product": product,
                    "previous": prev,
                    "changes": {
                        "price": {"old": prev.price, "new": product.price} if product.price != prev.price else None,
                        "stock": {"old": prev.stock, "new": product.stock} if product.stock != prev.stock else None,
                        "status": {"old": prev.stock_status, "new": product.stock_status} if product.stock_status != prev.stock_status else None,
                    }
                })
            else:
                unchanged.append(product)
    
    # Find removed products
    for key, product in previous_dict.items():
        if key not in current_dict:
            removed.append(product)
    
    return {
        "new": new,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "total_current": len(current),
        "total_previous": len(previous),
        "has_changes": len(new) > 0 or len(removed) > 0 or len(changed) > 0,
    }


def get_delta_response(
    retailer: str,
    query: str,
    current_products: List[Product],
    return_full: bool = False
) -> Dict[str, Any]:
    """
    Get delta response (only changes) or full response.
    
    Args:
        retailer: Retailer name
        query: Search query
        current_products: Current search results
        return_full: If True, return all products (ignore delta)
    
    Returns:
        Dict with delta info or full products
    """
    previous_products = []
    previous_data = Cache.get_previous(retailer, query)
    if previous_data:
        previous_products = [Product(**p) for p in previous_data]
    
    # Save current as new previous
    Cache.set(retailer, query, [p.to_dict() for p in current_products])
    
    # If no previous or return_full requested, return all
    if not previous_products or return_full:
        return {
            "products": current_products,
            "delta": None,
            "is_delta": False,
            "total": len(current_products),
        }
    
    # Compute delta
    delta = compute_delta(current_products, previous_products)
    
    # If no changes, return minimal response
    if not delta["has_changes"]:
        return {
            "products": [],  # Empty - no changes
            "delta": delta,
            "is_delta": True,
            "cached": True,
            "total": len(current_products),
            "message": "No changes since last search",
        }
    
    # Return only changes
    return {
        "products": delta["new"] + [c["product"] for c in delta["changed"]],
        "delta": {
            "new_count": len(delta["new"]),
            "removed_count": len(delta["removed"]),
            "changed_count": len(delta["changed"]),
            "unchanged_count": len(delta["unchanged"]),
            "new": [p.to_dict() for p in delta["new"]],
            "removed": [p.to_dict() for p in delta["removed"]],
            "changed": [
                {
                    "product": c["product"].to_dict(),
                    "previous": c["previous"].to_dict(),
                    "changes": c["changes"],
                }
                for c in delta["changed"]
            ],
        },
        "is_delta": True,
        "total": len(current_products),
        "unchanged_count": len(delta["unchanged"]),
    }


# =============================================================================
# UNIFIED SCANNER
# =============================================================================

class StockChecker:
    """Unified stock checker for all retailers."""
    
    # Retailers ordered by safety (API-based first, aggressive bot detectors last)
    # SAFE = Official API or scraping-friendly (faster scanning, no delays)
    # MODERATE = Standard websites (normal delays)
    # HIGH_RISK = Aggressive bot detection (longer delays, extra caution)
    SAFE_RETAILERS = {
        "target": scan_target,      # Uses official Redsky API - FAST
        "tcgplayer": scan_cards,    # Uses Pokemon TCG API - FAST
    }
    MODERATE_RETAILERS = {
        "bestbuy": scan_bestbuy,
        "costco": scan_costco,
        "barnesandnoble": scan_barnesandnoble,
        "walmart": scan_walmart,
    }
    HIGH_RISK_RETAILERS_SCAN = {
        "gamestop": scan_gamestop,
        "pokemoncenter": scan_pokemoncenter,
        "amazon": scan_amazon,
    }
    
    # Combined dict for backward compatibility
    RETAILERS = {
        **SAFE_RETAILERS,
        **MODERATE_RETAILERS,
        **HIGH_RISK_RETAILERS_SCAN,
    }
    
    def __init__(self, zip_code: str = "90210"):
        self.zip_code = zip_code
    
    def scan_all(self, query: str = "pokemon trading cards", parallel: bool = False, use_delta: bool = True, fast_initial: bool = False) -> Dict[str, Any]:
        """
        Scan all retailers for Pokemon products.
        
        NOTE: parallel parameter is ignored - always scans sequentially (one at a time)
        to reduce blocking risk.
        """
        # Force sequential scanning (ignore parallel parameter)
        parallel = False
        """
        Scan all retailers for Pokemon products.
        
        Args:
            query: Search query
            parallel: If True, scan retailers in parallel (faster)
            use_delta: If True, return only changes (delta logic)
            fast_initial: If True, skip warm-ups and reduce delays for initial scan
        
        Returns:
            Dict with products and delta information
        """
        all_products = []
        results = {}
        errors = []
        delta_info = {}
        
        # Check if this is an initial scan (no cache)
        is_initial_scan = not any(
            Cache.get_products(name, query) 
            for name in self.RETAILERS.keys()
        )
        
        # Auto-enable fast mode for initial scans if not explicitly set
        if is_initial_scan and fast_initial is None:
            fast_initial = True
        
        def scan_retailer(name: str, scan_func):
            """Scan a single retailer with error handling and browser fallback."""
            # Advanced blocking prevention
            try:
                from stealth.advanced_blocking_prevention import (
                    get_circuit_breaker,
                    get_deduplicator,
                    get_time_awareness,
                    get_progressive_backoff,
                )
                
                circuit_breaker = get_circuit_breaker()
                deduplicator = get_deduplicator()
                time_awareness = get_time_awareness()
                progressive_backoff = get_progressive_backoff()
                
                # Check circuit breaker
                can_attempt, reason = circuit_breaker.can_attempt(name)
                if not can_attempt:
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": f"Circuit breaker: {reason}"
                    }
                
                # Check request deduplication
                if deduplicator.should_skip(name, query):
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": "Skipped - duplicate request (recently scanned)"
                    }
                
                # Check time of day
                if time_awareness.should_avoid_scanning():
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": "Skipped - avoiding maintenance hours"
                    }
                
                # Get progressive backoff delay
                backoff_delay = progressive_backoff.get_delay(name)
                if backoff_delay > 1.0:
                    time.sleep(backoff_delay - 1.0)  # Apply extra delay
            except ImportError:
                pass  # Advanced features not available
            
            # Skip if retailer is blocked (unless we're using browser fallback)
            use_browser_fallback = False
            
            if is_retailer_blocked(name):
                # Check if browser fallback is available for this retailer
                try:
                    from scanners.browser_scanner import BROWSER_SCANNERS, BROWSER_AVAILABLE
                    if BROWSER_AVAILABLE and name in BROWSER_SCANNERS:
                        use_browser_fallback = True
                        print(f"🔄 {name} is blocked, trying browser fallback...")
                    else:
                        return {
                            "name": name,
                            "products": [],
                            "count": 0,
                            "in_stock": 0,
                            "error": f"Skipped - blocked (will retry in 1 hour)"
                        }
                except ImportError:
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": f"Skipped - blocked (will retry in 1 hour)"
                    }
            
            # Try fast requests-based method first (unless already blocked)
            if not use_browser_fallback:
                try:
                    # Determine if we should skip warm-ups
                    # High-risk retailers always use warm-ups, even in fast mode
                    is_high_risk = name.lower() in HIGH_RISK_RETAILERS
                    should_skip_warmup = fast_initial and not is_high_risk
                    
                    # Use realistic browsing pattern before scanning
                    # Always warm-up high-risk retailers, or if not in fast mode
                    if not should_skip_warmup:
                        if ADVANCED_STEALTH_AVAILABLE and BrowsingPattern:
                            browsing_seq = BrowsingPattern.get_browsing_sequence(name)
                            if browsing_seq and _advanced_session:
                                for warmup_url in browsing_seq:
                                    _advanced_session.get(warmup_url)
                                    time.sleep(HumanTiming.get_reading_delay(50))
                        elif STEALTH_AVAILABLE:
                            # Fallback: at least visit homepage for high-risk retailers
                            if is_high_risk:
                                try:
                                    if _stealth_session is None:
                                        _stealth_session = get_stealth_session(use_proxy=True)
                                    if _stealth_session:
                                        # Quick homepage visit
                                        homepage_urls = {
                                            "pokemoncenter": "https://www.pokemoncenter.com",
                                            "gamestop": "https://www.gamestop.com",
                                            "amazon": "https://www.amazon.com",
                                        }
                                        if name.lower() in homepage_urls:
                                            _stealth_session.get(homepage_urls[name.lower()], timeout=10)
                                            time.sleep(0.5)  # Brief pause
                                except:
                                    pass  # Continue even if warm-up fails
                    
                    if name == "target":
                        products = scan_func(query, self.zip_code)
                    elif name == "tcgplayer":
                        # For cards, extract card name from query
                        card_query = query.replace("pokemon", "").replace("trading cards", "").strip()
                        products = scan_func(card_query or "charizard")
                    else:
                        products = scan_func(query)
                    
                    # Check if we got results
                    if products and len(products) > 0:
                        # Filter by relevance to query
                        relevant_products = filter_by_relevance(products, query)
                        
                        # Record success in advanced blocking prevention
                        try:
                            from stealth.advanced_blocking_prevention import (
                                get_circuit_breaker,
                                get_progressive_backoff,
                                get_response_monitor,
                            )
                            circuit_breaker = get_circuit_breaker()
                            progressive_backoff = get_progressive_backoff()
                            response_monitor = get_response_monitor()
                            
                            circuit_breaker.record_success(name)
                            progressive_backoff.record_success(name)
                            response_monitor.record_response(name, True, 1.0, 200)
                        except ImportError:
                            pass
                        
                        # Proxy rotation disabled - no tracking
                        # (Removed proxy success tracking)
                        
                        # If we got products, retailer is working - unblock if it was blocked
                        if relevant_products:
                            blocked = load_blocked_retailers()
                            if name in blocked:
                                blocked.pop(name, None)
                                save_blocked_retailers(blocked)
                                print(f"✅ {name} is working again - unblocked")
                        
                        return {
                            "name": name,
                            "products": relevant_products,
                            "count": len(relevant_products),
                            "in_stock": len([p for p in relevant_products if p.stock]),
                            "error": None
                        }
                    
                    # No products - record failure
                    try:
                        from stealth.advanced_blocking_prevention import (
                            get_circuit_breaker,
                            get_progressive_backoff,
                            get_response_monitor,
                        )
                        circuit_breaker = get_circuit_breaker()
                        progressive_backoff = get_progressive_backoff()
                        response_monitor = get_response_monitor()
                        
                        circuit_breaker.record_failure(name)
                        progressive_backoff.record_failure(name)
                        response_monitor.record_response(name, False, 1.0, 0)
                    except ImportError:
                        pass
                    
                    # Proxy rotation disabled - no automatic rotation
                    # (Removed proxy rotation code)
                    
                    # No products - might be blocked, try browser fallback
                    print(f"⚠️ {name}: No products from requests, trying browser fallback...")
                    use_browser_fallback = True
                    
                except Exception as e:
                    error_msg = f"{name}: {str(e)}"
                    print(f"❌ {error_msg}")
                    
                    # Check if it's a blocking error
                    is_blocking_error = (
                        "403" in str(e) or 
                        "429" in str(e) or 
                        "timeout" in str(e).lower() or
                        "blocked" in str(e).lower() or
                        "forbidden" in str(e).lower()
                    )
                    
                    if is_blocking_error:
                        mark_retailer_blocked(name)
                        
                        # Try browser fallback if available
                        try:
                            from scanners.browser_scanner import BROWSER_SCANNERS, BROWSER_AVAILABLE
                            if BROWSER_AVAILABLE and name in BROWSER_SCANNERS:
                                use_browser_fallback = True
                                print(f"🔄 {name} blocked, trying browser fallback...")
                            else:
                                return {
                                    "name": name,
                                    "products": [],
                                    "count": 0,
                                    "in_stock": 0,
                                    "error": error_msg
                                }
                        except ImportError:
                            return {
                                "name": name,
                                "products": [],
                                "count": 0,
                                "in_stock": 0,
                                "error": error_msg
                            }
                    else:
                        # Non-blocking error, return it
                        return {
                            "name": name,
                            "products": [],
                            "count": 0,
                            "in_stock": 0,
                            "error": error_msg
                        }
            
            # Browser fallback (slower but more reliable)
            if use_browser_fallback:
                try:
                    from scanners.browser_scanner import scan_with_browser
                    
                    browser_products = scan_with_browser(name, query)
                    
                    if browser_products and len(browser_products) > 0:
                        # Filter by relevance
                        relevant_products = filter_by_relevance(browser_products, query)
                        
                        # Unblock since browser worked
                        blocked = load_blocked_retailers()
                        if name in blocked:
                            blocked.pop(name, None)
                            save_blocked_retailers(blocked)
                            print(f"✅ {name} unblocked (browser fallback worked)")
                        
                        return {
                            "name": name,
                            "products": relevant_products,
                            "count": len(relevant_products),
                            "in_stock": len([p for p in relevant_products if p.stock]),
                            "error": None,
                            "method": "browser"  # Indicate browser was used
                        }
                    else:
                        return {
                            "name": name,
                            "products": [],
                            "count": 0,
                            "in_stock": 0,
                            "error": f"Browser fallback also failed for {name}"
                        }
                        
                except ImportError:
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": f"Browser automation not available for {name}"
                    }
                except Exception as e:
                    return {
                        "name": name,
                        "products": [],
                        "count": 0,
                        "in_stock": 0,
                        "error": f"Browser fallback error: {str(e)}"
                    }
            
            # Should not reach here, but just in case
            return {
                "name": name,
                "products": [],
                "count": 0,
                "in_stock": 0,
                "error": "Unknown error"
            }
        
        # Sequential scanning only (parallel disabled for safety)
        # Always scan one retailer at a time to reduce blocking risk
        if False:  # Parallel scanning disabled
            # This code path is disabled - always use sequential
            with ThreadPoolExecutor(max_workers=len(self.RETAILERS)) as executor:
                futures = {
                    executor.submit(scan_retailer, name, scan_func): name
                    for name, scan_func in self.RETAILERS.items()
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    retailer_name = result["name"]
                    products = result["products"]
                    
                    # Record response time for monitoring
                    try:
                        from scanners.stock_optimizations import get_response_monitor
                        response_monitor = get_response_monitor()
                        # Response time would be tracked in scan_retailer function
                    except:
                        pass
                    
                    # Apply stock verification for in-stock items
                    try:
                        from scanners.stock_optimizations import get_stock_verifier
                        verifier = get_stock_verifier()
                        verified_products = []
                        for p in products:
                            is_stock, confidence = verifier.verify_stock(p)
                            if hasattr(p, 'confidence'):
                                p.confidence = confidence
                            if is_stock or not p.stock:  # Keep verified in-stock or confirmed out-of-stock
                                verified_products.append(p)
                        products = verified_products
                    except:
                        pass
                    
                    # Apply delta logic if enabled
                    if use_delta and products:
                        delta_response = get_delta_response(
                            retailer_name,
                            query,
                            products,
                            return_full=False
                        )
                        
                        if delta_response["is_delta"]:
                            # Only add changed products
                            delta_products = delta_response["products"]
                            results[retailer_name] = {
                                "count": len(products),  # Total count
                                "in_stock": len([p for p in products if p.stock]),
                                "delta_count": len(delta_products),  # Changed count
                                "delta": delta_response.get("delta"),
                                "cached": delta_response.get("cached", False),
                            }
                            all_products.extend([p.to_dict() for p in delta_products])
                        else:
                            # Full results (first search or return_full=True)
                            results[retailer_name] = {
                                "count": result["count"],
                                "in_stock": result["in_stock"],
                            }
                            all_products.extend([p.to_dict() for p in products])
                    else:
                        # No delta logic - return all
                        results[retailer_name] = {
                            "count": result["count"],
                            "in_stock": result["in_stock"],
                        }
                        all_products.extend([p.to_dict() for p in products])
                    
                    if result["error"]:
                        errors.append(result["error"])
        else:
            # OPTIMIZED TIERED SCANNING:
            # 1. SAFE retailers (API-based) - scan in parallel, minimal delays
            # 2. MODERATE retailers - sequential with normal delays
            # 3. HIGH_RISK retailers - sequential with longer delays
            
            def process_result(result):
                """Process scan result and add to results."""
                results[result["name"]] = {
                    "count": result["count"],
                    "in_stock": result["in_stock"],
                }
                all_products.extend([p.to_dict() for p in result["products"]])
                if result["error"]:
                    errors.append(result["error"])
            
            # TIER 1: Safe retailers (parallel, fast)
            # These use official APIs so can be scanned together without blocking risk
            safe_list = list(self.SAFE_RETAILERS.items())
            if safe_list:
                with ThreadPoolExecutor(max_workers=len(safe_list)) as executor:
                    futures = {executor.submit(scan_retailer, name, func): name for name, func in safe_list}
                    for future in as_completed(futures):
                        process_result(future.result())
                # Small delay before moving to moderate tier
                time.sleep(0.5)
            
            # TIER 2: Moderate risk retailers (sequential, normal delays)
            moderate_list = list(self.MODERATE_RETAILERS.items())
            for idx, (name, scan_func) in enumerate(moderate_list):
                result = scan_retailer(name, scan_func)
                process_result(result)
                # Normal delay between moderate retailers
                if idx < len(moderate_list) - 1:
                    time.sleep(get_random_delay())
            
            # Small delay before high-risk tier
            if moderate_list:
                time.sleep(1.0)
            
            # TIER 3: High risk retailers (sequential, longer delays)
            high_risk_list = list(self.HIGH_RISK_RETAILERS_SCAN.items())
            for idx, (name, scan_func) in enumerate(high_risk_list):
                result = scan_retailer(name, scan_func)
                process_result(result)
                # Longer delay between high-risk retailers
                if idx < len(high_risk_list) - 1:
                    delay = get_random_delay() * 2.5  # 5-10 seconds
                    time.sleep(delay)
        
        # Categorize and add to SKU database
        try:
            from scanners.sku_builder import categorize_product, SKUDatabase, SKUEntry
            
            db = SKUDatabase()
            
            for p in all_products:
                # Categorize if not already categorized
                if not p.get("category") or p.get("category") == "TCG":
                    category, set_name = categorize_product(p.get("name", ""))
                    p["category"] = category
                    if set_name:
                        p["set_name"] = set_name
                
                # Add to SKU database if has SKU
                if p.get("sku"):
                    entry = SKUEntry(
                        sku=p["sku"],
                        retailer=p.get("retailer", ""),
                        name=p.get("name", ""),
                        category=p.get("category", "other"),
                        set_name=p.get("set_name"),
                        price=p.get("price", 0),
                        url=p.get("url", ""),
                        image_url=p.get("image_url", ""),
                        discovery_method="stock_check",
                        confidence=0.8,
                    )
                    db.add_sku(entry, dedupe=True)
            
            # Save SKU database
            db.save()
        except Exception as e:
            # If categorization fails, continue without it
            pass
        
        # Deduplicate (use SKU as primary key if available)
        seen = set()
        unique = []
        for p in all_products:
            # Prefer SKU for deduplication, fallback to name
            key = p.get("sku") or p.get("name", "").lower()[:40]
            if key and key not in seen:
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
            
            # Filter by relevance
            relevant_products = filter_by_relevance(products, query)
            
            return {
                "success": True,
                "retailer": retailer,
                "query": query,
                "total": len(relevant_products),
                "in_stock": len([p for p in relevant_products if p.stock]),
                "products": [p.to_dict() for p in relevant_products],
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================



def scan_retailer(retailer: str, query: str, zip_code: str = "90210") -> Dict[str, Any]:
    """Scan specific retailer."""
    return StockChecker(zip_code).scan_retailer(retailer, query)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "pokemon elite trainer box"
    checker = StockChecker(zip_code="90210")
    result = checker.scan_all(query)
    print(json.dumps(result, indent=2))
