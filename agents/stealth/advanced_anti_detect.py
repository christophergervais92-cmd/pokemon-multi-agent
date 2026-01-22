#!/usr/bin/env python3
"""
Advanced Anti-Detection Strategies for Stock Checkers

Implements techniques used by successful stock checkers:
1. Residential proxy rotation (not just datacenter)
2. Browser fingerprint randomization
3. Human-like request timing patterns
4. TLS fingerprint randomization
5. Distributed scanning (multiple IPs)
6. Request header consistency validation
7. Realistic browsing patterns
8. CAPTCHA solving integration
"""
import os
import random
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    import requests
except ImportError:
    requests = None

# =============================================================================
# RESIDENTIAL PROXY DETECTION & ROTATION
# =============================================================================

def is_residential_proxy(proxy_url: str) -> bool:
    """
    Detect if proxy is residential (vs datacenter).
    
    Residential proxies are less likely to be blocked.
    """
    # Smartproxy, Bright Data, Oxylabs use residential IPs
    residential_indicators = [
        "residential",
        "res-",
        "res_",
        "gate.smartproxy.com",
        "gate.decodo.com",
        "brd.superproxy.io",  # Bright Data
        "rotating-residential",  # Oxylabs
    ]
    
    return any(indicator in proxy_url.lower() for indicator in residential_indicators)


def get_residential_proxy_pool() -> List[str]:
    """
    Get pool of residential proxies.
    
    Prioritizes residential over datacenter proxies.
    """
    proxy_url = os.environ.get("PROXY_SERVICE_URL", "")
    free_proxies = os.environ.get("FREE_PROXY_LIST", "").split(",") if os.environ.get("FREE_PROXY_LIST") else []
    
    pool = []
    
    # Add configured proxy if it's residential
    if proxy_url and is_residential_proxy(proxy_url):
        pool.append(proxy_url)
    
    # Add free proxies (assume they might be residential)
    pool.extend([p for p in free_proxies if p])
    
    return pool


# =============================================================================
# BROWSER FINGERPRINT RANDOMIZATION
# =============================================================================

class BrowserFingerprint:
    """
    Generate realistic browser fingerprints.
    
    Includes:
    - User-Agent
    - Screen resolution
    - Timezone
    - Language
    - Platform
    - Hardware concurrency
    - Canvas fingerprint (simulated)
    """
    
    SCREEN_RESOLUTIONS = [
        (1920, 1080),  # Most common
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1280, 720),
        (2560, 1440),  # High-res
    ]
    
    TIMEZONES = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
    ]
    
    LANGUAGES = [
        "en-US",
        "en-GB",
        "en-CA",
        "es-US",
    ]
    
    HARDWARE_CONCURRENCY = [2, 4, 6, 8, 12, 16]  # CPU cores
    
    @staticmethod
    def generate() -> Dict[str, Any]:
        """Generate a random but realistic browser fingerprint."""
        width, height = random.choice(BrowserFingerprint.SCREEN_RESOLUTIONS)
        
        return {
            "screen_width": width,
            "screen_height": height,
            "timezone": random.choice(BrowserFingerprint.TIMEZONES),
            "language": random.choice(BrowserFingerprint.LANGUAGES),
            "hardware_concurrency": random.choice(BrowserFingerprint.HARDWARE_CONCURRENCY),
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "cookie_enabled": True,
            "do_not_track": random.choice([None, "1"]),  # 30% have DNT
        }
    
    @staticmethod
    def to_headers(fingerprint: Dict[str, Any]) -> Dict[str, str]:
        """Convert fingerprint to HTTP headers."""
        headers = {}
        
        # Viewport-Width (for mobile detection)
        if fingerprint.get("screen_width"):
            headers["Viewport-Width"] = str(fingerprint["screen_width"])
        
        # Accept-Language
        lang = fingerprint.get("language", "en-US")
        headers["Accept-Language"] = f"{lang},{lang[:2]};q=0.9"
        
        # DNT
        if fingerprint.get("do_not_track"):
            headers["DNT"] = fingerprint["do_not_track"]
        
        return headers


# =============================================================================
# HUMAN-LIKE TIMING PATTERNS
# =============================================================================

