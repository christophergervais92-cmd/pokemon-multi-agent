#!/usr/bin/env python3
"""
Video Pipeline Integration Script

Integrates video generation into the main agents server.
Run this to start the complete system with video capabilities.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.agents_server import app
from agents.video_scheduler import VideoScheduler
import threading

def start_video_scheduler():
    """Start video scheduler in background thread."""
    scheduler = VideoScheduler()
    scheduler.start()
    print("✅ Video scheduler started")

def main():
    print("=" * 70)
    print("🎴 LO TCG Multi-Agent Server + AI TikTok Video Pipeline")
    print("=" * 70)
    print()
    
    # Start video scheduler
    print("🎬 Starting video generation scheduler...")
    scheduler_thread = threading.Thread(target=start_video_scheduler, daemon=True)
    scheduler_thread.start()
    print()
    
    # Start Flask server (from agents_server.py)
    print("🚀 Starting API server...")
    print()
    print("Available Video Endpoints:")
    print("  POST /video/generate          - Generate TikTok video")
    print("  POST /video/generate/batch    - Generate multiple videos")
    print("  GET  /video/status/<id>       - Check video status")
    print("  GET  /video/queue             - View pending videos")
    print("  GET  /video/schedule          - Get posting schedule")
    print("  POST /tiktok/post             - Upload to TikTok")
    print("  GET  /tiktok/stats            - Posting statistics")
    print()
    print("=" * 70)
    print()
    
    # Run Flask app (this blocks)
    app.run(host="127.0.0.1", port=5001, debug=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
