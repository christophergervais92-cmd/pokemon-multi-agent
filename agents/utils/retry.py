#!/usr/bin/env python3
"""
Retry Logic with Exponential Backoff

Provides automatic retry with:
- Exponential backoff
- Configurable max retries
- Retry on specific exceptions
- Jitter to prevent thundering herd
"""
import time
import random
from functools import wraps
from typing import Callable, Type, Tuple, List, Optional
from datetime import datetime, timedelta

from agents.utils.logger import get_logger

logger = get_logger("retry")

# =============================================================================
# RETRY DECORATOR
# =============================================================================

def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: Tuple[Type[Exception], ...] = None,
    on_retry: Optional[Callable] = None,
):
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff (2.0 = doubles each time)
        jitter: Add random jitter to prevent thundering herd
        retry_on: Tuple of exception types to retry on (None = all exceptions)
        on_retry: Optional callback function called on each retry
    
    Usage:
        @retry(max_retries=3, base_delay=1.0)
        def fetch_data():
            ...
    """
    if retry_on is None:
        retry_on = (Exception,)
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                
                except retry_on as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                            exc_info=True
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter (±20%)
                    if jitter:
                        jitter_amount = delay * random.uniform(-0.2, 0.2)
                        delay = max(0, delay + jitter_amount)
                    
                    logger.warning(
                        f"{func.__name__} failed, retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_seconds": round(delay, 2),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e, delay)
                        except Exception as callback_error:
                            logger.error(
                                "Retry callback error",
                                extra={"error": str(callback_error)},
                                exc_info=True
                            )
                    
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# SPECIFIC RETRY STRATEGIES
# =============================================================================

def retry_on_network_error(
    max_retries: int = 3,
    base_delay: float = 2.0,
):
    """Retry on network-related errors."""
    import requests
    
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        retry_on=(
            requests.exceptions.RequestException,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            ConnectionError,
            TimeoutError,
        ),
    )


def retry_on_rate_limit(
    max_retries: int = 5,
    base_delay: float = 5.0,
    max_delay: float = 300.0,  # 5 minutes max
):
    """Retry on rate limit errors with longer delays."""
    import requests
    
    def on_retry(attempt, error, delay):
        if hasattr(error, 'response') and error.response:
            retry_after = error.response.headers.get('Retry-After')
            if retry_after:
                logger.info(f"Rate limited, waiting {retry_after}s")
    
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=(
            requests.exceptions.HTTPError,
        ),
        on_retry=on_retry,
    )


def retry_on_timeout(
    max_retries: int = 2,
    base_delay: float = 1.0,
):
    """Retry on timeout errors."""
    import requests
    
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        retry_on=(
            requests.exceptions.Timeout,
            TimeoutError,
        ),
    )
