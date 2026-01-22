#!/usr/bin/env python3
"""
LO TCG (Locals Only TCG) - AI-Powered Discord Bot for TCG Stock Alerts

A high-speed Discord bot that provides:
- Stealth scanning of all major retailers (Target, Walmart, Best Buy, GameStop, Costco, Pokemon Center)
- ZIP code-based local inventory alerts
- AI card grading from photos
- Price trend sparklines
- Multi-channel notifications (SMS, Push, Email, Discord)
- Slash commands for user registration and settings
- Watchlist management
- Payment info storage (encrypted)
- Per-user auto-buy
- Real-time deal notifications

Run with: python3 bot.py
Requires: DISCORD_BOT_TOKEN environment variable
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import discord
from discord import app_commands
from discord.ext import commands, tasks

from user_db import (
    get_user, create_user, update_user_settings,
    save_payment_info, get_payment_info,
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    get_purchase_history, log_purchase,
    get_all_users_with_autobuy, get_users_watching,
    reset_daily_spend,
    set_user_location, get_user_location, get_users_with_location
)

# Bot configuration - Load from .env or environment
# Using the existing LO TCG bot token
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "1404800573206827139")
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")  # Optional: for faster command sync
DISCORD_ALERT_ROLES = os.environ.get("DISCORD_ALERT_ROLES", "").split(",") if os.environ.get("DISCORD_ALERT_ROLES") else []

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track monitored sets and alerts (imported from existing bot)
monitored_sets = {}
alert_history = set()
price_history = {}
last_prices = {}
product_status = {}
user_zip_codes = {}


# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    """Called when bot is ready."""
    print(f"🎴 LO TCG (Locals Only TCG) Bot logged in as {bot.user}")
    print(f"   Bot ID: {bot.user.id}")
    print(f"📡 Connected to {len(bot.guilds)} server(s)")
    print(f"⚡ Stealth scanning enabled with anti-detection")
    
    # Set bot activity
    activity = discord.Activity(type=discord.ActivityType.watching, name="for TCG stock alerts 🎴")
    await bot.change_presence(activity=activity)
    
    if DISCORD_CHANNEL_ID:
        channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
        if channel:
            print(f'   Monitoring channel: {channel.name}')
    else:
        print('   ⚠️  No channel ID configured')
    
    # Sync slash commands
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    # Start background tasks
    if not daily_reset.is_running():
        daily_reset.start()
    
    # Start stock monitor
    if not stock_monitor.is_running():
        stock_monitor.start()


@tasks.loop(hours=24)
async def daily_reset():
    """Reset daily spend limits at midnight."""
    reset_daily_spend()
    print("🔄 Daily spend limits reset")


@tasks.loop(minutes=1)
async def stock_monitor():
    """Background task to monitor stock across retailers."""
    if not monitored_sets:
        return
    
    try:
        import requests
        
        # Scan all retailers
        response = requests.post("http://127.0.0.1:5001/scanner/unified", timeout=60)
        if response.status_code != 200:
            return
        
        data = response.json()
        products = data.get("products", [])
        
        # Check for matches with monitored sets
        for set_name in monitored_sets:
            matching = [p for p in products if set_name.lower() in p.get("name", "").lower()]
            
            for product in matching:
                product_key = f"{product.get('retailer')}_{product.get('name')}"
                
                # Check if in stock and not already alerted
                if product.get("stock") and product_key not in alert_history:
                    alert_history.add(product_key)
                    
                    # Send alert
                    if DISCORD_CHANNEL_ID:
                        channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
                        if channel:
                            embed = discord.Embed(
                                title="🔥 STOCK ALERT!",
                                description=f"**{product.get('name')}** is IN STOCK!",
                                color=discord.Color.green()
                            )
                            embed.add_field(name="🏪 Retailer", value=product.get("retailer", "Unknown"), inline=True)
                            embed.add_field(name="💰 Price", value=f"${product.get('price', 'N/A')}", inline=True)
                            
                            if product.get("url"):
                                embed.add_field(name="🛒 Buy Now", value=f"[Click Here]({product['url']})", inline=False)
                            
                            # Ping roles if configured
                            mention_text = ""
                            if DISCORD_ALERT_ROLES:
                                mention_text = " ".join([f"<@&{role.strip()}>" for role in DISCORD_ALERT_ROLES if role.strip()])
                            
                            await channel.send(content=mention_text, embed=embed)
    
    except Exception as e:
        print(f"Stock monitor error: {e}")


# =============================================================================
# LEGACY COMMANDS (! prefix) - Compatible with existing LO TCG bot
# =============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test command to check if bot is responding"""
    await ctx.send('🏓 Pong! LO TCG Bot is online!')
    
    # Show configured roles if any
    if DISCORD_ALERT_ROLES:
        role_list = []
        for role_id in DISCORD_ALERT_ROLES:
            role_id = role_id.strip()
            if not role_id:
                continue
            try:
                role = ctx.guild.get_role(int(role_id)) or discord.utils.get(ctx.guild.roles, name=role_id)
                if role:
                    role_list.append(role.mention)
            except (ValueError, AttributeError):
                pass
        
        if role_list:
            await ctx.send(f"📢 Alert roles configured: {', '.join(role_list)}")


@bot.command(name='monitor')
async def monitor_set(ctx, *, set_name: str = None):
    """
    Start monitoring a Pokemon or TCG set for stock alerts
    
    Usage: 
        !monitor Paldean Fates
        !monitor Pokemon 151
    """
    if not set_name:
        await ctx.send('❌ Please provide a set name. Examples:\n`!monitor Paldean Fates`\n`!monitor Pokemon 151`')
        return
    
    monitored_sets[set_name.lower()] = {
        "added_by": ctx.author.name,
        "added_at": datetime.now().isoformat(),
    }
    
    embed = discord.Embed(
        title="🎴 Set Monitoring Started",
        description=f"Now monitoring **{set_name}** for stock alerts",
        color=discord.Color.green()
    )
    embed.add_field(name="Added by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Status", value="🟢 Active", inline=True)
    embed.set_footer(text="You'll receive alerts for stock, price drops, and best deals!")
    
    await ctx.send(embed=embed)


@bot.command(name='unmonitor')
async def unmonitor_set(ctx, *, set_name: str = None):
    """Stop monitoring a set"""
    if not set_name:
        await ctx.send('❌ Please provide a set name to stop monitoring.')
        return
    
    if set_name.lower() in monitored_sets:
        del monitored_sets[set_name.lower()]
        await ctx.send(f'✅ Stopped monitoring **{set_name}**')
    else:
        await ctx.send(f'❌ **{set_name}** is not being monitored')


@bot.command(name='list')
async def list_monitored(ctx):
    """List all currently monitored sets"""
    if not monitored_sets:
        await ctx.send('📋 No sets are currently being monitored.\nUse `!monitor <set name>` to start monitoring.')
        return
    
    embed = discord.Embed(
        title="📋 Monitored Sets",
        description=f"**Total:** {len(monitored_sets)} set(s) being monitored",
        color=discord.Color.blue()
    )
    
    for set_name, info in monitored_sets.items():
        embed.add_field(
            name=f"🎴 {set_name.title()}",
            value=f"Added by: {info['added_by']}\nStatus: 🟢 Active",
            inline=False
        )
    
    await ctx.send(embed=embed)


@bot.command(name='check')
async def check_stock(ctx, *, query: str = None):
    """
    Manually check for stock of Pokemon products
    
    Usage: 
        !check Paldean Fates booster box (all retailers)
        !check target Paldean Fates (Target only)
        !check walmart Pokemon 151 (Walmart only)
    """
    if not query:
        await ctx.send('❌ Please provide a search query. Examples:\n`!check Paldean Fates booster box`\n`!check target Paldean Fates`')
        return
    
    await ctx.send(f'🔍 Checking stock for **{query}**... (this may take a moment)')
    
    try:
        import requests
        
        # Scan all retailers
        response = requests.post("http://127.0.0.1:5001/scanner/unified", timeout=60)
        if response.status_code != 200:
            await ctx.send("❌ Error scanning retailers. Is the server running?")
            return
        
        data = response.json()
        products = data.get("products", [])
        
        # Filter by query
        query_lower = query.lower()
        matching = [p for p in products if query_lower in p.get("name", "").lower()]
        
        if not matching:
            await ctx.send(f"❌ No products found matching **{query}**")
            return
        
        # Build response
        embed = discord.Embed(
            title=f"🔍 Stock Check: {query}",
            description=f"Found {len(matching)} product(s)",
            color=discord.Color.blue()
        )
        
        in_stock = [p for p in matching if p.get("stock")]
        out_of_stock = [p for p in matching if not p.get("stock")]
        
        if in_stock:
            for product in in_stock[:5]:  # Limit to 5
                value = f"💰 ${product.get('price', 'N/A')}"
                if product.get("url"):
                    value += f"\n[Buy Now]({product['url']})"
                embed.add_field(
                    name=f"✅ {product.get('retailer', 'Unknown')} - IN STOCK",
                    value=value,
                    inline=True
                )
        
        if out_of_stock and len(in_stock) < 5:
            for product in out_of_stock[:3]:  # Limit to 3
                embed.add_field(
                    name=f"❌ {product.get('retailer', 'Unknown')} - Out of Stock",
                    value=f"${product.get('price', 'N/A')}",
                    inline=True
                )
        
        embed.set_footer(text=f"✅ {len(in_stock)} in stock | ❌ {len(out_of_stock)} out of stock")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='price')
