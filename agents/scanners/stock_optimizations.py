#!/usr/bin/env python3
"""
Stock Checker Optimizations

Advanced optimizations for stock checking:
1. Smart prioritization (high-value items scanned more often)
2. ETag/Last-Modified header support (only fetch if changed)
3. Geographic consistency (match IP to User-Agent region)
4. Robots.txt respect (check and respect crawl delays)
5. Adaptive delays (adjust based on response patterns)
6. Stock verification (double-check "in stock" items)
7. Product deduplication (better duplicate handling)
8. Response time monitoring (track and adapt)
"""
import os
import time
import hashlib
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

from agents.utils.logger import get_logger

logger = get_logger("stock_optimizations")

# =============================================================================
# SMART PRIORITIZATION
# =============================================================================

class ProductPrioritizer:
    """
    Prioritize products for scanning based on:
    - Value (high-value items scanned more often)
    - Volatility (frequently changing stock)
    - User demand (watched items)
    """
    
    def __init__(self):
        self.product_scores: Dict[str, float] = {}
        self.scan_frequencies: Dict[str, int] = {}  # seconds between scans
        self.last_scanned: Dict[str, datetime] = {}
    
    def calculate_priority(
        self,
        product_name: str,
        price: float = 0,
        is_watched: bool = False,
        volatility: float = 0.5,  # 0-1, how often stock changes
    ) -> float:
        """
        Calculate priority score (0-100).
        
        Higher score = scan more often.
        """
        score = 50.0  # Base priority
        
        # Price factor (high-value = higher priority)
        if price > 100:
            score += 20
        elif price > 50:
            score += 10
        elif price > 20:
            score += 5
        
        # Watched items (user demand)
        if is_watched:
            score += 30
        
        # Volatility (frequently changing = scan more)
        score += volatility * 20
        
        return min(100.0, score)
    
    def get_scan_interval(self, priority: float) -> int:
        """
        Get scan interval in seconds based on priority.
        
        High priority (80-100): 30 seconds
        Medium priority (50-79): 2 minutes
        Low priority (0-49): 5 minutes
        """
        if priority >= 80:
            return 30
        elif priority >= 50:
            return 120
        else:
            return 300
    
    def should_scan(self, product_key: str, priority: float) -> bool:
        """Check if product should be scanned now."""
        interval = self.get_scan_interval(priority)
        
        if product_key not in self.last_scanned:
            return True
        
        elapsed = (datetime.now() - self.last_scanned[product_key]).total_seconds()
        return elapsed >= interval
    
    def record_scan(self, product_key: str):
        """Record that product was scanned."""
        self.last_scanned[product_key] = datetime.now()


# =============================================================================
# ETAG / LAST-MODIFIED SUPPORT
# =============================================================================

