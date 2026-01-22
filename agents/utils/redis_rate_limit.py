#!/usr/bin/env python3
"""
Redis-Based Rate Limiting

Provides distributed rate limiting using Redis for multi-instance deployments.
Falls back to in-memory rate limiting if Redis is not available.
"""
import os
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from agents.utils.logger import get_logger

logger = get_logger("rate_limit")

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning("Redis not available. Install: pip install redis")

# =============================================================================
# CONFIGURATION
# =============================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))  # seconds

# =============================================================================
# REDIS RATE LIMITER
# =============================================================================

class RedisRateLimiter:
    """
    Redis-based distributed rate limiter.
    
    Uses sliding window algorithm for accurate rate limiting.
    Falls back to in-memory if Redis unavailable.
    """
    
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        redis_password: Optional[str] = None,
        max_requests: int = RATE_LIMIT_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW,
    ):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL
            redis_password: Redis password (if required)
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client = None
        self.use_redis = False
        
        # Fallback: in-memory rate limiting
        self.memory_limits: defaultdict = defaultdict(list)
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    password=redis_password or REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis rate limiter initialized", extra={"redis_url": redis_url})
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
                self.use_redis = False
        else:
            logger.info("Redis not available, using in-memory rate limiting")
    
    def check_rate_limit(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key (e.g., client IP, user ID, endpoint)
        
        Returns:
            (allowed, remaining_requests, reset_after_seconds)
        """
        if self.use_redis and self.redis_client:
            return self._check_redis(key)
        else:
            return self._check_memory(key)
    
    def _check_redis(self, key: str) -> Tuple[bool, int, int]:
        """Check rate limit using Redis."""
        try:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Use sorted set for sliding window
            redis_key = f"ratelimit:{key}"
            
            # Remove old entries
            self.redis_client.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            current_count = self.redis_client.zcard(redis_key)
            
            if current_count >= self.max_requests:
                # Get oldest request to calculate reset time
                oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    reset_after = int(oldest[0][1] + self.window_seconds - now)
                else:
                    reset_after = self.window_seconds
                
                return False, 0, max(0, reset_after)
            
            # Add current request
            self.redis_client.zadd(redis_key, {str(now): now})
            self.redis_client.expire(redis_key, self.window_seconds + 1)
            
            remaining = self.max_requests - current_count - 1
            reset_after = self.window_seconds
            
            return True, remaining, reset_after
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}", exc_info=True)
            # Fallback to memory
            return self._check_memory(key)
    
    def _check_memory(self, key: str) -> Tuple[bool, int, int]:
        """Check rate limit using in-memory storage."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old entries
        self.memory_limits[key] = [
            t for t in self.memory_limits[key] if t > window_start
        ]
        
        # Check limit
        current_count = len(self.memory_limits[key])
        
        if current_count >= self.max_requests:
            # Calculate reset time
            if self.memory_limits[key]:
                oldest = min(self.memory_limits[key])
                reset_after = int(oldest + self.window_seconds - now)
            else:
                reset_after = self.window_seconds
            
            return False, 0, max(0, reset_after)
        
        # Add current request
        self.memory_limits[key].append(now)
        
        remaining = self.max_requests - current_count - 1
        reset_after = self.window_seconds
        
        return True, remaining, reset_after
    
    def reset(self, key: str):
        """Reset rate limit for a key."""
        if self.use_redis and self.redis_client:
            try:
                redis_key = f"ratelimit:{key}"
                self.redis_client.delete(redis_key)
            except Exception as e:
                logger.error(f"Redis reset error: {e}")
        else:
            if key in self.memory_limits:
                del self.memory_limits[key]


# Global rate limiter
_rate_limiter: Optional[RedisRateLimiter] = None

def get_rate_limiter() -> RedisRateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter()
    return _rate_limiter
