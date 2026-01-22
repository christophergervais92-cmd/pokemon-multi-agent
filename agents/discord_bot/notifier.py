#!/usr/bin/env python3
"""
Discord Notifier Service

Sends personalized deal alerts to users based on their watchlists.
Can be called by the main agent server when deals are found.
"""
import os
import sys
import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import discord
from discord import Webhook
import aiohttp

# Add parent to path
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from user_db import (
    get_user, get_users_watching, get_all_users_with_autobuy,
    get_payment_info, log_purchase, get_watchlist
)

# Configuration
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


async def send_webhook_message(content: str = None, embed: dict = None):
    """Send a message via Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(DISCORD_WEBHOOK_URL, session=session)
        
        discord_embed = None
        if embed:
            discord_embed = discord.Embed.from_dict(embed)
        
        await webhook.send(content=content, embed=discord_embed)
        return True


async def send_dm_to_user(user_id: str, content: str = None, embed: dict = None):
    """Send a DM to a specific user."""
    if not DISCORD_BOT_TOKEN:
        return False
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        try:
            user = await client.fetch_user(int(user_id))
            dm_channel = await user.create_dm()
            
            discord_embed = None
            if embed:
                discord_embed = discord.Embed.from_dict(embed)
            
            await dm_channel.send(content=content, embed=discord_embed)
        except Exception as e:
            print(f"Failed to DM user {user_id}: {e}")
        finally:
            await client.close()
    
    await client.start(DISCORD_BOT_TOKEN)
    return True


def build_deal_embed(product: Dict[str, Any], is_personalized: bool = False) -> dict:
    """Build a Discord embed for a deal alert."""
    embed = {
        "title": "🔥 DEAL ALERT!" if not is_personalized else "🎯 WATCHLIST MATCH!",
        "color": 0xFF6B35 if not is_personalized else 0x00D166,
        "fields": [
            {
                "name": "📦 Product",
                "value": product.get("name", "Unknown"),
                "inline": False
            },
            {
                "name": "🏪 Retailer",
                "value": product.get("retailer", "Unknown"),
                "inline": True
            },
            {
                "name": "💰 Price",
                "value": f"**${product.get('price', 0):.2f}**",
                "inline": True
            },
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add market comparison if available
    pricing = product.get("pricing", {})
    if pricing.get("market_price"):
        delta = pricing.get("delta_pct", 0) * 100
        embed["fields"].append({
            "name": "📈 Market Price",
            "value": f"${pricing['market_price']:.2f} ({delta:.1f}% {'below' if delta < 0 else 'above'})",
            "inline": True
        })
    
    # Add buy link
    url = product.get("url", "")
    if url:
        embed["fields"].append({
            "name": "🛒 BUY NOW",
            "value": f"[Click to Purchase]({url})",
            "inline": False
        })
        embed["url"] = url
    
    # Stock status
    if product.get("stock"):
        embed["fields"].append({
            "name": "✅ Status",
            "value": "IN STOCK",
            "inline": True
        })
    
    return embed


def build_purchase_embed(purchase: Dict[str, Any], user_name: str = None) -> dict:
    """Build a Discord embed for a purchase confirmation."""
    is_simulation = purchase.get("simulation", True)
    
    embed = {
        "title": "✅ AUTO-BUY EXECUTED!" if not is_simulation else "🔄 AUTO-BUY SIMULATED",
        "color": 0x00D166 if not is_simulation else 0xFFA500,
        "fields": [
            {
                "name": "📦 Product",
                "value": purchase.get("product", "Unknown"),
                "inline": False
            },
            {
                "name": "🏪 Retailer",
                "value": purchase.get("retailer", "Unknown"),
                "inline": True
            },
            {
                "name": "💰 Price",
                "value": f"${purchase.get('price', 0):.2f}",
                "inline": True
            },
            {
                "name": "🧾 Order ID",
                "value": purchase.get("purchase_id", "N/A"),
                "inline": True
            },
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_name:
        embed["fields"].insert(0, {
            "name": "👤 Buyer",
            "value": user_name,
            "inline": True
        })
    
    if is_simulation:
        embed["footer"] = {"text": "⚠️ Simulation mode - no actual purchase made"}
    
    return embed


async def notify_deal_to_watchers(product: Dict[str, Any]) -> List[str]:
    """
    Send deal notifications to all users watching this product.
    Returns list of notified user IDs.
    """
    product_name = product.get("name", "")
    notified_users = []
    
    # Find users watching this product
    watchers = get_users_watching(product_name)
    
    for watcher in watchers:
        discord_id = watcher.get("discord_id")
        target_price = watcher.get("target_price")
        
        # Check if price meets target
        current_price = product.get("price", 0)
        if target_price and current_price > target_price:
            continue  # Price too high for this user
        
        # Build personalized embed
        embed = build_deal_embed(product, is_personalized=True)
        embed["description"] = f"A product on your watchlist is available!"
        
        if target_price:
            embed["fields"].append({
                "name": "🎯 Your Target",
                "value": f"${target_price:.2f}",
                "inline": True
            })
        
        # Send DM
        try:
            await send_dm_to_user(discord_id, embed=embed)
            notified_users.append(discord_id)
        except Exception as e:
            print(f"Failed to notify {discord_id}: {e}")
    
    return notified_users


async def broadcast_deal(product: Dict[str, Any], channel_webhook: str = None):
    """Broadcast a deal to the public channel."""
    webhook_url = channel_webhook or DISCORD_WEBHOOK_URL
    
    if not webhook_url:
        return False
    
    embed = build_deal_embed(product)
    
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(webhook_url, session=session)
        discord_embed = discord.Embed.from_dict(embed)
        await webhook.send(embed=discord_embed)
        return True


# =============================================================================
# FLASK INTEGRATION
# =============================================================================

def notify_users_sync(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synchronous wrapper for notifying users.
    Called by the Flask server.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    results = {
        "broadcasts": 0,
        "personal_notifications": 0,
        "notified_users": [],
    }
    
    async def process_all():
        for product in products:
            # Broadcast to public channel
            if await broadcast_deal(product):
                results["broadcasts"] += 1
            
            # Notify individual watchers
            notified = await notify_deal_to_watchers(product)
            results["notified_users"].extend(notified)
            results["personal_notifications"] += len(notified)
    
    try:
        loop.run_until_complete(process_all())
    finally:
        loop.close()
    
    return results


if __name__ == "__main__":
    # Test
    test_product = {
        "name": "Pokemon Paldean Fates ETB",
        "retailer": "Target",
        "price": 49.99,
        "url": "https://www.target.com/test",
        "stock": True,
        "pricing": {
            "market_price": 69.99,
            "delta_pct": -0.285,
        }
    }
    
    result = notify_users_sync([test_product])
    print(json.dumps(result, indent=2))
