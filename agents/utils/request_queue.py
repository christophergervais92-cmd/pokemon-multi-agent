#!/usr/bin/env python3
"""
Request Queue System

Manages concurrent requests to prevent system overload:
- Queue requests per endpoint
- Limit concurrent requests
- Priority queuing
- Request timeout handling
"""
import os
import threading
import time
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import PriorityQueue, Empty
from functools import wraps
import uuid

from agents.utils.logger import get_logger

logger = get_logger("request_queue")

# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_CONCURRENT_REQUESTS = int(os.environ.get("MAX_CONCURRENT_REQUESTS", "10"))
MAX_QUEUE_SIZE = int(os.environ.get("MAX_QUEUE_SIZE", "100"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))  # seconds
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 5
PRIORITY_LOW = 10

# =============================================================================
# REQUEST QUEUE
# =============================================================================

@dataclass
class QueuedRequest:
    """Represents a queued request."""
    request_id: str
    endpoint: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = PRIORITY_NORMAL
    timeout: int = REQUEST_TIMEOUT
    created_at: datetime = field(default_factory=datetime.now)
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """For priority queue (lower priority number = higher priority)."""
        return self.priority < other.priority


class RequestQueue:
    """
    Manages request queuing and execution.
    
    Features:
    - Priority queuing
    - Concurrent request limiting
    - Timeout handling
    - Request tracking
    """
    
    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
        max_queue_size: int = MAX_QUEUE_SIZE,
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)
        self.active_requests: Dict[str, threading.Thread] = {}
        self.request_results: Dict[str, Any] = {}
        self.request_errors: Dict[str, Exception] = {}
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_timeout": 0,
            "current_active": 0,
            "current_queued": 0,
        }
    
    def start(self):
        """Start the queue worker thread."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Request queue started", extra={"max_concurrent": self.max_concurrent})
    
    def stop(self):
        """Stop the queue worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Request queue stopped")
    
    def enqueue(
        self,
        endpoint: str,
        func: Callable,
        *args,
        priority: int = PRIORITY_NORMAL,
        timeout: int = REQUEST_TIMEOUT,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """
        Enqueue a request.
        
        Args:
            endpoint: Endpoint name (for tracking)
            func: Function to execute
            *args: Function arguments
            priority: Request priority (lower = higher priority)
            timeout: Request timeout in seconds
            callback: Callback on success
            error_callback: Callback on error
            **kwargs: Function keyword arguments
        
        Returns:
            Request ID
        """
        request_id = str(uuid.uuid4())
        
        # Check queue size
        if self.queue.qsize() >= self.max_queue_size:
            logger.warning(
                "Queue full, rejecting request",
                extra={"endpoint": endpoint, "queue_size": self.queue.qsize()}
            )
            raise RuntimeError(f"Queue is full ({self.max_queue_size} requests)")
        
        # Create queued request
        queued_request = QueuedRequest(
            request_id=request_id,
            endpoint=endpoint,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            callback=callback,
            error_callback=error_callback,
        )
        
        # Enqueue
        self.queue.put(queued_request)
        
        with self.lock:
            self.stats["total_queued"] += 1
            self.stats["current_queued"] = self.queue.qsize()
        
        logger.debug(
            "Request enqueued",
            extra={
                "request_id": request_id,
                "endpoint": endpoint,
                "priority": priority,
                "queue_size": self.queue.qsize(),
            }
        )
        
        return request_id
    
    def _worker(self):
        """Worker thread that processes queued requests."""
        while self.running:
            try:
                # Check if we can process more requests
                with self.lock:
                    if len(self.active_requests) >= self.max_concurrent:
                        time.sleep(0.1)  # Wait a bit
                        continue
                
                # Get next request (with timeout)
                try:
                    queued_request = self.queue.get(timeout=1)
                except Empty:
                    continue
                
                # Execute request in separate thread
                thread = threading.Thread(
                    target=self._execute_request,
                    args=(queued_request,),
                    daemon=True
                )
                thread.start()
                
                with self.lock:
                    self.active_requests[queued_request.request_id] = thread
                    self.stats["current_active"] = len(self.active_requests)
                
            except Exception as e:
                logger.error("Error in queue worker", extra={"error": str(e)}, exc_info=True)
    
    def _execute_request(self, queued_request: QueuedRequest):
        """Execute a queued request."""
        request_id = queued_request.request_id
        start_time = time.time()
        
        try:
            logger.debug(
                "Executing request",
                extra={
                    "request_id": request_id,
                    "endpoint": queued_request.endpoint,
                }
            )
            
            # Execute function with timeout
            result = self._execute_with_timeout(
                queued_request.func,
                queued_request.timeout,
                *queued_request.args,
                **queued_request.kwargs
            )
            
            duration = time.time() - start_time
            
            # Store result
            self.request_results[request_id] = {
                "result": result,
                "duration": duration,
                "completed_at": datetime.now().isoformat(),
            }
            
            # Call success callback
            if queued_request.callback:
                try:
                    queued_request.callback(result)
                except Exception as e:
                    logger.error(
                        "Callback error",
                        extra={"request_id": request_id, "error": str(e)},
                        exc_info=True
                    )
            
            with self.lock:
                self.stats["total_completed"] += 1
                self.stats["current_active"] = len(self.active_requests)
            
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "endpoint": queued_request.endpoint,
                    "duration_seconds": round(duration, 3),
                }
            )
            
        except TimeoutError:
            duration = time.time() - start_time
            error = TimeoutError(f"Request timeout after {queued_request.timeout}s")
            self.request_errors[request_id] = error
            
            with self.lock:
                self.stats["total_timeout"] += 1
                self.stats["total_failed"] += 1
            
            logger.warning(
                "Request timeout",
                extra={
                    "request_id": request_id,
                    "endpoint": queued_request.endpoint,
                    "timeout": queued_request.timeout,
                    "duration_seconds": round(duration, 3),
                }
            )
            
            # Call error callback
            if queued_request.error_callback:
                try:
                    queued_request.error_callback(error)
                except Exception as e:
                    logger.error(
                        "Error callback error",
                        extra={"request_id": request_id, "error": str(e)},
                        exc_info=True
                    )
        
        except Exception as e:
            duration = time.time() - start_time
            self.request_errors[request_id] = e
            
            with self.lock:
                self.stats["total_failed"] += 1
            
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "endpoint": queued_request.endpoint,
                    "error": str(e),
                    "duration_seconds": round(duration, 3),
                },
                exc_info=True
            )
            
            # Call error callback
            if queued_request.error_callback:
                try:
                    queued_request.error_callback(e)
                except Exception as callback_error:
                    logger.error(
                        "Error callback error",
                        extra={"request_id": request_id, "error": str(callback_error)},
                        exc_info=True
                    )
        
        finally:
            # Remove from active requests
            with self.lock:
                self.active_requests.pop(request_id, None)
                self.stats["current_active"] = len(self.active_requests)
                self.stats["current_queued"] = self.queue.qsize()
            
            # Mark task as done
            self.queue.task_done()
    
    def _execute_with_timeout(self, func: Callable, timeout: int, *args, **kwargs):
        """Execute function with timeout."""
        result_container = [None]
        exception_container = [None]
        
        def target():
            try:
                result_container[0] = func(*args, **kwargs)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Function execution exceeded {timeout}s timeout")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    def get_result(self, request_id: str, wait: bool = False, timeout: int = 30) -> Optional[Any]:
        """
        Get result for a request.
        
        Args:
            request_id: Request ID
            wait: If True, wait for completion
            timeout: Wait timeout in seconds
        
        Returns:
            Result if available, None otherwise
        """
        if wait:
            start_time = time.time()
            while request_id not in self.request_results and request_id not in self.request_errors:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Waiting for result exceeded {timeout}s")
                time.sleep(0.1)
        
        if request_id in self.request_results:
            return self.request_results[request_id]["result"]
        
        if request_id in self.request_errors:
            raise self.request_errors[request_id]
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self.lock:
            return {
                **self.stats,
                "queue_size": self.queue.qsize(),
                "active_count": len(self.active_requests),
            }


# Global request queue
_request_queue: Optional[RequestQueue] = None

def get_request_queue() -> RequestQueue:
    """Get or create global request queue."""
    global _request_queue
    if _request_queue is None:
        _request_queue = RequestQueue()
        _request_queue.start()
    return _request_queue


def queue_request(
    endpoint: str,
    func: Callable,
    *args,
    priority: int = PRIORITY_NORMAL,
    **kwargs
) -> str:
    """
    Convenience function to queue a request.
    
    Returns:
        Request ID
    """
    return get_request_queue().enqueue(endpoint, func, *args, priority=priority, **kwargs)


# =============================================================================
# DECORATOR
# =============================================================================

def queued(priority: int = PRIORITY_NORMAL, endpoint: str = None):
    """
    Decorator to automatically queue function calls.
    
    Usage:
        @queued(priority=PRIORITY_HIGH, endpoint="scanner/target")
        def scan_target(query):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            endpoint_name = endpoint or func.__name__
            request_id = queue_request(
                endpoint=endpoint_name,
                func=func,
                *args,
                priority=priority,
                **kwargs
            )
            return get_request_queue().get_result(request_id, wait=True)
        return wrapper
    return decorator