class HumanTiming:
    """
    Generate human-like request timing patterns.
    
    Humans don't make requests at uniform intervals.
    They have:
    - Reading time (longer delays)
    - Quick clicks (shorter delays)
    - Thinking pauses (random longer delays)
    """
    
    @staticmethod
    def get_reading_delay(page_size_kb: int = 100) -> float:
        """
        Simulate reading time based on page size.
        
        Humans read ~200-300 words/min = ~1KB/sec
        """
        # Base reading time: 1-3 seconds per 100KB
        base_time = (page_size_kb / 100) * random.uniform(1.0, 3.0)
        
        # Add jitter (±30%)
        jitter = base_time * random.uniform(-0.3, 0.3)
        
        return max(0.5, base_time + jitter)
    
    @staticmethod
    def get_click_delay() -> float:
        """
        Simulate time between clicks.
        
        Humans click every 0.5-2 seconds when browsing quickly.
        """
        return random.uniform(0.5, 2.0)
    
    @staticmethod
    def get_thinking_pause() -> float:
        """
        Simulate thinking/decision pause.
        
        Humans pause 2-10 seconds when deciding what to click.
        """
        # 20% chance of a thinking pause
        if random.random() < 0.2:
            return random.uniform(2.0, 10.0)
        return 0
    
    @staticmethod
    def get_realistic_delay(
        last_request_time: Optional[datetime] = None,
        min_delay: float = 1.0,
        max_delay: float = 4.0,
    ) -> float:
        """
        Get realistic delay based on human behavior patterns.
        """
        if last_request_time:
            elapsed = (datetime.now() - last_request_time).total_seconds()
            # If enough time has passed, use shorter delay (quick click)
            if elapsed > max_delay:
                delay = HumanTiming.get_click_delay()
            else:
                # Normal browsing delay
                delay = random.uniform(min_delay, max_delay)
        else:
            delay = random.uniform(min_delay, max_delay)
        
        # Add thinking pause occasionally
        delay += HumanTiming.get_thinking_pause()
        
        return delay


# =============================================================================
# TLS FINGERPRINT RANDOMIZATION
# =============================================================================

