#!/usr/bin/env python3
"""
Video Generation Scheduler

Integrates video pipeline with existing scheduler for automation.
"""
from datetime import datetime, time as dt_time

from agents.scheduler import get_scheduler
from agents.video_orchestrator import VideoOrchestrator
from agents.social.post_scheduler import PostScheduler
from agents.content.script_database import ScriptDatabase
from agents.utils.logger import get_logger

logger = get_logger("video_scheduler")


class VideoScheduler:
    """
    Scheduler for automated video generation and posting.
    
    Features:
    - Daily video generation
    - Optimal posting times
    - Batch generation
    """
    
    def __init__(self):
        """Initialize video scheduler."""
        self.orchestrator = VideoOrchestrator()
        self.post_scheduler = PostScheduler()
        self.script_db = ScriptDatabase()
        self.scheduler = get_scheduler()
        
        logger.info("Video scheduler initialized")
    
    def setup_scheduled_jobs(self):
        """Set up scheduled video generation jobs."""
        
        # Daily: Generate 3 videos at 8 AM
        self.scheduler.add_daily_job(
            func=self._generate_daily_videos,
            hour=8,
            minute=0,
            name="daily_video_generation"
        )
        
        # Check for pending renders every 15 minutes
        self.scheduler.add_interval_job(
            func=self._check_render_queue,
            interval_seconds=900,  # 15 minutes
            name="check_render_queue"
        )
        
        # Post rendered videos at optimal times
        self.scheduler.add_interval_job(
            func=self._auto_post_videos,
            interval_seconds=1800,  # 30 minutes
            name="auto_post_videos"
        )
        
        logger.info("Video scheduler jobs configured")
    
    def _generate_daily_videos(self):
        """Generate daily batch of videos."""
        logger.info("Starting daily video generation")
        
        try:
            # Generate 3 videos with different topics
            results = self.orchestrator.generate_batch(
                count=3,
                auto_post=False  # Don't auto-post, schedule them
            )
            
            success_count = sum(1 for r in results if r.get('success'))
            
            logger.info(f"Daily generation complete: {success_count}/3 successful")
            
        except Exception as e:
            logger.error(f"Daily video generation failed: {e}")
    
    def _check_render_queue(self):
        """Check for videos that need rendering."""
        logger.debug("Checking render queue")
        
        try:
            pending = self.script_db.get_pending_scripts(limit=5)
            
            if not pending:
                logger.debug("No pending videos to render")
                return
            
            logger.info(f"Found {len(pending)} pending videos")
            
            # Note: In production, you might want to use a background worker
            # for this instead of blocking the scheduler
            
        except Exception as e:
            logger.error(f"Render queue check failed: {e}")
    
    def _auto_post_videos(self):
        """Auto-post rendered videos at optimal times."""
        logger.debug("Checking for videos to post")
        
        try:
            # Check if we can post now
            if not self.post_scheduler.can_post_now():
                logger.debug("Cannot post now (rate limit or timing)")
                return
            
            # Get next optimal time
            next_time = self.post_scheduler.get_next_optimal_time()
            now = datetime.now()
            
            # If it's not a good time, skip
            if next_time > now:
                logger.debug(f"Next optimal time: {next_time}")
                return
            
            # Get rendered videos ready to post
            rendered = self.script_db.get_rendered_scripts(limit=1)
            
            if not rendered:
                logger.debug("No rendered videos ready to post")
                return
            
            video = rendered[0]
            
            # Post to TikTok
            logger.info(f"Auto-posting video: {video['topic']}")
            
            result = self.orchestrator._upload_to_tiktok(
                video_path=video['video_path'],
                topic_data={
                    'topic': video['topic'],
                    'keywords': video['keywords']
                }
            )
            
            if result['success']:
                self.script_db.update_status(
                    video['id'],
                    'posted',
                    tiktok_url=result.get('video_url'),
                    posted_at=datetime.now().isoformat()
                )
                
                self.post_scheduler.record_post()
                
                logger.info(f"Video posted successfully: {result.get('video_url')}")
            else:
                logger.error(f"Video posting failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Auto-post failed: {e}")
    
    def start(self):
        """Start the scheduler with video jobs."""
        self.setup_scheduled_jobs()
        self.scheduler.start()
        logger.info("Video scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.stop()
        logger.info("Video scheduler stopped")


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    scheduler = VideoScheduler()
    scheduler.start()
    
    print("Video scheduler running. Press Ctrl+C to stop.")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped")
