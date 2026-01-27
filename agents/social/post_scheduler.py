#!/usr/bin/env python3
"""
Post Scheduler for Optimal TikTok Posting Times

Determines best times to post based on audience engagement.
"""
from typing import Dict, List, Optional
from datetime import datetime, time as dt_time, timedelta

from agents.utils.logger import get_logger

logger = get_logger("post_scheduler")


class PostScheduler:
    """
    Smart posting scheduler for TikTok.
    
    Features:
    - Optimal posting times
    - Rate limiting (avoid spam)
    - Timezone-aware scheduling
    """
    
    # Peak engagement times (hours in 24h format)
    PEAK_TIMES = [9, 12, 15, 18, 21]  # 9 AM, 12 PM, 3 PM, 6 PM, 9 PM
    
    # Maximum posts per day to avoid spam flags
    MAX_POSTS_PER_DAY = 5
    
    def __init__(self, timezone: str = "UTC"):
        """
        Initialize post scheduler.
        
        Args:
            timezone: Timezone for scheduling (e.g., 'America/New_York')
        """
        self.timezone = timezone
        self.post_history: List[datetime] = []
        logger.info(f"Post scheduler initialized (timezone: {timezone})")
    
    def get_next_optimal_time(
        self,
        after: Optional[datetime] = None,
        avoid_weekends: bool = False
    ) -> datetime:
        """
        Get next optimal posting time.
        
        Args:
            after: Get time after this datetime (default: now)
            avoid_weekends: Skip Saturdays and Sundays
        
        Returns:
            Next optimal posting datetime
        """
        if after is None:
            after = datetime.now()
        
        # Check if we can post today
        today_posts = [p for p in self.post_history if p.date() == after.date()]
        
        if len(today_posts) >= self.MAX_POSTS_PER_DAY:
            # Move to next day
            after = after.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        
        # Find next peak time
        current_hour = after.hour
        
        for peak_hour in self.PEAK_TIMES:
            if peak_hour > current_hour:
                next_time = after.replace(hour=peak_hour, minute=0, second=0)
                
                # Check if weekend
                if avoid_weekends and next_time.weekday() >= 5:
                    # Skip to Monday
                    days_ahead = 7 - next_time.weekday()
                    next_time = next_time + timedelta(days=days_ahead)
                    next_time = next_time.replace(hour=self.PEAK_TIMES[0])
                
                return next_time
        
        # No more peak times today, go to first peak time tomorrow
        next_time = after.replace(hour=self.PEAK_TIMES[0], minute=0, second=0) + timedelta(days=1)
        
        if avoid_weekends and next_time.weekday() >= 5:
            days_ahead = 7 - next_time.weekday()
            next_time = next_time + timedelta(days=days_ahead)
        
        return next_time
    
    def get_posting_schedule(
        self,
        num_posts: int,
        start_date: Optional[datetime] = None,
        avoid_weekends: bool = False
    ) -> List[datetime]:
        """
        Generate posting schedule for multiple videos.
        
        Args:
            num_posts: Number of posts to schedule
            start_date: Start scheduling from this date
            avoid_weekends: Skip weekend posts
        
        Returns:
            List of scheduled datetimes
        """
        schedule = []
        current_time = start_date or datetime.now()
        
        for _ in range(num_posts):
            next_time = self.get_next_optimal_time(current_time, avoid_weekends)
            schedule.append(next_time)
            current_time = next_time + timedelta(hours=1)  # Ensure next is after this
        
        logger.info(f"Generated schedule for {num_posts} posts")
        
        return schedule
    
    def record_post(self, posted_at: Optional[datetime] = None):
        """
        Record a post in history.
        
        Args:
            posted_at: When the post was made (default: now)
        """
        posted_at = posted_at or datetime.now()
        self.post_history.append(posted_at)
        logger.info(f"Recorded post at {posted_at}")
    
    def can_post_now(self) -> bool:
        """
        Check if we can post right now without exceeding limits.
        
        Returns:
            True if safe to post
        """
        today = datetime.now().date()
        today_posts = [p for p in self.post_history if p.date() == today]
        
        if len(today_posts) >= self.MAX_POSTS_PER_DAY:
            logger.warning(f"Already posted {len(today_posts)} times today (limit: {self.MAX_POSTS_PER_DAY})")
            return False
        
        # Check minimum time between posts (2 hours)
        if self.post_history:
            last_post = max(self.post_history)
            if (datetime.now() - last_post).total_seconds() < 7200:
                logger.warning("Less than 2 hours since last post")
                return False
        
        return True
    
    def get_stats(self) -> Dict:
        """Get posting statistics."""
        if not self.post_history:
            return {
                'total_posts': 0,
                'posts_today': 0,
                'last_post': None
            }
        
        today = datetime.now().date()
        today_posts = [p for p in self.post_history if p.date() == today]
        
        return {
            'total_posts': len(self.post_history),
            'posts_today': len(today_posts),
            'last_post': max(self.post_history).isoformat(),
            'can_post_now': self.can_post_now()
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    scheduler = PostScheduler()
    
    # Get next optimal time
    next_time = scheduler.get_next_optimal_time()
    print(f"Next optimal posting time: {next_time}")
    
    # Generate schedule for 5 posts
    schedule = scheduler.get_posting_schedule(5, avoid_weekends=True)
    print(f"\nPosting schedule:")
    for i, time in enumerate(schedule, 1):
        print(f"{i}. {time.strftime('%Y-%m-%d %H:%M')}")
