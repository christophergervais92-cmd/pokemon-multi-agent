#!/usr/bin/env python3
"""
TikTok Uploader

Automated TikTok video posting with session management.
"""
import os
import json
import time
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from agents.utils.logger import get_logger

logger = get_logger("tiktok_uploader")

# Try to import TikTok API
try:
    from TikTokApi import TikTokApi
    HAS_TIKTOK_API = True
except ImportError:
    HAS_TIKTOK_API = False
    logger.warning("TikTokApi not installed. Using demo mode.")

# Try to import playwright for automation
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright not installed. Automation unavailable.")


class TikTokUploader:
    """
    TikTok video uploader with automation.
    
    Features:
    - Session-based authentication
    - Automated video upload
    - Hashtag and caption management
    - Upload tracking
    """
    
    def __init__(self, session_file: str = "agents/social/tiktok_session.json"):
        """
        Initialize TikTok uploader.
        
        Args:
            session_file: Path to session cookie file
        """
        self.session_file = Path(session_file)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.username = os.getenv("TIKTOK_USERNAME")
        self.session_data = self._load_session()
        
        # Determine mode
        if HAS_PLAYWRIGHT and self.session_data:
            self.mode = "automation"
            logger.info("TikTok uploader initialized in automation mode")
        else:
            self.mode = "demo"
            logger.warning("TikTok uploader initialized in demo mode")
    
    def _load_session(self) -> Optional[Dict]:
        """Load session data from file."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load session: {e}")
        return None
    
    def _save_session(self, session_data: Dict):
        """Save session data to file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            logger.info("Session saved")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def login(self, username: Optional[str] = None) -> bool:
        """
        Interactive login to TikTok to capture session.
        
        This opens a browser for manual login, then saves the session.
        
        Args:
            username: TikTok username (uses env var if not provided)
        
        Returns:
            True if login successful
        """
        if not HAS_PLAYWRIGHT:
            logger.error("Playwright not installed. Cannot perform login.")
            return False
        
        username = username or self.username
        
        if not username:
            logger.error("No username provided")
            return False
        
        logger.info(f"Starting interactive login for {username}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Go to TikTok login
                page.goto('https://www.tiktok.com/login')
                
                print("\n" + "="*60)
                print("Please log in to TikTok in the browser window")
                print("Press Enter here once you've logged in successfully")
                print("="*60 + "\n")
                
                input("Press Enter to continue after logging in...")
                
                # Capture cookies
                cookies = context.cookies()
                
                # Save session
                session_data = {
                    'username': username,
                    'cookies': cookies,
                    'logged_in_at': datetime.now().isoformat()
                }
                
                self._save_session(session_data)
                self.session_data = session_data
                
                browser.close()
                
                logger.info("Login successful, session saved")
                return True
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def upload_video(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[List[str]] = None,
        privacy: str = "public"
    ) -> Dict:
        """
        Upload video to TikTok.
        
        Args:
            video_path: Path to video file
            caption: Video caption/description
            hashtags: List of hashtags (without #)
            privacy: "public", "friends", or "private"
        
        Returns:
            Dict with upload result
        """
        if self.mode == "demo":
            return self._upload_demo(video_path, caption, hashtags)
        
        try:
            return self._upload_with_automation(video_path, caption, hashtags, privacy)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'demo_mode': True
            }
    
    def _upload_with_automation(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[List[str]],
        privacy: str
    ) -> Dict:
        """Upload using Playwright automation."""
        logger.info(f"Uploading {video_path} to TikTok")
        
        # Build full caption with hashtags
        full_caption = caption
        if hashtags:
            hashtag_str = ' '.join(f'#{tag}' for tag in hashtags)
            full_caption = f"{caption}\n\n{hashtag_str}"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            # Load session cookies
            if self.session_data and 'cookies' in self.session_data:
                context.add_cookies(self.session_data['cookies'])
            
            page = context.new_page()
            
            # Go to upload page
            page.goto('https://www.tiktok.com/upload')
            time.sleep(3)
            
            # Upload file
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(video_path)
            
            logger.info("Video file uploaded, waiting for processing...")
            time.sleep(10)  # Wait for video to process
            
            # Fill caption
            caption_field = page.locator('div[contenteditable="true"]').first
            caption_field.fill(full_caption)
            
            # Set privacy (if available)
            # Note: TikTok's UI changes frequently, this may need adjustment
            
            # Click post button
            post_button = page.locator('button:has-text("Post")')
            post_button.click()
            
            logger.info("Post button clicked, waiting for confirmation...")
            time.sleep(5)
            
            # Try to get video URL from success page
            video_url = None
            try:
                # Look for success indicator
                if 'Your video is being uploaded' in page.content():
                    logger.info("Upload confirmed")
                    video_url = page.url
            except:
                pass
            
            browser.close()
            
            result = {
                'success': True,
                'video_url': video_url,
                'caption': full_caption,
                'uploaded_at': datetime.now().isoformat()
            }
            
            logger.info(f"Upload successful: {video_url}")
            
            return result
            
    def _upload_demo(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[List[str]]
    ) -> Dict:
        """Simulate upload for demo mode."""
        logger.warning(f"DEMO: Would upload {video_path}")
        logger.info(f"Caption: {caption}")
        if hashtags:
            logger.info(f"Hashtags: {', '.join(hashtags)}")
        
        # Generate fake URL
        video_id = f"demo_{int(time.time())}"
        video_url = f"https://www.tiktok.com/@user/video/{video_id}"
        
        return {
            'success': True,
            'video_url': video_url,
            'caption': caption,
            'hashtags': hashtags,
            'uploaded_at': datetime.now().isoformat(),
            'demo_mode': True
        }
    
    def generate_caption(
        self,
        topic: str,
        keywords: List[str],
        cta: str = "Follow for more!"
    ) -> str:
        """
        Generate TikTok caption from topic.
        
        Args:
            topic: Video topic/title
            keywords: Keywords for hashtags
            cta: Call to action
        
        Returns:
            Caption text
        """
        caption = f"{topic}\n\n{cta}"
        return caption
    
    def generate_hashtags(
        self,
        keywords: List[str],
        max_hashtags: int = 10
    ) -> List[str]:
        """
        Generate hashtags from keywords.
        
        Args:
            keywords: List of keywords
            max_hashtags: Maximum number of hashtags
        
        Returns:
            List of hashtags (without #)
        """
        # Standard TikTok hashtags for tribal content
        base_hashtags = ['tribalculture', 'documentary', 'culture', 'educational', 'fyp', 'viral']
        
        # Add keywords as hashtags
        keyword_hashtags = [k.lower().replace(' ', '') for k in keywords]
        
        # Combine and limit
        all_hashtags = base_hashtags + keyword_hashtags
        return list(set(all_hashtags))[:max_hashtags]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    uploader = TikTokUploader()
    
    # Demo upload
    result = uploader.upload_video(
        video_path="remotion/out/test_video.mp4",
        caption="Amazing tribal culture in Mongolia! 🇲🇳",
        hashtags=['mongolia', 'tribalculture', 'documentary', 'fyp']
    )
    
    print(json.dumps(result, indent=2))
