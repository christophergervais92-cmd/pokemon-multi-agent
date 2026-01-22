#!/usr/bin/env python3
"""
CAPTCHA Detection and Handling Module

Detects CAPTCHA challenges from retailers and provides strategies:
1. Detection - Identify when a CAPTCHA is present
2. Backoff - Slow down requests when detected
3. Notification - Alert users that manual intervention may be needed
4. Bypass strategies - Cookie refresh, session rotation, etc.

NOTE: This module does NOT automatically solve CAPTCHAs.
Automated CAPTCHA solving may violate Terms of Service.
"""
import os
import re
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import requests


# =============================================================================
# CAPTCHA TYPES
# =============================================================================

class CaptchaType(Enum):
    """Types of CAPTCHAs we can detect."""
    NONE = "none"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    PERIMETERX = "perimeterx"
    DATADOME = "datadome"
    AKAMAI = "akamai"
    INCAPSULA = "incapsula"
    GENERIC = "generic"


@dataclass
class CaptchaDetection:
    """Result of CAPTCHA detection."""
    detected: bool
    captcha_type: CaptchaType
    confidence: float  # 0.0 to 1.0
    retry_after: int  # Suggested wait time in seconds
    message: str
    raw_indicators: List[str]


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

# Patterns that indicate CAPTCHA presence
CAPTCHA_PATTERNS = {
    CaptchaType.RECAPTCHA_V2: [
        r'class="g-recaptcha"',
        r'data-sitekey=',
        r'www\.google\.com/recaptcha',
        r'grecaptcha\.render',
        r'api\.recaptcha\.net',
    ],
    CaptchaType.RECAPTCHA_V3: [
        r'grecaptcha\.execute',
        r'recaptcha/api\.js\?render=',
        r'grecaptcha\.ready',
    ],
    CaptchaType.HCAPTCHA: [
        r'hcaptcha\.com',
        r'class="h-captcha"',
        r'data-hcaptcha-widget-id',
    ],
    CaptchaType.CLOUDFLARE: [
        r'cf-browser-verification',
        r'Checking your browser',
        r'cf_clearance',
        r'__cf_bm',
        r'ray ID',
        r'cloudflare',
        r'challenge-platform',
    ],
    CaptchaType.PERIMETERX: [
        r'_px\d+',
        r'px-captcha',
        r'perimeterx',
        r'human\.px-cdn',
    ],
    CaptchaType.DATADOME: [
        r'datadome',
        r'dd_p',
        r'captcha\.datadome\.co',
    ],
    CaptchaType.AKAMAI: [
        r'_abck',
        r'bm_sz',
        r'ak_bmsc',
        r'akamai',
    ],
    CaptchaType.INCAPSULA: [
        r'incap_ses',
        r'visid_incap',
        r'incapsula',
    ],
    CaptchaType.GENERIC: [
        r'captcha',
        r'robot',
        r'human verification',
        r'are you a robot',
        r'prove you\'re human',
        r'security check',
        r'please verify',
        r'access denied',
        r'blocked',
        r'rate limit',
        r'too many requests',
    ],
}

