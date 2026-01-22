#!/usr/bin/env python3
"""
Security Module for Pokemon Multi-Agent System

Provides:
- Input validation and sanitization
- Rate limiting
- API key validation
- Request logging (anonymized)
- SQL injection prevention
- XSS prevention
"""
import os
import re
import time
import hashlib
import secrets
from functools import wraps
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import html

# =============================================================================
# CONFIGURATION
# =============================================================================

# API key for protecting endpoints (optional)
API_KEY = os.environ.get("POKEMON_API_KEY", "")
API_KEY_REQUIRED = os.environ.get("POKEMON_API_KEY_REQUIRED", "false").lower() == "true"

# Rate limiting
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))  # seconds

# Request tracking for rate limiting
_request_counts: Dict[str, List[float]] = defaultdict(list)


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize a string input to prevent injection attacks.
    
    - Escapes HTML entities
    - Removes null bytes
    - Limits length
    - Strips leading/trailing whitespace
    """
    if not isinstance(value, str):
        return ""
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Escape HTML to prevent XSS
    value = html.escape(value)
    
    # Limit length
    value = value[:max_length]
    
    # Strip whitespace
    value = value.strip()
    
    return value


def validate_zip_code(zip_code: str) -> Optional[str]:
    """
    Validate and sanitize a US ZIP code.
    Returns sanitized ZIP or None if invalid.
    """
    if not zip_code:
        return None
    
    # Remove non-digits
    cleaned = re.sub(r'\D', '', str(zip_code))
    
    # Must be 5 digits
    if len(cleaned) != 5:
        return None
    
    # Basic range check (00000-99999 are valid formats)
    return cleaned


def validate_email(email: str) -> Optional[str]:
    """
    Validate and sanitize an email address.
    Returns sanitized email or None if invalid.
    """
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return None
    
    return email[:254]  # Max email length per RFC


def validate_price(price: Any) -> Optional[float]:
    """
    Validate and sanitize a price value.
    Returns float or None if invalid.
    """
    try:
        price = float(price)
        if price < 0 or price > 100000:  # Reasonable bounds
            return None
        return round(price, 2)
    except (TypeError, ValueError):
        return None


def validate_discord_id(discord_id: str) -> Optional[str]:
    """
    Validate a Discord user ID (snowflake).
    Must be a numeric string of 17-19 digits.
    """
    if not discord_id or not isinstance(discord_id, str):
        return None
    
    # Remove non-digits
    cleaned = re.sub(r'\D', '', str(discord_id))
    
    # Discord snowflakes are 17-19 digits
    if len(cleaned) < 17 or len(cleaned) > 19:
        return None
    
    return cleaned


def sanitize_search_query(query: str, max_length: int = 100) -> str:
    """
    Sanitize a search query.
    Removes SQL injection attempts and special characters.
    """
    if not query:
        return ""
    
    # Remove SQL injection patterns
    sql_patterns = [
        r"(;|--|/\*|\*/|'|\"|\bOR\b|\bAND\b|\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bUPDATE\b|\bDROP\b)",
    ]
    
    for pattern in sql_patterns:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    # Only allow alphanumeric, spaces, and basic punctuation
    query = re.sub(r'[^a-zA-Z0-9\s\-_.]', '', query)
    
    return query[:max_length].strip()


def validate_url(url: str) -> Optional[str]:
    """
    Validate and sanitize a URL.
    Only allows http/https URLs from known retailers.
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return None
    
    # Allowed domains
    allowed_domains = [
        'target.com', 'www.target.com',
        'walmart.com', 'www.walmart.com',
        'bestbuy.com', 'www.bestbuy.com',
        'gamestop.com', 'www.gamestop.com',
        'costco.com', 'www.costco.com',
        'pokemoncenter.com', 'www.pokemoncenter.com',
    ]
    
    # Extract domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if not any(domain == d or domain.endswith('.' + d) for d in allowed_domains):
            return None
        
        return url[:2000]  # Max URL length
    except Exception:
        return None


# =============================================================================
# RATE LIMITING
# =============================================================================

