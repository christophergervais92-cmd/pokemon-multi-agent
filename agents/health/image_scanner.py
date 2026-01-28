#!/usr/bin/env python3
"""
Image Scanner for Health Encouragement Agent

Scans the internet for images related to obesity/weight loss journeys
and overlays "HN" text for encouragement captions.
"""

import os
import io
import re
import time
import random
import hashlib
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Image processing
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Run: pip install Pillow")


@dataclass
class FoundImage:
    """Represents a found image with metadata."""
    id: str
    original_url: str
    source_page: str
    source_name: str
    title: str
    alt_text: str
    width: int
    height: int
    processed_b64: str  # Base64 of processed image with HN overlay
    found_at: str
    category: str  # progress, motivation, community, before_after
    
    def to_dict(self) -> Dict:
        return asdict(self)


# Search terms for finding obesity-related images
IMAGE_SEARCH_TERMS = [
    "weight loss transformation before after",
    "obesity weight loss progress",
    "morbid obesity transformation",
    "bariatric surgery before after",
    "weight loss journey progress pics",
    "obese to fit transformation",
    "300 pound weight loss",
    "gastric sleeve before after",
    "weight loss motivation progress",
    "plus size fitness journey",
]

# User agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def generate_image_id(url: str) -> str:
    """Generate unique ID for an image."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def download_image(url: str, timeout: int = 10) -> Optional[Image.Image]:
    """
    Download an image from URL.
    
    Returns PIL Image or None if failed.
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None
        
        # Load image
        img = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        return img
        
    except Exception as e:
        print(f"  Failed to download image: {e}")
        return None


def overlay_hn_text(
    img: Image.Image,
    text: str = "HN",
    position: str = "bottom-right",
    font_size: int = None,
    opacity: float = 0.85,
) -> Image.Image:
    """
    Overlay "HN" text on an image.
    
    Args:
        img: PIL Image
        text: Text to overlay (default "HN")
        position: Where to place text (bottom-right, bottom-left, center, etc.)
        font_size: Font size (auto-calculated if None)
        opacity: Text opacity (0-1)
    
    Returns:
        Image with text overlay
    """
    if not PIL_AVAILABLE:
        return img
    
    # Make a copy
    img = img.copy()
    
    # Calculate font size based on image dimensions
    if font_size is None:
        font_size = max(24, min(img.width, img.height) // 8)
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Try to load a bold font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position
    padding = 15
    
    if position == "bottom-right":
        x = img.width - text_width - padding
        y = img.height - text_height - padding
    elif position == "bottom-left":
        x = padding
        y = img.height - text_height - padding
    elif position == "top-right":
        x = img.width - text_width - padding
        y = padding
    elif position == "top-left":
        x = padding
        y = padding
    elif position == "center":
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2
    else:  # bottom-center
        x = (img.width - text_width) // 2
        y = img.height - text_height - padding
    
    # Draw shadow/outline for visibility
    shadow_color = (0, 0, 0)
    for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)
    
    # Draw main text (orange like HN)
    text_color = (255, 102, 0)  # HN orange
    draw.text((x, y), text, font=font, fill=text_color)
    
    return img