# HTTP status codes that indicate blocking
BLOCKING_STATUS_CODES = {
    403: "Forbidden - likely blocked",
    429: "Rate limited",
    503: "Service unavailable - may be blocking",
    520: "Cloudflare error",
    521: "Cloudflare origin unreachable",
    522: "Cloudflare connection timeout",
    523: "Cloudflare origin unreachable",
    524: "Cloudflare timeout",
}


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_captcha(
    response: requests.Response = None,
    html_content: str = None,
    headers: Dict[str, str] = None,
) -> CaptchaDetection:
    """
    Detect if a CAPTCHA or bot protection is present.
    
    Args:
        response: The HTTP response object
        html_content: Raw HTML content to analyze
        headers: Response headers to analyze
    
    Returns:
        CaptchaDetection with results
    """
    indicators = []
    detected_types = []
    
    # Get content to analyze
    content = html_content or ""
    if response is not None:
        try:
            content = response.text
            headers = dict(response.headers)
        except:
            pass
    
    content_lower = content.lower()
    
    # Check status code
    if response is not None:
        if response.status_code in BLOCKING_STATUS_CODES:
            indicators.append(f"Status {response.status_code}: {BLOCKING_STATUS_CODES[response.status_code]}")
            detected_types.append(CaptchaType.GENERIC)
    
    # Check for specific CAPTCHA types
    for captcha_type, patterns in CAPTCHA_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                indicators.append(f"{captcha_type.value}: {pattern}")
                if captcha_type not in detected_types:
                    detected_types.append(captcha_type)
    
    # Check headers for protection indicators
    if headers:
        header_lower = {k.lower(): v for k, v in headers.items()}
        
        # Cloudflare headers
        if 'cf-ray' in header_lower:
            indicators.append("Cloudflare detected (CF-Ray header)")
            if CaptchaType.CLOUDFLARE not in detected_types:
                detected_types.append(CaptchaType.CLOUDFLARE)
        
        # Server header
        server = header_lower.get('server', '').lower()
        if 'cloudflare' in server:
            indicators.append("Cloudflare server")
            if CaptchaType.CLOUDFLARE not in detected_types:
                detected_types.append(CaptchaType.CLOUDFLARE)
        
        # Check for challenge cookies
        set_cookie = header_lower.get('set-cookie', '')
        if '__cf_bm' in set_cookie or 'cf_clearance' in set_cookie:
            indicators.append("Cloudflare challenge cookie")
            if CaptchaType.CLOUDFLARE not in detected_types:
                detected_types.append(CaptchaType.CLOUDFLARE)
    
    # Determine result
    detected = len(detected_types) > 0
    
    # Get primary type (most specific)
    primary_type = CaptchaType.NONE
    if detected_types:
        # Prefer specific types over generic
        for ct in detected_types:
            if ct != CaptchaType.GENERIC:
                primary_type = ct
                break
        if primary_type == CaptchaType.NONE:
            primary_type = detected_types[0]
    
    # Calculate confidence
    confidence = min(1.0, len(indicators) * 0.25)
    
    # Determine retry time based on type
    retry_times = {
        CaptchaType.CLOUDFLARE: 30,
        CaptchaType.PERIMETERX: 60,
        CaptchaType.DATADOME: 45,
        CaptchaType.AKAMAI: 60,
        CaptchaType.RECAPTCHA_V2: 120,  # Needs manual solve
        CaptchaType.RECAPTCHA_V3: 30,
        CaptchaType.HCAPTCHA: 120,
        CaptchaType.GENERIC: 60,
    }
    retry_after = retry_times.get(primary_type, 30)
    
    # Build message
    if detected:
        message = f"CAPTCHA/Bot protection detected: {primary_type.value}"
    else:
        message = "No CAPTCHA detected"
    
    return CaptchaDetection(
        detected=detected,
        captcha_type=primary_type,
        confidence=confidence,
        retry_after=retry_after,
        message=message,
        raw_indicators=indicators,
    )


def is_blocked(response: requests.Response) -> bool:
    """Quick check if response indicates blocking."""
    detection = detect_captcha(response=response)
    return detection.detected


# =============================================================================
# HANDLING STRATEGIES
# =============================================================================

