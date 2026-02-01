"""
Tweet templates for different content types.
Provides pre-built templates and hashtag suggestions for Pokemon TCG content.
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class TweetTemplate:
    """A tweet template with placeholders."""
    template: str
    hashtags: List[str]
    content_type: str
    max_length: int = 280


class TweetTemplates:
    """Collection of tweet templates for Pokemon TCG content."""
    
    # Common hashtags
    COMMON_HASHTAGS = [
        "#PokemonTCG",
        "#Pokemon",
        "#TCG",
        "#PokemonCards"
    ]
    
    RESTOCK_HASHTAGS = [
        "#PokemonRestock",
        "#TCGRestock",
        "#InStock",
        "#PokemonAlert"
    ]
    
    DEAL_HASHTAGS = [
        "#PokemonDeal",
        "#TCGDeal",
        "#PokemonSale",
        "#CardDeals"
    ]
    
    MARKET_HASHTAGS = [
        "#PokemonInvesting",
        "#TCGMarket",
        "#CardMarket",
        "#PokemonPrices"
    ]
    
    # Template collections
    RESTOCK_TEMPLATES = [
        TweetTemplate(
            template="🚨 RESTOCK ALERT! {product_name} is now IN STOCK at {retailer}!\n\n💰 ${price}\n🔗 {url}\n\nAct fast - these sell out quick!",
            hashtags=RESTOCK_HASHTAGS + ["#PokemonTCG"],
            content_type="restock"
        ),
        TweetTemplate(
            template="⚡ {product_name} just dropped at {retailer}!\n\nPrice: ${price}\nLink: {url}\n\n🏃 Go go go!",
            hashtags=RESTOCK_HASHTAGS + ["#Pokemon"],
            content_type="restock"
        ),
        TweetTemplate(
            template="🎴 LIVE NOW: {product_name}\n\n📍 {retailer}\n💵 ${price}\n\n{url}\n\nDon't sleep on this one!",
            hashtags=RESTOCK_HASHTAGS + ["#TCG"],
            content_type="restock"
        ),
        TweetTemplate(
            template="🔥 {retailer} just restocked {product_name}!\n\n${price} - Link below 👇\n{url}",
            hashtags=RESTOCK_HASHTAGS,
            content_type="restock"
        ),
    ]
    
    DEAL_TEMPLATES = [
        TweetTemplate(
            template="💰 DEAL ALERT!\n\n{product_name} is {discount}% OFF at {retailer}!\n\nWas: ${original_price}\nNow: ${sale_price}\n\n🔗 {url}",
            hashtags=DEAL_HASHTAGS + ["#PokemonTCG"],
            content_type="deal"
        ),
        TweetTemplate(
            template="🏷️ Price Drop! {product_name}\n\n{retailer}: ${sale_price} (was ${original_price})\nSave {discount}%!\n\n{url}",
            hashtags=DEAL_HASHTAGS + ["#Pokemon"],
            content_type="deal"
        ),
        TweetTemplate(
            template="⬇️ {product_name} dropped to ${sale_price}!\n\nThat's {discount}% off at {retailer}\n\nGrab it: {url}",
            hashtags=DEAL_HASHTAGS,
            content_type="deal"
        ),
    ]
    
    MARKET_TEMPLATES = [
        TweetTemplate(
            template="📊 Market Update: {card_name}\n\n📈 Current: ${current_price}\n{trend_emoji} {trend_direction}: {trend_percent}%\n\nPSA 10: ${psa10_price}\n\n{analysis}",
            hashtags=MARKET_HASHTAGS + ["#PokemonTCG"],
            content_type="market"
        ),
        TweetTemplate(
            template="💹 {card_name} Price Watch\n\nRaw: ${current_price}\nPSA 10: ${psa10_price}\n\n{trend_emoji} {trend_percent}% this week\n\n{analysis}",
            hashtags=MARKET_HASHTAGS + ["#Pokemon"],
            content_type="market"
        ),
    ]
    
    DROP_TEMPLATES = [
        TweetTemplate(
            template="📅 UPCOMING DROP!\n\n{product_name}\n📆 Release: {release_date}\n💵 MSRP: ${msrp}\n\n{description}\n\nSet your alarms! ⏰",
            hashtags=["#PokemonTCG", "#NewRelease", "#Pokemon", "#TCG"],
            content_type="drop"
        ),
        TweetTemplate(
            template="🆕 Mark your calendars!\n\n{product_name} drops {release_date}\n\nMSRP: ${msrp}\n\n{description}",
            hashtags=["#PokemonTCG", "#Upcoming", "#Pokemon"],
            content_type="drop"
        ),
    ]
    
    GRADING_TEMPLATES = [
        TweetTemplate(
            template="🔍 Card Grading Tip:\n\n{tip}\n\nAlways check:\n✅ Centering\n✅ Corners\n✅ Surface\n✅ Edges\n\nWhat grade would you give this? 👀",
            hashtags=["#CardGrading", "#PSA", "#CGC", "#PokemonTCG"],
            content_type="grading"
        ),
    ]
    
    GENERAL_TEMPLATES = [
        TweetTemplate(
            template="{content}",
            hashtags=COMMON_HASHTAGS,
            content_type="general"
        ),
    ]
    
    @classmethod
    def get_templates(cls, content_type: str) -> List[TweetTemplate]:
        """Get templates for a specific content type."""
        template_map = {
            "restock": cls.RESTOCK_TEMPLATES,
            "deal": cls.DEAL_TEMPLATES,
            "market": cls.MARKET_TEMPLATES,
            "drop": cls.DROP_TEMPLATES,
            "grading": cls.GRADING_TEMPLATES,
            "general": cls.GENERAL_TEMPLATES,
        }
        return template_map.get(content_type, cls.GENERAL_TEMPLATES)
    
    @classmethod
    def get_hashtags(cls, content_type: str, limit: int = 4) -> List[str]:
        """Get relevant hashtags for content type."""
        hashtag_map = {
            "restock": cls.RESTOCK_HASHTAGS,
            "deal": cls.DEAL_HASHTAGS,
            "market": cls.MARKET_HASHTAGS,
            "drop": ["#PokemonTCG", "#NewRelease", "#Pokemon"],
            "grading": ["#CardGrading", "#PSA", "#PokemonTCG"],
            "general": cls.COMMON_HASHTAGS,
        }
        hashtags = hashtag_map.get(content_type, cls.COMMON_HASHTAGS)
        return hashtags[:limit]
    
    @classmethod
    def format_template(cls, template: TweetTemplate, **kwargs) -> Dict:
        """Format a template with provided values."""
        try:
            content = template.template.format(**kwargs)
            hashtags = template.hashtags[:4]  # Limit hashtags
            hashtag_str = " ".join(hashtags)
            
            # Check if content + hashtags fits in tweet
            full_tweet = f"{content}\n\n{hashtag_str}"
            if len(full_tweet) > 280:
                # Trim hashtags if needed
                while len(full_tweet) > 280 and hashtags:
                    hashtags.pop()
                    hashtag_str = " ".join(hashtags)
                    full_tweet = f"{content}\n\n{hashtag_str}"
            
            return {
                "content": content,
                "hashtags": hashtags,
                "full_tweet": full_tweet,
                "length": len(full_tweet),
                "valid": len(full_tweet) <= 280
            }
        except KeyError as e:
            return {
                "error": f"Missing template variable: {e}",
                "content": None,
                "valid": False
            }