def image_to_base64(img: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def search_images_duckduckgo(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search for images using DuckDuckGo.
    
    Returns list of image info dicts.
    """
    results = []
    
    try:
        # DuckDuckGo image search
        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}&iax=images&ia=images"
        
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(search_url, headers=headers, timeout=10)
        
        # DDG uses JavaScript, so we need to extract vqd token and use their API
        # For simplicity, let's use their HTML results
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find image elements
        for img in soup.find_all("img", src=True)[:max_results * 2]:
            src = img.get("src", "")
            alt = img.get("alt", "")
            
            # Filter for actual content images
            if not src or "duckduckgo" in src.lower():
                continue
            if src.startswith("data:"):
                continue
            if any(skip in src.lower() for skip in ["logo", "icon", "button", "sprite"]):
                continue
            
            results.append({
                "url": src,
                "alt": alt,
                "source": "DuckDuckGo",
            })
        
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
    
    return results[:max_results]


def search_reddit_images(subreddit: str, limit: int = 10) -> List[Dict]:
    """
    Fetch images from a Reddit subreddit.
    
    Returns list of image info dicts.
    """
    results = []
    
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        headers = {"User-Agent": "HealthEncouragementAgent/1.0"}
        
        response = requests.get(url, headers=headers, params={"limit": limit * 2}, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        for post in posts:
            post_data = post.get("data", {})
            
            # Check for image posts
            url = post_data.get("url", "")
            
            # Direct image links
            if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                results.append({
                    "url": url,
                    "alt": post_data.get("title", ""),
                    "source": f"r/{subreddit}",
                    "source_page": f"https://reddit.com{post_data.get('permalink', '')}",
                    "title": post_data.get("title", ""),
                    "score": post_data.get("score", 0),
                })
            
            # Reddit hosted images
            elif "i.redd.it" in url or "i.imgur.com" in url:
                results.append({
                    "url": url,
                    "alt": post_data.get("title", ""),
                    "source": f"r/{subreddit}",
                    "source_page": f"https://reddit.com{post_data.get('permalink', '')}",
                    "title": post_data.get("title", ""),
                    "score": post_data.get("score", 0),
                })
            
            # Reddit gallery
            elif post_data.get("is_gallery"):
                media_metadata = post_data.get("media_metadata", {})
                for media_id, media_info in media_metadata.items():
                    if media_info.get("status") == "valid":
                        # Get the image URL
                        if "s" in media_info and "u" in media_info["s"]:
                            img_url = media_info["s"]["u"].replace("&amp;", "&")
                            results.append({
                                "url": img_url,
                                "alt": post_data.get("title", ""),
                                "source": f"r/{subreddit}",
                                "source_page": f"https://reddit.com{post_data.get('permalink', '')}",
                                "title": post_data.get("title", ""),
                                "score": post_data.get("score", 0),
                            })
                            break  # Just get first image from gallery
            
            if len(results) >= limit:
                break
        
    except Exception as e:
        print(f"Reddit image fetch error for r/{subreddit}: {e}")
    
    return results[:limit]


def scan_for_obesity_images(max_per_source: int = 5) -> List[FoundImage]:
    """
    Scan internet for obesity/weight loss related images.
    
    Returns list of FoundImage with HN overlay applied.
    """
    if not PIL_AVAILABLE:
        print("Error: Pillow required for image processing")
        return []
    
    found_images = []
    
    # Reddit subreddits with progress pics
    reddit_subs = [
        "progresspics",
        "loseit",
        "SuperMorbidlyObese",
        "GastricSleeve",
        "wls",
        "intermittentfasting",
        "BTFC",  # Body Transformation Fitness Challenge
    ]
    
    print("Scanning internet for obesity encouragement images...")
    print("=" * 50)
    
    # Scan Reddit
    for sub in reddit_subs:
        print(f"  Scanning r/{sub}...")
        
        images = search_reddit_images(sub, limit=max_per_source)
        
        for img_info in images:
            try:
                # Download image
                img = download_image(img_info["url"])
                if not img:
                    continue
                
                # Skip tiny images
                if img.width < 200 or img.height < 200:
                    continue
                
                # Apply HN overlay
                processed = overlay_hn_text(img, "HN", position="bottom-right")
                
                # Convert to base64
                b64 = image_to_base64(processed)
                
                found_image = FoundImage(
                    id=generate_image_id(img_info["url"]),
                    original_url=img_info["url"],
                    source_page=img_info.get("source_page", ""),
                    source_name=img_info.get("source", f"r/{sub}"),
                    title=img_info.get("title", img_info.get("alt", "")),
                    alt_text=img_info.get("alt", ""),
                    width=img.width,
                    height=img.height,
                    processed_b64=b64,
                    found_at=datetime.now().isoformat(),
                    category="progress" if "progress" in sub.lower() else "community",
                )
                
                found_images.append(found_image)
                print(f"    Found: {found_image.title[:50]}...")
                
            except Exception as e:
                print(f"    Error processing image: {e}")
                continue
        
        time.sleep(1)  # Be nice to Reddit
    
    print("=" * 50)
    print(f"Total images found: {len(found_images)}")
    
    return found_images


def create_image_gallery_html(images: List[FoundImage]) -> str:
    """
    Create HTML gallery of images with HN overlay.
    """
    html = """<!DOCTYPE html>
<html>
<head>
    <title>HN - Health Encouragement Gallery</title>
    <style>
        body {
            font-family: Verdana, sans-serif;
            background: #f6f6ef;
            margin: 0;
            padding: 20px;
        }
        .header {
            background: #ff6600;
            padding: 10px 20px;
            margin: -20px -20px 20px -20px;
        }
        .header h1 {
            color: #000;
            margin: 0;
            font-size: 18px;
        }
        .header p {
            color: #000;
            margin: 5px 0 0 0;
            font-size: 12px;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .image-card {
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .image-card img {
            width: 100%;
            height: auto;
            display: block;
        }
        .image-info {
            padding: 10px;
        }
        .image-title {
            font-size: 12px;
            color: #000;
            margin: 0 0 5px 0;
            line-height: 1.4;
        }
        .image-source {
            font-size: 10px;
            color: #828282;
        }
        .banner {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            text-align: center;
            margin: -20px -20px 20px -20px;
            margin-top: 0;
        }
        .banner h2 { margin: 0 0 10px 0; }
        .banner p { margin: 0; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="header">
        <h1>HN - Health Encouragement</h1>
        <p>Real transformations. Real people. Real inspiration.</p>
    </div>
    <div class="banner">
        <h2>You Are Not Alone</h2>
        <p>Every image here represents someone who started their journey. You can too.</p>
    </div>
    <div class="gallery">
"""
    
    for img in images:
        html += f"""
        <div class="image-card">
            <img src="data:image/jpeg;base64,{img.processed_b64}" alt="{img.alt_text}">
            <div class="image-info">
                <p class="image-title">{img.title[:100]}</p>
                <p class="image-source">{img.source_name}</p>
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>"""
    
    return html


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan for obesity images and overlay HN text")
    parser.add_argument("--scan", action="store_true", help="Scan for images")
    parser.add_argument("--output", type=str, default="hn_gallery.html", help="Output HTML file")
    parser.add_argument("--limit", type=int, default=5, help="Max images per source")
    
    args = parser.parse_args()
    
    if args.scan:
        images = scan_for_obesity_images(max_per_source=args.limit)
        
        if images:
            html = create_image_gallery_html(images)
            with open(args.output, "w") as f:
                f.write(html)
            print(f"\nGallery saved to {args.output}")
        else:
            print("No images found")
    else:
        parser.print_help()