class ChangeDetection:
    """
    Use HTTP headers (ETag, Last-Modified) to detect if content changed.
    Only fetch if content has changed.
    """
    
    def __init__(self):
        self.etags: Dict[str, str] = {}
        self.last_modified: Dict[str, datetime] = {}
        cache_file = Path(__file__).parent.parent.parent / ".stock_cache" / "change_detection.json"
        self.cache_file = cache_file
        self._load_cache()
    
    def _load_cache(self):
        """Load ETag/Last-Modified cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            import json
            with open(self.cache_file) as f:
                data = json.load(f)
                self.etags = data.get("etags", {})
                self.last_modified = {
                    k: datetime.fromisoformat(v)
                    for k, v in data.get("last_modified", {}).items()
                }
        except:
            pass
    
    def _save_cache(self):
        """Save ETag/Last-Modified cache to disk."""
        try:
            import json
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "etags": self.etags,
                    "last_modified": {
                        k: v.isoformat()
                        for k, v in self.last_modified.items()
                    },
                }, f)
        except:
            pass
    
    def get_conditional_headers(self, url: str) -> Dict[str, str]:
        """
        Get conditional request headers (If-None-Match, If-Modified-Since).
        
        Returns headers to send if we have cached ETag/Last-Modified.
        """
        headers = {}
        
        # ETag support
        if url in self.etags:
            headers["If-None-Match"] = self.etags[url]
        
        # Last-Modified support
        if url in self.last_modified:
            headers["If-Modified-Since"] = self.last_modified[url].strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
        
        return headers
    
    def process_response(self, url: str, response):
        """Process response headers and update cache."""
        # Store ETag if present
        etag = response.headers.get("ETag")
        if etag:
            self.etags[url] = etag
        
        # Store Last-Modified if present
        last_modified = response.headers.get("Last-Modified")
        if last_modified:
            try:
                from email.utils import parsedate_to_datetime
                self.last_modified[url] = parsedate_to_datetime(last_modified)
            except:
                pass
        
        # Save cache periodically
        if len(self.etags) % 10 == 0:
            self._save_cache()
    
    def is_not_modified(self, response) -> bool:
        """Check if response is 304 Not Modified."""
        return response.status_code == 304


# =============================================================================
# GEOGRAPHIC CONSISTENCY
# =============================================================================

class GeographicMatcher:
    """
    Match User-Agent and headers to proxy geographic region.
    
    Prevents detection from IP/UA mismatches.
    """
    
    REGIONS = {
        "US": {
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            ],
            "accept_language": "en-US,en;q=0.9",
            "timezone": "America/New_York",
        },
        "EU": {
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ],
            "accept_language": "en-GB,en;q=0.9",
            "timezone": "Europe/London",
        },
    }
    
    @staticmethod
    def get_headers_for_region(region: str = "US") -> Dict[str, str]:
        """Get headers consistent with geographic region."""
        import random
        
        region_config = GeographicMatcher.REGIONS.get(region, GeographicMatcher.REGIONS["US"])
        
        return {
            "User-Agent": random.choice(region_config["user_agents"]),
            "Accept-Language": region_config["accept_language"],
        }
    
    @staticmethod
    def detect_region_from_proxy(proxy_url: str) -> str:
        """Detect region from proxy URL."""
        # Simple detection based on proxy URL patterns
        if "us" in proxy_url.lower() or "united-states" in proxy_url.lower():
            return "US"
        elif "eu" in proxy_url.lower() or "europe" in proxy_url.lower():
            return "EU"
        else:
            return "US"  # Default


# =============================================================================
# ROBOTS.TXT RESPECT
# =============================================================================

class RobotsTxtChecker:
    """
    Check and respect robots.txt crawl delays.
    """
    
    def __init__(self):
        self.parsers: Dict[str, RobotFileParser] = {}
        self.crawl_delays: Dict[str, float] = {}
        self.last_checked: Dict[str, datetime] = {}
    
    def get_crawl_delay(self, url: str) -> float:
        """
        Get crawl delay for a URL from robots.txt.
        
        Returns delay in seconds, or 0 if not specified.
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check cache (refresh every hour)
        if domain in self.last_checked:
            if (datetime.now() - self.last_checked[domain]).total_seconds() < 3600:
                return self.crawl_delays.get(domain, 0)
        
        try:
            import requests
            
            # Fetch robots.txt
            robots_url = f"{domain}/robots.txt"
            resp = requests.get(robots_url, timeout=5)
            
            if resp.status_code == 200:
                # Parse robots.txt
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.read()
                
                self.parsers[domain] = parser
                
                # Get crawl delay for our user agent
                delay = parser.crawl_delay("*")  # Check for all user agents
                if delay:
                    self.crawl_delays[domain] = delay
                    logger.info(f"Respecting robots.txt crawl delay: {delay}s for {domain}")
                    return delay
                
                self.last_checked[domain] = datetime.now()
        except Exception as e:
            logger.debug(f"Could not fetch robots.txt for {domain}: {e}")
        
        return 0
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in self.parsers:
            # Try to fetch robots.txt
            self.get_crawl_delay(url)
        
        if domain in self.parsers:
            return self.parsers[domain].can_fetch(user_agent, url)
        
        # Default: allow if robots.txt not available
        return True


