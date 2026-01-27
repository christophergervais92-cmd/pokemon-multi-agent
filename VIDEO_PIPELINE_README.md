# AI TikTok Video Pipeline

Automated AI-powered TikTok video creation system that generates tribal culture content with voiceovers, smart asset matching, and auto-posting.

## 🎬 Features

- **AI Topic Generation**: Generates viral TikTok topics about tribal cultures using OpenAI/Anthropic
- **ElevenLabs Voiceover**: High-quality text-to-speech with word-level timestamps for captions
- **Smart Asset Matching**: Automatically selects relevant video clips based on script keywords
- **Remotion Video Assembly**: Programmatic video creation with React components
- **Animated Captions**: TikTok-style word-by-word caption animations synced to audio
- **TikTok Auto-Posting**: Automated upload with optimal timing and hashtag generation
- **Scheduled Automation**: Daily video generation and posting at peak engagement times
- **Multi-Channel Notifications**: Discord/Email alerts for video events

## 🚀 Quick Start

### 1. Install Python Dependencies

```bash
pip install openai elevenlabs TikTokApi playwright pillow
```

### 2. Install Node.js Dependencies (Remotion)

```bash
cd remotion
npm install
```

### 3. Set Environment Variables

```bash
# AI Services
export OPENAI_API_KEY="sk-..."
export ELEVENLABS_API_KEY="..."

# TikTok (optional for auto-posting)
export TIKTOK_USERNAME="your_username"

# Optional
export ANTHROPIC_API_KEY="..."
```

### 4. Set Up Your Video Assets

Place your tribal footage in:
```
remotion/public/assets/footage/
  ├── mongolia/
  ├── nepal/
  └── papua_new_guinea/
```

Then index them:
```bash
python -c "from agents.assets.asset_manager import AssetManager; AssetManager().scan_directory()"
```

### 5. Generate Your First Video

```bash
python agents/video_orchestrator.py
```

Or via API:
```bash
curl -X POST http://127.0.0.1:5001/video/generate \
  -H "Content-Type: application/json" \
  -d '{"location": "Mongolia", "category": "hunting", "duration": 30}'
```

## 📁 Project Structure

```
agents/
  ├── content/
  │   ├── topic_generator.py      # AI topic generation
  │   └── script_database.py      # Script storage & tracking
  ├── audio/
  │   └── elevenlabs_service.py   # Voiceover generation
  ├── assets/
  │   ├── asset_manager.py        # Video asset library
  │   └── smart_matcher.py        # Keyword-based matching
  ├── social/
  │   ├── tiktok_uploader.py      # TikTok posting
  │   └── post_scheduler.py       # Optimal timing
  ├── video_orchestrator.py       # Main pipeline coordinator
  ├── video_scheduler.py          # Automated scheduling
  └── video_notifier.py           # Notification system

remotion/
  └── src/
      └── compositions/
          ├── TikTokVideo.tsx     # Main composition
          ├── CaptionOverlay.tsx  # Animated captions
          └── VideoSequencer.tsx  # Multi-clip stitching
```

## 🎯 API Endpoints

### Video Generation

- **POST /video/generate** - Generate complete video
  ```json
  {
    "category": "hunting",
    "location": "Mongolia",
    "duration": 30,
    "auto_post": false
  }
  ```

- **POST /video/generate/batch** - Generate multiple videos
  ```json
  {
    "count": 3,
    "auto_post": false
  }
  ```

- **GET /video/status/{script_id}** - Check generation status
- **GET /video/queue** - View pending videos
- **GET /video/schedule** - Get optimal posting times

### TikTok Posting

- **POST /tiktok/post** - Upload video to TikTok
  ```json
  {
    "video_path": "remotion/out/video.mp4",
    "caption": "Amazing tribal culture!",
    "hashtags": ["mongolia", "tribalculture", "documentary"]
  }
  ```

- **GET /tiktok/stats** - Get posting statistics

## 🔄 Data Flow

