"""
X/Twitter Content Generator - AI-powered tweet generation for Pokemon TCG.

Features:
- AI-generated tweets using OpenAI
- Template-based content for restocks, deals, market updates
- Automatic hashtag optimization
- Thread generation for longer content
- Scheduled content queue
- Content analytics tracking
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .content_templates import TweetTemplates, TweetTemplate
from .x_api_client import XAPIClient, PostResult, MockXAPIClient


class ContentType(Enum):
    """Types of content that can be generated."""
    RESTOCK = "restock"
    DEAL = "deal"
    MARKET = "market"
    DROP = "drop"
    GRADING = "grading"
    NEWS = "news"
    ENGAGEMENT = "engagement"
    GENERAL = "general"


@dataclass
class GeneratedContent:
    """Container for generated content."""
    content_type: ContentType
    text: str
    hashtags: List[str]
    full_tweet: str
    length: int
    is_valid: bool
    metadata: Dict = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "template"  # "template" or "ai"


@dataclass
class ScheduledTweet:
    """A tweet scheduled for future posting."""
    id: str
    content: GeneratedContent
    scheduled_time: datetime
    posted: bool = False
    post_result: Optional[PostResult] = None


class XContentGenerator:
    """
    AI-powered content generator for X/Twitter.
    
    Generates engaging Pokemon TCG content including:
    - Restock alerts
    - Deal notifications
    - Market updates
    - Product drops
    - Grading tips
    - Engagement posts
    """
    
    def __init__(
        self,
        x_client: Optional[XAPIClient] = None,
        openai_api_key: Optional[str] = None,
        use_mock: bool = False
    ):
        """
        Initialize the content generator.
        
        Args:
            x_client: X API client for posting (creates new if not provided)
            openai_api_key: OpenAI API key for AI generation
            use_mock: Use mock client for testing
        """
        if use_mock:
            self.x_client = MockXAPIClient()
        else:
            self.x_client = x_client or XAPIClient()
        
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self._scheduled_queue: List[ScheduledTweet] = []
        self._posted_history: List[Dict] = []
        self._generation_stats = {
            "total_generated": 0,
            "total_posted": 0,
            "by_type": {}
        }
        
        # Initialize OpenAI client if available
        if HAS_OPENAI and self.openai_api_key:
            openai.api_key = self.openai_api_key
    
    # =========================================================================
    # Template-Based Generation
    # =========================================================================
    
    def generate_restock_tweet(
        self,
        product_name: str,
        retailer: str,
        price: float,
        url: str
    ) -> GeneratedContent:
        """Generate a restock alert tweet."""
        templates = TweetTemplates.get_templates("restock")
        template = random.choice(templates)
        
        result = TweetTemplates.format_template(
            template,
            product_name=product_name,
            retailer=retailer,
            price=f"{price:.2f}",
            url=url
        )
        
        if result.get("error"):
            return GeneratedContent(
                content_type=ContentType.RESTOCK,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": result["error"]}
            )
        
        return GeneratedContent(
            content_type=ContentType.RESTOCK,
            text=result["content"],
            hashtags=result["hashtags"],
            full_tweet=result["full_tweet"],
            length=result["length"],
            is_valid=result["valid"],
            metadata={
                "product_name": product_name,
                "retailer": retailer,
                "price": price,
                "url": url
            },
            source="template"
        )
    
    def generate_deal_tweet(
        self,
        product_name: str,
        retailer: str,
        original_price: float,
        sale_price: float,
        url: str
    ) -> GeneratedContent:
        """Generate a deal alert tweet."""
        discount = int(((original_price - sale_price) / original_price) * 100)
        
        templates = TweetTemplates.get_templates("deal")
        template = random.choice(templates)
        
        result = TweetTemplates.format_template(
            template,
            product_name=product_name,
            retailer=retailer,
            original_price=f"{original_price:.2f}",
            sale_price=f"{sale_price:.2f}",
            discount=discount,
            url=url
        )
        
        if result.get("error"):
            return GeneratedContent(
                content_type=ContentType.DEAL,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": result["error"]}
            )
        
        return GeneratedContent(
            content_type=ContentType.DEAL,
            text=result["content"],
            hashtags=result["hashtags"],
            full_tweet=result["full_tweet"],
            length=result["length"],
            is_valid=result["valid"],
            metadata={
                "product_name": product_name,
                "retailer": retailer,
                "original_price": original_price,
                "sale_price": sale_price,
                "discount": discount,
                "url": url
            },
            source="template"
        )
    
    def generate_market_tweet(
        self,
        card_name: str,
        current_price: float,
        psa10_price: float,
        trend_percent: float,
        analysis: str = ""
    ) -> GeneratedContent:
        """Generate a market update tweet."""
        trend_direction = "Up" if trend_percent > 0 else "Down"
        trend_emoji = "📈" if trend_percent > 0 else "📉"
        
        templates = TweetTemplates.get_templates("market")
        template = random.choice(templates)
        
        result = TweetTemplates.format_template(
            template,
            card_name=card_name,
            current_price=f"{current_price:.2f}",
            psa10_price=f"{psa10_price:.2f}",
            trend_percent=f"{abs(trend_percent):.1f}",
            trend_direction=trend_direction,
            trend_emoji=trend_emoji,
            analysis=analysis or "Watch this one closely!"
        )
        
        if result.get("error"):
            return GeneratedContent(
                content_type=ContentType.MARKET,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": result["error"]}
            )
        
        return GeneratedContent(
            content_type=ContentType.MARKET,
            text=result["content"],
            hashtags=result["hashtags"],
            full_tweet=result["full_tweet"],
            length=result["length"],
            is_valid=result["valid"],
            metadata={
                "card_name": card_name,
                "current_price": current_price,
                "psa10_price": psa10_price,
                "trend_percent": trend_percent
            },
            source="template"
        )
    
    def generate_drop_tweet(
        self,
        product_name: str,
        release_date: str,
        msrp: float,
        description: str = ""
    ) -> GeneratedContent:
        """Generate an upcoming drop announcement tweet."""
        templates = TweetTemplates.get_templates("drop")
        template = random.choice(templates)
        
        result = TweetTemplates.format_template(
            template,
            product_name=product_name,
            release_date=release_date,
            msrp=f"{msrp:.2f}",
            description=description or "Get ready for this release!"
        )
        
        if result.get("error"):
            return GeneratedContent(
                content_type=ContentType.DROP,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": result["error"]}
            )
        
        return GeneratedContent(
            content_type=ContentType.DROP,
            text=result["content"],
            hashtags=result["hashtags"],
            full_tweet=result["full_tweet"],
            length=result["length"],
            is_valid=result["valid"],
            metadata={
                "product_name": product_name,
                "release_date": release_date,
                "msrp": msrp
            },
            source="template"
        )
    
    # =========================================================================
    # AI-Powered Generation
    # =========================================================================
    
    def generate_ai_tweet(
        self,
        content_type: ContentType,
        context: Dict[str, Any],
        tone: str = "exciting",
        include_hashtags: bool = True,
        max_length: int = 250
    ) -> GeneratedContent:
        """
        Generate a tweet using AI (OpenAI).
        
        Args:
            content_type: Type of content to generate
            context: Context data for generation
            tone: Tone of the tweet (exciting, informative, casual, urgent)
            include_hashtags: Whether to include hashtags
            max_length: Maximum character length (before hashtags)
            
        Returns:
            GeneratedContent with AI-generated tweet
        """
        if not HAS_OPENAI or not self.openai_api_key:
            return GeneratedContent(
                content_type=content_type,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": "OpenAI not available. Install openai package and set OPENAI_API_KEY."}
            )
        
        # Build the prompt based on content type
        prompt = self._build_ai_prompt(content_type, context, tone, max_length)
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a social media expert for Pokemon TCG content. "
                            "Generate engaging, concise tweets that drive engagement. "
                            "Use emojis strategically. Be authentic and enthusiastic. "
                            "Never exceed the character limit. Do not include hashtags in the response."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Clean up the response
            tweet_text = tweet_text.strip('"\'')
            
            # Get hashtags for this content type
            hashtags = TweetTemplates.get_hashtags(content_type.value, limit=3) if include_hashtags else []
            hashtag_str = " ".join(hashtags)
            
            full_tweet = f"{tweet_text}\n\n{hashtag_str}" if hashtags else tweet_text
            
            # Validate length
            is_valid = len(full_tweet) <= 280
            
            return GeneratedContent(
                content_type=content_type,
                text=tweet_text,
                hashtags=hashtags,
                full_tweet=full_tweet,
                length=len(full_tweet),
                is_valid=is_valid,
                metadata=context,
                source="ai"
            )
            
        except Exception as e:
            return GeneratedContent(
                content_type=content_type,
                text="",
                hashtags=[],
                full_tweet="",
                length=0,
                is_valid=False,
                metadata={"error": str(e)}
            )
    
    def _build_ai_prompt(
        self,
        content_type: ContentType,
        context: Dict,
        tone: str,
        max_length: int
    ) -> str:
        """Build the AI prompt based on content type."""
        tone_descriptions = {
            "exciting": "exciting and energetic with enthusiasm",
            "informative": "informative and helpful with clear facts",
            "casual": "casual and friendly like talking to a fellow collector",
            "urgent": "urgent with a sense of FOMO (fear of missing out)"
        }
        
        tone_desc = tone_descriptions.get(tone, tone_descriptions["exciting"])
        
        prompts = {
            ContentType.RESTOCK: f"""
