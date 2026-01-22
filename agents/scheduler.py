#!/usr/bin/env python3
"""
Automated Scheduler for Daily Jobs

Runs scheduled tasks:
- Daily SKU list build
- Periodic stock checks
- Alert monitoring
"""
import time
import threading
from datetime import datetime, time as dt_time
from typing import Callable, Optional, Dict, List

from agents.utils.logger import get_logger

logger = get_logger("scheduler")


class Scheduler:
    """Simple scheduler for daily/weekly jobs."""
    
    def __init__(self):
        self.jobs: List[Dict] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def add_daily_job(self, func: Callable, hour: int = 2, minute: int = 0, name: str = None):
        """
        Add a daily job.
        
        Args:
            func: Function to call
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            name: Job name
        """
        self.jobs.append({
            "func": func,
            "type": "daily",
            "hour": hour,
            "minute": minute,
            "name": name or func.__name__,
            "last_run": None,
        })
        logger.info(f"Added daily job: {name or func.__name__} at {hour:02d}:{minute:02d}")
    
    def add_interval_job(self, func: Callable, interval_seconds: int, name: str = None):
        """
        Add an interval job.
        
        Args:
            func: Function to call
            interval_seconds: Seconds between runs
            name: Job name
        """
        self.jobs.append({
            "func": func,
            "type": "interval",
            "interval": interval_seconds,
            "name": name or func.__name__,
            "last_run": None,
        })
        logger.info(f"Added interval job: {name or func.__name__} every {interval_seconds}s")
    
    def _should_run_daily(self, job: Dict) -> bool:
        """Check if daily job should run."""
        now = datetime.now()
        
        if job["last_run"]:
            last_run = datetime.fromisoformat(job["last_run"])
            # Check if it's the right time and hasn't run today
            if (now.hour == job["hour"] and 
                now.minute == job["minute"] and
                (now - last_run).total_seconds() > 3600):  # At least 1 hour since last run
                return True
        else:
            # First run - check if it's past the scheduled time
            if now.hour >= job["hour"] and now.minute >= job["minute"]:
                return True
        
        return False
    
    def _should_run_interval(self, job: Dict) -> bool:
        """Check if interval job should run."""
        if not job["last_run"]:
            return True
        
        last_run = datetime.fromisoformat(job["last_run"])
        elapsed = (datetime.now() - last_run).total_seconds()
        return elapsed >= job["interval"]
    
    def _run_job(self, job: Dict):
        """Run a job."""
        try:
            logger.info(f"Running job: {job['name']}")
            job["func"]()
            job["last_run"] = datetime.now().isoformat()
            logger.info(f"Job completed: {job['name']}")
        except Exception as e:
            logger.error(f"Job failed {job['name']}: {e}")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                for job in self.jobs:
                    if job["type"] == "daily" and self._should_run_daily(job):
                        self._run_job(job)
                    elif job["type"] == "interval" and self._should_run_interval(job):
                        self._run_job(job)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")


# =============================================================================
# GLOBAL SCHEDULER
# =============================================================================

_scheduler = Scheduler()

def get_scheduler() -> Scheduler:
    """Get the global scheduler."""
    return _scheduler

def start_scheduler():
    """Start the global scheduler."""
    _scheduler.start()

def stop_scheduler():
    """Stop the global scheduler."""
    _scheduler.stop()
