#!/usr/bin/env python3
"""
Quick Start Script for Video Pipeline

Run this to test the complete video generation pipeline.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.video_orchestrator import VideoOrchestrator
from agents.assets.asset_manager import AssetManager

def main():
    print("🎬 AI TikTok Video Pipeline - Quick Start")
    print("=" * 60)
    
    # Step 1: Check assets
    print("\n📁 Step 1: Checking video assets...")
    asset_manager = AssetManager()
    stats = asset_manager.get_stats()
    
    if stats['total_assets'] == 0:
        print("⚠️  No video assets found!")
        print("\nPlease add your tribal footage to:")
        print("  remotion/public/assets/footage/mongolia/")
        print("  remotion/public/assets/footage/nepal/")
        print("  remotion/public/assets/footage/papua_new_guinea/")
        print("\nThen run:")
        print("  python -c \"from agents.assets.asset_manager import AssetManager; AssetManager().scan_directory()\"")
        return
    
    print(f"✅ Found {stats['total_assets']} video assets")
    print(f"   - Mongolia: {stats['by_location'].get('Mongolia', 0)}")
    print(f"   - Nepal: {stats['by_location'].get('Nepal', 0)}")
    print(f"   - Papua New Guinea: {stats['by_location'].get('Papua New Guinea', 0)}")
    
    # Step 2: Generate video
    print("\n🎯 Step 2: Generating video...")
    print("This will:")
    print("  1. Generate AI topic and script")
    print("  2. Create voiceover with ElevenLabs")
    print("  3. Match video clips to script")
    print("  4. Render video with Remotion")
    print()
    
    orchestrator = VideoOrchestrator()
    
    result = orchestrator.generate_video(
        category='hunting',
        location='Mongolia',
        duration=30,
        auto_post=False  # Don't auto-post on first run
    )
    
    # Step 3: Show results
    print("\n" + "=" * 60)
    if result['success']:
        print("✅ VIDEO GENERATION SUCCESSFUL!")
        print()
        print(f"📝 Topic: {result['topic']}")
        print(f"🎬 Video: {result['video_path']}")
        print(f"⏱️  Duration: {result['duration']:.1f}s")
        print(f"🎞️  Clips: {result['clips_used']}")
        print()
        print("Next steps:")
        print("1. Review the video in Remotion Studio:")
        print("   cd remotion && npm run dev")
        print()
        print("2. Post to TikTok manually:")
        print(f"   Upload {result['video_path']} to TikTok")
        print()
        print("3. Or auto-post via API:")
        print("   POST /video/generate with auto_post=true")
    else:
        print("❌ VIDEO GENERATION FAILED")
        print(f"Error: {result.get('error')}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