```
1. Topic Generator → AI-generated script
2. ElevenLabs → Voiceover audio + timestamps
3. Smart Matcher → Select relevant video clips
4. Remotion → Assemble video with captions
5. Output → 1080x1920 MP4 (TikTok format)
6. TikTok Uploader → Post with hashtags
7. Notifications → Discord/Email alerts
```

## ⏰ Automated Scheduling

The system can automatically:
- Generate 3 videos daily at 8 AM
- Post videos at optimal times (9 AM, 12 PM, 3 PM, 6 PM, 9 PM)
- Check render queue every 15 minutes
- Avoid spam limits (max 5 posts/day, 2-hour intervals)

Start the scheduler:
```bash
python agents/video_scheduler.py
```

Or integrate with existing scheduler:
```python
from agents.video_scheduler import VideoScheduler
scheduler = VideoScheduler()
scheduler.start()
```

## 🎨 Customizing Videos

### Change Caption Style

Edit `remotion/src/compositions/CaptionOverlay.tsx`:
```typescript
style?: 'default' | 'bold' | 'minimal'
```

### Adjust Video Format

Edit composition in `remotion/src/Root.tsx`:
```typescript
width={1080}   // TikTok vertical
height={1920}
fps={30}
```

### Add Background Music

Place music files in `remotion/public/audio/music/` and reference in props:
```typescript
backgroundMusicPath: 'audio/music/background.mp3'
```

## 🔐 TikTok Login

For auto-posting, you need a TikTok session:

```bash
python -c "from agents.social.tiktok_uploader import TikTokUploader; TikTokUploader().login()"
```

This opens a browser for manual login and saves session cookies.

## 📊 Monitoring

### Check Statistics

```python
from agents.content.script_database import ScriptDatabase
db = ScriptDatabase()
stats = db.get_stats()
print(stats)
```

### View Top Performing Videos

```python
top_videos = db.get_top_performing(metric='views', limit=10)
```

### Update Performance Metrics

```python
db.update_performance(
    script_id=1,
    views=10000,
    likes=500,
    shares=50
)
```

## 🎭 Demo Mode

The system works in demo mode without API keys:
- **Topic Generator**: Uses pre-written demo topics
- **ElevenLabs**: Creates empty audio files with estimated timestamps
- **TikTok Uploader**: Simulates uploads without posting

Perfect for testing the pipeline!

## 🐛 Troubleshooting

### No assets found
- Run `AssetManager().scan_directory()` to index videos
- Check that files are in `remotion/public/assets/footage/`
- Supported formats: mp4, mov, avi, mkv, webm

### Remotion render fails
- Ensure Remotion is installed: `cd remotion && npm install`
- Check Node.js version: `node --version` (requires 18+)
- Verify video paths in props are relative to `public/`

### TikTok upload fails
- Re-run login: `TikTokUploader().login()`
- Check session file exists: `agents/social/tiktok_session.json`
- TikTok's UI changes frequently - automation may need updates

### ElevenLabs quota exceeded
- Check API usage at elevenlabs.io
- System falls back to demo mode automatically
- Consider upgrading plan for production use

## 📈 Performance Tips

1. **Pre-generate content**: Run batch generation during off-hours
2. **Optimize assets**: Use compressed video files (H.264, 720p)
3. **Background workers**: Use job queue for render-heavy tasks
4. **Cache results**: Reuse rendered videos with different captions
5. **Monitor limits**: Track TikTok posting limits to avoid restrictions

## 🎓 Learn More

- [Remotion Documentation](https://www.remotion.dev/docs)
- [ElevenLabs API](https://elevenlabs.io/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [TikTok Best Practices](https://www.tiktok.com/creators)

## 📝 License

MIT

## 🙏 Credits

Built with:
- [Remotion](https://remotion.dev) - Video rendering
- [ElevenLabs](https://elevenlabs.io) - Voice synthesis
- [OpenAI](https://openai.com) - Content generation
- [TikTokApi](https://github.com/davidteather/TikTok-Api) - TikTok automation