Generate a tweet about a Pokemon TCG restock alert.
Product: {context.get('product_name', 'Pokemon TCG Product')}
Retailer: {context.get('retailer', 'Major Retailer')}
Price: ${context.get('price', 'N/A')}
URL: {context.get('url', '')}

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags.
""",
            ContentType.DEAL: f"""
Generate a tweet about a Pokemon TCG deal/sale.
Product: {context.get('product_name', 'Pokemon TCG Product')}
Retailer: {context.get('retailer', 'Major Retailer')}
Original Price: ${context.get('original_price', 'N/A')}
Sale Price: ${context.get('sale_price', 'N/A')}
Discount: {context.get('discount', 'N/A')}%

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags.
""",
            ContentType.MARKET: f"""
Generate a tweet about Pokemon TCG market/price trends.
Card: {context.get('card_name', 'Pokemon Card')}
Current Price: ${context.get('current_price', 'N/A')}
PSA 10 Price: ${context.get('psa10_price', 'N/A')}
Trend: {context.get('trend_percent', 0)}% {'up' if context.get('trend_percent', 0) > 0 else 'down'}

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags.
""",
            ContentType.NEWS: f"""
Generate a tweet about Pokemon TCG news.
Topic: {context.get('topic', 'Pokemon TCG News')}
Details: {context.get('details', '')}

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags.
""",
            ContentType.ENGAGEMENT: f"""
