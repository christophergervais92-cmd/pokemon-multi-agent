#!/usr/bin/env python3
"""
Advanced Blocking Prevention Strategies

Additional techniques to reduce blocking risk:
1. Circuit Breaker Pattern - Stop trying if consistently failing
2. Request Pattern Randomization - Vary order and timing
3. Session Longevity - Keep sessions alive longer
4. Time-of-Day Awareness - Avoid peak hours
5. Response Pattern Monitoring - Adapt to what works
6. Request Deduplication - Avoid duplicate requests
7. Progressive Backoff - Gradual slowdown on issues
8. Connection Pooling - Reuse connections
"""
import os
import time
import random
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading

from agents.utils.logger import get_logger

logger = get_logger("blocking_prevention")


# =============================================================================
# CIRCUIT BREAKER PATTERN
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, don't try
    HALF_OPEN = "half_open"  # Testing if fixed


class CircuitBreaker:
    """
    Circuit breaker pattern - stops trying if consistently failing.
    
    Prevents hammering a failing retailer and getting permanently banned.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 300,  # 5 minutes
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        
        self.state: Dict[str, CircuitState] = {}
        self.failure_count: Dict[str, int] = {}
        self.success_count: Dict[str, int] = {}
        self.last_failure: Dict[str, datetime] = {}
        self.opened_at: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def record_success(self, retailer: str):
        """Record a successful request."""
        with self.lock:
            if retailer not in self.state:
                self.state[retailer] = CircuitState.CLOSED
            
            if self.state[retailer] == CircuitState.HALF_OPEN:
                self.success_count[retailer] = self.success_count.get(retailer, 0) + 1
                
                if self.success_count[retailer] >= self.success_threshold:
                    # Circuit closed - working again
                    self.state[retailer] = CircuitState.CLOSED
                    self.failure_count[retailer] = 0
                    self.success_count[retailer] = 0
                    logger.info(f"Circuit breaker CLOSED for {retailer} - working again")
            else:
                # Reset failure count on success
                self.failure_count[retailer] = 0
    
    def record_failure(self, retailer: str):
        """Record a failed request."""
        with self.lock:
            if retailer not in self.state:
                self.state[retailer] = CircuitState.CLOSED
            
            self.failure_count[retailer] = self.failure_count.get(retailer, 0) + 1
            self.last_failure[retailer] = datetime.now()
            
            if self.failure_count[retailer] >= self.failure_threshold:
                # Open circuit - stop trying
                self.state[retailer] = CircuitState.OPEN
                self.opened_at[retailer] = datetime.now()
                logger.warning(
                    f"Circuit breaker OPENED for {retailer} - "
                    f"{self.failure_count[retailer]} consecutive failures"
                )
    
    def can_attempt(self, retailer: str) -> Tuple[bool, str]:
        """
        Check if we can attempt a request.
        
        Returns:
            (can_attempt, reason)
        """
        with self.lock:
            if retailer not in self.state:
                self.state[retailer] = CircuitState.CLOSED
                return True, "ok"
            
            state = self.state[retailer]
            
            if state == CircuitState.CLOSED:
                return True, "ok"
            
            elif state == CircuitState.OPEN:
                # Check if timeout has passed
                if retailer in self.opened_at:
                    elapsed = (datetime.now() - self.opened_at[retailer]).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        # Try half-open
                        self.state[retailer] = CircuitState.HALF_OPEN
                        self.success_count[retailer] = 0
                        logger.info(f"Circuit breaker HALF_OPEN for {retailer} - testing")
                        return True, "half_open"
                    else:
                        remaining = int(self.timeout_seconds - elapsed)
                        return False, f"circuit_open (retry in {remaining}s)"
                else:
                    return False, "circuit_open"
            
            elif state == CircuitState.HALF_OPEN:
                return True, "half_open"
            
            return True, "ok"
    
    def get_status(self, retailer: str) -> Dict:
        """Get circuit breaker status for retailer."""
        with self.lock:
            return {
                "state": self.state.get(retailer, CircuitState.CLOSED).value,
                "failure_count": self.failure_count.get(retailer, 0),
                "success_count": self.success_count.get(retailer, 0),
            }


# =============================================================================
# REQUEST PATTERN RANDOMIZATION
# =============================================================================

class RequestPatternRandomizer:
    """
    Randomizes request patterns to avoid detection.
    
    - Varies request order
    - Adds random pauses
    - Varies request timing
    """
    
    def __init__(self):
        self.request_history: Dict[str, deque] = {}  # retailer -> recent requests
        self.max_history = 10
    
    def get_randomized_order(self, retailers: List[str]) -> List[str]:
        """Get retailers in randomized order."""
        # Shuffle, but prefer retailers we haven't hit recently
        shuffled = retailers.copy()
        random.shuffle(shuffled)
        
        # Move recently-hit retailers to end
        for retailer in shuffled:
            if retailer in self.request_history:
                recent = list(self.request_history[retailer])
                if len(recent) > 0:
                    # Recently hit - move to end
                    shuffled.remove(retailer)
                    shuffled.append(retailer)
        
        return shuffled
    
    def get_inter_request_delay(self, retailer: str, base_delay: float) -> float:
        """
        Get delay between requests with randomization.
        
        Adds jitter and varies based on recent request frequency.
        """
        # Base delay
        delay = base_delay
        
        # Add jitter (±30%)
        jitter = delay * random.uniform(-0.3, 0.3)
        delay = max(0.1, delay + jitter)
        
        # If we've been hitting this retailer frequently, add extra delay
        if retailer in self.request_history:
            recent = list(self.request_history[retailer])
            if len(recent) >= 3:
                # Been hitting frequently - slow down
                delay *= 1.5
        
        return delay
    
    def record_request(self, retailer: str):
        """Record that we made a request to this retailer."""
        if retailer not in self.request_history:
            self.request_history[retailer] = deque(maxlen=self.max_history)
        
        self.request_history[retailer].append(datetime.now())


# =============================================================================
# SESSION LONGEVITY
# =============================================================================

class SessionManager:
    """
    Manages long-lived sessions for better trust.
    
    - Keeps sessions alive longer
    - Reuses cookies across requests
    - Maintains session state
    """
    
    def __init__(self, session_ttl_seconds: int = 3600):  # 1 hour
        self.sessions: Dict[str, Dict] = {}  # retailer -> session info
        self.session_ttl = session_ttl_seconds
        self.lock = threading.Lock()
    
    def get_session_id(self, retailer: str) -> Optional[str]:
        """Get active session ID for retailer."""
        with self.lock:
            if retailer in self.sessions:
                session_info = self.sessions[retailer]
                age = (datetime.now() - session_info["created"]).total_seconds()
                
                if age < self.session_ttl:
                    return session_info["session_id"]
                else:
                    # Session expired
                    del self.sessions[retailer]
            
            return None
    
    def create_session(self, retailer: str) -> str:
        """Create a new session for retailer."""
        with self.lock:
            session_id = hashlib.md5(
                f"{retailer}_{datetime.now().isoformat()}_{random.random()}".encode()
            ).hexdigest()[:16]
            
            self.sessions[retailer] = {
                "session_id": session_id,
                "created": datetime.now(),
                "request_count": 0,
            }
            
            return session_id
    
    def record_request(self, retailer: str):
        """Record a request in the session."""
        with self.lock:
            if retailer in self.sessions:
                self.sessions[retailer]["request_count"] += 1


# =============================================================================
# TIME-OF-DAY AWARENESS
# =============================================================================

class TimeOfDayAwareness:
    """
    Adjusts behavior based on time of day.
    
    - Avoids peak hours (more likely to be monitored)
    - Slows down during business hours
    - Speeds up during off-peak hours
    """
    
    def __init__(self):
        # Peak hours (more monitoring, slower)
        self.peak_hours = set(range(9, 18))  # 9 AM - 6 PM
        # Off-peak hours (less monitoring, faster)
        self.off_peak_hours = set(range(0, 6))  # Midnight - 6 AM
    
    def get_delay_multiplier(self) -> float:
        """
        Get delay multiplier based on time of day.
        
        Returns:
            Multiplier (1.0 = normal, >1.0 = slower, <1.0 = faster)
        """
        hour = datetime.now().hour
        
        if hour in self.peak_hours:
            # Peak hours - be more careful (1.5x slower)
            return 1.5
        elif hour in self.off_peak_hours:
            # Off-peak hours - can be faster (0.8x)
            return 0.8
        else:
            # Normal hours
            return 1.0
    
    def should_avoid_scanning(self) -> bool:
        """
        Check if we should avoid scanning right now.
        
        Returns True if it's a bad time (e.g., maintenance hours).
        """
        hour = datetime.now().hour
        # Avoid 2-4 AM (common maintenance window)
        if hour in [2, 3]:
            return True
        return False


# =============================================================================
# RESPONSE PATTERN MONITORING
# =============================================================================

class ResponsePatternMonitor:
    """
    Monitors response patterns and adapts behavior.
    
    - Tracks success/failure rates
    - Adapts delays based on response times
    - Detects anomalies
    """
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.responses: Dict[str, deque] = {}  # retailer -> recent responses
        self.response_times: Dict[str, deque] = {}  # retailer -> recent response times
    
    def record_response(
        self,
        retailer: str,
        success: bool,
        response_time: float,
        status_code: int = 200
    ):
        """Record a response."""
        if retailer not in self.responses:
            self.responses[retailer] = deque(maxlen=self.window_size)
            self.response_times[retailer] = deque(maxlen=self.window_size)
        
        self.responses[retailer].append({
            "success": success,
            "status_code": status_code,
            "timestamp": datetime.now(),
        })
        self.response_times[retailer].append(response_time)
    
    def get_success_rate(self, retailer: str) -> float:
        """Get recent success rate (0-1)."""
        if retailer not in self.responses:
            return 1.0
        
        responses = list(self.responses[retailer])
        if not responses:
            return 1.0
        
        successes = sum(1 for r in responses if r["success"])
        return successes / len(responses)
    
    def get_avg_response_time(self, retailer: str) -> float:
        """Get average response time."""
        if retailer not in self.response_times:
            return 1.0
        
        times = list(self.response_times[retailer])
        if not times:
            return 1.0
        
        return sum(times) / len(times)
    
    def is_degraded(self, retailer: str, threshold: float = 0.7) -> bool:
        """Check if retailer is degraded (low success rate)."""
        return self.get_success_rate(retailer) < threshold
    
    def get_recommended_delay(self, retailer: str, base_delay: float) -> float:
        """
        Get recommended delay based on response patterns.
        
        - Slow response times = increase delay
        - Low success rate = increase delay
        """
        delay = base_delay
        
        success_rate = self.get_success_rate(retailer)
        avg_time = self.get_avg_response_time(retailer)
        
        # Adjust based on success rate
        if success_rate < 0.8:
            delay *= 1.5  # 50% slower if low success
        elif success_rate < 0.9:
            delay *= 1.2  # 20% slower if moderate success
        
        # Adjust based on response time
        if avg_time > 5.0:
            delay *= 1.3  # 30% slower if slow responses
        
        return delay


# =============================================================================
# REQUEST DEDUPLICATION
# =============================================================================

class RequestDeduplicator:
    """
    Prevents duplicate requests within a time window.
    
    - Tracks recent requests
    - Prevents duplicate queries
    - Reduces unnecessary load
    """
    
    def __init__(self, dedup_window_seconds: int = 60):
        self.dedup_window = dedup_window_seconds
        self.recent_requests: Dict[str, datetime] = {}  # request_key -> timestamp
        self.lock = threading.Lock()
    
    def _make_key(self, retailer: str, query: str) -> str:
        """Create a deduplication key."""
        return hashlib.md5(f"{retailer}:{query.lower()}".encode()).hexdigest()
    
    def should_skip(self, retailer: str, query: str) -> bool:
        """
        Check if we should skip this request (recently made).
        
        Returns True if we should skip (duplicate).
        """
        with self.lock:
            key = self._make_key(retailer, query)
            
            if key in self.recent_requests:
                age = (datetime.now() - self.recent_requests[key]).total_seconds()
                if age < self.dedup_window:
                    return True  # Too recent, skip
            
            # Record this request
            self.recent_requests[key] = datetime.now()
            
            # Cleanup old entries
            cutoff = datetime.now() - timedelta(seconds=self.dedup_window * 2)
            self.recent_requests = {
                k: v for k, v in self.recent_requests.items()
                if v > cutoff
            }
            
            return False


# =============================================================================
# PROGRESSIVE BACKOFF
# =============================================================================

class ProgressiveBackoff:
    """
    Progressive backoff - gradually slows down on issues.
    
    - Starts fast
    - Gradually slows down if issues detected
    - Resets on success
    """
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delays: Dict[str, float] = {}
        self.consecutive_failures: Dict[str, int] = {}
    
    def record_success(self, retailer: str):
        """Record success - reset backoff."""
        self.consecutive_failures[retailer] = 0
        self.current_delays[retailer] = self.base_delay
    
    def record_failure(self, retailer: str):
        """Record failure - increase backoff."""
        failures = self.consecutive_failures.get(retailer, 0) + 1
        self.consecutive_failures[retailer] = failures
        
        # Exponential backoff: base * 2^failures
        delay = min(
            self.max_delay,
            self.base_delay * (2 ** min(failures, 5))  # Cap at 2^5 = 32x
        )
        self.current_delays[retailer] = delay
    
    def get_delay(self, retailer: str) -> float:
        """Get current delay for retailer."""
        return self.current_delays.get(retailer, self.base_delay)


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_circuit_breaker = CircuitBreaker()
_pattern_randomizer = RequestPatternRandomizer()
_session_manager = SessionManager()
_time_awareness = TimeOfDayAwareness()
_response_monitor = ResponsePatternMonitor()
_deduplicator = RequestDeduplicator()
_progressive_backoff = ProgressiveBackoff()

def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker

def get_pattern_randomizer() -> RequestPatternRandomizer:
    return _pattern_randomizer

def get_session_manager() -> SessionManager:
    return _session_manager

def get_time_awareness() -> TimeOfDayAwareness:
    return _time_awareness

def get_response_monitor() -> ResponsePatternMonitor:
    return _response_monitor

def get_deduplicator() -> RequestDeduplicator:
    return _deduplicator

def get_progressive_backoff() -> ProgressiveBackoff:
    return _progressive_backoff
