#!/usr/bin/env python3
"""
Content Sources for Health Encouragement Agent

Scans the internet for content about and for people dealing with
obesity and weight issues. Aggregates ENCOURAGING content only.

Sources:
- Reddit communities for weight loss support
- Health news about obesity
- Web search for success stories
- Motivational content
"""

import os
import json
import time
import random
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, quote, quote_plus

import requests
from bs4 import BeautifulSoup

# Try to import feedparser for RSS
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False


@dataclass
class HealthContent:
    """Represents a piece of health/motivational content."""
    id: str
    title: str
    url: str
    source: str
    category: str  # success_story, tip, motivation, news, community
    summary: str
    author: str
    score: int  # Upvotes/engagement score
    comments: int
    created_at: str
    fetched_at: str
    thumbnail: str = ""
    is_encouraging: bool = True
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# REDDIT SOURCES
# =============================================================================

REDDIT_SUBREDDITS = [
    # === PRIMARY: Obesity & Weight Loss Support ===
    {
        "name": "loseit",
        "category": "success_story",
        "description": "Weight loss support community",
        "flair_filter": ["SV", "NSV", "Progress"],  # Scale Victory, Non-Scale Victory
    },
    {
        "name": "progresspics",
        "category": "success_story",
        "description": "Before/after progress pictures",
        "flair_filter": None,
    },
    {
        "name": "SuperMorbidlyObese",
        "category": "community",
        "description": "Support for those with 200+ lbs to lose",
        "flair_filter": None,
    },
    {
        "name": "ObesityHealthConcern",
        "category": "community",
        "description": "Health-focused obesity support",
        "flair_filter": None,
    },
    {
        "name": "PlusSize",
        "category": "community",
        "description": "Plus size community support",
        "flair_filter": None,
    },
    {
        "name": "fatlogic",  # Actually has success stories and motivation
        "category": "success_story",
        "description": "Weight loss success stories",
        "flair_filter": ["Progress", "Sanity", "Article"],
    },
    {
        "name": "wls",
        "category": "community",
        "description": "Weight loss surgery support",
        "flair_filter": None,
    },
    {
        "name": "gastricsleeve",
        "category": "community",
        "description": "Gastric sleeve surgery support",
        "flair_filter": None,
    },
    {
        "name": "gastricbypass",
        "category": "community",
        "description": "Gastric bypass surgery support",
        "flair_filter": None,
    },
    # === SECONDARY: General Weight Loss ===
    {
        "name": "fitness",
        "category": "tip",
        "description": "Fitness advice and motivation",
        "flair_filter": ["Progress", "Success Story"],
    },
    {
        "name": "GetMotivated",
        "category": "motivation",
        "description": "General motivation",
        "flair_filter": ["Text", "Image"],
    },
    {
        "name": "xxfitness",
        "category": "community",
        "description": "Women's fitness community",
        "flair_filter": None,
    },
    {
        "name": "CICO",
        "category": "tip",
        "description": "Calories In, Calories Out community",
        "flair_filter": None,
    },
    {
        "name": "intermittentfasting",
        "category": "success_story",
        "description": "Intermittent fasting support",
        "flair_filter": ["Progress Pic", "Success Story"],
    },
    {
        "name": "1500isplenty",
        "category": "tip",
        "description": "Calorie-conscious meal ideas",
        "flair_filter": None,
    },
    {
        "name": "1200isplenty",
        "category": "tip",
        "description": "Low calorie meal ideas",
        "flair_filter": None,
    },
    {
        "name": "EatCheapAndHealthy",
        "category": "tip",
        "description": "Budget-friendly healthy eating",
        "flair_filter": None,
    },
    {
        "name": "MealPrepSunday",
        "category": "tip",
        "description": "Meal prep ideas and motivation",
        "flair_filter": None,
    },
    {
        "name": "keto",
        "category": "tip",
        "description": "Ketogenic diet support",
        "flair_filter": ["Progress", "Success Story"],
    },
    {
        "name": "Volumeeating",
        "category": "tip",
        "description": "High volume, low calorie meals",
        "flair_filter": None,
    },
]

# Search terms for finding obesity-related content
OBESITY_SEARCH_TERMS = [
    "obese weight loss journey",
    "morbidly obese transformation",
    "obesity success story",
    "overweight to healthy",
    "300 pounds weight loss",
    "400 pounds weight loss",
    "obesity recovery story",
    "fat to fit transformation",
    "plus size fitness journey",
    "obesity motivation",
    "bariatric surgery success",
    "weight loss inspiration obese",
    "heavy weight loss progress",
    "obesity health improvement",
    "turning point obesity",
]