def check_rate_limit(client_id: str) -> tuple[bool, int]:
    """
    Check if client is within rate limit.
    
    Returns:
        (allowed, remaining_requests)
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old requests
    _request_counts[client_id] = [
        t for t in _request_counts[client_id] if t > window_start
    ]
    
    # Check limit
    current_count = len(_request_counts[client_id])
    remaining = max(0, RATE_LIMIT_REQUESTS - current_count)
    
    if current_count >= RATE_LIMIT_REQUESTS:
        return False, 0
    
    # Record this request
    _request_counts[client_id].append(now)
    
    return True, remaining - 1


def rate_limit(get_client_id: Callable = None):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        get_client_id: Function to extract client ID from request
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get client ID (default to IP or 'anonymous')
            client_id = 'anonymous'
            if get_client_id:
                try:
                    client_id = get_client_id()
                except:
                    pass
            
            allowed, remaining = check_rate_limit(client_id)
            
            if not allowed:
                return {
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Try again in {RATE_LIMIT_WINDOW} seconds.",
                    "retry_after": RATE_LIMIT_WINDOW,
                }
            
            result = func(*args, **kwargs)
            
            # Add rate limit headers to response if it's a dict
            if isinstance(result, dict):
                result["_rate_limit"] = {
                    "remaining": remaining,
                    "window": RATE_LIMIT_WINDOW,
                }
            
            return result
        
        return wrapper
    return decorator


# =============================================================================
# API KEY VALIDATION
# =============================================================================

def validate_api_key(provided_key: str) -> bool:
    """
    Validate an API key using constant-time comparison.
    """
    if not API_KEY:
        return True  # No key configured = allow all
    
    if not provided_key:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(API_KEY, provided_key)


def require_api_key(func):
    """
    Decorator to require API key for an endpoint.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not API_KEY_REQUIRED:
            return func(*args, **kwargs)
        
        # Try to get API key from header or query param
        provided_key = None
        try:
            from flask import request
            provided_key = (
                request.headers.get('X-API-Key') or
                request.headers.get('Authorization', '').replace('Bearer ', '') or
                request.args.get('api_key')
            )
        except:
            pass
        
        if not validate_api_key(provided_key):
            return {
                "error": "unauthorized",
                "message": "Invalid or missing API key",
            }
        
        return func(*args, **kwargs)
    
    return wrapper


# =============================================================================
# LOGGING (Anonymized)
# =============================================================================

def anonymize_ip(ip: str) -> str:
    """
    Anonymize an IP address for privacy-compliant logging.
    Hashes the full IP but keeps enough for basic analysis.
    """
    if not ip:
        return "unknown"
    
    # Hash the IP
    hashed = hashlib.sha256(ip.encode()).hexdigest()[:8]
    
    # For IPv4, keep first two octets
    if '.' in ip:
        parts = ip.split('.')
        return f"{parts[0]}.{parts[1]}.x.x ({hashed})"
    
    # For IPv6, keep first block
    if ':' in ip:
        parts = ip.split(':')
        return f"{parts[0]}:x:x:x ({hashed})"
    
    return f"x.x.x.x ({hashed})"


def log_request(
    endpoint: str,
    client_id: str,
    success: bool,
    details: str = ""
):
    """
    Log a request in a privacy-compliant way.
    """
    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILURE"
    
    # Anonymize client ID if it looks like an IP
    if '.' in client_id or ':' in client_id:
        client_id = anonymize_ip(client_id)
    
    # Print log (in production, send to logging service)
    print(f"[{timestamp}] {status} {endpoint} client={client_id} {details}")


# =============================================================================
# SECURE CONFIGURATION
# =============================================================================

def get_secure_config() -> Dict[str, Any]:
    """
    Get current security configuration.
    Does not expose sensitive values.
    """
    return {
        "api_key_required": API_KEY_REQUIRED,
        "api_key_configured": bool(API_KEY),
        "rate_limit": {
            "requests": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW,
        },
        "features": {
            "input_sanitization": True,
            "sql_injection_prevention": True,
            "xss_prevention": True,
            "rate_limiting": True,
            "anonymized_logging": True,
        }
    }


# =============================================================================
# UTILITY
# =============================================================================

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data for storage.
    Use for comparing passwords, not for reversible encryption.
    """
    salt = os.environ.get("POKEMON_SALT", "default-salt-change-me")
    return hashlib.pbkdf2_hmac(
        'sha256',
        data.encode(),
        salt.encode(),
        100000
    ).hex()