# =============================================================================
# ADAPTIVE DELAYS
# =============================================================================

class AdaptiveDelayManager:
    """
    Adjust delays based on response patterns.
    
    - Slow responses = increase delay
    - Fast responses = decrease delay
    - Errors = increase delay significantly
    """
    
    def __init__(self, base_delay: float = 2.0):
        self.base_delay = base_delay
        self.current_delays: Dict[str, float] = {}
        self.response_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
    
    def get_delay(self, retailer: str) -> float:
        """Get adaptive delay for retailer."""
        if retailer not in self.current_delays:
            self.current_delays[retailer] = self.base_delay
        
        return self.current_delays[retailer]
    
    def record_response(self, retailer: str, response_time: float, success: bool):
        """Record response and adjust delay."""
        if retailer not in self.response_times:
            self.response_times[retailer] = []
        
        self.response_times[retailer].append(response_time)
        
        # Keep only last 10 responses
        if len(self.response_times[retailer]) > 10:
            self.response_times[retailer].pop(0)
        
        # Adjust delay based on performance
        if not success:
            self.error_counts[retailer] = self.error_counts.get(retailer, 0) + 1
            # Increase delay on errors
            self.current_delays[retailer] = min(
                self.current_delays.get(retailer, self.base_delay) * 1.5,
                10.0  # Max 10 seconds
            )
        else:
            # Reset error count on success
            self.error_counts[retailer] = 0
            
            # Adjust based on response time
            avg_time = sum(self.response_times[retailer]) / len(self.response_times[retailer])
            
            if avg_time > 5.0:  # Slow responses
                self.current_delays[retailer] = min(
                    self.current_delays.get(retailer, self.base_delay) * 1.2,
                    8.0
                )
            elif avg_time < 1.0:  # Fast responses
                self.current_delays[retailer] = max(
                    self.current_delays.get(retailer, self.base_delay) * 0.9,
                    1.0  # Min 1 second
                )


# =============================================================================
# STOCK VERIFICATION
# =============================================================================

class StockVerifier:
    """
    Double-check "in stock" items to reduce false positives.
    """
    
    def __init__(self):
        self.verification_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.cache_ttl = 60  # 1 minute
    
    def verify_stock(
        self,
        product: 'Product',
        verify_func: Optional[callable] = None
    ) -> Tuple[bool, float]:
        """
        Verify stock status by double-checking.
        
        Returns:
            (is_in_stock, confidence)
        """
        # Check cache
        cache_key = f"{product.retailer}:{product.url}"
        if cache_key in self.verification_cache:
            cached_result, cached_time = self.verification_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_result, 0.8  # Cached = slightly lower confidence
        
        # If product says out of stock, trust it (no need to verify)
        if not product.stock:
            return False, 0.9
        
        # Verify in-stock items
        confidence = 0.7  # Base confidence for single check
        
        if verify_func:
            try:
                verified = verify_func(product)
                if verified:
                    confidence = 0.95  # Verified = high confidence
                else:
                    confidence = 0.3  # Verification failed = low confidence
                    return False, confidence
            except Exception as e:
                logger.warning(f"Stock verification failed: {e}")
                confidence = 0.6  # Verification error = medium confidence
        
        # Cache result
        self.verification_cache[cache_key] = (product.stock, datetime.now())
        
        return product.stock, confidence


# =============================================================================
# PRODUCT DEDUPLICATION
# =============================================================================

