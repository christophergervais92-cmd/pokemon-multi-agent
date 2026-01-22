#!/usr/bin/env python3
"""
Background Job Queue System

Manages background jobs with:
- Priority queuing
- Retry logic
- Job status tracking
- Scheduled jobs
"""
import time
import threading
import uuid
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import PriorityQueue, Empty
from enum import Enum

from agents.utils.logger import get_logger
from agents.utils.retry import retry

logger = get_logger("job_queue")

# =============================================================================
# JOB STATUS
# =============================================================================

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# =============================================================================
# JOB DEFINITION
# =============================================================================

@dataclass
class Job:
    """Represents a background job."""
    job_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 5  # Lower = higher priority
    max_retries: int = 3
    retry_delay: float = 1.0
    scheduled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    
    def __lt__(self, other):
        """For priority queue."""
        # Scheduled jobs come first
        if self.scheduled_at and other.scheduled_at:
            return self.scheduled_at < other.scheduled_at
        if self.scheduled_at:
            return self.scheduled_at <= datetime.now()
        if other.scheduled_at:
            return False
        # Then by priority
        return self.priority < other.priority

# =============================================================================
# JOB QUEUE
# =============================================================================

class JobQueue:
    """
    Background job queue system.
    
    Features:
    - Priority queuing
    - Scheduled jobs
    - Automatic retries
    - Job status tracking
    - Concurrent job execution
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize job queue.
        
        Args:
            max_workers: Maximum concurrent jobs
        """
        self.max_workers = max_workers
        self.queue: PriorityQueue = PriorityQueue()
        self.jobs: Dict[str, Job] = {}
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }
    
    def start(self):
        """Start job queue workers."""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True, name=f"JobWorker-{i}")
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Job queue started with {self.max_workers} workers")
    
    def stop(self):
        """Stop job queue workers."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers.clear()
        logger.info("Job queue stopped")
    
    def enqueue(
        self,
        name: str,
        func: Callable,
        *args,
        priority: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        schedule_at: Optional[datetime] = None,
        **kwargs
    ) -> str:
        """
        Enqueue a job.
        
        Args:
            name: Job name
            func: Function to execute
            *args: Function arguments
            priority: Job priority (lower = higher)
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            schedule_at: Schedule job for later execution
            **kwargs: Function keyword arguments
        
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            scheduled_at=schedule_at,
        )
        
        self.queue.put(job)
        self.jobs[job_id] = job
        
        with self.lock:
            self.stats["total_jobs"] += 1
        
        logger.info(f"Job enqueued: {name}", extra={"job_id": job_id, "priority": priority})
        
        return job_id
    
    def _worker(self):
        """Worker thread that processes jobs."""
        while self.running:
            try:
                # Get next job
                try:
                    job = self.queue.get(timeout=1)
                except Empty:
                    continue
                
                # Check if scheduled for later
                if job.scheduled_at and job.scheduled_at > datetime.now():
                    # Put back in queue
                    self.queue.put(job)
                    time.sleep(0.1)
                    continue
                
                # Execute job
                self._execute_job(job)
                
            except Exception as e:
                logger.error("Error in job worker", extra={"error": str(e)}, exc_info=True)
    
    def _execute_job(self, job: Job):
        """Execute a job with retry logic."""
        job.status = JobStatus.RUNNING
        job.attempts += 1
        
        try:
            logger.debug(f"Executing job: {job.name}", extra={"job_id": job.job_id, "attempt": job.attempts})
            
            # Execute function
            result = job.func(*job.args, **job.kwargs)
            
            job.status = JobStatus.COMPLETED
            job.result = result
            
            with self.lock:
                self.stats["completed"] += 1
            
            logger.info(f"Job completed: {job.name}", extra={"job_id": job.job_id})
            
        except Exception as e:
            job.error = str(e)
            
            # Retry if attempts remaining
            if job.attempts < job.max_retries:
                job.status = JobStatus.PENDING
                job.attempts += 1
                
                # Re-queue with delay
                time.sleep(job.retry_delay * job.attempts)  # Exponential backoff
                self.queue.put(job)
                
                logger.warning(
                    f"Job failed, retrying: {job.name}",
                    extra={"job_id": job.job_id, "attempt": job.attempts, "error": str(e)}
                )
            else:
                job.status = JobStatus.FAILED
                
                with self.lock:
                    self.stats["failed"] += 1
                
                logger.error(
                    f"Job failed after {job.max_retries} attempts: {job.name}",
                    extra={"job_id": job.job_id, "error": str(e)},
                    exc_info=True
                )
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            with self.lock:
                self.stats["cancelled"] += 1
            logger.info(f"Job cancelled: {job.name}", extra={"job_id": job_id})
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job queue statistics."""
        with self.lock:
            return {
                **self.stats,
                "queue_size": self.queue.qsize(),
                "active_jobs": len([j for j in self.jobs.values() if j.status == JobStatus.RUNNING]),
                "pending_jobs": len([j for j in self.jobs.values() if j.status == JobStatus.PENDING]),
            }


# Global job queue
_job_queue: Optional[JobQueue] = None

def get_job_queue() -> JobQueue:
    """Get or create global job queue."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
        _job_queue.start()
    return _job_queue