# Health-focused keywords for filtering encouraging content
ENCOURAGING_KEYWORDS = [
    "success", "progress", "journey", "milestone", "achieved", "goal",
    "proud", "finally", "transformation", "motivation", "inspired",
    "healthy", "wellness", "support", "victory", "celebrate",
    "tip", "advice", "helped", "recommend", "worked for me",
    "nsv", "sv", "non-scale victory", "scale victory",
    "before and after", "pounds down", "kg down", "lost weight",
    "feeling better", "energy", "confidence", "self-love",
    "meal prep", "recipe", "workout", "exercise", "walking",
    "small steps", "habit", "routine", "discipline", "consistency",
    "you can do it", "keep going", "don't give up", "believe",
    # Obesity-specific encouraging terms
    "obese to healthy", "morbidly obese", "super obese",
    "300 lbs", "400 lbs", "200 lbs lost", "half my weight",
    "bariatric", "gastric sleeve", "gastric bypass",
    "life changing", "saved my life", "can walk again",
    "off medications", "diabetes reversed", "mobility improved",
]

# Keywords to filter out (not encouraging/supportive)
NEGATIVE_KEYWORDS = [
    "relapsed", "failed", "giving up", "hate myself", "worthless",
    "disgusting", "fat shaming", "mock", "ridicule", "make fun",
    "lazy", "gross", "pathetic", "loser", "whale", "pig",
    "hambeast", "deathfat", "glorifying obesity",
]


def generate_content_id(url: str, title: str) -> str:
    """Generate a unique ID for content."""
    content = f"{url}:{title}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def is_encouraging_content(title: str, body: str = "") -> bool:
    """Check if content is encouraging/supportive."""
    text = (title + " " + body).lower()
    
    # Check for negative keywords
    for neg in NEGATIVE_KEYWORDS:
        if neg in text:
            return False
    
    # Check for positive keywords
    for pos in ENCOURAGING_KEYWORDS:
        if pos in text:
            return True
    
    # Default to True for neutral content
    return True


