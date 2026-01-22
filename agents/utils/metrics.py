#!/usr/bin/env python3
"""
Performance Metrics Collection

Tracks:
- Request times
- Success/failure rates
- Cache hit rates
- Error rates
- Queue statistics
"""
import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock
from functools import wraps

from agents.utils.logger import get_logger

logger = get_logger("metrics")

# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    
    Tracks:
    - Request times per endpoint
    - Success/failure rates
    - Cache hit rates
    - Error rates
    - Throughput
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of recent measurements to keep
        """
        self.window_size = window_size
        self.lock = Lock()
        
        # Request metrics
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        
        # Cache metrics
        self.cache_hits: Dict[str, int] = defaultdict(int)
        self.cache_misses: Dict[str, int] = defaultdict(int)
        
        # Error metrics
        self.error_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Timestamps for time-based calculations
        self.start_time = datetime.now()
    
    def record_request(
        self,
        endpoint: str,
        duration: float,
        success: bool = True,
        error_type: Optional[str] = None,
    ):
        """Record a request metric."""
        with self.lock:
            self.request_times[endpoint].append(duration)
            self.request_counts[endpoint] += 1
            
            if success:
                self.success_counts[endpoint] += 1
            else:
                self.failure_counts[endpoint] += 1
                if error_type:
                    self.error_counts[endpoint][error_type] += 1
    
    def record_cache(self, cache_key: str, hit: bool):
        """Record a cache hit/miss."""
        with self.lock:
            if hit:
                self.cache_hits[cache_key] += 1
            else:
                self.cache_misses[cache_key] += 1
    
    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get statistics for an endpoint."""
        with self.lock:
            times = list(self.request_times[endpoint])
            count = self.request_counts[endpoint]
            success = self.success_counts[endpoint]
            failure = self.failure_counts[endpoint]
            
            if not times:
                return {
                    "endpoint": endpoint,
                    "total_requests": 0,
                    "success_rate": 0.0,
                    "avg_duration": 0.0,
                    "p50_duration": 0.0,
                    "p95_duration": 0.0,
                    "p99_duration": 0.0,
                }
            
            sorted_times = sorted(times)
            n = len(sorted_times)
            
            return {
                "endpoint": endpoint,
                "total_requests": count,
                "success_count": success,
                "failure_count": failure,
                "success_rate": (success / count * 100) if count > 0 else 0.0,
                "avg_duration": sum(times) / n,
                "min_duration": min(times),
                "max_duration": max(times),
                "p50_duration": sorted_times[int(n * 0.50)],
                "p95_duration": sorted_times[int(n * 0.95)] if n > 1 else sorted_times[0],
                "p99_duration": sorted_times[int(n * 0.99)] if n > 1 else sorted_times[0],
                "errors": dict(self.error_counts[endpoint]),
            }
    
    def get_cache_stats(self, cache_key: str = None) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            if cache_key:
                hits = self.cache_hits.get(cache_key, 0)
                misses = self.cache_misses.get(cache_key, 0)
                total = hits + misses
                
                return {
                    "cache_key": cache_key,
                    "hits": hits,
                    "misses": misses,
                    "total": total,
                    "hit_rate": (hits / total * 100) if total > 0 else 0.0,
                }
            else:
                # Aggregate stats
                all_hits = sum(self.cache_hits.values())
                all_misses = sum(self.cache_misses.values())
                total = all_hits + all_misses
                
                return {
                    "total_hits": all_hits,
                    "total_misses": all_misses,
                    "total_requests": total,
                    "overall_hit_rate": (all_hits / total * 100) if total > 0 else 0.0,
                    "by_key": {
                        key: {
                            "hits": self.cache_hits[key],
                            "misses": self.cache_misses[key],
                        }
                        for key in set(list(self.cache_hits.keys()) + list(self.cache_misses.keys()))
                    },
                }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary."""
        with self.lock:
            uptime = (datetime.now() - self.start_time).total_seconds()
            total_requests = sum(self.request_counts.values())
            total_success = sum(self.success_counts.values())
            total_failure = sum(self.failure_counts.values())
            
            # Calculate throughput
            requests_per_second = total_requests / uptime if uptime > 0 else 0
            
            # Get all endpoint stats
            endpoint_stats = {
                endpoint: self.get_endpoint_stats(endpoint)
                for endpoint in self.request_counts.keys()
            }
            
            return {
                "uptime_seconds": round(uptime, 2),
                "total_requests": total_requests,
                "total_success": total_success,
                "total_failure": total_failure,
                "overall_success_rate": (total_success / total_requests * 100) if total_requests > 0 else 0.0,
                "requests_per_second": round(requests_per_second, 2),
                "endpoints": endpoint_stats,
                "cache": self.get_cache_stats(),
            }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.request_times.clear()
            self.request_counts.clear()
            self.success_counts.clear()
            self.failure_counts.clear()
            self.cache_hits.clear()
            self.cache_misses.clear()
            self.error_counts.clear()
            self.start_time = datetime.now()


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None

def get_metrics() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# =============================================================================
# DECORATORS
# =============================================================================

def track_metrics(endpoint: str = None):
    """
    Decorator to track function performance metrics.
    
    Usage:
        @track_metrics(endpoint="scanner/target")
        def scan_target(query):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            endpoint_name = endpoint or func.__name__
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                get_metrics().record_request(
                    endpoint=endpoint_name,
                    duration=duration,
                    success=success,
                    error_type=error_type,
                )
        
        return wrapper
    return decorator