class CaptchaHandler:
    """
    Handles CAPTCHA detection and response strategies.
    """
    
    def __init__(self):
        self.detections: List[Tuple[datetime, str, CaptchaDetection]] = []
        self.backoff_until: Dict[str, datetime] = {}
        self.consecutive_blocks: Dict[str, int] = {}
    
    def record_detection(self, domain: str, detection: CaptchaDetection):
        """Record a CAPTCHA detection."""
        self.detections.append((datetime.now(), domain, detection))
        
        if detection.detected:
            self.consecutive_blocks[domain] = self.consecutive_blocks.get(domain, 0) + 1
            
            # Exponential backoff
            backoff_multiplier = min(8, 2 ** self.consecutive_blocks[domain])
            backoff_seconds = detection.retry_after * backoff_multiplier
            
            self.backoff_until[domain] = datetime.now() + timedelta(seconds=backoff_seconds)
        else:
            # Reset on success
            self.consecutive_blocks[domain] = 0
    
    def should_wait(self, domain: str) -> Tuple[bool, int]:
        """
        Check if we should wait before making a request.
        
        Returns:
            (should_wait, seconds_to_wait)
        """
        if domain not in self.backoff_until:
            return False, 0
        
        if datetime.now() < self.backoff_until[domain]:
            wait_seconds = int((self.backoff_until[domain] - datetime.now()).total_seconds())
            return True, wait_seconds
        
        return False, 0
    
    def get_strategy(self, detection: CaptchaDetection) -> Dict[str, Any]:
        """
        Get recommended handling strategy for a detection.
        """
        strategies = {
            CaptchaType.CLOUDFLARE: {
                "action": "wait_and_retry",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "Clear cookies and try again",
                    "Use a different IP (proxy rotation)",
                    "Slow down request rate",
                    "Try accessing from a browser first to get cf_clearance cookie",
                ],
                "can_auto_solve": False,
            },
            CaptchaType.RECAPTCHA_V2: {
                "action": "manual_intervention",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "Manual solve required in browser",
                    "Consider using a CAPTCHA solving service (2Captcha, Anti-Captcha)",
                    "Slow down significantly",
                ],
                "can_auto_solve": False,  # Requires paid service
            },
            CaptchaType.RECAPTCHA_V3: {
                "action": "wait_and_retry",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "Score-based - improve browser fingerprint",
                    "Slow down requests",
                    "Use residential proxies",
                ],
                "can_auto_solve": False,
            },
            CaptchaType.HCAPTCHA: {
                "action": "manual_intervention",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "Manual solve usually required",
                    "hCaptcha solving services exist",
                ],
                "can_auto_solve": False,
            },
            CaptchaType.PERIMETERX: {
                "action": "session_rotation",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "Rotate session/cookies",
                    "Change IP address",
                    "PerimeterX tracks browser fingerprint",
                ],
                "can_auto_solve": False,
            },
            CaptchaType.DATADOME: {
                "action": "wait_and_retry",
                "wait_seconds": detection.retry_after,
                "tips": [
                    "DataDome uses behavioral analysis",
                    "Slow down significantly",
                    "Use realistic mouse/scroll patterns in browser automation",
                ],
                "can_auto_solve": False,
            },
        }
        
        default_strategy = {
            "action": "wait_and_retry",
            "wait_seconds": detection.retry_after,
            "tips": [
                "Wait and retry",
                "Consider slowing down",
                "Try rotating IP/proxy",
            ],
            "can_auto_solve": False,
        }
        
        return strategies.get(detection.captcha_type, default_strategy)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CAPTCHA detection statistics."""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        
        recent = [d for d in self.detections if d[0] > last_hour]
        
        by_type = {}
        by_domain = {}
        
        for ts, domain, detection in recent:
            if detection.detected:
                t = detection.captcha_type.value
                by_type[t] = by_type.get(t, 0) + 1
                by_domain[domain] = by_domain.get(domain, 0) + 1
        
        return {
            "total_requests_last_hour": len(recent),
            "captchas_detected_last_hour": sum(by_type.values()),
            "by_type": by_type,
            "by_domain": by_domain,
            "currently_blocked_domains": list(self.backoff_until.keys()),
        }


# =============================================================================
# GLOBAL HANDLER
# =============================================================================

_handler = CaptchaHandler()


def check_response(response: requests.Response, domain: str = None) -> CaptchaDetection:
    """
    Check a response for CAPTCHA and record it.
    
    This is the main function to call after each request.
    """
    if domain is None:
        try:
            from urllib.parse import urlparse
            domain = urlparse(response.url).netloc
        except:
            domain = "unknown"
    
    detection = detect_captcha(response=response)
    _handler.record_detection(domain, detection)
    
    return detection


def should_wait_for_domain(domain: str) -> Tuple[bool, int]:
    """Check if we should wait before requesting from a domain."""
    return _handler.should_wait(domain)


def get_captcha_stats() -> Dict[str, Any]:
    """Get CAPTCHA statistics."""
    return _handler.get_stats()


def get_strategy_for_response(response: requests.Response) -> Dict[str, Any]:
    """Get recommended strategy for handling a blocked response."""
    detection = detect_captcha(response=response)
    return _handler.get_strategy(detection)


# =============================================================================
# INTEGRATION WITH STEALTH SESSION
# =============================================================================

def wrap_request(func):
    """
    Decorator to add CAPTCHA detection to a request function.
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if we should wait
        url = args[0] if args else kwargs.get('url', '')
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            should_wait, wait_time = should_wait_for_domain(domain)
            if should_wait:
                print(f"⚠️ Waiting {wait_time}s before request to {domain} (CAPTCHA backoff)")
                time.sleep(wait_time)
        except:
            pass
        
        # Make the request
        response = func(*args, **kwargs)
        
        # Check for CAPTCHA
        try:
            detection = check_response(response)
            if detection.detected:
                print(f"🔒 CAPTCHA detected: {detection.message}")
                print(f"   Suggested wait: {detection.retry_after}s")
        except:
            pass
        
        return response
    
    return wrapper


if __name__ == "__main__":
    # Test detection
    test_html = """
    <html>
    <head><title>Please verify</title></head>
    <body>
    <div class="g-recaptcha" data-sitekey="test123"></div>
    <script src="https://www.google.com/recaptcha/api.js"></script>
    </body>
    </html>
    """
    
    detection = detect_captcha(html_content=test_html)
    print(f"Detection result: {detection}")
    print(f"Strategy: {_handler.get_strategy(detection)}")