def fetch_reddit_posts(subreddit: str, limit: int = 25, sort: str = "hot") -> List[HealthContent]:
    """
    Fetch posts from a Reddit subreddit using the JSON API.
    
    Args:
        subreddit: Subreddit name (without r/)
        limit: Number of posts to fetch
        sort: Sort method (hot, new, top, rising)
    
    Returns:
        List of HealthContent objects
    """
    contents = []
    
    # Find subreddit config
    sub_config = next(
        (s for s in REDDIT_SUBREDDITS if s["name"].lower() == subreddit.lower()),
        {"name": subreddit, "category": "community", "flair_filter": None}
    )
    
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    headers = {
        "User-Agent": "HealthEncouragementAgent/1.0 (Health Support Content Aggregator)"
    }
    
    try:
        params = {"limit": limit, "raw_json": 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        for post in posts:
            post_data = post.get("data", {})
            
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")
            
            # Filter for encouraging content
            if not is_encouraging_content(title, selftext):
                continue
            
            # Check flair filter if specified
            flair = post_data.get("link_flair_text", "") or ""
            if sub_config.get("flair_filter"):
                if not any(f.lower() in flair.lower() for f in sub_config["flair_filter"]):
                    # Still include if title seems encouraging
                    if not any(kw in title.lower() for kw in ["progress", "success", "victory", "milestone"]):
                        continue
            
            # Get thumbnail
            thumbnail = post_data.get("thumbnail", "")
            if thumbnail in ["self", "default", "nsfw", "spoiler", ""]:
                thumbnail = ""
            
            # Create content object
            post_url = f"https://www.reddit.com{post_data.get('permalink', '')}"
            
            content = HealthContent(
                id=generate_content_id(post_url, title),
                title=title,
                url=post_url,
                source=f"r/{subreddit}",
                category=sub_config["category"],
                summary=selftext[:300] + "..." if len(selftext) > 300 else selftext,
                author=post_data.get("author", "anonymous"),
                score=post_data.get("score", 0),
                comments=post_data.get("num_comments", 0),
                created_at=datetime.fromtimestamp(
                    post_data.get("created_utc", time.time())
                ).isoformat(),
                fetched_at=datetime.now().isoformat(),
                thumbnail=thumbnail,
                is_encouraging=True,
                tags=[flair] if flair else [],
            )
            
            contents.append(content)
            
    except requests.RequestException as e:
        print(f"Error fetching r/{subreddit}: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing r/{subreddit} response: {e}")
    
    return contents


def fetch_all_reddit_content(limit_per_sub: int = 15) -> List[HealthContent]:
    """Fetch content from all configured Reddit subreddits."""
    all_content = []
    
    for sub in REDDIT_SUBREDDITS:
        print(f"  Fetching r/{sub['name']}...")
        posts = fetch_reddit_posts(sub["name"], limit=limit_per_sub)
        all_content.extend(posts)
        # Be nice to Reddit
        time.sleep(1)
    
    return all_content


# =============================================================================
# RSS FEED SOURCES
# =============================================================================

RSS_FEEDS = [
    # Obesity-focused news
    {
        "name": "Medical News Today - Obesity",
        "url": "https://www.medicalnewstoday.com/categories/obesity/rss",
        "category": "news",
    },
    {
        "name": "Healthline - Weight Management",
        "url": "https://www.healthline.com/rss/weight-management",
        "category": "news",
    },
    {
        "name": "Obesity Action Coalition",
        "url": "https://www.obesityaction.org/feed/",
        "category": "news",
    },
    # General health
    {
        "name": "Harvard Health - Nutrition",
        "url": "https://www.health.harvard.edu/blog/feed",
        "category": "tip",
    },
    {
        "name": "Mayo Clinic - Healthy Lifestyle",
        "url": "https://newsnetwork.mayoclinic.org/feed/",
        "category": "tip",
    },
    {
        "name": "ACE Fitness Blog",
        "url": "https://www.acefitness.org/resources/everyone/blog/rss/",
        "category": "tip",
    },
    {
        "name": "Precision Nutrition",
        "url": "https://www.precisionnutrition.com/feed",
        "category": "tip",
    },
]


def fetch_rss_feed(feed_config: Dict) -> List[HealthContent]:
    """
    Fetch content from an RSS feed.
    
    Args:
        feed_config: Feed configuration with name, url, category
    
    Returns:
        List of HealthContent objects
    """
    contents = []
    
    if not FEEDPARSER_AVAILABLE:
        print("Warning: feedparser not installed, skipping RSS feeds")
        return contents
    
    try:
        feed = feedparser.parse(feed_config["url"])
        
        for entry in feed.entries[:15]:
            title = entry.get("title", "")
            
            # Filter for encouraging/relevant content
            if not is_encouraging_content(title, entry.get("summary", "")):
                continue
            
            # Get published date
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                created_at = datetime(*published[:6]).isoformat()
            else:
                created_at = datetime.now().isoformat()
            
            content = HealthContent(
                id=generate_content_id(entry.get("link", ""), title),
                title=title,
                url=entry.get("link", ""),
                source=feed_config["name"],
                category=feed_config["category"],
                summary=entry.get("summary", "")[:300],
                author=entry.get("author", feed_config["name"]),
                score=0,  # RSS feeds don't have scores
                comments=0,
                created_at=created_at,
                fetched_at=datetime.now().isoformat(),
                thumbnail=entry.get("media_thumbnail", [{}])[0].get("url", "") if entry.get("media_thumbnail") else "",
                is_encouraging=True,
                tags=[],
            )
            
            contents.append(content)
            
    except Exception as e:
        print(f"Error fetching RSS feed {feed_config['name']}: {e}")
    
    return contents


def fetch_all_rss_content() -> List[HealthContent]:
    """Fetch content from all configured RSS feeds."""
    all_content = []
    
    for feed in RSS_FEEDS:
        print(f"  Fetching {feed['name']}...")
        posts = fetch_rss_feed(feed)
        all_content.extend(posts)
        time.sleep(0.5)
    
    return all_content


# =============================================================================
# WEB SEARCH - Scan Internet for Obesity Content
# =============================================================================

def search_web_for_obesity_content(query: str, num_results: int = 10) -> List[HealthContent]:
    """
    Search the web for obesity-related encouraging content.
    
    Uses DuckDuckGo HTML search (no API key needed).
    
    Args:
        query: Search query
        num_results: Max results to return
    
    Returns:
        List of HealthContent objects
    """
    contents = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Use DuckDuckGo HTML search
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find search results
        results = soup.find_all("div", class_="result")
        
        for result in results[:num_results]:
            try:
                # Get title and link
                title_elem = result.find("a", class_="result__a")
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                
                # Get snippet
                snippet_elem = result.find("a", class_="result__snippet")
                summary = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # Filter for encouraging content
                if not is_encouraging_content(title, summary):
                    continue
                
                # Extract domain for source
                domain = ""
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "")
                except:
                    domain = "Web"
                
                content = HealthContent(
                    id=generate_content_id(url, title),
                    title=title,
                    url=url,
                    source=domain or "Web Search",
                    category="success_story" if any(kw in title.lower() for kw in ["transformation", "journey", "lost", "before", "after"]) else "news",
                    summary=summary[:300],
                    author="Web",
                    score=random.randint(50, 300),  # Estimate engagement
                    comments=0,
                    created_at=datetime.now().isoformat(),
                    fetched_at=datetime.now().isoformat(),
                    is_encouraging=True,
                    tags=["web_search"],
                )
                
                contents.append(content)
                
            except Exception as e:
                continue
        
    except requests.RequestException as e:
        print(f"Web search error for '{query}': {e}")
    except Exception as e:
        print(f"Web search parse error: {e}")
    
    return contents