Generate an engaging Pokemon TCG community tweet.
Topic: {context.get('topic', 'What are you collecting?')}
Goal: Get replies and engagement from collectors

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags. Ask a question or create discussion.
""",
            ContentType.GENERAL: f"""
Generate a tweet about Pokemon TCG.
Topic: {context.get('topic', 'Pokemon TCG')}
Details: {context.get('details', '')}

Tone: {tone_desc}
Max length: {max_length} characters
Do NOT include hashtags.
"""
        }
        
        return prompts.get(content_type, prompts[ContentType.GENERAL])
    
    def generate_thread(
        self,
        topic: str,
        points: List[str],
        use_ai: bool = True
    ) -> List[GeneratedContent]:
        """
        Generate a thread of tweets on a topic.
        
        Args:
            topic: Main topic for the thread
            points: Key points to cover (one per tweet)
            use_ai: Whether to use AI for generation
            
        Returns:
            List of GeneratedContent for each tweet in thread
        """
        thread = []
        
        # First tweet introduces the topic
        first_tweet_context = {
            "topic": f"🧵 Thread: {topic}",
            "details": "Introduction to start a thread"
        }
        
        if use_ai and HAS_OPENAI and self.openai_api_key:
            intro = self.generate_ai_tweet(
                ContentType.GENERAL,
                first_tweet_context,
                tone="exciting",
                include_hashtags=True
            )
        else:
            intro = GeneratedContent(
                content_type=ContentType.GENERAL,
                text=f"🧵 Thread: {topic}\n\nLet me break this down for you 👇",
                hashtags=TweetTemplates.get_hashtags("general"),
                full_tweet=f"🧵 Thread: {topic}\n\nLet me break this down for you 👇\n\n" + " ".join(TweetTemplates.get_hashtags("general")),
                length=0,
                is_valid=True,
                source="template"
            )
            intro.length = len(intro.full_tweet)
        
        thread.append(intro)
        
        # Generate tweets for each point
        for i, point in enumerate(points, 1):
            point_context = {
                "topic": f"{i}/ {point}",
                "details": f"Point {i} of {len(points)} in the thread"
            }
            
            if use_ai and HAS_OPENAI and self.openai_api_key:
                tweet = self.generate_ai_tweet(
                    ContentType.GENERAL,
                    point_context,
                    tone="informative",
                    include_hashtags=False
                )
            else:
                tweet = GeneratedContent(
                    content_type=ContentType.GENERAL,
                    text=f"{i}/ {point}",
                    hashtags=[],
                    full_tweet=f"{i}/ {point}",
                    length=len(f"{i}/ {point}"),
                    is_valid=True,
                    source="template"
                )
            
            thread.append(tweet)
        
        return thread
    
    # =========================================================================
    # Posting Functions
    # =========================================================================
    
    def post(self, content: GeneratedContent) -> PostResult:
        """
        Post generated content to X.
        
        Args:
            content: Generated content to post
            
        Returns:
            PostResult with posting details
        """
        if not content.is_valid:
            return PostResult(
                success=False,
                error=f"Content is not valid: {content.metadata.get('error', 'Unknown error')}"
            )
        
        result = self.x_client.post_tweet(content.full_tweet)
        
        if result.success:
            self._posted_history.append({
                "content": content.full_tweet,
                "type": content.content_type.value,
                "tweet_id": result.tweet_id,
                "posted_at": datetime.utcnow().isoformat()
            })
            self._generation_stats["total_posted"] += 1
        
        return result
    
    def post_thread(self, thread: List[GeneratedContent]) -> List[PostResult]:
        """
        Post a thread of tweets.
        
        Args:
            thread: List of generated content for thread
            
        Returns:
            List of PostResults for each tweet
        """
        tweet_texts = [t.full_tweet for t in thread if t.is_valid]
        return self.x_client.create_thread(tweet_texts)
    
    def generate_and_post(
        self,
        content_type: ContentType,
        use_ai: bool = False,
        **kwargs
    ) -> PostResult:
        """
        Generate content and immediately post it.
        
        Args:
            content_type: Type of content
            use_ai: Whether to use AI generation
            **kwargs: Arguments for content generation
            
        Returns:
            PostResult from posting
        """
        # Generate content based on type
        if use_ai and HAS_OPENAI and self.openai_api_key:
            content = self.generate_ai_tweet(content_type, kwargs)
        else:
            generators = {
                ContentType.RESTOCK: lambda: self.generate_restock_tweet(
                    kwargs.get("product_name", ""),
                    kwargs.get("retailer", ""),
                    kwargs.get("price", 0),
                    kwargs.get("url", "")
                ),
                ContentType.DEAL: lambda: self.generate_deal_tweet(
                    kwargs.get("product_name", ""),
                    kwargs.get("retailer", ""),
                    kwargs.get("original_price", 0),
                    kwargs.get("sale_price", 0),
                    kwargs.get("url", "")
                ),
                ContentType.MARKET: lambda: self.generate_market_tweet(
                    kwargs.get("card_name", ""),
                    kwargs.get("current_price", 0),
                    kwargs.get("psa10_price", 0),
                    kwargs.get("trend_percent", 0),
                    kwargs.get("analysis", "")
                ),
                ContentType.DROP: lambda: self.generate_drop_tweet(
                    kwargs.get("product_name", ""),
                    kwargs.get("release_date", ""),
                    kwargs.get("msrp", 0),
                    kwargs.get("description", "")
                ),
            }
            
            generator = generators.get(content_type)
            if generator:
                content = generator()
            else:
                return PostResult(success=False, error=f"No template generator for {content_type.value}")
        
        self._generation_stats["total_generated"] += 1
        self._generation_stats["by_type"][content_type.value] = \
            self._generation_stats["by_type"].get(content_type.value, 0) + 1
        
        return self.post(content)
    
    # =========================================================================
    # Scheduling Functions
    # =========================================================================
    
    def schedule_tweet(
        self,
        content: GeneratedContent,
        scheduled_time: datetime
    ) -> ScheduledTweet:
        """
        Schedule a tweet for future posting.
        
        Args:
            content: Generated content to schedule
            scheduled_time: When to post
            
        Returns:
            ScheduledTweet object
        """
        scheduled = ScheduledTweet(
            id=f"sched_{len(self._scheduled_queue)}_{datetime.utcnow().timestamp()}",
            content=content,
            scheduled_time=scheduled_time
        )
        self._scheduled_queue.append(scheduled)
        return scheduled
    
    def get_scheduled_tweets(self) -> List[ScheduledTweet]:
        """Get all scheduled tweets."""
        return self._scheduled_queue.copy()
    
    def cancel_scheduled_tweet(self, tweet_id: str) -> bool:
        """Cancel a scheduled tweet by ID."""
        for i, tweet in enumerate(self._scheduled_queue):
            if tweet.id == tweet_id:
                self._scheduled_queue.pop(i)
                return True
        return False
    
    async def process_scheduled_queue(self):
        """Process the scheduled queue and post due tweets."""
        now = datetime.utcnow()
        
        for scheduled in self._scheduled_queue:
            if not scheduled.posted and scheduled.scheduled_time <= now:
                result = self.post(scheduled.content)
                scheduled.posted = True
                scheduled.post_result = result
    
    # =========================================================================
    # Analytics & Stats
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get generation statistics."""
        return {
            **self._generation_stats,
            "scheduled_pending": len([t for t in self._scheduled_queue if not t.posted]),
            "history_count": len(self._posted_history)
        }
    
    def get_post_history(self, limit: int = 50) -> List[Dict]:
        """Get recent post history."""
        return self._posted_history[-limit:]
    
    def verify_credentials(self) -> Dict:
        """Verify X API credentials."""
        return self.x_client.verify_credentials()