class ProductDeduplicator:
    """
    Better handling of duplicate products across retailers.
    """
    
    @staticmethod
    def generate_fingerprint(product: 'Product') -> str:
        """
        Generate fingerprint for product deduplication.
        
        Uses: name (normalized), price range, retailer
        """
        # Normalize name
        name_normalized = re.sub(r'[^a-z0-9]', '', product.name.lower())
        
        # Price range (round to nearest $5)
        price_range = int(product.price / 5) * 5
        
        # Generate hash
        fingerprint = hashlib.md5(
            f"{name_normalized}:{price_range}:{product.retailer}".encode()
        ).hexdigest()
        
        return fingerprint
    
    @staticmethod
    def deduplicate(products: List['Product']) -> List['Product']:
        """
        Remove duplicates, keeping best version of each.
        
        Prefers:
        - In-stock over out-of-stock
        - Higher confidence
        - Lower price
        """
        seen = {}
        
        for product in products:
            fingerprint = ProductDeduplicator.generate_fingerprint(product)
            
            if fingerprint not in seen:
                seen[fingerprint] = product
            else:
                existing = seen[fingerprint]
                
                # Prefer in-stock
                if product.stock and not existing.stock:
                    seen[fingerprint] = product
                elif existing.stock and not product.stock:
                    continue
                
                # Prefer higher confidence
                product_conf = getattr(product, 'confidence', 0.5)
                existing_conf = getattr(existing, 'confidence', 0.5)
                if product_conf > existing_conf:
                    seen[fingerprint] = product
                elif existing_conf > product_conf:
                    continue
                
                # Prefer lower price (better deal)
                if product.price < existing.price and product.price > 0:
                    seen[fingerprint] = product
        
        return list(seen.values())


# =============================================================================
# RESPONSE TIME MONITORING
# =============================================================================

class ResponseTimeMonitor:
    """
    Monitor response times and adapt scanning strategy.
    """
    
    def __init__(self):
        self.response_times: Dict[str, List[float]] = {}
        self.slow_retailers: set = set()
    
    def record_time(self, retailer: str, response_time: float):
        """Record response time."""
        if retailer not in self.response_times:
            self.response_times[retailer] = []
        
        self.response_times[retailer].append(response_time)
        
        # Keep only last 20 measurements
        if len(self.response_times[retailer]) > 20:
            self.response_times[retailer].pop(0)
        
        # Mark as slow if average > 5 seconds
        if len(self.response_times[retailer]) >= 5:
            avg_time = sum(self.response_times[retailer]) / len(self.response_times[retailer])
            if avg_time > 5.0:
                self.slow_retailers.add(retailer)
                logger.warning(
                    f"Retailer {retailer} is slow (avg: {avg_time:.2f}s)",
                    extra={"retailer": retailer, "avg_time": avg_time}
                )
            else:
                self.slow_retailers.discard(retailer)
    
    def is_slow(self, retailer: str) -> bool:
        """Check if retailer is consistently slow."""
        return retailer in self.slow_retailers
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get response time statistics."""
        stats = {}
        for retailer, times in self.response_times.items():
            if times:
                stats[retailer] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "count": len(times),
                }
        return stats


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_prioritizer = ProductPrioritizer()
_change_detection = ChangeDetection()
_geographic_matcher = GeographicMatcher()
_robots_checker = RobotsTxtChecker()
_adaptive_delays = AdaptiveDelayManager()
_stock_verifier = StockVerifier()
_deduplicator = ProductDeduplicator()
_response_monitor = ResponseTimeMonitor()

def get_prioritizer() -> ProductPrioritizer:
    return _prioritizer

def get_change_detection() -> ChangeDetection:
    return _change_detection

def get_geographic_matcher() -> GeographicMatcher:
    return _geographic_matcher

def get_robots_checker() -> RobotsTxtChecker:
    return _robots_checker

def get_adaptive_delays() -> AdaptiveDelayManager:
    return _adaptive_delays

def get_stock_verifier() -> StockVerifier:
    return _stock_verifier

def get_deduplicator() -> ProductDeduplicator:
    return _deduplicator

def get_response_monitor() -> ResponseTimeMonitor:
    return _response_monitor
