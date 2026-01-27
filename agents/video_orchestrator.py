#!/usr/bin/env python3
"""
Video Generation Orchestrator

Coordinates the full video generation pipeline:
Topic → Audio → Assets → Rendering → Posting
"""
import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from agents.content.topic_generator import TopicGenerator
from agents.content.script_database import ScriptDatabase
from agents.audio.elevenlabs_service import ElevenLabsService
from agents.assets.asset_manager import AssetManager
from agents.assets.smart_matcher import SmartMatcher
from agents.social.tiktok_uploader import TikTokUploader
from agents.utils.logger import get_logger

logger = get_logger("video_orchestrator")


class VideoOrchestrator:
    """
    Orchestrates end-to-end video generation pipeline.
    
    Pipeline:
    1. Generate topic & script
    2. Generate voiceover audio
    3. Match video assets
    4. Render video with Remotion
    5. Upload to TikTok
    """
    
    def __init__(self):
        """Initialize all services."""
        self.topic_gen = TopicGenerator()
        self.script_db = ScriptDatabase()
        self.audio_service = ElevenLabsService()
        self.asset_manager = AssetManager()
        self.matcher = SmartMatcher(self.asset_manager)
        self.uploader = TikTokUploader()
        
        self.remotion_dir = Path("remotion")
        self.output_dir = Path("remotion/out")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Video orchestrator initialized")
    
    def generate_video(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        duration: int = 30,
        auto_post: bool = False
    ) -> Dict:
        """
        Generate complete video from scratch.
        
        Args:
            category: Topic category
            location: Geographic location
            duration: Video duration in seconds
            auto_post: Automatically post to TikTok
        
        Returns:
            Result dictionary with video info
        """
        logger.info(f"Starting video generation: {location}/{category}")
        
        try:
            # Step 1: Generate topic and script
            logger.info("Step 1: Generating topic and script...")
            topic_data = self.topic_gen.generate_topic(
                category=category,
                location=location,
                duration=duration
            )
            
            # Save to database
            script_id = self.script_db.add_script(topic_data)
            
            # Step 2: Generate voiceover
            logger.info("Step 2: Generating voiceover...")
            self.script_db.update_status(script_id, 'generating_audio')
            
            audio_result = self.audio_service.generate_voiceover(
                script=topic_data['script'],
                voice_style='documentary'
            )
            
            # Step 3: Match video assets
            logger.info("Step 3: Matching video assets...")
            matched_clips = self.matcher.match_for_topic(topic_data)
            
            if not matched_clips:
                raise ValueError("No video assets found")
            
            # Step 4: Render video with Remotion
            logger.info("Step 4: Rendering video with Remotion...")
            self.script_db.update_status(script_id, 'rendering')
            
            video_path = self._render_video(
                script_id=script_id,
                topic_data=topic_data,
                audio_result=audio_result,
                clips=matched_clips
            )
            
            self.script_db.update_status(
                script_id,
                'rendered',
                video_path=str(video_path),
                rendered_at=datetime.now().isoformat()
            )
            
            # Step 5: Upload to TikTok (if auto_post)
            tiktok_result = None
            if auto_post:
                logger.info("Step 5: Uploading to TikTok...")
                tiktok_result = self._upload_to_tiktok(
                    video_path=video_path,
                    topic_data=topic_data
                )
                
                if tiktok_result['success']:
                    self.script_db.update_status(
                        script_id,
                        'posted',
                        tiktok_url=tiktok_result.get('video_url'),
                        posted_at=datetime.now().isoformat()
                    )
            
            result = {
                'success': True,
                'script_id': script_id,
                'topic': topic_data['topic'],
                'video_path': str(video_path),
                'duration': audio_result['duration'],
                'clips_used': len(matched_clips),
                'tiktok_result': tiktok_result
            }
            
            logger.info(f"Video generation complete: {video_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            if 'script_id' in locals():
                self.script_db.update_status(script_id, 'failed')
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _render_video(
        self,
        script_id: int,
        topic_data: Dict,
        audio_result: Dict,
        clips: List[Dict]
    ) -> Path:
        """
        Render video using Remotion.
        
        Args:
            script_id: Script database ID
            topic_data: Topic information
            audio_result: Audio generation result
            clips: Matched video clips
        
        Returns:
            Path to rendered video
        """
        # Prepare props for Remotion
        fps = 30
        total_duration_seconds = audio_result['duration']
        total_frames = int(total_duration_seconds * fps)
        
        # Convert clips to Remotion format
        video_clips = []
        current_frame = 0
        
        for clip in clips:
            clip_duration_frames = int(clip['duration'] * fps)
            
            video_clips.append({
                'filepath': clip['filepath'].replace('remotion/public/', ''),
                'duration': clip_duration_frames,
                'startFrame': current_frame
            })
            
            current_frame += clip_duration_frames
            
            # Stop if we have enough footage
            if current_frame >= total_frames:
                break
        
        # Build props JSON
        props = {
            'audioPath': audio_result['audio_path'].replace('remotion/public/', ''),
            'videoClips': video_clips,
            'timestamps': audio_result['timestamps'],
            'title': topic_data['topic']
        }
        
        # Save props to temp file
        props_file = self.remotion_dir / f'props_{script_id}.json'
        with open(props_file, 'w') as f:
            json.dump(props, f, indent=2)
        
        # Output filename
        output_filename = f"tiktok_{script_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = self.output_dir / output_filename
        
        # Render with Remotion CLI
        logger.info("Calling Remotion renderer...")
        
        try:
            result = subprocess.run([
                'npm', 'run', 'render',
                '--',
                'TikTokVideo',
                str(output_path),
                '--props', str(props_file),
                '--height', '1920',
                '--width', '1080'
            ], cwd=self.remotion_dir, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Remotion render failed: {result.stderr}")
                raise RuntimeError(f"Remotion render failed: {result.stderr}")
            
            logger.info(f"Video rendered: {output_path}")
            
            # Clean up props file
            props_file.unlink()
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("Remotion render timeout")
            raise RuntimeError("Video rendering timed out")
    
    def _upload_to_tiktok(self, video_path: Path, topic_data: Dict) -> Dict:
        """Upload video to TikTok."""
        # Generate caption and hashtags
        caption = self.uploader.generate_caption(
            topic=topic_data['topic'],
            keywords=topic_data['keywords']
        )
        
        hashtags = self.uploader.generate_hashtags(
            keywords=topic_data['keywords']
        )
        
        # Upload
        result = self.uploader.upload_video(
            video_path=str(video_path),
            caption=caption,
            hashtags=hashtags
        )
        
        return result
    
    def generate_batch(
        self,
        count: int = 3,
        auto_post: bool = False
    ) -> List[Dict]:
        """
        Generate multiple videos in batch.
        
        Args:
            count: Number of videos to generate
            auto_post: Auto-post to TikTok
        
        Returns:
            List of results
        """
        results = []
        
        for i in range(count):
            logger.info(f"Generating video {i+1}/{count}")
            
            result = self.generate_video(auto_post=auto_post)
            results.append(result)
        
        logger.info(f"Batch complete: {len(results)} videos")
        
        return results


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    orchestrator = VideoOrchestrator()
    
    # Generate single video
    result = orchestrator.generate_video(
        category='hunting',
        location='Mongolia',
        duration=30,
        auto_post=False
    )
    
    print(json.dumps(result, indent=2))