# Convenience function for quick generation
def generate_tweet(
    content_type: str,
    use_ai: bool = False,
    **kwargs
) -> GeneratedContent:
    """
    Quick function to generate a tweet.
    
    Args:
        content_type: Type string (restock, deal, market, drop, etc.)
        use_ai: Whether to use AI generation
        **kwargs: Content-specific arguments
        
    Returns:
        GeneratedContent
    """
    generator = XContentGenerator()
    ct = ContentType(content_type) if content_type in [e.value for e in ContentType] else ContentType.GENERAL
    
    if use_ai:
        return generator.generate_ai_tweet(ct, kwargs)
    else:
        generators = {
            "restock": lambda: generator.generate_restock_tweet(
                kwargs.get("product_name", ""),
                kwargs.get("retailer", ""),
                kwargs.get("price", 0),
                kwargs.get("url", "")
            ),
            "deal": lambda: generator.generate_deal_tweet(
                kwargs.get("product_name", ""),
                kwargs.get("retailer", ""),
                kwargs.get("original_price", 0),
                kwargs.get("sale_price", 0),
                kwargs.get("url", "")
            ),
            "market": lambda: generator.generate_market_tweet(
                kwargs.get("card_name", ""),
                kwargs.get("current_price", 0),
                kwargs.get("psa10_price", 0),
                kwargs.get("trend_percent", 0),
                kwargs.get("analysis", "")
            ),
            "drop": lambda: generator.generate_drop_tweet(
                kwargs.get("product_name", ""),
                kwargs.get("release_date", ""),
                kwargs.get("msrp", 0),
                kwargs.get("description", "")
            ),
        }
        
        gen = generators.get(content_type)
        if gen:
            return gen()
        
        return generator.generate_ai_tweet(ct, kwargs) if use_ai else GeneratedContent(
            content_type=ct,
            text="",
            hashtags=[],
            full_tweet="",
            length=0,
            is_valid=False,
            metadata={"error": f"No template generator for {content_type}"}
        )
