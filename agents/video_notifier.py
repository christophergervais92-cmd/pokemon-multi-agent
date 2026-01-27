#!/usr/bin/env python3
"""
Video Notification System

Integrates video pipeline with existing notification system.
"""
import json
from typing import Dict, Optional
from datetime import datetime

from agents.utils.logger import get_logger

logger = get_logger("video_notifier")

# Try to import notification system
try:
    from agents.notifications.multi_channel import send_notification
    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False
    logger.warning("Multi-channel notifications not available")


class VideoNotifier:
    """
    Notification system for video generation pipeline.
    
    Integrates with existing multi-channel notification system
    to send alerts for video events.
    """
    
    def __init__(self):
        """Initialize video notifier."""
        self.has_notifications = HAS_NOTIFICATIONS
        logger.info("Video notifier initialized")
    
    def notify_generation_started(self, topic: str, script_id: int):
        """Notify when video generation starts."""
        message = f"🎬 Video Generation Started\n\nTopic: {topic}\nScript ID: {script_id}"
        
        self._send_notification(
            title="Video Generation Started",
            message=message,
            priority="normal"
        )
    
    def notify_generation_complete(
        self,
        topic: str,
        script_id: int,
        video_path: str,
        duration: float
    ):
        """Notify when video generation completes."""
        message = f"""🎉 Video Generation Complete!

Topic: {topic}
Script ID: {script_id}
Duration: {duration:.1f}s
File: {video_path}

Video is ready for review and posting."""
        
        self._send_notification(
            title="Video Ready",
            message=message,
            priority="high"
        )
    
    def notify_generation_failed(
        self,
        topic: str,
        script_id: int,
        error: str
    ):
        """Notify when video generation fails."""
        message = f"""❌ Video Generation Failed

Topic: {topic}
Script ID: {script_id}

Error: {error}

Please check logs for details."""
        
        self._send_notification(
            title="Video Generation Failed",
            message=message,
            priority="high"
        )
    
    def notify_video_posted(
        self,
        topic: str,
        script_id: int,
        tiktok_url: Optional[str] = None
    ):
        """Notify when video is posted to TikTok."""
        url_text = f"\n\nView: {tiktok_url}" if tiktok_url and not tiktok_url.startswith('https://www.tiktok.com/@user/video/demo') else ""
        
        message = f"""🚀 Video Posted to TikTok!

Topic: {topic}
Script ID: {script_id}{url_text}

Your tribal culture video is now live!"""
        
        self._send_notification(
            title="TikTok Post Published",
            message=message,
            priority="high"
        )
    
    def notify_posting_failed(
        self,
        topic: str,
        script_id: int,
        error: str
    ):
        """Notify when TikTok posting fails."""
        message = f"""⚠️ TikTok Posting Failed

Topic: {topic}
Script ID: {script_id}

Error: {error}

Video file is still available for manual posting."""
        
        self._send_notification(
            title="TikTok Post Failed",
            message=message,
            priority="high"
        )
    
    def notify_daily_summary(
        self,
        generated: int,
        posted: int,
        failed: int,
        stats: Dict
    ):
        """Send daily summary of video activity."""
        message = f"""📊 Daily Video Report

Generated: {generated} videos
Posted: {posted} videos
Failed: {failed} videos

Total Views: {stats.get('total_views', 0):,}
Total Likes: {stats.get('total_likes', 0):,}

Keep up the great work!"""
        
        self._send_notification(
            title="Daily Video Summary",
            message=message,
            priority="normal"
        )
    
    def _send_notification(
        self,
        title: str,
        message: str,
        priority: str = "normal"
    ):
        """Send notification through multi-channel system."""
        if not self.has_notifications:
            # Just log if notifications aren't available
            logger.info(f"[Notification] {title}: {message}")
            return
        
        try:
            # Send notification
            send_notification(
                title=title,
                message=message,
                channels=['discord'],
                priority=priority
            )
            
            logger.info(f"Notification sent: {title}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def notify_batch_progress(
        self,
        current: int,
        total: int,
        current_topic: str
    ):
        """Notify progress during batch generation."""
        message = f"""⏳ Batch Progress: {current}/{total}

Currently generating: {current_topic}

This may take a few minutes..."""
        
        self._send_notification(
            title=f"Generating Video {current}/{total}",
            message=message,
            priority="normal"
        )


# =============================================================================
# INTEGRATION WITH VIDEO ORCHESTRATOR
# =============================================================================

def create_notifying_orchestrator():
    """
    Create a VideoOrchestrator with notification integration.
    
    This wraps the orchestrator methods to send notifications.
    """
    from agents.video_orchestrator import VideoOrchestrator
    
    class NotifyingOrchestrator(VideoOrchestrator):
        """VideoOrchestrator with notifications."""
        
        def __init__(self):
            super().__init__()
            self.notifier = VideoNotifier()
        
        def generate_video(self, *args, **kwargs):
            """Generate video with notifications."""
            # Get topic first
            category = kwargs.get('category')
            location = kwargs.get('location')
            
            try:
                # Generate topic to get title
                topic_data = self.topic_gen.generate_topic(
                    category=category,
                    location=location,
                    duration=kwargs.get('duration', 30)
                )
                
                script_id = self.script_db.add_script(topic_data)
                
                # Notify start
                self.notifier.notify_generation_started(
                    topic=topic_data['topic'],
                    script_id=script_id
                )
                
                # Generate
                result = super().generate_video(*args, **kwargs)
                
                # Notify result
                if result.get('success'):
                    self.notifier.notify_generation_complete(
                        topic=result['topic'],
                        script_id=result['script_id'],
                        video_path=result['video_path'],
                        duration=result['duration']
                    )
                    
                    # Check if posted
                    if result.get('tiktok_result', {}).get('success'):
                        self.notifier.notify_video_posted(
                            topic=result['topic'],
                            script_id=result['script_id'],
                            tiktok_url=result['tiktok_result'].get('video_url')
                        )
                else:
                    self.notifier.notify_generation_failed(
                        topic=topic_data['topic'],
                        script_id=script_id,
                        error=result.get('error', 'Unknown error')
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Video generation with notifications failed: {e}")
                if 'script_id' in locals():
                    self.notifier.notify_generation_failed(
                        topic=topic_data.get('topic', 'Unknown'),
                        script_id=script_id,
                        error=str(e)
                    )
                raise
        
        def generate_batch(self, count=3, **kwargs):
            """Generate batch with progress notifications."""
            results = []
            
            for i in range(count):
                # Notify progress
                topic_preview = f"Video {i+1}"
                self.notifier.notify_batch_progress(
                    current=i+1,
                    total=count,
                    current_topic=topic_preview
                )
                
                result = self.generate_video(**kwargs)
                results.append(result)
            
            return results
    
    return NotifyingOrchestrator()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Create notifying orchestrator
    orchestrator = create_notifying_orchestrator()
    
    # Generate video with notifications
    result = orchestrator.generate_video(
        category='hunting',
        location='Mongolia',
        duration=30
    )
    
    print(json.dumps(result, indent=2))