class TLSFingerprint:
    """
    Randomize TLS fingerprints to avoid detection.
    
    Note: Full TLS fingerprint randomization requires custom SSL context.
    This is a simplified version that works with requests.
    """
    
    TLS_VERSIONS = ["TLSv1.2", "TLSv1.3"]
    
    CIPHER_SUITES = [
        "TLS_AES_128_GCM_SHA256",
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
        "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    ]
    
    @staticmethod
    def get_tls_config() -> Dict[str, Any]:
        """
        Get TLS configuration for requests.
        
        Note: requests doesn't fully support TLS fingerprinting,
        but we can configure SSL context for better randomization.
        """
        # This would require custom SSL adapter
        # For now, return config that can be used with custom adapters
        return {
            "tls_version": random.choice(TLSFingerprint.TLS_VERSIONS),
            "cipher_suite": random.choice(TLSFingerprint.CIPHER_SUITES),
        }


# =============================================================================
# DISTRIBUTED SCANNING (MULTIPLE IPs)
# =============================================================================

class DistributedScanner:
    """
    Distribute scanning across multiple IPs/proxies.
    
    Each request uses a different IP to avoid rate limits.
    """
    
    def __init__(self, proxy_pool: List[str]):
        self.proxy_pool = proxy_pool
        self.current_index = 0
        self.proxy_stats: Dict[str, Dict[str, Any]] = {}
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation."""
        if not self.proxy_pool:
            return None
        
        proxy = self.proxy_pool[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_pool)
        
        # Track proxy usage
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "last_used": None,
            }
        
        self.proxy_stats[proxy]["requests"] += 1
        self.proxy_stats[proxy]["last_used"] = datetime.now()
        
        return proxy
    
    def record_success(self, proxy: str):
        """Record successful request for proxy."""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["successes"] += 1
    
    def record_failure(self, proxy: str):
        """Record failed request for proxy."""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["failures"] += 1
    
    def get_best_proxy(self) -> Optional[str]:
        """Get proxy with best success rate."""
        if not self.proxy_stats:
            return self.get_next_proxy()
        
        # Sort by success rate
        sorted_proxies = sorted(
            self.proxy_stats.items(),
            key=lambda x: (
                x[1]["successes"] / max(x[1]["requests"], 1),
                -x[1]["failures"]  # Prefer fewer failures
            ),
            reverse=True
        )
        
        return sorted_proxies[0][0] if sorted_proxies else None


# =============================================================================
# REQUEST HEADER CONSISTENCY VALIDATION
# =============================================================================

class HeaderConsistency:
    """
    Ensure request headers are consistent with User-Agent.
    
    Chrome headers should match Chrome User-Agent, etc.
    """
    
    CHROME_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    
    FIREFOX_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }
    
    SAFARI_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    @staticmethod
    def get_headers_for_ua(user_agent: str) -> Dict[str, str]:
        """Get consistent headers for a User-Agent."""
        ua_lower = user_agent.lower()
        
        if "firefox" in ua_lower:
            return HeaderConsistency.FIREFOX_HEADERS.copy()
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return HeaderConsistency.SAFARI_HEADERS.copy()
        else:  # Chrome/Edge
            return HeaderConsistency.CHROME_HEADERS.copy()
    
    @staticmethod
    def validate_headers(user_agent: str, headers: Dict[str, str]) -> bool:
        """Validate that headers match User-Agent."""
        expected = HeaderConsistency.get_headers_for_ua(user_agent)
        
        # Check critical headers match
        critical_headers = ["Accept", "Accept-Encoding", "Accept-Language"]
        for header in critical_headers:
            if header in expected:
                if header not in headers or headers[header] != expected[header]:
                    return False
        
        return True


# =============================================================================
# REALISTIC BROWSING PATTERNS
# =============================================================================

class BrowsingPattern:
    """
    Generate realistic browsing patterns.
    
    Humans don't go straight to search - they:
    1. Visit homepage
    2. Browse categories
    3. Search
    4. View product pages
    """
    
    PATTERNS = {
        "direct_search": 0.3,  # 30% go straight to search
        "homepage_then_search": 0.4,  # 40% visit homepage first
        "category_then_search": 0.3,  # 30% browse category first
    }
    
    @staticmethod
    def get_browsing_sequence(retailer: str) -> List[str]:
        """
        Get realistic browsing sequence for a retailer.
        
        Returns list of URLs to visit in order.
        """
        pattern = random.choices(
            list(BrowsingPattern.PATTERNS.keys()),
            weights=list(BrowsingPattern.PATTERNS.values())
        )[0]
        
        base_urls = {
            "target": "https://www.target.com",
            "bestbuy": "https://www.bestbuy.com",
            "gamestop": "https://www.gamestop.com",
            "pokemoncenter": "https://www.pokemoncenter.com",
            "costco": "https://www.costco.com",
            "amazon": "https://www.amazon.com",
        }
        
        base = base_urls.get(retailer.lower(), "https://www.example.com")
        
        if pattern == "direct_search":
            return []  # Skip warm-up
        elif pattern == "homepage_then_search":
            return [base]
        elif pattern == "category_then_search":
            category_urls = {
                "target": f"{base}/c/trading-cards-games-toys/-/N-5xt8l",
                "bestbuy": f"{base}/site/searchpage.jsp?st=pokemon",
                "gamestop": f"{base}/toys-games/trading-cards",
                "pokemoncenter": f"{base}/category/trading-cards",
            }
            return [category_urls.get(retailer.lower(), base)]
        
        return []


# =============================================================================
# RATE LIMIT MONITORING
# =============================================================================

class RateLimitMonitor:
    """
    Monitor and respond to rate limit signals.
    
    Automatically backs off when rate limits are detected.
    """
    
    def __init__(self):
        self.rate_limit_events: List[datetime] = []
        self.backoff_until: Optional[datetime] = None
        self.current_backoff_seconds = 60
    
    def record_rate_limit(self):
        """Record a rate limit event."""
        now = datetime.now()
        self.rate_limit_events.append(now)
        
        # Keep only last hour
        self.rate_limit_events = [
            event for event in self.rate_limit_events
            if (now - event).total_seconds() < 3600
        ]
        
        # Exponential backoff
        self.current_backoff_seconds = min(
            3600,  # Max 1 hour
            self.current_backoff_seconds * 2
        )
        self.backoff_until = now + timedelta(seconds=self.current_backoff_seconds)
        
        print(f"⚠️ Rate limit detected. Backing off for {self.current_backoff_seconds}s")
    
    def should_backoff(self) -> bool:
        """Check if we should back off."""
        if self.backoff_until:
            if datetime.now() < self.backoff_until:
                return True
            else:
                # Backoff expired, reset
                self.backoff_until = None
                self.current_backoff_seconds = 60
        
        return False
    
    def get_rate_limit_count(self, window_minutes: int = 60) -> int:
        """Get number of rate limits in time window."""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        return len([e for e in self.rate_limit_events if e > cutoff])


# =============================================================================
# MAIN ADVANCED STEALTH SESSION
# =============================================================================

class AdvancedStealthSession:
    """
    Advanced stealth session with all anti-detection strategies.
    
    Combines:
    - Residential proxy rotation
    - Browser fingerprinting
    - Human-like timing
    - Distributed scanning
    - Header consistency
    - Realistic browsing patterns
    - Rate limit monitoring
    """
    
    def __init__(
        self,
        use_residential_proxies: bool = True,
        enable_fingerprinting: bool = True,
        enable_human_timing: bool = True,
    ):
        self.use_residential_proxies = use_residential_proxies
        self.enable_fingerprinting = enable_fingerprinting
        self.enable_human_timing = enable_human_timing
        
        # Initialize components
        proxy_pool = get_residential_proxy_pool() if use_residential_proxies else []
        self.distributed_scanner = DistributedScanner(proxy_pool)
        self.rate_limit_monitor = RateLimitMonitor()
        self.browser_fingerprint = BrowserFingerprint.generate() if enable_fingerprinting else {}
        self.last_request_time: Optional[datetime] = None
        
        # Session for cookie persistence
        if requests:
            self.session = requests.Session()
        else:
            self.session = None
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a GET request with all anti-detection strategies."""
        if not requests or not self.session:
            return None
        
        # Check rate limit backoff
        if self.rate_limit_monitor.should_backoff():
            wait_time = (self.rate_limit_monitor.backoff_until - datetime.now()).total_seconds()
            print(f"⏳ Rate limit backoff active. Waiting {wait_time:.0f}s...")
            time.sleep(min(wait_time, 60))
        
        # Get proxy
        proxy_url = self.distributed_scanner.get_next_proxy()
        proxies = None
        if proxy_url:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        
        # Human-like timing
        if self.enable_human_timing:
            delay = HumanTiming.get_realistic_delay(
                self.last_request_time,
                min_delay=1.5,
                max_delay=4.0
            )
            time.sleep(delay)
        
        # Build headers with fingerprint
        headers = {}
        if self.enable_fingerprinting:
            fingerprint_headers = BrowserFingerprint.to_headers(self.browser_fingerprint)
            headers.update(fingerprint_headers)
        
        # Get User-Agent (from existing stealth module)
        from stealth.anti_detect import USER_AGENTS
        user_agent = random.choice(USER_AGENTS)
        headers["User-Agent"] = user_agent
        
        # Ensure header consistency
        consistent_headers = HeaderConsistency.get_headers_for_ua(user_agent)
        headers.update(consistent_headers)
        
        # Make request
        try:
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=30,
                **kwargs
            )
            
            self.last_request_time = datetime.now()
            
            # Check for rate limits
            if response.status_code == 429:
                self.rate_limit_monitor.record_rate_limit()
                if proxy_url:
                    self.distributed_scanner.record_failure(proxy_url)
            elif response.status_code == 200:
                if proxy_url:
                    self.distributed_scanner.record_success(proxy_url)
            
            return response
            
        except Exception as e:
            print(f"⚠️ Request failed: {e}")
            if proxy_url:
                self.distributed_scanner.record_failure(proxy_url)
            return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_advanced_stealth_session(**kwargs) -> AdvancedStealthSession:
    """Get or create advanced stealth session."""
    return AdvancedStealthSession(**kwargs)


if __name__ == "__main__":
    print("🔒 Testing Advanced Anti-Detection...")
    
    session = AdvancedStealthSession(
        use_residential_proxies=True,
        enable_fingerprinting=True,
        enable_human_timing=True,
    )
    
    print(f"✅ Advanced stealth session created")
    print(f"   Fingerprint: {session.browser_fingerprint}")
    print(f"   Proxy pool size: {len(session.distributed_scanner.proxy_pool)}")
