#!/usr/bin/env python3
"""
Anti-Detection Module for Retail Scanners

Implements techniques to avoid bot detection:
1. Rotating User-Agents (mimics real browsers)
2. Proxy rotation support
3. Random request delays (jitter)
4. Cookie persistence
5. Referer header spoofing
6. Request fingerprint randomization

Usage:
    from stealth.anti_detect import StealthSession
    
    session = StealthSession()
    response = session.get("https://target.com/products")
"""
import os
import random
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import requests

# =============================================================================
# USER AGENTS - Realistic browser signatures
# =============================================================================

USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Chrome on Android (mobile)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    
    # Safari on iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

# =============================================================================
# ACCEPT LANGUAGE VARIATIONS
# =============================================================================

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-US,en;q=0.8",
    "en-GB,en-US;q=0.9,en;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
]

# =============================================================================
# REFERER PATTERNS
# =============================================================================

REFERERS = {
    "target.com": [
        "https://www.google.com/",
        "https://www.target.com/",
        "https://www.target.com/c/trading-cards-games-toys/-/N-5xt8l",
        None,  # Sometimes no referer
    ],
    "walmart.com": [
        "https://www.google.com/",
        "https://www.walmart.com/",
        "https://www.walmart.com/browse/toys/trading-cards",
        None,
    ],
    "bestbuy.com": [
        "https://www.google.com/",
        "https://www.bestbuy.com/",
        "https://www.bestbuy.com/site/searchpage.jsp?st=pokemon",
        None,
    ],
    "gamestop.com": [
        "https://www.google.com/",
        "https://www.gamestop.com/",
        "https://www.gamestop.com/toys-games/trading-cards",
        None,
    ],
    "costco.com": [
        "https://www.google.com/",
        "https://www.costco.com/",
        None,
    ],
}


# =============================================================================
# PROXY CONFIGURATION
# =============================================================================

# Proxy service URLs (user provides their own proxy service)
PROXY_SERVICE_URL = os.environ.get("PROXY_SERVICE_URL", "")
PROXY_SERVICE_KEY = os.environ.get("PROXY_SERVICE_KEY", "")

# Free proxy list (fallback - less reliable)
FREE_PROXIES = os.environ.get("FREE_PROXY_LIST", "").split(",") if os.environ.get("FREE_PROXY_LIST") else []

# Free proxy sources (scraped from public lists)
FREE_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]


def fetch_free_proxies() -> List[str]:
    """
    Fetch free proxies from public sources.
    
    WARNING: Free proxies are unreliable and may be slow/insecure.
    Use at your own risk.
    """
    proxies = []
    
    if not requests:
        return proxies
    
    for source in FREE_PROXY_SOURCES:
        try:
            resp = requests.get(source, timeout=10)
            if resp.status_code == 200:
                # Parse proxy list (format: ip:port)
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if line and ':' in line and not line.startswith('#'):
                        proxies.append(f"http://{line}")
        except:
            continue
    
    return proxies[:50]  # Limit to 50 to avoid too many


# Cache for free proxies (refresh every hour)
_free_proxy_cache: List[str] = []
_free_proxy_cache_time: Optional[datetime] = None

def get_random_proxy() -> Optional[Dict[str, str]]:
    """Get a random proxy for the request."""
    global _free_proxy_cache, _free_proxy_cache_time
    
    if PROXY_SERVICE_URL:
        # Use configured proxy directly (no rotation, no port switching)
        return {
            "http": PROXY_SERVICE_URL,
            "https": PROXY_SERVICE_URL,
        }
    elif FREE_PROXIES and FREE_PROXIES[0]:
        # Use free proxy list from env (less reliable)
        proxy = random.choice(FREE_PROXIES)
        return {
            "http": proxy,
            "https": proxy,
        }
    else:
        # Try fetching free proxies from public sources
        # Only fetch once per hour to avoid rate limits
        if (_free_proxy_cache_time is None or 
            (datetime.now() - _free_proxy_cache_time).total_seconds() > 3600):
            _free_proxy_cache = fetch_free_proxies()
            _free_proxy_cache_time = datetime.now()
            if _free_proxy_cache:
                print(f"📡 Fetched {len(_free_proxy_cache)} free proxies from public sources")
        
        if _free_proxy_cache:
            proxy = random.choice(_free_proxy_cache)
            return {
                "http": proxy,
                "https": proxy,
            }
    
    return None