def search_reddit_for_obesity(query: str = "obese weight loss", limit: int = 20) -> List[HealthContent]:
    """
    Search Reddit specifically for obesity-related posts.
    
    Args:
        query: Search query
        limit: Max results
    
    Returns:
        List of HealthContent
    """
    contents = []
    
    url = f"https://www.reddit.com/search.json"
    headers = {
        "User-Agent": "HealthEncouragementAgent/1.0 (Obesity Support Content)"
    }
    
    try:
        params = {
            "q": query,
            "limit": limit,
            "sort": "relevance",
            "t": "month",  # Last month
            "raw_json": 1,
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        for post in posts:
            post_data = post.get("data", {})
            
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")
            subreddit = post_data.get("subreddit", "")
            
            # Filter for encouraging content
            if not is_encouraging_content(title, selftext):
                continue
            
            post_url = f"https://www.reddit.com{post_data.get('permalink', '')}"
            
            content = HealthContent(
                id=generate_content_id(post_url, title),
                title=title,
                url=post_url,
                source=f"r/{subreddit}",
                category="success_story" if any(kw in title.lower() for kw in ["progress", "lost", "down", "transformation", "sv", "nsv"]) else "community",
                summary=selftext[:300] + "..." if len(selftext) > 300 else selftext,
                author=post_data.get("author", "anonymous"),
                score=post_data.get("score", 0),
                comments=post_data.get("num_comments", 0),
                created_at=datetime.fromtimestamp(
                    post_data.get("created_utc", time.time())
                ).isoformat(),
                fetched_at=datetime.now().isoformat(),
                is_encouraging=True,
                tags=[subreddit],
            )
            
            contents.append(content)
            
    except Exception as e:
        print(f"Reddit search error: {e}")
    
    return contents


def scan_internet_for_obesity_content(max_per_source: int = 10) -> List[HealthContent]:
    """
    Comprehensive internet scan for obesity-related encouraging content.
    
    Searches multiple sources for content about/for obese people.
    
    Returns:
        List of HealthContent from various sources
    """
    all_content = []
    
    print("Scanning internet for obesity encouragement content...")
    
    # Reddit-wide searches
    reddit_queries = [
        "obese weight loss progress",
        "morbidly obese transformation",
        "400 pounds lost weight",
        "obesity success story",
        "bariatric surgery results",
        "super obese to healthy",
    ]
    
    for query in reddit_queries:
        print(f"  Reddit search: {query}")
        results = search_reddit_for_obesity(query, limit=max_per_source)
        all_content.extend(results)
        time.sleep(1)  # Be nice to Reddit
    
    # Web searches
    web_queries = [
        "obese person weight loss success story",
        "morbidly obese transformation inspiration",
        "obesity recovery motivation",
        "400 pound weight loss journey",
        "overweight to healthy transformation",
        "obesity encouragement support",
    ]
    
    for query in web_queries:
        print(f"  Web search: {query}")
        results = search_web_for_obesity_content(query, num_results=max_per_source)
        all_content.extend(results)
        time.sleep(1)  # Be polite
    
    print(f"  Found {len(all_content)} items from internet scan")
    
    return all_content


# =============================================================================
# MOTIVATIONAL QUOTES API
# =============================================================================

HEALTH_QUOTES = [
    # Obesity-specific encouragement
    {"text": "Your weight does not define your worth. Your journey does.", "author": "Unknown"},
    {"text": "Every pound lost is a victory. Every healthy choice is a win.", "author": "Unknown"},
    {"text": "You didn't gain it overnight. You won't lose it overnight. But you WILL lose it.", "author": "Unknown"},
    {"text": "The scale is just one measure. Your energy, your mood, your life - those matter more.", "author": "Unknown"},
    {"text": "Start where you are. Use what you have. Do what you can.", "author": "Arthur Ashe"},
    {"text": "You are not too far gone. You are not too heavy to start. Today is your day.", "author": "Unknown"},
    {"text": "100 pounds lost starts with the first pound. You've got this.", "author": "Unknown"},
    {"text": "Your body has carried you this far. Now let's take care of it together.", "author": "Unknown"},
    # General health motivation
    {"text": "The only bad workout is the one that didn't happen.", "author": "Unknown"},
    {"text": "Take care of your body. It's the only place you have to live.", "author": "Jim Rohn"},
    {"text": "Your body can stand almost anything. It's your mind that you have to convince.", "author": "Unknown"},
    {"text": "Health is not about the weight you lose, but about the life you gain.", "author": "Unknown"},
    {"text": "Success is the sum of small efforts repeated day in and day out.", "author": "Robert Collier"},
    {"text": "Progress, not perfection.", "author": "Unknown"},
    {"text": "Every step is progress, no matter how small.", "author": "Unknown"},
    {"text": "You don't have to be extreme, just consistent.", "author": "Unknown"},
    {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"text": "Small steps still move you forward.", "author": "Unknown"},
    {"text": "It's not about perfect. It's about effort.", "author": "Jillian Michaels"},
    {"text": "You are stronger than you think.", "author": "Unknown"},
    {"text": "Every day is a new beginning. Take a deep breath and start again.", "author": "Unknown"},
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "A year from now, you'll wish you had started today.", "author": "Karen Lamb"},
    {"text": "Don't compare your chapter 1 to someone else's chapter 20.", "author": "Unknown"},
]