async def check_price(ctx, *, card_name: str = None):
    """
    Check the price and trend for a card
    
    Usage: !price Charizard VMAX
    """
    if not card_name:
        await ctx.send('❌ Please provide a card name. Example: `!price Charizard VMAX`')
        return
    
    await ctx.send(f'📊 Getting price data for **{card_name}**...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.price_trends import PriceTrendAnalyzer
        
        analyzer = PriceTrendAnalyzer()
        trend = analyzer.get_trend(card_name, days=7)
        
        if "error" in trend:
            await ctx.send(f"❌ Could not find price data for **{card_name}**")
            return
        
        sign = "+" if trend['change'] >= 0 else ""
        
        embed = discord.Embed(
            title=f"{trend['trend_emoji']} {card_name}",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Current Price",
            value=f"**${trend['current_price']:.2f}**",
            inline=True
        )
        embed.add_field(
            name="📈 7-Day Change",
            value=f"{sign}${trend['change']:.2f} ({sign}{trend['change_pct']:.1f}%)",
            inline=True
        )
        embed.add_field(
            name="📊 Trend",
            value=f"`{trend['sparkline']}`",
            inline=False
        )
        embed.add_field(
            name="📉 7d Range",
            value=f"Low: ${trend['low']:.2f} | High: ${trend['high']:.2f}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='market')
async def market_report(ctx):
    """Get a market report with top gainers and losers"""
    await ctx.send('📊 Generating market report...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.price_trends import get_top_movers
        
        movers = get_top_movers(limit=5)
        
        embed = discord.Embed(
            title="📊 TCG Market Report",
            description="Top gainers and losers over the last 7 days",
            color=discord.Color.gold()
        )
        
        # Top gainers
        gainers_text = ""
        for i, g in enumerate(movers.get("gainers", [])[:5], 1):
            gainers_text += f"{i}. {g['trend_emoji']} **{g['card_name']}**\n"
            gainers_text += f"   ${g['current_price']:.2f} (+{g['change_pct']:.1f}%)\n"
        
        if gainers_text:
            embed.add_field(name="🚀 Top Gainers", value=gainers_text, inline=True)
        
        # Top losers
        losers_text = ""
        for i, l in enumerate(movers.get("losers", [])[:5], 1):
            losers_text += f"{i}. {l['trend_emoji']} **{l['card_name']}**\n"
            losers_text += f"   ${l['current_price']:.2f} ({l['change_pct']:.1f}%)\n"
        
        if losers_text:
            embed.add_field(name="📉 Top Losers", value=losers_text, inline=True)
        
        embed.set_footer(text=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='psa')
async def psa_prices(ctx, *, card_name: str = None):
    """
    Get PSA graded prices for a card
    
    Usage: !psa Charizard VMAX
    """
    if not card_name:
        await ctx.send('❌ Please provide a card name. Example: `!psa Charizard VMAX`')
        return
    
    await ctx.send(f'💰 Getting graded prices for **{card_name}**...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.graded_prices import get_card_prices
        
        prices = get_card_prices(card_name, include_ebay=False)
        
        if not prices.get("raw"):
            await ctx.send(f"❌ Could not find price data for **{card_name}**")
            return
        
        embed = discord.Embed(
            title=f"💰 {prices['card_name']}",
            description=f"**Set:** {prices.get('set_name', 'Unknown')}",
            color=discord.Color.gold()
        )
        
        # Set thumbnail if available
        if prices.get("image_url"):
            embed.set_thumbnail(url=prices["image_url"])
        
        # Raw price
        raw = prices["raw"]
        embed.add_field(
            name="📦 Raw (Ungraded)",
            value=f"**${raw['price']:.2f}**\n${raw['low']:.2f} - ${raw['high']:.2f}",
            inline=True
        )
        
        # PSA prices
        graded = prices.get("graded", {})
        psa_text = ""
        for grade in ["PSA 10", "PSA 9", "PSA 8", "PSA 7"]:
            if grade in graded:
                g = graded[grade]
                psa_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if psa_text:
            embed.add_field(name="🏆 PSA", value=psa_text, inline=True)
        
        # CGC prices
        cgc_text = ""
        for grade in ["CGC 10", "CGC 9.5", "CGC 9"]:
            if grade in graded:
                g = graded[grade]
                cgc_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if cgc_text:
            embed.add_field(name="🥇 CGC", value=cgc_text, inline=True)
        
        # BGS prices
        bgs_text = ""
        for grade in ["BGS 10 Black", "BGS 10", "BGS 9.5", "BGS 9"]:
            if grade in graded:
                g = graded[grade]
                bgs_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if bgs_text:
            embed.add_field(name="⭐ BGS", value=bgs_text, inline=True)
        
        # Add ROI calculation
        if raw['price'] > 0 and "PSA 10" in graded:
            psa10 = graded["PSA 10"]["price"]
            roi = ((psa10 - raw['price'] - 25) / raw['price']) * 100  # $25 grading cost
            roi_emoji = "🚀" if roi > 100 else "📈" if roi > 0 else "📉"
            embed.add_field(
                name="📊 PSA 10 ROI",
                value=f"{roi_emoji} **{roi:.0f}%** after grading",
                inline=False
            )
        
        embed.set_footer(text=f"Updated: {prices.get('last_updated', 'N/A')[:19]} | Source: {prices.get('source', 'TCGPlayer')}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='grade')
async def grade_card(ctx, *, image_url: str = None):
    """
    AI-grade a card from an image
    
    Usage: !grade <image_url>
    Or attach an image and use: !grade
    """
    # Get image URL from attachment if not provided
    if not image_url and ctx.message.attachments:
        image_url = ctx.message.attachments[0].url
    
    if not image_url:
        await ctx.send(
            "📸 **How to use !grade:**\n"
            "1. Attach an image: `!grade` with image attached\n"
            "2. Or provide URL: `!grade https://example.com/card.jpg`"
        )
        return
    
    await ctx.send(f'🔍 Analyzing card image...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from vision.card_scanner import CardScanner
        
        scanner = CardScanner()
        result = scanner.scan_card(image_url=image_url)
        
        if "error" in result and not result.get("demo_mode"):
            await ctx.send(f"❌ Could not analyze card: {result['error']}")
            return
        
        embed = discord.Embed(
            title=f"📸 {result.get('card_name', 'Unknown Card')}",
            description=f"**Set:** {result.get('set_name', 'Unknown')}\n**Number:** {result.get('card_number', 'N/A')}",
            color=discord.Color.gold()
        )
        
        # Set thumbnail
        if image_url:
            embed.set_thumbnail(url=image_url)
        
        # Pricing
        pricing = result.get("pricing", {})
        embed.add_field(
            name="💰 Pricing",
            value=(
                f"Raw: ${pricing.get('raw', 0):.2f}\n"
                f"PSA 9: ${pricing.get('psa_9', 0):.2f}\n"
                f"PSA 10: ${pricing.get('psa_10', 0):.2f}"
            ),
            inline=True
        )
        
        # Condition
        condition = result.get("condition", {})
        embed.add_field(
            name="🔍 Condition",
            value=(
                f"Centering: {condition.get('centering', 'N/A')}/10\n"
                f"Corners: {condition.get('corners', 'N/A')}/10\n"
                f"Edges: {condition.get('edges', 'N/A')}/10"
            ),
            inline=True
        )
        
        # Grade analysis
        grade_analysis = result.get("grade_analysis", {})
        embed.add_field(
            name="📊 Grade Estimate",
            value=(
                f"**PSA Grade:** {grade_analysis.get('estimated_grade', result.get('estimated_grade', 'N/A'))}\n"
                f"**Worth Grading:** {'✅ Yes' if grade_analysis.get('worth_grading') else '❌ No'}\n"
                f"**Profit Potential:** ${grade_analysis.get('potential_profit', 0):.2f}"
            ),
            inline=False
        )
        
        # Recommendation
        if grade_analysis.get("recommendation"):
            embed.add_field(
                name="💡 Recommendation",
                value=grade_analysis["recommendation"],
                inline=False
            )
        
        # Demo mode notice
        if result.get("demo_mode"):
            embed.set_footer(text="⚠️ Demo mode - Set AI API key for real analysis")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='flip')
async def flip_calculator(ctx, *, card_name: str = None):
    """
    Calculate if grading a card is profitable
    
    Usage: !flip Charizard VMAX
    """
    if not card_name:
        await ctx.send(
            '🔄 **Flip Calculator**\n'
            'Calculate if grading a card is worth it!\n\n'
            '**Usage:** `!flip <card name>`\n'
            '**Example:** `!flip Charizard VMAX`'
        )
        return
    
    await ctx.send(f'📊 Calculating flip profitability for **{card_name}**...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.flip_calculator import calculate_flip, format_flip_discord
        
        result = calculate_flip(card_name)
        
        # Create embed
        embed = discord.Embed(
            title=f"🔄 Flip Calculator - {result['card_name']}",
            description=f"**Is grading this card profitable?**",
            color=discord.Color.gold() if result['expected_profit'] > 0 else discord.Color.red()
        )
        
        # Cost breakdown
        embed.add_field(
            name="💵 Cost Analysis",
            value=(
                f"**Raw Price:** ${result['raw_price']}\n"
                f"**Grading:** ${result['grading_cost']} ({result['grading_company']} {result['grading_tier']})\n"
                f"**Shipping:** ${result['shipping_cost']}\n"
                f"**Total Cost:** ${result['total_cost']}"
            ),
            inline=False
        )
        
        # Grade scenarios
        scenarios_text = ""
        for s in result['scenarios'][:4]:
            profit_str = f"+${s['profit']}" if s['profit'] >= 0 else f"-${abs(s['profit'])}"
            scenarios_text += f"{s['emoji']} **{s['grade']}:** ${s['graded_value']} → {profit_str} ({s['roi_percent']}% ROI)\n"
        
        embed.add_field(
            name="📈 Grade Scenarios",
            value=scenarios_text,
            inline=False
        )
        
        # Expected value
        ev_emoji = "🚀" if result['expected_roi'] > 50 else "✅" if result['expected_roi'] > 0 else "❌"
        embed.add_field(
            name="📊 Expected Value",
            value=(
                f"**EV:** ${result['expected_value']}\n"
                f"**Expected Profit:** ${result['expected_profit']}\n"
                f"**Expected ROI:** {ev_emoji} {result['expected_roi']}%"
            ),
            inline=True
        )
        
        # Break-even
        embed.add_field(
            name="⚖️ Break-Even",
            value=f"Must grade **{result['break_even_grade']}** or higher",
            inline=True
        )
        
        # Recommendation
        embed.add_field(
            name="💡 Recommendation",
            value=result['recommendation'],
            inline=False
        )
        
        embed.set_footer(text=f"Confidence: {result['confidence']} | {result['calculated_at'][:16]}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='stockmap', aliases=['map', 'nearby'])
async def stock_map(ctx, zip_code: str = None, *, query: str = "pokemon"):
    """
    Find Pokemon TCG stock at nearby stores
    
    Usage: !stockmap <zip_code> [query]
    Example: !stockmap 90210 pokemon etb
    """
    if not zip_code:
        # Try to get user's saved location
        user = get_user(str(ctx.author.id))
        if user and user.get('zip_code'):
            zip_code = user['zip_code']
        else:
            await ctx.send(
                '🗺️ **Local Stock Map**\n'
                'Find Pokemon stock near you!\n\n'
                '**Usage:** `!stockmap <zip_code> [query]`\n'
                '**Example:** `!stockmap 90210 pokemon etb`\n\n'
                '_Tip: Use `/setlocation` to save your ZIP code!_'
            )
            return
    
    await ctx.send(f'🗺️ Scanning stores near **{zip_code}** for **{query}**...')
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.stock_map import get_stock_map, STORE_CHAINS
        
        result = get_stock_map(zip_code, 25, query)
        
        # Create embed
        embed = discord.Embed(
            title=f"🗺️ Pokemon Stock Map - {zip_code}",
            description=f"🔍 Search: **{query}**\n📍 Radius: 25 miles",
            color=discord.Color.green() if result['stores_with_stock'] > 0 else discord.Color.red()
        )
        
        # Summary
        embed.add_field(
            name="📊 Summary",
            value=(
                f"**Stores with stock:** {result['stores_with_stock']}/{result['total_stores']}\n"
                f"**Total products found:** {result['total_products']}"
            ),
            inline=False
        )
        
        # In-stock stores
        in_stock = [s for s in result['stores'] if s['has_stock']]
        if in_stock:
            in_stock_text = ""
            for store in in_stock[:6]:
                chain_info = STORE_CHAINS.get(store['chain'], {})
                emoji = chain_info.get('emoji', '🏪')
                in_stock_text += f"{emoji} **{store['chain']}** ({store['distance_miles']} mi)\n"
                in_stock_text += f"   📦 {store['stock_count']} items\n"
                # Show first product
                if store['products']:
                    p = store['products'][0]
                    price = p.get('price', 0)
                    in_stock_text += f"   • {p.get('name', 'Unknown')[:40]}"
                    if price:
                        in_stock_text += f" - ${price}"
                    in_stock_text += "\n"
            
            embed.add_field(
                name="✅ In Stock",
                value=in_stock_text or "None found",
                inline=False
            )
        
        # Out of stock
        out_stock = [s for s in result['stores'] if not s['has_stock']][:5]
        if out_stock:
            out_text = ""
            for store in out_stock:
                chain_info = STORE_CHAINS.get(store['chain'], {})
                emoji = chain_info.get('emoji', '🏪')
                out_text += f"{emoji} {store['chain']} ({store['distance_miles']} mi)\n"
            
            embed.add_field(
                name="❌ Out of Stock",
                value=out_text,
                inline=False
            )
        
        embed.set_footer(text=f"Updated: {result['generated_at'][:16]}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='commands', aliases=['cmds'])
async def show_commands(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎴 LO TCG Bot - Commands",
        description="Your AI-powered TCG stock tracker!",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="📊 Stock & Monitoring",
        value=(
            "`!monitor <set>` - Start monitoring a set\n"
            "`!unmonitor <set>` - Stop monitoring\n"
            "`!list` - List monitored sets\n"
            "`!check <query>` - Check stock manually\n"
            "`!stockmap <zip>` - **🆕 Find nearby stock!**\n"
            "`!ping` - Check if bot is online"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💰 Price & Grading",
        value=(
            "`!price <card>` - Get price & trend\n"
            "`!psa <card>` - **Raw + PSA + CGC + BGS prices**\n"
            "`!flip <card>` - **🆕 Grading ROI calculator!**\n"
            "`!market` - Market report (gainers/losers)\n"
            "`!grade [url]` - AI grade a card photo"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 Slash Commands",
        value=(
            "`/register` - Create account\n"
            "`/settings` - View/change settings\n"
            "`/flip` - **🆕 Flip calculator**\n"
            "`/stockmap` - **🆕 Local stock map**\n"
            "`/scancard` - AI scan card photo\n"
            "`/gradeprices` - Raw + graded prices\n"
            "`/help` - Full command list"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)


# =============================================================================
# SLASH COMMANDS - REGISTRATION
# =============================================================================

@bot.tree.command(name="register", description="Register for Pokemon deal alerts and auto-buy")
async def register(interaction: discord.Interaction):
    """Register a new user."""
    discord_id = str(interaction.user.id)
    username = interaction.user.name
    
    existing = get_user(discord_id)
    if existing:
        await interaction.response.send_message(
            f"✅ You're already registered, {username}!\n"
            f"Use `/settings` to view your current settings.",
            ephemeral=True
        )
        return
    
    user = create_user(discord_id, username)
    
    embed = discord.Embed(
        title="🎴 Welcome to LO TCG!",
        description=f"You're now registered, {username}!\n\n⚡ **Features:**\n• Stealth scanning (anti-detection)\n• ZIP code local stock alerts\n• Auto-buy with your payment info",
        color=discord.Color.green()
    )
    embed.add_field(
        name="🔔 Notifications",
        value="Enabled (default)",
        inline=True
    )
    embed.add_field(
        name="🛒 Auto-Buy",
        value="Disabled (set up payment first)",
        inline=True
    )
    embed.add_field(
        name="💰 Daily Limit",
        value="$500 (default)",
        inline=True
    )
    embed.add_field(
        name="📝 Next Steps",
        value=(
            "• `/setlocation` - Set your zip code for local stock alerts\n"
            "• `/watchlist add` - Add items to watch\n"
            "• `/payment setup` - Set up auto-buy\n"
            "• `/settings` - View/change settings"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="settings", description="View or change your settings")
@app_commands.describe(
    notifications="Enable/disable deal notifications",
    autobuy="Enable/disable auto-buy",
    max_price="Maximum price per item ($)",
    daily_limit="Daily spending limit ($)"
)
async def settings(
    interaction: discord.Interaction,
    notifications: Optional[bool] = None,
    autobuy: Optional[bool] = None,
    max_price: Optional[float] = None,
    daily_limit: Optional[float] = None
):
    """View or update user settings."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    # Update settings if any provided
    updates = {}
    if notifications is not None:
        updates['notification_enabled'] = 1 if notifications else 0
    if autobuy is not None:
        updates['autobuy_enabled'] = 1 if autobuy else 0
    if max_price is not None:
        updates['max_price_limit'] = max_price
    if daily_limit is not None:
        updates['daily_spend_limit'] = daily_limit
    
    if updates:
        update_user_settings(discord_id, updates)
        user = get_user(discord_id)  # Refresh
    
    # Display current settings
    embed = discord.Embed(
        title="⚙️ Your Settings",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🔔 Notifications",
        value="✅ Enabled" if user['notification_enabled'] else "❌ Disabled",
        inline=True
    )
    embed.add_field(
        name="🛒 Auto-Buy",
        value="✅ Enabled" if user['autobuy_enabled'] else "❌ Disabled",
        inline=True
    )
    embed.add_field(
        name="💰 Max Price",
        value=f"${user['max_price_limit']:.2f}",
        inline=True
    )
    embed.add_field(
        name="📊 Daily Limit",
        value=f"${user['daily_spend_limit']:.2f}",
        inline=True
    )
    embed.add_field(
        name="💵 Spent Today",
        value=f"${user['daily_spent']:.2f}",
        inline=True
    )
    embed.add_field(
        name="⭐ Status",
        value="Premium" if user['is_premium'] else "Free",
        inline=True
    )
    
    if updates:
        embed.set_footer(text="✅ Settings updated!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =============================================================================
# SLASH COMMANDS - LOCATION
# =============================================================================

@bot.tree.command(name="setlocation", description="Set your ZIP code for local stock alerts")
@app_commands.describe(
    zip_code="Your 5-digit US ZIP code",
    radius="Search radius in miles (default: 25)",
    local_only="Only alert for local stock (skip online-only deals)"
)
async def setlocation(
    interaction: discord.Interaction,
    zip_code: str,
    radius: int = 25,
    local_only: bool = False
):
    """Set user's location for local inventory scanning."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    # Validate zip code
    if not zip_code.isdigit() or len(zip_code) != 5:
        await interaction.response.send_message(
            "❌ Invalid ZIP code. Please enter a 5-digit US ZIP code.",
            ephemeral=True
        )
        return
    
    # Validate radius
    if radius < 5:
        radius = 5
    elif radius > 100:
        radius = 100
    
    # Save location
    set_user_location(discord_id, zip_code, radius, local_only)
    
    embed = discord.Embed(
        title="📍 Location Set!",
        description=f"You'll now get alerts for stock near **{zip_code}**",
        color=discord.Color.green()
    )
    embed.add_field(name="🗺️ ZIP Code", value=zip_code, inline=True)
    embed.add_field(name="📏 Radius", value=f"{radius} miles", inline=True)
    embed.add_field(
        name="🎯 Alert Mode", 
        value="Local only" if local_only else "All deals + local", 
        inline=True
    )
    embed.add_field(
        name="🏪 Retailers Scanned",
        value="Target • Walmart • Best Buy • GameStop • Costco",
        inline=False
    )
    embed.set_footer(text="💡 Stock checks run every minute with stealth scanning")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="location", description="View your current location settings")
async def view_location(interaction: discord.Interaction):
    """View user's location settings."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    location = get_user_location(discord_id)
    
    if not location or not location.get("zip_code"):
        await interaction.response.send_message(
            "📍 No location set yet!\nUse `/setlocation <zip_code>` to enable local stock alerts.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="📍 Your Location Settings",
        color=discord.Color.blue()
    )
    embed.add_field(name="🗺️ ZIP Code", value=location["zip_code"], inline=True)
    embed.add_field(name="📏 Radius", value=f"{location['radius_miles']} miles", inline=True)
    embed.add_field(
        name="🎯 Alert Mode",
        value="Local only" if location["local_only"] else "All deals + local",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="scan", description="Manually trigger a stock scan for your location")
@app_commands.describe(
    search="Product to search for (e.g., 'pokemon 151')"
)
async def manual_scan(interaction: discord.Interaction, search: str = "pokemon"):
    """Manually trigger a local stock scan."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    location = get_user_location(discord_id)
    
    if not location or not location.get("zip_code"):
        await interaction.response.send_message(
            "📍 No location set! Use `/setlocation <zip_code>` first.",
            ephemeral=True
        )
        return
    
    # Defer response since scan takes time
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Import and run the local scanner
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from stealth.local_inventory import LocalInventoryScanner
        
        scanner = LocalInventoryScanner(
            zip_code=location["zip_code"],
            radius_miles=location["radius_miles"],
        )
        
        results = scanner.scan_all_retailers(search)
        
        # Build response
        embed = discord.Embed(
            title=f"🔍 Scan Results for '{search}'",
            description=f"📍 Near {location['zip_code']} ({location['radius_miles']} mi radius)",
            color=discord.Color.green() if results["total_in_stock"] > 0 else discord.Color.orange()
        )
        
        embed.add_field(
            name="📊 Summary",
            value=f"🏪 {results['total_stores_checked']} stores | 📦 {results['total_products_found']} products | ✅ {results['total_in_stock']} in stock",
            inline=False
        )
        
        # Add results per retailer
        for retailer, data in results.get("retailers", {}).items():
            in_stock = data.get("in_stock", 0)
            emoji = "✅" if in_stock > 0 else "❌"
            
            # Get first in-stock item if available
            stock_items = [r for r in data.get("results", []) if r.get("in_stock")]
            if stock_items:
                item = stock_items[0]
                value = f"{emoji} {in_stock} in stock\n${item['price']:.2f} - {item['distance_miles']:.1f} mi\n[Buy Now]({item['url']})"
            else:
                value = f"{emoji} No stock found"
            
            embed.add_field(name=f"🏬 {retailer}", value=value, inline=True)
        
        embed.set_footer(text="⚡ Stealth scan completed")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Scan failed: {str(e)}",
            ephemeral=True
        )


# =============================================================================
# SLASH COMMANDS - WATCHLIST
# =============================================================================

watchlist_group = app_commands.Group(name="watchlist", description="Manage your Pokemon watchlist")

@watchlist_group.command(name="add", description="Add an item to your watchlist")
@app_commands.describe(
    item_name="Name of the product (e.g., 'Paldean Fates ETB')",
    item_type="Type of item",
    target_price="Alert me when price drops below this",
    autobuy="Automatically buy when deal is found"
)
@app_commands.choices(item_type=[
    app_commands.Choice(name="Elite Trainer Box", value="etb"),
    app_commands.Choice(name="Booster Box", value="booster_box"),
    app_commands.Choice(name="Booster Pack", value="booster_pack"),
    app_commands.Choice(name="Collection Box", value="collection"),
    app_commands.Choice(name="Ultra Premium Collection", value="upc"),
    app_commands.Choice(name="Single Card", value="single"),
    app_commands.Choice(name="Graded Card (Slab)", value="slab"),
    app_commands.Choice(name="Any", value="any"),
])
async def watchlist_add(
    interaction: discord.Interaction,
    item_name: str,
    item_type: str = "any",
    target_price: Optional[float] = None,
    autobuy: bool = False
):
    """Add item to watchlist."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    watchlist_id = add_to_watchlist(
        discord_id=discord_id,
        item_type=item_type,
        item_name=item_name,
        target_price=target_price,
        notify_on_stock=True,
        autobuy_on_deal=autobuy
    )
    
    embed = discord.Embed(
        title="✅ Added to Watchlist",
        color=discord.Color.green()
    )
    embed.add_field(name="📦 Item", value=item_name, inline=False)
    embed.add_field(name="🏷️ Type", value=item_type, inline=True)
    embed.add_field(
        name="💰 Target Price",
        value=f"${target_price:.2f}" if target_price else "Any",
        inline=True
    )
    embed.add_field(
        name="🛒 Auto-Buy",
        value="✅ Yes" if autobuy else "❌ No",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@watchlist_group.command(name="view", description="View your watchlist")
async def watchlist_view(interaction: discord.Interaction):
    """View user's watchlist."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    watchlist = get_watchlist(discord_id)
    
    if not watchlist:
        await interaction.response.send_message(
            "📋 Your watchlist is empty!\nUse `/watchlist add` to add items.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="📋 Your Watchlist",
        color=discord.Color.blue()
    )
    
    for i, item in enumerate(watchlist[:10], 1):
        target = f"${item['target_price']:.2f}" if item['target_price'] else "Any"
        autobuy = "🛒" if item['autobuy_on_deal'] else ""
        embed.add_field(
            name=f"{i}. {item['item_name']} {autobuy}",
            value=f"Type: {item['item_type']} | Target: {target} | ID: {item['id']}",
            inline=False
        )
    
    if len(watchlist) > 10:
        embed.set_footer(text=f"Showing 10 of {len(watchlist)} items")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@watchlist_group.command(name="remove", description="Remove an item from your watchlist")
@app_commands.describe(item_id="The ID of the item to remove (from /watchlist view)")
async def watchlist_remove(interaction: discord.Interaction, item_id: int):
    """Remove item from watchlist."""
    discord_id = str(interaction.user.id)
    
    if remove_from_watchlist(discord_id, item_id):
        await interaction.response.send_message(
            f"✅ Removed item #{item_id} from your watchlist.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Item #{item_id} not found in your watchlist.",
            ephemeral=True
        )


bot.tree.add_command(watchlist_group)


# =============================================================================
# SLASH COMMANDS - PAYMENT
# =============================================================================

payment_group = app_commands.Group(name="payment", description="Manage payment info for auto-buy")

@payment_group.command(name="setup", description="Set up payment info for auto-buy (DM only for security)")
async def payment_setup(interaction: discord.Interaction):
    """Start payment setup flow (sends DM for security)."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    # Send setup instructions via DM for security
    try:
        dm_channel = await interaction.user.create_dm()
        
        embed = discord.Embed(
            title="🔒 Payment Setup",
            description=(
                "For security, payment info should be set up carefully.\n\n"
                "**⚠️ IMPORTANT:**\n"
                "• Your credentials are encrypted before storage\n"
                "• We recommend creating separate retailer accounts for bot use\n"
                "• Never share your main account passwords\n\n"
                "**Use this command in the server to set up each retailer:**\n"
                "`/payment add retailer:Target email:your@email.com`\n\n"
                "The bot will DM you to securely collect the password."
            ),
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Supported Retailers",
            value="• Target\n• Walmart\n• Best Buy\n• GameStop\n• Costco",
            inline=False
        )
        
        await dm_channel.send(embed=embed)
        await interaction.response.send_message(
            "📬 Check your DMs for payment setup instructions!",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't DM you. Please enable DMs from server members.",
            ephemeral=True
        )


@payment_group.command(name="add", description="Add payment info for a retailer")
@app_commands.describe(
    retailer="Which retailer",
    email="Your account email for this retailer",
    shipping_name="Name for shipping",
    shipping_address="Street address",
    shipping_city="City",
    shipping_state="State (2 letter)",
    shipping_zip="ZIP code"
)
@app_commands.choices(retailer=[
    app_commands.Choice(name="Target", value="Target"),
    app_commands.Choice(name="Walmart", value="Walmart"),
    app_commands.Choice(name="Best Buy", value="Best Buy"),
    app_commands.Choice(name="GameStop", value="GameStop"),
    app_commands.Choice(name="Costco", value="Costco"),
])
async def payment_add(
    interaction: discord.Interaction,
    retailer: str,
    email: str,
    shipping_name: str,
    shipping_address: str,
    shipping_city: str,
    shipping_state: str,
    shipping_zip: str
):
    """Add payment info for a retailer."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    # Save the info (password will be collected via DM)
    shipping = {
        'name': shipping_name,
        'address': shipping_address,
        'city': shipping_city,
        'state': shipping_state,
        'zip': shipping_zip,
    }
    
    # For now, save without password (user will add via DM)
    save_payment_info(
        discord_id=discord_id,
        retailer=retailer,
        email=email,
        password="",  # Will be set via DM
        shipping=shipping
    )
    
    embed = discord.Embed(
        title=f"✅ {retailer} Info Saved",
        description=(
            f"Email: {email}\n"
            f"Shipping: {shipping_name}, {shipping_city}, {shipping_state}\n\n"
            f"⚠️ **Password not set** - For security, DM me with:\n"
            f"`!setpassword {retailer} your_password`"
        ),
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@payment_group.command(name="status", description="Check your payment setup status")
async def payment_status(interaction: discord.Interaction):
    """Check payment setup status."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    retailers = ["Target", "Walmart", "Best Buy", "GameStop", "Costco"]
    
    embed = discord.Embed(
        title="💳 Payment Setup Status",
        color=discord.Color.blue()
    )
    
    for retailer in retailers:
        info = get_payment_info(discord_id, retailer)
        if info:
            has_password = bool(info.get('password'))
            status = "✅ Ready" if has_password else "⚠️ No password"
            embed.add_field(
                name=retailer,
                value=f"{status}\n{info.get('shipping_city', 'No address')}",
                inline=True
            )
        else:
            embed.add_field(
                name=retailer,
                value="❌ Not set up",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(payment_group)


# =============================================================================
# SLASH COMMANDS - PHOTO CARD SCANNER
# =============================================================================

@bot.tree.command(name="scancard", description="📸 AI identifies a card from a photo")
@app_commands.describe(
    image_url="URL to the card image (or attach an image)"
)
async def scan_card(interaction: discord.Interaction, image_url: str = None):
    """Scan a card photo using AI to identify and price it."""
    discord_id = str(interaction.user.id)
    
    # Defer since AI analysis takes time
    await interaction.response.defer()
    
    # Get image URL from attachment if not provided
    if not image_url and interaction.message and interaction.message.attachments:
        image_url = interaction.message.attachments[0].url
    
    if not image_url:
        await interaction.followup.send(
            "📸 **How to use /scancard:**\n"
            "1. Upload an image with the command: `/scancard` then attach image\n"
            "2. Or provide a URL: `/scancard image_url:https://example.com/card.jpg`",
            ephemeral=True
        )
        return
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from vision.card_scanner import CardScanner
        
        scanner = CardScanner()
        result = scanner.scan_card(image_url=image_url)
        
        if "error" in result:
            await interaction.followup.send(
                f"❌ Could not scan card: {result['error']}",
                ephemeral=True
            )
            return
        
        # Build response embed
        embed = discord.Embed(
            title=f"📸 {result.get('card_name', 'Unknown Card')}",
            description=f"**Set:** {result.get('set_name', 'Unknown')}\n**Number:** {result.get('card_number', 'N/A')}",
            color=discord.Color.gold()
        )
        
        # Add image if available
        if image_url:
            embed.set_thumbnail(url=image_url)
        
        # Pricing
        pricing = result.get("pricing", {})
        embed.add_field(
            name="💰 Pricing",
            value=(
                f"**Raw:** ${pricing.get('raw', 0):.2f}\n"
                f"**PSA 9:** ${pricing.get('psa_9', 0):.2f}\n"
                f"**PSA 10:** ${pricing.get('psa_10', 0):.2f}"
            ),
            inline=True
        )
        
        # Condition
        condition = result.get("condition", {})
        embed.add_field(
            name="🔍 Condition",
            value=(
                f"Centering: {condition.get('centering', 'N/A')}/10\n"
                f"Corners: {condition.get('corners', 'N/A')}/10\n"
                f"Edges: {condition.get('edges', 'N/A')}/10\n"
                f"Surface: {condition.get('surface', 'N/A')}/10"
            ),
            inline=True
        )
        
        # Grade analysis
        grade_analysis = result.get("grade_analysis", {})
        embed.add_field(
            name="📊 Grade Estimate",
            value=(
                f"**PSA Grade:** {grade_analysis.get('estimated_grade', result.get('estimated_grade', 'N/A'))}\n"
                f"**Worth Grading:** {'✅ Yes' if grade_analysis.get('worth_grading') else '❌ No'}\n"
                f"**Potential Profit:** ${grade_analysis.get('potential_profit', 0):.2f}"
            ),
            inline=False
        )
        
        # Recommendation
        if grade_analysis.get("recommendation"):
            embed.add_field(
                name="💡 Recommendation",
                value=grade_analysis["recommendation"],
                inline=False
            )
        
        # Confidence
        confidence = result.get("confidence", 0)
        if confidence:
            embed.set_footer(text=f"Confidence: {confidence*100:.0f}% | Source: {pricing.get('source', 'Unknown')}")
        
        # Note if demo mode
        if result.get("demo_mode"):
            embed.add_field(
                name="⚠️ Demo Mode",
                value="Set ANTHROPIC_API_KEY or OPENAI_API_KEY for real scanning",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Scan failed: {str(e)}",
            ephemeral=True
        )


# =============================================================================
# SLASH COMMANDS - PRICE TRENDS
# =============================================================================

@bot.tree.command(name="trend", description="📈 Get 7-day price trend with sparkline")
@app_commands.describe(
    card_name="Name of the card (e.g., 'Charizard VMAX')",
    set_name="Optional: Set name for disambiguation"
)
async def price_trend(interaction: discord.Interaction, card_name: str, set_name: str = None):
    """Get price trend for a card."""
    await interaction.response.defer()
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.price_trends import PriceTrendAnalyzer
        
        analyzer = PriceTrendAnalyzer()
        trend = analyzer.get_trend(card_name, set_name, days=7)
        
        if "error" in trend:
            await interaction.followup.send(
                f"❌ Could not get trend: {trend['error']}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"{trend['trend_emoji']} {card_name}",
            description=f"**Set:** {trend.get('set_name', 'Unknown')}",
            color=discord.Color.blue()
        )
        
        # Sparkline
        embed.add_field(
            name="📊 7-Day Trend",
            value=f"`{trend['sparkline']}`",
            inline=False
        )
        
        # Prices
        sign = "+" if trend['change'] >= 0 else ""
        embed.add_field(
            name="💰 Current Price",
            value=f"**${trend['current_price']:.2f}**",
            inline=True
        )
        embed.add_field(
            name="📈 Change",
            value=f"{sign}${trend['change']:.2f} ({sign}{trend['change_pct']:.1f}%)",
            inline=True
        )
        embed.add_field(
            name="📉 7d Range",
            value=f"${trend['low']:.2f} - ${trend['high']:.2f}",
            inline=True
        )
        
        embed.set_footer(text=f"Data points: {trend['data_points']} | Last updated: {trend.get('last_date', 'N/A')}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="gradeprices", description="💰 Get raw + PSA + CGC + BGS prices for a card")
@app_commands.describe(
    card_name="Name of the card (e.g., 'Charizard VMAX')",
    set_name="Optional: Set name for disambiguation"
)
async def graded_prices_cmd(interaction: discord.Interaction, card_name: str, set_name: str = None):
    """Get graded prices for a card."""
    await interaction.response.defer()
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.graded_prices import get_card_prices
        
        prices = get_card_prices(card_name, set_name or "", include_ebay=False)
        
        if not prices.get("raw"):
            await interaction.followup.send(
                f"❌ Could not find price data for **{card_name}**",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"💰 {prices['card_name']}",
            description=f"**Set:** {prices.get('set_name', 'Unknown')}",
            color=discord.Color.gold()
        )
        
        # Set thumbnail if available
        if prices.get("image_url"):
            embed.set_thumbnail(url=prices["image_url"])
        
        # Raw price
        raw = prices["raw"]
        embed.add_field(
            name="📦 Raw (Ungraded)",
            value=f"**${raw['price']:.2f}**\nRange: ${raw['low']:.2f} - ${raw['high']:.2f}",
            inline=False
        )
        
        graded = prices.get("graded", {})
        
        # PSA prices
        psa_text = ""
        for grade in ["PSA 10", "PSA 9", "PSA 8", "PSA 7"]:
            if grade in graded:
                g = graded[grade]
                psa_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if psa_text:
            embed.add_field(name="🏆 PSA Grades", value=psa_text, inline=True)
        
        # CGC prices
        cgc_text = ""
        for grade in ["CGC 10", "CGC 9.5", "CGC 9"]:
            if grade in graded:
                g = graded[grade]
                cgc_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if cgc_text:
            embed.add_field(name="🥇 CGC Grades", value=cgc_text, inline=True)
        
        # BGS prices
        bgs_text = ""
        for grade in ["BGS 10 Black", "BGS 10", "BGS 9.5", "BGS 9"]:
            if grade in graded:
                g = graded[grade]
                bgs_text += f"**{grade}:** ${g['price']:.2f}\n"
        
        if bgs_text:
            embed.add_field(name="⭐ BGS/Beckett", value=bgs_text, inline=True)
        
        # Grade recommendation
        if raw['price'] > 0 and "PSA 10" in graded and "PSA 9" in graded:
            psa10 = graded["PSA 10"]["price"]
            psa9 = graded["PSA 9"]["price"]
            grading_cost = 25
            
            profit_10 = psa10 - raw['price'] - grading_cost
            profit_9 = psa9 - raw['price'] - grading_cost
            
            recommendation = ""
            if profit_10 > 100:
                recommendation = f"🚀 **Worth grading!** PSA 10 profit: +${profit_10:.0f}"
            elif profit_9 > 50:
                recommendation = f"📈 Consider grading if PSA 9+. Profit: +${profit_9:.0f}"
            else:
                recommendation = f"⚠️ Low margin. Keep raw unless confident in PSA 10."
            
            embed.add_field(
                name="💡 Grading Recommendation",
                value=recommendation,
                inline=False
            )
        
        embed.set_footer(text=f"Updated: {prices.get('last_updated', 'N/A')[:16]} | {prices.get('source', 'TCGPlayer')}")
        
        # Add TCGPlayer link if available
        if prices.get("tcgplayer_url"):
            embed.url = prices["tcgplayer_url"]
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="flip", description="🔄 Calculate if grading a card is profitable")
@app_commands.describe(
    card_name="Name of the card (e.g., 'Charizard VMAX')",
    company="Grading company: PSA, CGC, or BGS",
    condition="Card condition: mint, near_mint, lightly_played, played"
)
@app_commands.choices(company=[
    app_commands.Choice(name="PSA", value="PSA"),
    app_commands.Choice(name="CGC", value="CGC"),
    app_commands.Choice(name="BGS/Beckett", value="BGS"),
])
@app_commands.choices(condition=[
    app_commands.Choice(name="Mint (Pack Fresh)", value="mint"),
    app_commands.Choice(name="Near Mint", value="near_mint"),
    app_commands.Choice(name="Lightly Played", value="lightly_played"),
    app_commands.Choice(name="Played", value="played"),
])
async def flip_slash(
    interaction: discord.Interaction, 
    card_name: str, 
    company: str = "PSA",
    condition: str = "mint"
):
    """Calculate grading profitability."""
    await interaction.response.defer()
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.flip_calculator import calculate_flip
        
        result = calculate_flip(
            card_name=card_name,
            company=company,
            condition=condition,
        )
        
        # Create embed
        embed = discord.Embed(
            title=f"🔄 Flip Calculator - {result['card_name']}",
            description=f"**Should you grade this card?**",
            color=discord.Color.gold() if result['expected_profit'] > 0 else discord.Color.red()
        )
        
        # Cost breakdown
        embed.add_field(
            name="💵 Investment",
            value=(
                f"**Raw:** ${result['raw_price']}\n"
                f"**Grading:** ${result['grading_cost']}\n"
                f"**Total:** ${result['total_cost']}"
            ),
            inline=True
        )
        
        # Expected value
        ev_emoji = "🚀" if result['expected_roi'] > 50 else "✅" if result['expected_roi'] > 0 else "❌"
        embed.add_field(
            name="📊 Expected Return",
            value=(
                f"**EV:** ${result['expected_value']}\n"
                f"**Profit:** ${result['expected_profit']}\n"
                f"**ROI:** {ev_emoji} {result['expected_roi']}%"
            ),
            inline=True
        )
        
        # Grade scenarios
        scenarios_text = ""
        for s in result['scenarios'][:4]:
            profit_str = f"+${s['profit']}" if s['profit'] >= 0 else f"-${abs(s['profit'])}"
            scenarios_text += f"{s['emoji']} **{s['grade']}:** ${s['graded_value']} ({profit_str})\n"
        
        embed.add_field(
            name="🎯 Grade Scenarios",
            value=scenarios_text,
            inline=False
        )
        
        # Recommendation
        embed.add_field(
            name="💡 Verdict",
            value=f"{result['recommendation']}\n\n*Break-even: {result['break_even_grade']}*",
            inline=False
        )
        
        embed.set_footer(text=f"Company: {result['grading_company']} | Condition: {condition.replace('_', ' ').title()}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="stockmap", description="🗺️ Find Pokemon TCG stock at nearby stores")
@app_commands.describe(
    zip_code="Your ZIP code (e.g., '90210')",
    query="What to search for (e.g., 'pokemon etb')",
    radius="Search radius in miles"
)
async def stockmap_slash(
    interaction: discord.Interaction, 
    zip_code: str,
    query: str = "pokemon elite trainer box",
    radius: int = 25
):
    """Find nearby store stock."""
    await interaction.response.defer()
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.stock_map import get_stock_map, STORE_CHAINS
        
        result = get_stock_map(zip_code, radius, query)
        
        # Create embed
        embed = discord.Embed(
            title=f"🗺️ Stock Map - {zip_code}",
            description=f"🔍 **{query}** within {radius} miles",
            color=discord.Color.green() if result['stores_with_stock'] > 0 else discord.Color.red()
        )
        
        # Summary
        stock_pct = (result['stores_with_stock'] / result['total_stores'] * 100) if result['total_stores'] > 0 else 0
        embed.add_field(
            name="📊 Overview",
            value=(
                f"**{result['stores_with_stock']}/{result['total_stores']}** stores have stock ({stock_pct:.0f}%)\n"
                f"**{result['total_products']}** products found"
            ),
            inline=False
        )
        
        # In-stock stores
        in_stock = [s for s in result['stores'] if s['has_stock']]
        if in_stock:
            stock_text = ""
            for store in in_stock[:5]:
                chain_info = STORE_CHAINS.get(store['chain'], {})
                emoji = chain_info.get('emoji', '🏪')
                stock_text += f"{emoji} **{store['chain']}** ({store['distance_miles']} mi) - {store['stock_count']} items\n"
            embed.add_field(name="✅ In Stock", value=stock_text, inline=False)
        
        # Out of stock
        out_stock = [s for s in result['stores'] if not s['has_stock']][:4]
        if out_stock:
            out_text = ", ".join([f"{s['chain']} ({s['distance_miles']} mi)" for s in out_stock])
            embed.add_field(name="❌ Out of Stock", value=out_text, inline=False)
        
        embed.set_footer(text=f"Updated: {result['generated_at'][:16]}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="movers", description="📊 See top gaining and losing cards")
async def top_movers(interaction: discord.Interaction):
    """Get top market movers."""
    await interaction.response.defer()
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from market.price_trends import get_top_movers
        
        movers = get_top_movers(limit=5)
        
        embed = discord.Embed(
            title="📊 Top Market Movers (7 Days)",
            color=discord.Color.gold()
        )
        
        # Top gainers
        gainers_text = ""
        for i, g in enumerate(movers.get("gainers", [])[:5], 1):
            gainers_text += f"{i}. {g['trend_emoji']} **{g['card_name']}**\n"
            gainers_text += f"   ${g['current_price']:.2f} (+{g['change_pct']:.1f}%)\n"
        embed.add_field(
            name="🚀 Top Gainers",
            value=gainers_text or "No data",
            inline=True
        )
        
        # Top losers
        losers_text = ""
        for i, l in enumerate(movers.get("losers", [])[:5], 1):
            losers_text += f"{i}. {l['trend_emoji']} **{l['card_name']}**\n"
            losers_text += f"   ${l['current_price']:.2f} ({l['change_pct']:.1f}%)\n"
        embed.add_field(
            name="📉 Top Losers",
            value=losers_text or "No data",
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


# =============================================================================
# SLASH COMMANDS - NOTIFICATION SETTINGS
# =============================================================================

alerts_group = app_commands.Group(name="alerts", description="📱 Manage notification settings")

@alerts_group.command(name="setup", description="📱 Set up SMS/Push/Email notifications")
@app_commands.describe(
    phone="Your phone number for SMS alerts (e.g., +14155551234)",
    email="Your email for alerts",
    pushover_key="Your Pushover user key (optional)"
)
async def alerts_setup(
    interaction: discord.Interaction,
    phone: str = None,
    email: str = None,
    pushover_key: str = None
):
    """Set up notification channels."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        
        updates = {}
        if phone:
            updates["phone_number"] = phone
            updates["sms_enabled"] = True
        if email:
            updates["email"] = email
            updates["email_enabled"] = True
        if pushover_key:
            updates["pushover_user_key"] = pushover_key
            updates["push_enabled"] = True
        
        if updates:
            manager.update_user_prefs(discord_id, **updates)
        
        embed = discord.Embed(
            title="📱 Notification Settings Updated",
            color=discord.Color.green()
        )
        
        if phone:
            embed.add_field(name="📱 SMS", value=f"✅ {phone[:6]}****", inline=True)
        if email:
            embed.add_field(name="📧 Email", value=f"✅ {email.split('@')[0][:3]}***@{email.split('@')[1]}", inline=True)
        if pushover_key:
            embed.add_field(name="🔔 Push", value="✅ Pushover configured", inline=True)
        
        embed.add_field(
            name="💡 Next Steps",
            value="Use `/alerts toggle` to enable/disable each channel\nUse `/alerts priority` to set when each channel fires",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@alerts_group.command(name="toggle", description="📱 Enable/disable notification channels")
@app_commands.describe(
    sms="Enable SMS alerts",
    email="Enable email alerts",
    push="Enable push notifications",
    discord_dm="Enable Discord DM alerts"
)
async def alerts_toggle(
    interaction: discord.Interaction,
    sms: bool = None,
    email: bool = None,
    push: bool = None,
    discord_dm: bool = None
):
    """Toggle notification channels."""
    discord_id = str(interaction.user.id)
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        
        updates = {}
        if sms is not None:
            updates["sms_enabled"] = sms
        if email is not None:
            updates["email_enabled"] = email
        if push is not None:
            updates["push_enabled"] = push
        if discord_dm is not None:
            updates["discord_dm_enabled"] = discord_dm
        
        if updates:
            manager.update_user_prefs(discord_id, **updates)
        
        # Get current settings
        prefs = manager.get_user_prefs(discord_id) or {}
        
        embed = discord.Embed(
            title="📱 Notification Channels",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📱 SMS",
            value="✅ On" if prefs.get("sms_enabled") else "❌ Off",
            inline=True
        )
        embed.add_field(
            name="📧 Email",
            value="✅ On" if prefs.get("email_enabled") else "❌ Off",
            inline=True
        )
        embed.add_field(
            name="🔔 Push",
            value="✅ On" if prefs.get("push_enabled") else "❌ Off",
            inline=True
        )
        embed.add_field(
            name="💬 Discord DM",
            value="✅ On" if prefs.get("discord_dm_enabled", True) else "❌ Off",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@alerts_group.command(name="priority", description="📱 Set when each channel fires")
@app_commands.describe(
    sms_min="Minimum priority for SMS (critical = restocks only)",
    email_min="Minimum priority for email",
    push_min="Minimum priority for push"
)
@app_commands.choices(
    sms_min=[
        app_commands.Choice(name="Critical (restocks only)", value="critical"),
        app_commands.Choice(name="High (deals >20% off)", value="high"),
        app_commands.Choice(name="Normal (all watchlist)", value="normal"),
    ],
    email_min=[
        app_commands.Choice(name="Critical (restocks only)", value="critical"),
        app_commands.Choice(name="High (deals >20% off)", value="high"),
        app_commands.Choice(name="Normal (all watchlist)", value="normal"),
    ],
    push_min=[
        app_commands.Choice(name="Critical (restocks only)", value="critical"),
        app_commands.Choice(name="High (deals >20% off)", value="high"),
        app_commands.Choice(name="Normal (all watchlist)", value="normal"),
    ],
)
async def alerts_priority(
    interaction: discord.Interaction,
    sms_min: str = None,
    email_min: str = None,
    push_min: str = None
):
    """Set notification priority thresholds."""
    discord_id = str(interaction.user.id)
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        
        updates = {}
        if sms_min:
            updates["sms_min_priority"] = sms_min
        if email_min:
            updates["email_min_priority"] = email_min
        if push_min:
            updates["push_min_priority"] = push_min
        
        if updates:
            manager.update_user_prefs(discord_id, **updates)
        
        # Get current settings
        prefs = manager.get_user_prefs(discord_id) or {}
        
        embed = discord.Embed(
            title="🔔 Notification Priority Settings",
            description="Each channel will only fire for alerts at or above the set priority level.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📱 SMS fires on",
            value=prefs.get("sms_min_priority", "critical").title(),
            inline=True
        )
        embed.add_field(
            name="📧 Email fires on",
            value=prefs.get("email_min_priority", "high").title(),
            inline=True
        )
        embed.add_field(
            name="🔔 Push fires on",
            value=prefs.get("push_min_priority", "high").title(),
            inline=True
        )
        
        embed.add_field(
            name="📊 Priority Levels",
            value="• **Critical:** Restocks, limited drops\n• **High:** Price drops >20%\n• **Normal:** Watchlist matches",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@alerts_group.command(name="quiet", description="📱 Set quiet hours (no notifications)")
@app_commands.describe(
    start_time="Start of quiet hours (24h format, e.g., 23:00)",
    end_time="End of quiet hours (24h format, e.g., 07:00)"
)
async def alerts_quiet_hours(
    interaction: discord.Interaction,
    start_time: str = None,
    end_time: str = None
):
    """Set quiet hours."""
    discord_id = str(interaction.user.id)
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        
        if start_time and end_time:
            # Validate format
            import re
            if not re.match(r'^\d{2}:\d{2}$', start_time) or not re.match(r'^\d{2}:\d{2}$', end_time):
                await interaction.response.send_message(
                    "❌ Invalid time format. Use 24-hour format like `23:00`",
                    ephemeral=True
                )
                return
            
            manager.update_user_prefs(discord_id, 
                quiet_hours_start=start_time,
                quiet_hours_end=end_time
            )
        
        prefs = manager.get_user_prefs(discord_id) or {}
        
        start = prefs.get("quiet_hours_start")
        end = prefs.get("quiet_hours_end")
        
        embed = discord.Embed(
            title="🌙 Quiet Hours",
            color=discord.Color.dark_blue()
        )
        
        if start and end:
            embed.add_field(
                name="⏰ Current Setting",
                value=f"Quiet from **{start}** to **{end}**\n(No SMS/Push during these hours)",
                inline=False
            )
        else:
            embed.add_field(
                name="⏰ Current Setting",
                value="Quiet hours not set\nAll alerts will come through 24/7",
                inline=False
            )
        
        embed.add_field(
            name="💡 Example",
            value="`/alerts quiet start_time:23:00 end_time:07:00`\nNo alerts from 11 PM to 7 AM",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


@alerts_group.command(name="test", description="📱 Send a test notification to all channels")
async def alerts_test(interaction: discord.Interaction):
    """Send a test notification."""
    discord_id = str(interaction.user.id)
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        
        result = manager.send_alert(
            discord_id=discord_id,
            title="🧪 Test Notification",
            message="This is a test notification from LO TCG! If you received this, your notifications are working.",
            priority="normal",
            url="https://discord.com",
        )
        
        embed = discord.Embed(
            title="🧪 Test Notification Sent",
            color=discord.Color.green()
        )
        
        channels = result.get("channels", {})
        for channel, status in channels.items():
            emoji = "✅" if status.get("success") else "❌"
            error = f" - {status.get('error', '')[:30]}" if not status.get("success") else ""
            embed.add_field(
                name=f"{emoji} {channel.replace('_', ' ').title()}",
                value=f"{'Sent!' if status.get('success') else 'Failed'}{error}",
                inline=True
            )
        
        if result.get("quiet_hours"):
            embed.add_field(
                name="🌙 Quiet Hours",
                value="SMS/Push skipped (quiet hours active)",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )


bot.tree.add_command(alerts_group)


# =============================================================================
# SLASH COMMANDS - INFO
# =============================================================================

@bot.tree.command(name="history", description="View your purchase history")
async def history(interaction: discord.Interaction):
    """View purchase history."""
    discord_id = str(interaction.user.id)
    user = get_user(discord_id)
    
    if not user:
        await interaction.response.send_message(
            "❌ You're not registered. Use `/register` first!",
            ephemeral=True
        )
        return
    
    purchases = get_purchase_history(discord_id, limit=10)
    
    if not purchases:
        await interaction.response.send_message(
            "📋 No purchase history yet!",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🛒 Your Purchase History",
        color=discord.Color.green()
    )
    
    for p in purchases:
        status_emoji = "✅" if p['status'] == 'success' else "❌"
        embed.add_field(
            name=f"{status_emoji} {p['product_name']}",
            value=f"${p['price']:.2f} @ {p['retailer']}\n{p['created_at']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help."""
    embed = discord.Embed(
        title="🎴 LO TCG - Commands",
        description="Your high-speed Pokemon card stock tracker with stealth scanning!",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="📝 Getting Started",
        value=(
            "`/register` - Create your account\n"
            "`/settings` - View/change settings\n"
            "`/help` - Show this message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📸 Card Scanner (NEW!)",
        value=(
            "`/scancard` - AI identifies card from photo\n"
            "→ Get name, set, price, and grade estimate!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📈 Price Trends (NEW!)",
        value=(
            "`/trend` - 7-day price trend with sparkline\n"
            "`/movers` - Top gaining & losing cards"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📍 Location & Scanning",
        value=(
            "`/setlocation` - Set your ZIP for local alerts\n"
            "`/location` - View your location settings\n"
            "`/scan` - Manually scan nearby stores"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📱 Notifications (NEW!)",
        value=(
            "`/alerts setup` - Add SMS/Email/Push\n"
            "`/alerts toggle` - Enable/disable channels\n"
            "`/alerts priority` - Set when each fires\n"
            "`/alerts quiet` - Set quiet hours\n"
            "`/alerts test` - Send test notification"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📋 Watchlist",
        value=(
            "`/watchlist add` - Add item to watch\n"
            "`/watchlist view` - See your watchlist\n"
            "`/watchlist remove` - Remove an item"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💳 Payment & Auto-Buy",
        value=(
            "`/payment setup` - Setup instructions\n"
            "`/payment add` - Add retailer info\n"
            "`/payment status` - Check setup status"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Info",
        value=(
            "`/history` - Purchase history"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =============================================================================
# DM COMMANDS (for sensitive info)
# =============================================================================

@bot.event
async def on_message(message: discord.Message):
    """Handle DM messages for password setting."""
    if message.author.bot:
        return
    
    # Only process DMs
    if not isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return
    
    # Handle password setting
    if message.content.startswith("!setpassword"):
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send(
                "❌ Usage: `!setpassword <retailer> <password>`\n"
                "Example: `!setpassword Target mypassword123`"
            )
            return
        
        retailer = parts[1]
        password = parts[2]
        discord_id = str(message.author.id)
        
        # Get existing info
        info = get_payment_info(discord_id, retailer)
        if not info:
            await message.channel.send(
                f"❌ No {retailer} info found. Use `/payment add` first."
            )
            return
        
        # Update with password
        save_payment_info(
            discord_id=discord_id,
            retailer=retailer,
            email=info.get('email', ''),
            password=password,
            shipping={
                'name': info.get('shipping_name', ''),
                'address': info.get('shipping_address', ''),
                'city': info.get('shipping_city', ''),
                'state': info.get('shipping_state', ''),
                'zip': info.get('shipping_zip', ''),
            }
        )
        
        # Delete the message with the password for security
        try:
            await message.delete()
        except:
            pass
        
        await message.channel.send(
            f"✅ Password saved for {retailer}!\n"
            f"Your auto-buy for {retailer} is now ready.\n"
            f"Use `/settings autobuy:true` to enable auto-buy."
        )
        return
    
    await bot.process_commands(message)


# =============================================================================
# MAIN
# =============================================================================

def main():
    if not DISCORD_BOT_TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set!")
        print("Get a bot token from https://discord.com/developers/applications")
        print("Then: export DISCORD_BOT_TOKEN='your_token_here'")
        return
    
    print("═" * 60)
    print("🎴 LO TCG (Locals Only TCG) - AI-Powered Stock Alert Bot")
    print("═" * 60)
    print()
    print("⚡ FEATURES:")
    print("   • Stealth scanning (6 retailers + Pokemon Center)")
    print("   • ZIP code-based local alerts")
    print("   • AI card grading from photos")
    print("   • Price trend sparklines")
    print("   • Multi-channel notifications (SMS, Push, Email)")
    print("   • Multi-user auto-buy")
    print()
    print("📝 COMMANDS:")
    print("   !monitor <set>  - Start monitoring")
    print("   !check <query>  - Manual stock check")
    print("   !price <card>   - Price & trends")
    print("   !grade [url]    - AI grade card")
    print("   !market         - Market report")
    print("   !commands       - All commands")
    print()
    print("🔧 SLASH COMMANDS:")
    print("   /register, /settings, /scancard, /trend, /alerts")
    print()
    print("═" * 60)
    
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