# =============================================================================
# STEALTH SESSION
# =============================================================================

class StealthSession:
    """
    A requests session with anti-detection features.
    
    Features:
    - Rotating user agents
    - Random delays between requests
    - Proxy support
    - Cookie persistence & sharing
    - Realistic headers
    - Header consistency
    - Referer chain building
    """
    
    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 4.0,
        use_proxy: bool = True,  # Default to True if proxy is configured
        persist_cookies: bool = True,
        cookie_jar_file: Optional[str] = None,  # Save/load cookies from file
    ):
        """
        Initialize stealth session.
        
        Args:
            min_delay: Minimum seconds between requests
            max_delay: Maximum seconds between requests
            use_proxy: Whether to use proxy rotation
            persist_cookies: Whether to persist cookies between requests
            cookie_jar_file: Path to save/load cookies (enables cookie sharing)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.use_proxy = use_proxy
        self.persist_cookies = persist_cookies
        self.cookie_jar_file = cookie_jar_file
        
        self.session = requests.Session() if persist_cookies else None
        self.last_request_time: Optional[datetime] = None
        self.request_count = 0
        self.current_user_agent: Optional[str] = None  # Track for consistency
        self.referer_chain: List[str] = []  # Build realistic referer chain
        
        # Load cookies if file exists
        if cookie_jar_file and self.session:
            self._load_cookies()
        
    def _get_session(self) -> requests.Session:
        """Get or create session."""
        if self.persist_cookies and self.session:
            return self.session
        return requests.Session()
    
    def _load_cookies(self):
        """Load cookies from file if exists."""
        if not self.cookie_jar_file or not self.session:
            return
        
        try:
            import json
            cookie_file = Path(self.cookie_jar_file)
            if cookie_file.exists():
                with open(cookie_file) as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        # Convert back to Cookie object
                        from http.cookies import SimpleCookie
                        c = SimpleCookie()
                        c.load(cookie.get('value', ''))
                        self.session.cookies.set(
                            cookie.get('name', ''),
                            cookie.get('value', ''),
                            domain=cookie.get('domain', ''),
                            path=cookie.get('path', '/'),
                        )
                print(f"✅ Loaded {len(cookies)} cookies from {cookie_jar_file}")
        except Exception as e:
            print(f"⚠️ Failed to load cookies: {e}")
    
    def _save_cookies(self):
        """Save cookies to file for reuse."""
        if not self.cookie_jar_file or not self.session:
            return
        
        try:
            import json
            from pathlib import Path
            
            cookies = []
            for cookie in self.session.cookies:
                cookies.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'expires': cookie.expires,
                })
            
            cookie_file = Path(self.cookie_jar_file)
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
        except Exception as e:
            print(f"⚠️ Failed to save cookies: {e}")
    
    def _random_delay(self):
        """Apply random delay before request (jitter)."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            min_wait = max(0, self.min_delay - elapsed)
            max_wait = max(min_wait, self.max_delay - elapsed)
            
            if max_wait > 0:
                delay = random.uniform(min_wait, max_wait)
                # Add extra jitter (±20%)
                jitter = delay * random.uniform(-0.2, 0.2)
                actual_delay = max(0, delay + jitter)
                time.sleep(actual_delay)
    
    def _get_headers(self, url: str) -> Dict[str, str]:
        """Generate realistic headers with consistency."""
        # Extract domain for referer selection
        domain = None
        for d in REFERERS.keys():
            if d in url:
                domain = d
                break
        
        # Choose User-Agent and keep it consistent for this session
        if not self.current_user_agent:
            self.current_user_agent = random.choice(USER_AGENTS)
        
        # Match Accept headers with User-Agent (Chrome vs Firefox vs Safari)
        ua = self.current_user_agent.lower()
        if "firefox" in ua:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            accept_lang = random.choice(["en-US,en;q=0.5", "en-GB,en-US;q=0.9,en;q=0.8"])
        elif "safari" in ua and "chrome" not in ua:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            accept_lang = random.choice(["en-US,en;q=0.9", "en-GB,en-US;q=0.9,en;q=0.8"])
        else:  # Chrome/Edge
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            accept_lang = random.choice(ACCEPT_LANGUAGES)
        
        headers = {
            "User-Agent": self.current_user_agent,
            "Accept": accept,
            "Accept-Language": accept_lang,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # Build referer chain (more realistic)
        if self.referer_chain:
            # Use last URL as referer (realistic browsing)
            headers["Referer"] = self.referer_chain[-1]
        elif domain and domain in REFERERS:
            # First request - use random referer
            referer = random.choice(REFERERS[domain])
            if referer:
                headers["Referer"] = referer
        
        # Add to referer chain (keep last 5)
        self.referer_chain.append(url)
        if len(self.referer_chain) > 5:
            self.referer_chain.pop(0)
        
        # Occasionally add DNT header (realistic - not everyone has it)
        if random.random() > 0.7:
            headers["DNT"] = "1"
        
        # Add Viewport-Width for mobile user agents
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            headers["Viewport-Width"] = str(random.choice([375, 390, 414, 428, 768]))
        
        return headers
    
    def warm_retailer(self, retailer_url: str) -> bool:
        """
        Warm up session by visiting retailer homepage.
        Makes requests look more like a real user browsing.
        
        Args:
            retailer_url: Base URL of retailer (e.g., "https://www.gamestop.com")
        
        Returns:
            True if successful
        """
        try:
            # Visit homepage first
            self.get(retailer_url, timeout=15)
            time.sleep(random.uniform(1, 3))  # Mimic reading page
            
            # Visit a category page if available
            category_urls = {
                "gamestop.com": f"{retailer_url}/toys-games/trading-cards",
                "pokemoncenter.com": f"{retailer_url}/category/trading-cards",
                "costco.com": f"{retailer_url}/toys-games.html",
                "amazon.com": f"{retailer_url}/s?k=trading+cards",
                "barnesandnoble.com": f"{retailer_url}/b/toys-games/trading-cards/_/N-1p0i",
            }
            
            for domain, cat_url in category_urls.items():
                if domain in retailer_url:
                    self.get(cat_url, timeout=15)
                    time.sleep(random.uniform(1, 2))
                    break
            
            return True
        except Exception as e:
            print(f"⚠️ Session warming error: {e}")
            return False
    
    def get(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = 30,
        warm_session: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        Make a GET request with anti-detection.
        
        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers (merged with generated ones)
            timeout: Request timeout
            warm_session: If True, warm session by visiting homepage first
            **kwargs: Additional requests arguments
        
        Returns:
            requests.Response
        """
        # Warm session if requested (for first request to a retailer)
        if warm_session:
            # Extract base URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            self.warm_retailer(base_url)
        
        # Apply jitter delay
        self._random_delay()
        
        # Get session
        session = self._get_session()
        
        # Build headers
        request_headers = self._get_headers(url)
        if headers:
            request_headers.update(headers)
        
        # Get proxy - always try to use if configured
        proxies = get_random_proxy() if (self.use_proxy or PROXY_SERVICE_URL) else None
        
        # Make request
        try:
            response = session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=timeout,
                proxies=proxies,
                **kwargs
            )
            
            self.last_request_time = datetime.now()
            self.request_count += 1
            
            # Save cookies after successful request
            if self.cookie_jar_file and self.request_count % 5 == 0:  # Save every 5 requests
                self._save_cookies()
            
            return response
            
        except requests.exceptions.RequestException as e:
            # Log but don't crash
            print(f"⚠️ Request failed: {e}")
            raise
    
    def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        headers: Dict[str, str] = None,
        timeout: int = 30,
        **kwargs
    ) -> requests.Response:
        """Make a POST request with anti-detection."""
        self._random_delay()
        
        session = self._get_session()
        
        request_headers = self._get_headers(url)
        request_headers["Content-Type"] = "application/json" if json else "application/x-www-form-urlencoded"
        if headers:
            request_headers.update(headers)
        
        proxies = get_random_proxy() if self.use_proxy else None
        
        response = session.post(
            url,
            data=data,
            json=json,
            headers=request_headers,
            timeout=timeout,
            proxies=proxies,
            **kwargs
        )
        
        self.last_request_time = datetime.now()
        self.request_count += 1
        
        return response


# =============================================================================
# RATE LIMITER
# =============================================================================

class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts speed based on response patterns.
    
    - Slows down if seeing captchas or 429s
    - Speeds up if requests are successful
    """
    
    def __init__(self, base_delay: float = 2.0):
        self.base_delay = base_delay
        self.current_delay = base_delay
        self.success_streak = 0
        self.failure_streak = 0
        
        # Limits
        self.min_delay = 0.5  # Fastest allowed
        self.max_delay = 60.0  # Slowest (backoff)
    
    def record_success(self):
        """Record a successful request."""
        self.success_streak += 1
        self.failure_streak = 0
        
        # Speed up after 5 successful requests
        if self.success_streak >= 5:
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            self.success_streak = 0
    
    def record_failure(self, is_rate_limit: bool = False):
        """Record a failed request."""
        self.failure_streak += 1
        self.success_streak = 0
        
        # Slow down significantly for rate limits
        if is_rate_limit:
            self.current_delay = min(self.max_delay, self.current_delay * 2.0)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def get_delay(self) -> float:
        """Get current delay with jitter."""
        jitter = self.current_delay * random.uniform(-0.2, 0.2)
        return max(self.min_delay, self.current_delay + jitter)
    
    def wait(self):
        """Wait the current delay."""
        time.sleep(self.get_delay())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global session for reuse
_global_session: Optional[StealthSession] = None

def get_stealth_session(use_proxy: bool = None) -> StealthSession:
    """Get or create global stealth session."""
    global _global_session
    
    if _global_session is None:
        # Use proxy if configured
        proxy_enabled = use_proxy if use_proxy is not None else bool(PROXY_SERVICE_URL or FREE_PROXIES)
        _global_session = StealthSession(
            min_delay=2.0,  # Increased from 1.0 for better success
            max_delay=4.0,
            use_proxy=proxy_enabled,
            persist_cookies=True,
        )
    
    return _global_session


def stealth_request(
    url: str,
    method: str = "GET",
    **kwargs
) -> requests.Response:
    """
    Make a single stealth request.
    
    Convenience function for quick requests.
    """
    session = get_stealth_session()
    
    if method.upper() == "GET":
        return session.get(url, **kwargs)
    elif method.upper() == "POST":
        return session.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported method: {method}")


# =============================================================================
# SCANNER CONFIGURATION
# =============================================================================

def get_scan_config() -> Dict[str, Any]:
    """
    Get scanning configuration from environment.
    
    Returns recommended settings for anti-detection.
    """
    return {
        "min_delay_seconds": float(os.environ.get("SCAN_MIN_DELAY", "1.5")),
        "max_delay_seconds": float(os.environ.get("SCAN_MAX_DELAY", "4.0")),
        "use_proxy": bool(PROXY_SERVICE_URL or FREE_PROXIES),
        "proxy_configured": bool(PROXY_SERVICE_URL),
        "max_requests_per_minute": int(os.environ.get("SCAN_MAX_RPM", "15")),
        "adaptive_rate_limit": True,
    }


if __name__ == "__main__":
    # Test the stealth session
    print("🔒 Testing Stealth Session...")
    
    config = get_scan_config()
    print(f"📋 Config: {config}")
    
    session = StealthSession(min_delay=1.0, max_delay=2.0)
    
    # Test with a safe URL
    try:
        resp = session.get("https://httpbin.org/headers")
        print(f"✅ Request successful!")
        print(f"📝 Headers sent: {resp.json()['headers']}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