def get_motivational_quotes(count: int = 5) -> List[HealthContent]:
    """Get random motivational quotes as content."""
    selected = random.sample(HEALTH_QUOTES, min(count, len(HEALTH_QUOTES)))
    contents = []
    
    for quote in selected:
        content = HealthContent(
            id=generate_content_id(quote["text"], quote["author"]),
            title=f'"{quote["text"]}"',
            url="",
            source="Daily Motivation",
            category="motivation",
            summary=f"— {quote['author']}",
            author=quote["author"],
            score=random.randint(100, 1000),  # Simulate engagement
            comments=0,
            created_at=datetime.now().isoformat(),
            fetched_at=datetime.now().isoformat(),
            is_encouraging=True,
            tags=["quote", "motivation"],
        )
        contents.append(content)
    
    return contents


# =============================================================================
# CONTENT AGGREGATION
# =============================================================================

def calculate_hn_score(content: HealthContent) -> float:
    """
    Calculate HN-style score for ranking content.
    
    Uses a modified version of HN's algorithm:
    Score = (votes - 1) / (hours + 2)^gravity
    
    With adjustments for health content relevance.
    """
    # Parse created_at
    try:
        created = datetime.fromisoformat(content.created_at.replace("Z", "+00:00"))
    except:
        created = datetime.now()
    
    # Hours since posted
    hours = max(1, (datetime.now() - created.replace(tzinfo=None)).total_seconds() / 3600)
    
    # Base score from upvotes
    votes = max(1, content.score)
    
    # Comment engagement boost
    comment_boost = 1 + (content.comments * 0.1)
    
    # Category boost (success stories and motivation rank higher)
    category_boost = {
        "success_story": 1.5,
        "motivation": 1.3,
        "tip": 1.2,
        "community": 1.1,
        "news": 1.0,
    }.get(content.category, 1.0)
    
    # Gravity (how fast posts decay)
    gravity = 1.5
    
    # Calculate score
    score = (votes * comment_boost * category_boost) / ((hours + 2) ** gravity)
    
    return score


def aggregate_and_rank_content(
    include_reddit: bool = True,
    include_rss: bool = True,
    include_quotes: bool = True,
    include_web_scan: bool = True,
    max_items: int = 50,
) -> List[HealthContent]:
    """
    Aggregate content from all sources and rank by HN-style score.
    
    Scans the internet for content about obese people - for ENCOURAGEMENT.
    
    Args:
        include_reddit: Include Reddit community content
        include_rss: Include RSS feed content
        include_quotes: Include motivational quotes
        include_web_scan: Include internet-wide scan for obesity content
        max_items: Maximum items to return
    
    Returns:
        List of HealthContent sorted by HN score (highest first)
    """
    all_content = []
    
    print("=" * 50)
    print("SCANNING INTERNET FOR OBESITY ENCOURAGEMENT CONTENT")
    print("=" * 50)
    
    if include_reddit:
        print("\n[1/4] Scanning Reddit weight loss communities...")
        reddit_content = fetch_all_reddit_content(limit_per_sub=10)
        all_content.extend(reddit_content)
        print(f"      Found {len(reddit_content)} Reddit posts")
    
    if include_web_scan:
        print("\n[2/4] Scanning internet for obesity success stories...")
        web_content = scan_internet_for_obesity_content(max_per_source=8)
        all_content.extend(web_content)
        print(f"      Found {len(web_content)} web results")
    
    if include_rss:
        print("\n[3/4] Scanning health news feeds...")
        rss_content = fetch_all_rss_content()
        all_content.extend(rss_content)
        print(f"      Found {len(rss_content)} news articles")
    
    if include_quotes:
        print("\n[4/4] Adding motivational quotes...")
        quotes = get_motivational_quotes(count=5)
        all_content.extend(quotes)
        print(f"      Added {len(quotes)} quotes")
    
    # Remove duplicates by ID
    seen_ids = set()
    unique_content = []
    for content in all_content:
        if content.id not in seen_ids:
            seen_ids.add(content.id)
            unique_content.append(content)
    
    # Calculate HN scores and sort
    scored_content = [(calculate_hn_score(c), c) for c in unique_content]
    scored_content.sort(key=lambda x: x[0], reverse=True)
    
    # Return top items
    ranked_content = [c for _, c in scored_content[:max_items]]
    
    print("\n" + "=" * 50)
    print(f"TOTAL: {len(ranked_content)} encouraging items ranked")
    print("=" * 50)
    
    return ranked_content


# =============================================================================
# CACHING
# =============================================================================

_content_cache: Dict[str, Any] = {
    "content": [],
    "last_fetched": None,
    "cache_duration": 900,  # 15 minutes
}


def get_cached_content(force_refresh: bool = False) -> List[HealthContent]:
    """
    Get content with caching support.
    
    Args:
        force_refresh: Force refresh even if cache is valid
    
    Returns:
        List of ranked HealthContent
    """
    now = datetime.now()
    
    # Check if cache is valid
    if not force_refresh and _content_cache["last_fetched"]:
        elapsed = (now - _content_cache["last_fetched"]).total_seconds()
        if elapsed < _content_cache["cache_duration"]:
            return _content_cache["content"]
    
    # Fetch fresh content
    content = aggregate_and_rank_content()
    
    # Update cache
    _content_cache["content"] = content
    _content_cache["last_fetched"] = now
    
    return content


def save_content_to_json(content: List[HealthContent], filepath: str):
    """Save content list to JSON file."""
    data = [c.to_dict() for c in content]
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_content_from_json(filepath: str) -> List[HealthContent]:
    """Load content list from JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return [HealthContent(**item) for item in data]


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch health encouragement content")
    parser.add_argument("--reddit", action="store_true", help="Fetch Reddit content only")
    parser.add_argument("--rss", action="store_true", help="Fetch RSS content only")
    parser.add_argument("--all", action="store_true", help="Fetch all content")
    parser.add_argument("--output", type=str, help="Output JSON file")
    parser.add_argument("--limit", type=int, default=30, help="Max items to return")
    
    args = parser.parse_args()
    
    # Determine what to fetch
    fetch_reddit = args.reddit or args.all or (not args.reddit and not args.rss)
    fetch_rss = args.rss or args.all or (not args.reddit and not args.rss)
    
    content = aggregate_and_rank_content(
        include_reddit=fetch_reddit,
        include_rss=fetch_rss,
        max_items=args.limit,
    )
    
    # Output
    if args.output:
        save_content_to_json(content, args.output)
        print(f"Saved to {args.output}")
    else:
        print("\n" + "=" * 60)
        print("TOP HEALTH ENCOURAGEMENT CONTENT")
        print("=" * 60)
        
        for i, item in enumerate(content[:30], 1):
            print(f"\n{i}. {item.title[:70]}...")
            print(f"   [{item.category}] {item.source} | {item.score} points | {item.comments} comments")
            if item.summary:
                print(f"   {item.summary[:100]}...")
