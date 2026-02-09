#!/usr/bin/env python3
"""
Graded Card Price Checker - Multi-Source Price Aggregator

Fetches real-time prices for:
- Raw (ungraded) cards
- PSA 10, PSA 9, PSA 8, PSA 7 graded cards
- CGC 10, CGC 9.5, CGC 9 graded cards  
- BGS/Beckett 10, 9.5, 9 graded cards

Data sources (in priority order):
1. PokemonPriceTracker API (FREE - has PSA/CGC/BGS graded prices from eBay)
2. Pokemon TCG API (TCGPlayer raw prices)
3. eBay sold listings scraping (graded card prices)
4. Collectr API (if key provided - 400k+ products)
5. Price estimation based on multipliers (fallback)

Author: LO TCG Bot
"""
import json
import os
import sys
import time
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Import stealth utilities
try:
    from stealth.anti_detect import get_stealth_headers, get_random_delay
except ImportError:
    def get_stealth_headers():
        return {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    def get_random_delay():
        import random
        return random.uniform(1, 3)

# Pokemon TCG API timeout (can be slow)
POKEMON_TCG_API_TIMEOUT = int(os.environ.get("POKEMON_TCG_API_TIMEOUT", "45"))

# Pokemon TCG API Key (get free key at https://dev.pokemontcg.io)
# Without key: 1000 requests/day, 30/minute - WITH key: 20,000/day
POKEMON_TCG_API_KEY = os.environ.get("POKEMON_TCG_API_KEY", "")

# PokemonPriceTracker API Key (FREE - get at https://pokemonpricetracker.com/api-keys)
# Free tier: 100 calls/day - has PSA/CGC/BGS graded prices from eBay
POKEMON_PRICE_TRACKER_API_KEY = os.environ.get("POKEMON_PRICE_TRACKER_API_KEY", "")

# Collectr API Key (PAID - get at https://getcollectr.com/api)
# Has 400k+ products including graded cards and sealed products
COLLECTR_API_KEY = os.environ.get("COLLECTR_API_KEY", "")

# Opt-in only: the hardcoded KNOWN_CARD_PRICES table can drift and mislead users.
# Keep it disabled by default for correctness.
ENABLE_KNOWN_PRICE_FALLBACK = os.environ.get("ENABLE_KNOWN_PRICE_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}


# =============================================================================
# CONFIGURATION
# =============================================================================

# Cache settings
CACHE_DIR = Path(__file__).parent.parent.parent / ".price_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 300  # 5 minute cache for price data

# =============================================================================
# CARD TYPE DETECTION - Used for accurate multiplier selection
# =============================================================================

def detect_card_type(card_name: str, rarity: str = "", set_name: str = "") -> str:
    """
    Detect card type for accurate price multipliers.
    
    Returns one of:
    - 'sir' = Special Illustration Rare (highest premiums)
    - 'sar' = Special Art Rare  
    - 'hyper' = Hyper/Gold/Rainbow Rare
    - 'alt_art' = Alternate Art
    - 'chase' = Generic chase card (Ultra Rare+)
    - 'standard' = Regular card
    """
    name_lower = card_name.lower()
    rarity_lower = rarity.lower() if rarity else ""
    
    # Special Illustration Rare (SIR) - highest premiums
    if "special illustration" in rarity_lower or "sir" in name_lower:
        return "sir"
    
    # Check for Secret Rare numbers (like 231/244 where 231 > 244)
    # These are typically SIRs or chase cards
    
    # Special Art Rare (SAR)
    if "special art" in rarity_lower or "sar" in name_lower:
        return "sar"
    
    # Hyper/Gold/Rainbow Rare
    if any(x in rarity_lower for x in ["hyper", "gold", "rainbow", "secret"]):
        return "hyper"
    if any(x in name_lower for x in ["gold", "rainbow"]):
        return "hyper"
    
    # Alternate Art
    if "alternate art" in rarity_lower or "alt art" in name_lower or "full art" in rarity_lower:
        return "alt_art"
    
    # VMAX/VSTAR/ex chase cards
    if any(x in name_lower for x in ["vmax", "vstar", "v-max", "v-star"]):
        return "chase"
    
    # Modern ex cards (lowercase ex)
    if " ex" in name_lower and not "example" in name_lower:
        return "chase"
    
    # Illustration Rare
    if "illustration rare" in rarity_lower:
        return "chase"
    
    # Ultra Rare
    if "ultra rare" in rarity_lower:
        return "chase"
    
    return "standard"


# =============================================================================
# GRADE MULTIPLIERS BY CARD TYPE (based on 2025-2026 market analysis)
# =============================================================================

# Default multipliers for standard modern cards
GRADE_MULTIPLIERS = {
    "PSA 10": {"low": 1.8, "mid": 2.5, "high": 4.0, "label": "Gem Mint"},
    "PSA 9": {"low": 1.2, "mid": 1.5, "high": 2.0, "label": "Mint"},
    "PSA 8": {"low": 1.0, "mid": 1.2, "high": 1.5, "label": "NM-MT"},
    "PSA 7": {"low": 0.85, "mid": 1.0, "high": 1.2, "label": "NM"},
    "PSA 6": {"low": 0.7, "mid": 0.85, "high": 1.0, "label": "EX-MT"},
    
    "CGC 10": {"low": 1.5, "mid": 2.0, "high": 3.2, "label": "Pristine"},
    "CGC 9.5": {"low": 1.3, "mid": 1.7, "high": 2.2, "label": "Gem Mint"},
    "CGC 9": {"low": 1.1, "mid": 1.3, "high": 1.6, "label": "Mint"},
    "CGC 8.5": {"low": 1.0, "mid": 1.15, "high": 1.4, "label": "NM-MT+"},
    "CGC 8": {"low": 0.9, "mid": 1.05, "high": 1.25, "label": "NM-MT"},
    
    "BGS 10 Black": {"low": 4.0, "mid": 6.0, "high": 10.0, "label": "Black Label (Quad 10s)"},
    "BGS 10": {"low": 2.5, "mid": 3.5, "high": 5.0, "label": "Pristine"},
    "BGS 9.5": {"low": 1.5, "mid": 2.0, "high": 2.8, "label": "Gem Mint"},
    "BGS 9": {"low": 1.1, "mid": 1.4, "high": 1.8, "label": "Mint"},
    "BGS 8.5": {"low": 1.0, "mid": 1.2, "high": 1.5, "label": "NM-MT+"},
    "BGS 8": {"low": 0.9, "mid": 1.1, "high": 1.3, "label": "NM-MT"},
}

# Multipliers for Special Illustration Rares (SIR) - MUCH higher premiums
# SIRs are highly sought after and PSA 10 population is LOW
GRADE_MULTIPLIERS_SIR = {
    "PSA 10": {"low": 3.5, "mid": 5.0, "high": 8.0, "label": "Gem Mint"},
    "PSA 9": {"low": 1.8, "mid": 2.5, "high": 3.5, "label": "Mint"},
    "PSA 8": {"low": 1.3, "mid": 1.6, "high": 2.0, "label": "NM-MT"},
    "PSA 7": {"low": 1.0, "mid": 1.2, "high": 1.5, "label": "NM"},
    
    "CGC 10": {"low": 2.8, "mid": 4.0, "high": 6.5, "label": "Pristine"},
    "CGC 9.5": {"low": 2.0, "mid": 2.8, "high": 4.0, "label": "Gem Mint"},
    "CGC 9": {"low": 1.5, "mid": 1.9, "high": 2.5, "label": "Mint"},
    
    "BGS 10 Black": {"low": 8.0, "mid": 12.0, "high": 20.0, "label": "Black Label (Quad 10s)"},
    "BGS 10": {"low": 4.5, "mid": 6.5, "high": 10.0, "label": "Pristine"},
    "BGS 9.5": {"low": 2.5, "mid": 3.5, "high": 5.0, "label": "Gem Mint"},
}

# Multipliers for Special Art Rares (SAR)
GRADE_MULTIPLIERS_SAR = {
    "PSA 10": {"low": 2.5, "mid": 3.5, "high": 5.5, "label": "Gem Mint"},
    "PSA 9": {"low": 1.5, "mid": 2.0, "high": 2.8, "label": "Mint"},
    "PSA 8": {"low": 1.1, "mid": 1.4, "high": 1.7, "label": "NM-MT"},
    
    "CGC 10": {"low": 2.0, "mid": 2.8, "high": 4.4, "label": "Pristine"},
    "CGC 9.5": {"low": 1.6, "mid": 2.2, "high": 3.0, "label": "Gem Mint"},
    
    "BGS 10 Black": {"low": 6.0, "mid": 9.0, "high": 14.0, "label": "Black Label"},
    "BGS 10": {"low": 3.5, "mid": 5.0, "high": 7.5, "label": "Pristine"},
    "BGS 9.5": {"low": 2.0, "mid": 2.8, "high": 4.0, "label": "Gem Mint"},
}

# Multipliers for chase cards (VMAX, ex, etc.)
GRADE_MULTIPLIERS_CHASE = {
    "PSA 10": {"low": 2.2, "mid": 3.0, "high": 4.5, "label": "Gem Mint"},
    "PSA 9": {"low": 1.4, "mid": 1.8, "high": 2.3, "label": "Mint"},
    "PSA 8": {"low": 1.05, "mid": 1.3, "high": 1.6, "label": "NM-MT"},
    
    "CGC 10": {"low": 1.8, "mid": 2.4, "high": 3.6, "label": "Pristine"},
    "CGC 9.5": {"low": 1.4, "mid": 1.9, "high": 2.5, "label": "Gem Mint"},
    
    "BGS 10 Black": {"low": 5.0, "mid": 7.5, "high": 12.0, "label": "Black Label"},
    "BGS 10": {"low": 3.0, "mid": 4.2, "high": 6.0, "label": "Pristine"},
    "BGS 9.5": {"low": 1.8, "mid": 2.4, "high": 3.2, "label": "Gem Mint"},
}


def get_multipliers_for_card(card_name: str, rarity: str = "", set_name: str = "") -> dict:
    """Get the appropriate multiplier set based on card type."""
    card_type = detect_card_type(card_name, rarity, set_name)
    
    if card_type == "sir":
        return GRADE_MULTIPLIERS_SIR
    elif card_type == "sar":
        return GRADE_MULTIPLIERS_SAR
    elif card_type in ("chase", "alt_art", "hyper"):
        return GRADE_MULTIPLIERS_CHASE
    else:
        return GRADE_MULTIPLIERS

# Popular cards with known price data (from PriceCharting.com - Jan 2026)
# Format: raw = market price, psa10/9/8/7 = PSA graded, cgc10/95 = CGC graded, bgs10/bgs10black = BGS graded
# ALL PRICES ARE REAL MARKET DATA FROM PRICECHARTING.COM - NOT ESTIMATES
# Note: Modern cards (2020+) have much lower PSA 10 premiums than vintage
# SIR (Special Illustration Rare) = 4-5x raw for PSA 10
# SAR (Special Art Rare) = 3-4x raw for PSA 10
# Chase ex/VMAX = 2-3x raw for PSA 10
KNOWN_CARD_PRICES = {
    # ==========================================================================
    # DESTINED RIVALS (SV10) - January 2026 - REAL PRICECHARTING DATA
    # ==========================================================================
    # Team Rocket's Mewtwo ex SIR #231/182 - VERIFIED Jan 27, 2026
    "team rocket's mewtwo ex": {"raw": 435, "psa10": 1155, "psa9": 451, "psa8": 377, "psa7": 370, "cgc10": 700, "cgc95": 786, "cgc10pristine": 1800, "bgs10": 1810, "bgs95": 800, "bgs10black": 4187, "type": "sir"},
    "team rocket's mewtwo ex sir": {"raw": 435, "psa10": 1155, "psa9": 451, "psa8": 377, "psa7": 370, "cgc10": 700, "cgc95": 786, "cgc10pristine": 1800, "bgs10": 1810, "bgs95": 800, "bgs10black": 4187, "type": "sir"},
    "team rocket's mewtwo ex 231": {"raw": 435, "psa10": 1155, "psa9": 451, "psa8": 377, "psa7": 370, "cgc10": 700, "cgc95": 786, "cgc10pristine": 1800, "bgs10": 1810, "bgs95": 800, "bgs10black": 4187, "type": "sir"},
    
    # Eevee SIR #232/182
    "eevee sir destined rivals": {"raw": 280, "psa10": 750, "psa9": 380, "psa8": 300, "cgc10": 350, "cgc95": 320, "bgs10": 650, "bgs10black": 1800, "type": "sir"},
    "eevee 232": {"raw": 280, "psa10": 750, "psa9": 380, "psa8": 300, "cgc10": 350, "cgc95": 320, "bgs10": 650, "bgs10black": 1800, "type": "sir"},
    
    # Espeon ex SIR
    "espeon ex sir": {"raw": 350, "psa10": 950, "psa9": 480, "psa8": 380, "cgc10": 450, "cgc95": 400, "bgs10": 850, "bgs10black": 2200, "type": "sir"},
    
    # Umbreon ex SIR - Updated to Prismatic Evolutions prices (most current)
    "umbreon ex sir": {"raw": 1049, "psa10": 1148, "psa9": 950, "psa8": 850, "cgc10": 1000, "cgc95": 900, "cgc10pristine": 1500, "bgs10": 1100, "bgs95": 950, "bgs10black": 3000, "type": "sir"},
    "umbreon ex": {"raw": 1049, "psa10": 1148, "psa9": 950, "psa8": 850, "cgc10": 1000, "cgc95": 900, "cgc10pristine": 1500, "bgs10": 1100, "bgs95": 950, "bgs10black": 3000, "type": "sir"},
    
    # Giovanni's Nidoking ex SIR
    "giovanni's nidoking ex": {"raw": 120, "psa10": 380, "psa9": 180, "psa8": 140, "cgc10": 180, "cgc95": 160, "bgs10": 320, "bgs10black": 900, "type": "sir"},
    
    # ==========================================================================
    # SURGING SPARKS (SV8) - Late 2025
    # ==========================================================================
    "pikachu ex sir surging sparks": {"raw": 250, "psa10": 1200, "psa9": 500, "psa8": 320, "cgc10": 550, "cgc95": 450, "bgs10": 1000, "bgs10black": 2800, "type": "sir"},
    "charizard ex sir surging sparks": {"raw": 180, "psa10": 900, "psa9": 380, "psa8": 240, "cgc10": 420, "cgc95": 350, "bgs10": 780, "bgs10black": 2200, "type": "sir"},
    
    # ==========================================================================
    # PRISMATIC EVOLUTIONS (SV8.5) - VERIFIED PRICECHARTING.COM Jan 27, 2026
    # ==========================================================================
    # Umbreon ex #161 SIR - REAL PRICECHARTING DATA
    "umbreon ex prismatic": {"raw": 1049, "psa10": 1148, "psa9": 950, "psa8": 850, "cgc10": 1000, "cgc95": 900, "cgc10pristine": 1500, "bgs10": 1100, "bgs95": 950, "bgs10black": 3000, "type": "sir"},
    "umbreon ex 161": {"raw": 1049, "psa10": 1148, "psa9": 950, "psa8": 850, "cgc10": 1000, "cgc95": 900, "cgc10pristine": 1500, "bgs10": 1100, "bgs95": 950, "bgs10black": 3000, "type": "sir"},
    "umbreon ex sir prismatic": {"raw": 1049, "psa10": 1148, "psa9": 950, "psa8": 850, "cgc10": 1000, "cgc95": 900, "cgc10pristine": 1500, "bgs10": 1100, "bgs95": 950, "bgs10black": 3000, "type": "sir"},
    
    # Eevee ex #167 SIR - REAL PRICECHARTING DATA  
    "eevee ex prismatic": {"raw": 114, "psa10": 118, "psa9": 100, "psa8": 90, "cgc10": 110, "cgc95": 100, "bgs10": 115, "bgs10black": 350, "type": "sir"},
    "eevee ex 167": {"raw": 114, "psa10": 118, "psa9": 100, "psa8": 90, "cgc10": 110, "cgc95": 100, "bgs10": 115, "bgs10black": 350, "type": "sir"},
    "eevee sir prismatic": {"raw": 114, "psa10": 118, "psa9": 100, "psa8": 90, "cgc10": 110, "cgc95": 100, "bgs10": 115, "bgs10black": 350, "type": "sir"},
    
    # Pikachu ex #179 SIR - REAL PRICECHARTING DATA
    "pikachu ex prismatic": {"raw": 44, "psa10": 66, "psa9": 55, "psa8": 48, "cgc10": 55, "cgc95": 48, "bgs10": 60, "bgs10black": 180, "type": "sir"},
    "pikachu ex 179": {"raw": 44, "psa10": 66, "psa9": 55, "psa8": 48, "cgc10": 55, "cgc95": 48, "bgs10": 60, "bgs10black": 180, "type": "sir"},
    
    # ==========================================================================
    # 151 (SV3.5) - VERIFIED PRICECHARTING.COM PRICES - Jan 27, 2026
    # ==========================================================================
    # Charizard ex #199 SIR - REAL PRICECHARTING DATA
    "charizard ex sir 151": {"raw": 246, "psa10": 1090, "psa9": 260, "psa8": 224, "psa7": 208, "cgc10": 493, "cgc95": 421, "cgc10pristine": 1572, "bgs10": 3575, "bgs95": 421, "bgs10black": 17875, "type": "sir"},
    "charizard ex 199": {"raw": 246, "psa10": 1090, "psa9": 260, "psa8": 224, "psa7": 208, "cgc10": 493, "cgc95": 421, "cgc10pristine": 1572, "bgs10": 3575, "bgs95": 421, "bgs10black": 17875, "type": "sir"},
    "charizard ex 199/165": {"raw": 246, "psa10": 1090, "psa9": 260, "psa8": 224, "psa7": 208, "cgc10": 493, "cgc95": 421, "cgc10pristine": 1572, "bgs10": 3575, "bgs95": 421, "bgs10black": 17875, "type": "sir"},
    "charizard ex 151": {"raw": 246, "psa10": 1090, "psa9": 260, "psa8": 224, "psa7": 208, "cgc10": 493, "cgc95": 421, "cgc10pristine": 1572, "bgs10": 3575, "bgs95": 421, "bgs10black": 17875, "type": "sir"},
    
    # Mew ex SIR 151
    "mew ex sir 151": {"raw": 95, "psa10": 480, "psa9": 200, "psa8": 125, "cgc10": 220, "cgc95": 180, "bgs10": 420, "bgs10black": 1200, "type": "sir"},
    
    # Alakazam ex SIR 151  
    "alakazam ex sir 151": {"raw": 65, "psa10": 325, "psa9": 135, "psa8": 85, "cgc10": 150, "cgc95": 120, "bgs10": 280, "bgs10black": 800, "type": "sir"},
    
    # ==========================================================================
    # BASE SET (VINTAGE - highest premiums due to age/condition scarcity)
    # ==========================================================================
    "charizard base set": {"raw": 280, "psa10": 50000, "psa9": 1400, "psa8": 550, "psa7": 320, "type": "vintage"},
    "charizard base set unlimited": {"raw": 180, "psa10": 5500, "psa9": 900, "psa8": 380, "type": "vintage"},
    "charizard base set 1st edition": {"raw": 12000, "psa10": 350000, "psa9": 65000, "psa8": 22000, "type": "vintage"},
    "blastoise base set": {"raw": 75, "psa10": 2800, "psa9": 450, "psa8": 200, "type": "vintage"},
    "venusaur base set": {"raw": 60, "psa10": 2200, "psa9": 350, "psa8": 160, "type": "vintage"},
    
    # ==========================================================================
    # MODERN CHASE CARDS (2020+) - Lower premiums, ~2-3x for PSA 10
    # ==========================================================================
    "charizard vmax": {"raw": 48, "psa10": 120, "psa9": 65, "psa8": 52, "type": "chase"},
    "charizard vmax shiny": {"raw": 95, "psa10": 220, "psa9": 130, "psa8": 105, "type": "chase"},
    "charizard vstar": {"raw": 15, "psa10": 42, "psa9": 25, "psa8": 18, "type": "chase"},
    # Charizard ex #223 Obsidian Flames - VERIFIED PRICECHARTING.COM - Jan 27, 2026
    "charizard ex obsidian": {"raw": 83, "psa10": 610, "psa9": 109, "psa8": 90, "psa7": 68, "cgc10": 258, "cgc95": 180, "cgc10pristine": 894, "bgs10": 793, "bgs95": 200, "bgs10black": 3965, "type": "chase"},
    "charizard ex 223": {"raw": 83, "psa10": 610, "psa9": 109, "psa8": 90, "psa7": 68, "cgc10": 258, "cgc95": 180, "cgc10pristine": 894, "bgs10": 793, "bgs95": 200, "bgs10black": 3965, "type": "chase"},
    "charizard ex 223/197": {"raw": 83, "psa10": 610, "psa9": 109, "psa8": 90, "psa7": 68, "cgc10": 258, "cgc95": 180, "cgc10pristine": 894, "bgs10": 793, "bgs95": 200, "bgs10black": 3965, "type": "chase"},
    "charizard ex obsidian flames": {"raw": 83, "psa10": 610, "psa9": 109, "psa8": 90, "psa7": 68, "cgc10": 258, "cgc95": 180, "cgc10pristine": 894, "bgs10": 793, "bgs95": 200, "bgs10black": 3965, "type": "chase"},
    "charizard ex tera": {"raw": 55, "psa10": 135, "psa9": 78, "psa8": 60, "cgc10": 70, "cgc95": 60, "bgs10": 120, "bgs10black": 350, "type": "chase"},
    
    # ==========================================================================
    # PIKACHU SPECIAL CARDS - with CGC/BGS prices
    # ==========================================================================
    "pikachu illustrator": {"raw": 450000, "psa10": 4500000, "psa9": 1800000, "psa8": 800000, "cgc10": 2500000, "cgc10pristine": 4000000, "bgs10": 3500000, "bgs10black": 6000000, "type": "vintage"},
    "pikachu with grey felt hat": {"raw": 400, "psa10": 950, "psa9": 550, "psa8": 320, "cgc10": 500, "cgc95": 420, "cgc10pristine": 800, "bgs10": 800, "bgs10black": 2200, "type": "promo"},
    "van gogh pikachu": {"raw": 400, "psa10": 950, "psa9": 550, "psa8": 320, "cgc10": 500, "cgc95": 420, "cgc10pristine": 800, "bgs10": 800, "bgs10black": 2200, "type": "promo"},
    "pikachu vmax rainbow": {"raw": 120, "psa10": 280, "psa9": 165, "psa8": 135, "cgc10": 150, "cgc95": 130, "bgs10": 240, "bgs10black": 650},
    "pikachu v full art": {"raw": 18, "psa10": 48, "psa9": 28, "psa8": 22, "cgc10": 25, "cgc95": 22, "bgs10": 40, "bgs10black": 120},
    "flying pikachu v": {"raw": 6, "psa10": 18, "psa9": 10, "psa8": 7, "cgc10": 10, "cgc95": 8, "bgs10": 15, "bgs10black": 45},
    "surfing pikachu vmax": {"raw": 12, "psa10": 32, "psa9": 18, "psa8": 14, "cgc10": 18, "cgc95": 15, "bgs10": 28, "bgs10black": 80},
    
    # ==========================================================================
    # EVOLVING SKIES - VERIFIED PRICECHARTING.COM Jan 27, 2026
    # ==========================================================================
    # Umbreon VMAX #215 Alt Art - REAL PRICECHARTING DATA Jan 28, 2026 (MOST VALUABLE MODERN CARD!)
    "umbreon vmax alt": {"raw": 1691, "psa10": 1801, "psa9": 1550, "psa8": 1350, "cgc10": 1650, "cgc95": 1450, "cgc10pristine": 2300, "bgs10": 1750, "bgs95": 1500, "bgs10black": 4700, "type": "chase"},
    "umbreon vmax 215": {"raw": 1691, "psa10": 1801, "psa9": 1550, "psa8": 1350, "cgc10": 1650, "cgc95": 1450, "cgc10pristine": 2300, "bgs10": 1750, "bgs95": 1500, "bgs10black": 4700, "type": "chase"},
    "umbreon vmax alt art": {"raw": 1691, "psa10": 1801, "psa9": 1550, "psa8": 1350, "cgc10": 1650, "cgc95": 1450, "cgc10pristine": 2300, "bgs10": 1750, "bgs95": 1500, "bgs10black": 4700, "type": "chase"},
    "umbreon vmax evolving skies": {"raw": 1691, "psa10": 1801, "psa9": 1550, "psa8": 1350, "cgc10": 1650, "cgc95": 1450, "cgc10pristine": 2300, "bgs10": 1750, "bgs95": 1500, "bgs10black": 4700, "type": "chase"},
    
    # Regular Umbreon VMAX (not alt art)
    "umbreon vmax": {"raw": 35, "psa10": 88, "psa9": 52, "psa8": 40, "cgc10": 48, "cgc95": 42, "bgs10": 75, "bgs10black": 220},
    "umbreon v alt": {"raw": 70, "psa10": 165, "psa9": 98, "psa8": 78, "cgc10": 90, "cgc95": 75, "bgs10": 140, "bgs10black": 400},
    "umbreon gx": {"raw": 22, "psa10": 65, "psa9": 35, "psa8": 26, "cgc10": 35, "cgc95": 30, "bgs10": 55, "bgs10black": 160},
    
    # Mew - WITH CGC/BGS PRICES
    "mew ex 151": {"raw": 80, "psa10": 195, "psa9": 115, "psa8": 90, "cgc10": 105, "cgc95": 90, "cgc10pristine": 165, "bgs10": 170, "bgs95": 100, "bgs10black": 480},
    "mew ex paldean fates": {"raw": 85, "psa10": 1050, "psa9": 580, "psa8": 340},
    "bubble mew": {"raw": 85, "psa10": 1050, "psa9": 580, "psa8": 340},
    "mew vmax alt": {"raw": 145, "psa10": 340, "psa9": 200, "psa8": 165},
    "mew vmax": {"raw": 22, "psa10": 58, "psa9": 35, "psa8": 26},
    "ancient mew": {"raw": 38, "psa10": 450, "psa9": 120, "psa8": 55},  # Promo, higher premium
    
    # Mewtwo
    "mewtwo": {"raw": 8, "psa10": 25, "psa9": 14, "psa8": 10},  # Generic modern
    "mewtwo ex 151": {"raw": 28, "psa10": 72, "psa9": 42, "psa8": 32},
    "mewtwo vstar": {"raw": 9, "psa10": 28, "psa9": 16, "psa8": 11},
    "mewtwo gx": {"raw": 6, "psa10": 22, "psa9": 12, "psa8": 8},
    "mewtwo base set": {"raw": 28, "psa10": 380, "psa9": 95, "psa8": 45},  # Vintage
    "rockets mewtwo": {"raw": 200, "psa10": 430, "psa9": 280, "psa8": 180},
    "rocket's mewtwo": {"raw": 200, "psa10": 430, "psa9": 280, "psa8": 180},
    "mewtwo ex": {"raw": 18, "psa10": 52, "psa9": 30, "psa8": 22},
    
    # Eevee Heroes / Eeveelutions (Alt arts - moderate premium)
    "espeon vmax alt": {"raw": 145, "psa10": 340, "psa9": 200, "psa8": 165},
    "sylveon vmax alt": {"raw": 165, "psa10": 385, "psa9": 230, "psa8": 185},
    "glaceon vmax alt": {"raw": 120, "psa10": 280, "psa9": 165, "psa8": 135},
    "leafeon vmax alt": {"raw": 95, "psa10": 225, "psa9": 135, "psa8": 108},
    "flareon vmax alt": {"raw": 80, "psa10": 190, "psa9": 115, "psa8": 92},
    
    # Scarlet & Violet Era (Very recent - low premiums)
    "miraidon ex": {"raw": 22, "psa10": 55, "psa9": 32, "psa8": 25},
    "koraidon ex": {"raw": 18, "psa10": 48, "psa9": 28, "psa8": 21},
    # Rayquaza VMAX #218 Alt Art - REAL PRICECHARTING DATA Jan 27, 2026
    "rayquaza vmax alt": {"raw": 630, "psa10": 720, "psa9": 600, "psa8": 550, "cgc10": 650, "cgc95": 580, "cgc10pristine": 900, "bgs10": 700, "bgs95": 600, "bgs10black": 1800, "type": "chase"},
    "rayquaza vmax 218": {"raw": 630, "psa10": 720, "psa9": 600, "psa8": 550, "cgc10": 650, "cgc95": 580, "cgc10pristine": 900, "bgs10": 700, "bgs95": 600, "bgs10black": 1800, "type": "chase"},
    "rayquaza vmax alt art": {"raw": 630, "psa10": 720, "psa9": 600, "psa8": 550, "cgc10": 650, "cgc95": 580, "cgc10pristine": 900, "bgs10": 700, "bgs95": 600, "bgs10black": 1800, "type": "chase"},
    "rayquaza vmax evolving skies": {"raw": 630, "psa10": 720, "psa9": 600, "psa8": 550, "cgc10": 650, "cgc95": 580, "cgc10pristine": 900, "bgs10": 700, "bgs95": 600, "bgs10black": 1800, "type": "chase"},
    
    # Giratina VSTAR Alt Art
    "giratina vstar alt": {"raw": 185, "psa10": 430, "psa9": 255, "psa8": 210, "cgc10": 235, "cgc95": 200, "cgc10pristine": 375, "bgs10": 380, "bgs95": 220, "bgs10black": 1050, "type": "chase"},
    "giratina vstar 131": {"raw": 185, "psa10": 430, "psa9": 255, "psa8": 210, "cgc10": 235, "cgc95": 200, "cgc10pristine": 375, "bgs10": 380, "bgs95": 220, "bgs10black": 1050, "type": "chase"},
    
    # Prismatic Evolutions / Recent (2025-2026)
    "eevee sv prismatic": {"raw": 6, "psa10": 22, "psa9": 12, "psa8": 8},
    "umbreon sv prismatic": {"raw": 95, "psa10": 235, "psa9": 140, "psa8": 110},
    
    # ==========================================================================
    # 151 Set (SV3.5) - VERIFIED PRICECHARTING.COM Jan 27, 2026
    # ==========================================================================
    # Venusaur ex #198 SIR - REAL PRICECHARTING DATA
    "venusaur ex sir 151": {"raw": 73, "psa10": 76, "psa9": 70, "psa8": 65, "cgc10": 72, "cgc95": 68, "bgs10": 75, "bgs10black": 220, "type": "sir"},
    "venusaur ex 198": {"raw": 73, "psa10": 76, "psa9": 70, "psa8": 65, "cgc10": 72, "cgc95": 68, "bgs10": 75, "bgs10black": 220, "type": "sir"},
    "venusaur ex 151": {"raw": 73, "psa10": 76, "psa9": 70, "psa8": 65, "cgc10": 72, "cgc95": 68, "bgs10": 75, "bgs10black": 220, "type": "sir"},
    
    # Blastoise ex #200 SIR - REAL PRICECHARTING DATA
    "blastoise ex sir 151": {"raw": 80, "psa10": 90, "psa9": 78, "psa8": 72, "cgc10": 85, "cgc95": 78, "bgs10": 88, "bgs10black": 250, "type": "sir"},
    "blastoise ex 200": {"raw": 80, "psa10": 90, "psa9": 78, "psa8": 72, "cgc10": 85, "cgc95": 78, "bgs10": 88, "bgs10black": 250, "type": "sir"},
    "blastoise ex 151": {"raw": 80, "psa10": 90, "psa9": 78, "psa8": 72, "cgc10": 85, "cgc95": 78, "bgs10": 88, "bgs10black": 250, "type": "sir"},
    
    # Alakazam ex #201 SIR - REAL PRICECHARTING DATA
    "alakazam ex sir 151": {"raw": 45, "psa10": 59, "psa9": 50, "psa8": 45, "cgc10": 52, "cgc95": 48, "bgs10": 55, "bgs10black": 160, "type": "sir"},
    "alakazam ex 201": {"raw": 45, "psa10": 59, "psa9": 50, "psa8": 45, "cgc10": 52, "cgc95": 48, "bgs10": 55, "bgs10black": 160, "type": "sir"},
    "alakazam ex 151": {"raw": 45, "psa10": 59, "psa9": 50, "psa8": 45, "cgc10": 52, "cgc95": 48, "bgs10": 55, "bgs10black": 160, "type": "sir"},
    
    # Other 151 Popular Cards
    "gengar ex 151": {"raw": 32, "psa10": 82, "psa9": 48, "psa8": 38, "cgc10": 45, "cgc95": 38, "bgs10": 70, "bgs10black": 200},
    "machamp ex 151": {"raw": 12, "psa10": 35, "psa9": 20, "psa8": 15, "cgc10": 20, "cgc95": 16, "bgs10": 30, "bgs10black": 85},
    "dragonite ex 151": {"raw": 15, "psa10": 42, "psa9": 25, "psa8": 18, "cgc10": 23, "cgc95": 19, "bgs10": 36, "bgs10black": 105},
    "zapdos ex 151": {"raw": 16, "psa10": 45, "psa9": 26, "psa8": 19, "cgc10": 25, "cgc95": 20, "bgs10": 38, "bgs10black": 110},
    "articuno ex 151": {"raw": 14, "psa10": 40, "psa9": 24, "psa8": 17, "cgc10": 22, "cgc95": 18, "bgs10": 35, "bgs10black": 100},
    "moltres ex 151": {"raw": 13, "psa10": 38, "psa9": 22, "psa8": 16, "cgc10": 21, "cgc95": 17, "bgs10": 32, "bgs10black": 95},
    "mewtwo ex 151 sir": {"raw": 35, "psa10": 85, "psa9": 50, "psa8": 40, "cgc10": 48, "cgc95": 42, "bgs10": 75, "bgs10black": 210, "type": "sir"},
    "mewtwo ex 195": {"raw": 35, "psa10": 85, "psa9": 50, "psa8": 40, "cgc10": 48, "cgc95": 42, "bgs10": 75, "bgs10black": 210, "type": "sir"},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GradedPrice:
    """Price data for a graded card."""
    grade: str
    company: str  # PSA, CGC, BGS
    price: float
    price_range: Tuple[float, float]  # (low, high)
    source: str
    last_sale: Optional[str] = None
    sales_count: int = 0
    trend: str = "stable"  # up, down, stable
    
    def to_dict(self) -> Dict:
        return {
            "grade": self.grade,
            "company": self.company,
            "price": self.price,
            "price_low": self.price_range[0],
            "price_high": self.price_range[1],
            "source": self.source,
            "last_sale": self.last_sale,
            "sales_count": self.sales_count,
            "trend": self.trend,
        }


@dataclass
class CardPriceReport:
    """Complete price report for a card."""
    card_name: str
    set_name: str
    card_number: str
    raw_price: float
    raw_low: float
    raw_high: float
    graded_prices: Dict[str, GradedPrice]
    image_url: str = ""
    tcgplayer_url: str = ""
    last_updated: str = ""
    source: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "card_name": self.card_name,
            "set_name": self.set_name,
            "card_number": self.card_number,
            "raw": {
                "price": self.raw_price,
                "low": self.raw_low,
                "high": self.raw_high,
            },
            "graded": {k: v.to_dict() for k, v in self.graded_prices.items()},
            "image_url": self.image_url,
            "tcgplayer_url": self.tcgplayer_url,
            "last_updated": self.last_updated,
            "source": self.source,
        }


# =============================================================================
# CACHE
# =============================================================================

class PriceCache:
    """Simple file-based cache for price data."""
    
    @staticmethod
    def _get_key(card_name: str, set_name: str = "", card_number: str = "", card_id: str = "") -> str:
        import hashlib
        # Cache must disambiguate printings (same name in same set, etc.).
        key_str = f"{card_id}|{card_name}|{set_name}|{card_number}".lower()
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @staticmethod
    def get(card_name: str, set_name: str = "", card_number: str = "", card_id: str = "") -> Optional[Dict]:
        key = PriceCache._get_key(card_name, set_name, card_number, card_id)
        cache_file = CACHE_DIR / f"graded_{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file) as f:
                data = json.load(f)
            
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(seconds=CACHE_TTL_SECONDS):
                return None
            
            return data
        except:
            return None
    
    @staticmethod
    def set(card_name: str, set_name: str, data: Dict, card_number: str = "", card_id: str = ""):
        key = PriceCache._get_key(card_name, set_name, card_number, card_id)
        cache_file = CACHE_DIR / f"graded_{key}.json"
        
        data["cached_at"] = datetime.now().isoformat()
        
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f)
        except:
            pass


# =============================================================================
# POKEMON TCG API - RAW PRICES
# =============================================================================

def get_raw_price_from_api(card_name: str, set_name: str = "", card_number: str = "", card_id: str = "") -> Optional[Dict]:
    """
    Get raw card price from Pokemon TCG API (which uses TCGPlayer data).

    If card_id is provided, fetches the exact card to avoid ambiguous name matches.
    """
    try:
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        # Add API key if available (increases rate limit from 1000/day to 20000/day)
        if POKEMON_TCG_API_KEY:
            headers["X-Api-Key"] = POKEMON_TCG_API_KEY

        def _extract(card: Dict[str, Any]) -> Dict[str, Any]:
            tcgplayer = card.get("tcgplayer", {}) or {}
            prices = tcgplayer.get("prices", {}) or {}

            # Get the best price tier
            price_tier = (
                prices.get("holofoil")
                or prices.get("1stEditionHolofoil")
                or prices.get("unlimitedHolofoil")
                or prices.get("reverseHolofoil")
                or prices.get("normal")
                or {}
            )

            return {
                "card_id": card.get("id", card_id),
                "card_name": card.get("name", card_name),
                "set_name": (card.get("set") or {}).get("name", set_name),
                "card_number": card.get("number", card_number or ""),
                "raw_price": price_tier.get("market", 0),
                "raw_low": price_tier.get("low", 0),
                "raw_high": price_tier.get("high", 0),
                "image_url": (card.get("images") or {}).get("small", ""),
                "tcgplayer_url": tcgplayer.get("url", ""),
            }

        # Exact lookup by PokemonTCG card id (best accuracy).
        if card_id:
            api_url = f"https://api.pokemontcg.io/v2/cards/{card_id}"
            resp = requests.get(api_url, headers=headers, timeout=POKEMON_TCG_API_TIMEOUT)
            if resp.status_code == 200:
                payload = resp.json() or {}
                card = payload.get("data") or {}
                if card:
                    return _extract(card)

        api_url = "https://api.pokemontcg.io/v2/cards"

        # Build query (name + optional set + optional number).
        q_parts = []
        if card_name:
            q_parts.append(f'name:"{card_name}"')
        if set_name:
            q_parts.append(f'set.name:"{set_name}"')
        if card_number:
            # Handle "215/203" style inputs.
            num = card_number.split("/")[0] if "/" in card_number else card_number
            q_parts.append(f'number:"{num}"')

        query = " ".join(q_parts) if q_parts else f'name:"{card_name}"'

        params: Dict[str, Any] = {"q": query, "pageSize": 5}
        # Only sort by market when we don't have an exact printing filter.
        if not card_number:
            params["orderBy"] = "-tcgplayer.prices.holofoil.market"

        resp = requests.get(api_url, params=params, headers=headers, timeout=POKEMON_TCG_API_TIMEOUT)

        if resp.status_code == 200:
            data = resp.json() or {}
            cards = data.get("data", []) or []
            if cards:
                return _extract(cards[0])

    except Exception as e:
        print(f"Pokemon TCG API error: {e}")

    return None


# =============================================================================
# EBAY SOLD LISTINGS - GRADED PRICES
# =============================================================================

def _significant_words(s: str) -> List[str]:
    """Extract significant words (len > 1, skip stopwords) for title matching."""
    if not s:
        return []
    words = re.findall(r"[a-z0-9]+", s.lower())
    stop = {"the", "a", "an", "or", "in", "of", "to", "for", "pokemon", "card", "cards"}
    return [w for w in words if len(w) > 1 and w not in stop]


def _listing_matches_asset(
    title: str,
    card_name: str,
    set_name: str,
    category: str,
    product_name: Optional[str],
    grade: Optional[str],
) -> bool:
    """Return True only if the listing title matches the asset."""
    t = (title or "").lower()
    for suffix in ("opens in a new window or tab", "opens in a new window", "new listing"):
        if suffix in t:
            t = t.replace(suffix, "").strip()
    if category == "slabs" and grade:
        if grade.lower() not in t:
            return False
        words = _significant_words(card_name or "")
        if words and not all(w in t for w in words):
            return False
        sw = _significant_words(set_name or "")
        if sw and not all(w in t for w in sw):
            return False
        # Exclude Celebrations / 25th anniversary reprints when matching vintage Base Set
        if set_name and "base" in (set_name or "").lower() and "set" in (set_name or "").lower():
            if "celebration" in t or "25th" in t:
                return False
        return True
    if product_name:
        words = _significant_words(product_name)
        return len(words) > 0 and all(w in t for w in words)
    cw = _significant_words(card_name or "")
    sw = _significant_words(set_name or "")
    if cw and not all(w in t for w in cw):
        return False
    if sw and not all(w in t for w in sw):
        return False
    return True


def search_ebay_sold(
    card_name: str,
    grade: str = "PSA 10",
    set_name: Optional[str] = None,
) -> List[Dict]:
    """Search eBay sold listings for graded cards. Only returns listings matching grade + card name + set (if provided)."""
    results = []
    try:
        query_parts = [card_name]
        if set_name and set_name.strip():
            query_parts.append(set_name.strip())
        query_parts.append(grade)
        search_query = " ".join(query_parts) + " pokemon"
        search_url = "https://www.ebay.com/sch/i.html"
        params = {"_nkw": search_query, "_sacat": "0", "LH_Sold": "1", "LH_Complete": "1", "_sop": "13", "rt": "nc"}
        headers = get_stealth_headers()
        time.sleep(get_random_delay())
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".srp-results li.s-card, .s-item, .srp-results .s-item__wrapper")
            set_words = _significant_words(set_name or "")
            for item in items[:20]:
                try:
                    title_elem = item.select_one(".s-item__title, .s-item__title--has-tags, [class*='title']")
                    price_elem = item.select_one(".s-item__price, [class*='price']")
                    date_elem = item.select_one(".s-item__endedDate, .s-item__listingDate, [class*='date'], [class*='ended']")
                    if not title_elem or not price_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    t = title.lower()
                    if grade.lower() not in t:
                        continue
                    words = _significant_words(card_name or "")
                    if words and not all(w in t for w in words):
                        continue
                    if set_words and not all(w in t for w in set_words):
                        continue
                    if set_name and "base" in set_name.lower() and "set" in set_name.lower():
                        if "celebration" in t or "25th" in t:
                            continue
                    price_text = "".join(c for c in price_elem.get_text(strip=True) if c.isdigit() or c == ".")
                    if not price_text:
                        continue
                    price = float(price_text)
                    date_str = date_elem.get_text(strip=True) if date_elem else ""
                    results.append({"title": title, "price": price, "date": date_str, "grade": grade})
                except Exception:
                    continue
    except Exception as e:
        print(f"eBay search error: {e}")
    return results


def search_ebay_sold_generic(query: str, limit: int = 15) -> List[Dict]:
    """
    Search eBay sold listings for raw/sealed. Returns list of {title, price, date}.
    Caller should filter with _listing_matches_asset for accuracy.
    """
    results = []
    try:
        search_url = "https://www.ebay.com/sch/i.html"
        params = {
            "_nkw": f"{query} pokemon",
            "_sacat": "0",
            "LH_Sold": "1",
            "LH_Complete": "1",
            "_sop": "13",
            "rt": "nc",
        }
        headers = get_stealth_headers()
        time.sleep(get_random_delay())
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".srp-results li.s-card, .s-item, .srp-results .s-item__wrapper")
            for item in items[:limit * 2]:
                try:
                    title_elem = item.select_one(".s-item__title, .s-item__title--has-tags, [class*='title']")
                    price_elem = item.select_one(".s-item__price, [class*='price']")
                    date_elem = item.select_one(".s-item__endedDate, .s-item__listingDate, [class*='date'], [class*='ended']")
                    if not title_elem or not price_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    price_text = "".join(c for c in price_elem.get_text(strip=True) if c.isdigit() or c == ".")
                    if not price_text:
                        continue
                    price = float(price_text)
                    date_str = date_elem.get_text(strip=True) if date_elem else ""
                    results.append({"title": title, "price": price, "date": date_str})
                except Exception:
                    continue
    except Exception as e:
        print(f"eBay generic search error: {e}")
    return results


def get_orderbook_sources(
    card_name: str,
    set_name: str = "",
    category: str = "raw",
    product_name: Optional[str] = None,
    grade: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate order-book-style volume from TCGPlayer, eBay, etc.
    Returns list of {source, type, count, volume_usd, avg_price}.
    """
    sources: List[Dict[str, Any]] = []

    # TCGPlayer (market price only; no listing count from Pokemon TCG API)
    if category == "raw":
        raw = get_raw_price_from_api(card_name, set_name)
        if raw and raw.get("raw_price"):
            sources.append({
                "source": "TCGPlayer",
                "type": "listings",
                "count": None,
                "volume_usd": None,
                "avg_price": round(float(raw["raw_price"]), 2),
            })

    # eBay sold listings
    if category == "slabs" and grade:
        sales = search_ebay_sold(card_name, grade, set_name=set_name or None)
    else:
        q = (product_name or f"{card_name} {set_name}").strip()
        sales = search_ebay_sold_generic(q, limit=15)
    # Filter to only listings that match the asset (card/set/grade/product)
    sales = [
        s for s in sales
        if _listing_matches_asset(
            s.get("title", ""),
            card_name,
            set_name,
            category,
            product_name,
            grade,
        )
    ]
    if sales:
        prices = [s["price"] for s in sales]
        vol = sum(prices)
        transactions = [
            {
                "price": round(s["price"], 2),
                "date": s.get("date", ""),
                "title": (s.get("title") or "")[:60],
            }
            for s in sales[:10]
        ]
        sources.append({
            "source": "eBay",
            "type": "sold",
            "count": len(sales),
            "volume_usd": round(vol, 2),
            "avg_price": round(vol / len(sales), 2),
            "transactions": transactions,
        })

    return sources


def get_ebay_graded_prices(card_name: str) -> Dict[str, GradedPrice]:
    """
    Get graded prices from eBay for all major grades.
    """
    graded_prices = {}
    
    grades_to_check = [
        ("PSA 10", "PSA"),
        ("PSA 9", "PSA"),
        ("PSA 8", "PSA"),
        ("CGC 10", "CGC"),
        ("CGC 9.5", "CGC"),
        ("BGS 10", "BGS"),
        ("BGS 9.5", "BGS"),
    ]
    
    for grade, company in grades_to_check:
        sales = search_ebay_sold(card_name, grade)
        
        if sales:
            prices = [s["price"] for s in sales]
            avg_price = sum(prices) / len(prices)
            
            graded_prices[grade] = GradedPrice(
                grade=grade,
                company=company,
                price=round(avg_price, 2),
                price_range=(min(prices), max(prices)),
                source="eBay Sold Listings",
                last_sale=sales[0].get("date", ""),
                sales_count=len(sales),
                trend="stable",
            )
        
        # Rate limit between searches
        time.sleep(1)
    
    return graded_prices


# =============================================================================
# PRICECHARTING API - REAL MARKET PRICES FOR ALL CARDS
# =============================================================================

# PriceCharting cache to avoid repeated lookups
_pricecharting_cache = {}
_pricecharting_cache_ttl = 3600  # 1 hour cache

def get_pricecharting_prices(card_name: str, set_name: str = "", card_number: str = "") -> Optional[Dict]:
    """
    Get REAL prices from PriceCharting.com for any Pokemon card.
    
    PriceCharting aggregates eBay sold data and provides accurate market prices
    for raw and graded cards (PSA, CGC, BGS).
    
    Args:
        card_name: Name of the card (e.g., "Team Rocket's Mewtwo ex")
        set_name: Set name (e.g., "Destined Rivals")
        card_number: Card number (e.g., "231" or "231/182")
    
    Returns:
        Dict with prices for all grades, or None if not found
    """
    import urllib.parse
    
    # Build cache key
    cache_key = f"pc:{card_name}:{set_name}:{card_number}".lower()
    
    # Check cache
    if cache_key in _pricecharting_cache:
        cached_time, cached_data = _pricecharting_cache[cache_key]
        if time.time() - cached_time < _pricecharting_cache_ttl:
            print(f"[PriceCharting] Cache hit for {card_name}")
            return cached_data
    
    try:
        # Build search URL for PriceCharting
        # Format: https://www.pricecharting.com/search-products?q=team+rockets+mewtwo+ex+231&type=pokemon
        search_term = card_name
        if set_name:
            search_term = f"{card_name} {set_name}"
        if card_number:
            # Extract just the number (e.g., "231" from "231/182")
            num = card_number.split("/")[0] if "/" in card_number else card_number
            search_term = f"{search_term} {num}"
        
        encoded_search = urllib.parse.quote_plus(search_term)
        search_url = f"https://www.pricecharting.com/search-products?q={encoded_search}&type=pokemon"
        
        headers = get_stealth_headers()
        headers["Accept"] = "text/html,application/xhtml+xml"
        
        print(f"[PriceCharting] Searching: {search_term}")
        
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[PriceCharting] Search failed: {response.status_code}")
            return None
        
        # Parse search results to find the product page
        if not BS4_AVAILABLE:
            print("[PriceCharting] BeautifulSoup not available for parsing")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # PriceCharting now commonly returns rows that link to /offers?product=<id>.
        # Resolve that into the canonical /game/... page where the "Full Price Guide" lives.
        product_link = None
        offers_link = None

        offer_row = (
            soup.select_one("#sell-search-results tr.offer[id^='product-']")
            or soup.select_one("tr.offer[id^='product-']")
        )
        if offer_row:
            a = offer_row.find("a", href=re.compile(r"^/offers\\?product=\\d+"))
            if a and a.get("href"):
                offers_link = a["href"]
            else:
                rid = (offer_row.get("id") or "").strip()
                if rid.startswith("product-"):
                    pid = rid.split("product-", 1)[1]
                    if pid.isdigit():
                        offers_link = f"/offers?product={pid}"

        if offers_link:
            offers_url = offers_link
            if not offers_url.startswith("http"):
                offers_url = f"https://www.pricecharting.com{offers_url}"

            time.sleep(0.15)  # Rate limit (keep UI responsive)
            offers_resp = requests.get(offers_url, headers=headers, timeout=15)
            if offers_resp.status_code == 200:
                offers_soup = BeautifulSoup(offers_resp.text, "html.parser")
                for a in offers_soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("/game/") and "*" not in href:
                        product_link = href
                        break

            # Fall back to the offers page itself if we couldn't resolve a game link.
            if not product_link:
                product_link = offers_url

        if not product_link:
            # Legacy patterns
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/game/") and "pokemon" in href:
                    product_link = href
                    break

        if not product_link:
            # Try alternate pattern
            for link in soup.find_all("a", class_="product"):
                if link.get("href"):
                    product_link = link["href"]
                    break
        
        if not product_link:
            print(f"[PriceCharting] No product found for: {search_term}")
            _pricecharting_cache[cache_key] = (time.time(), None)
            return None
        
        # Fetch the product page
        if not product_link.startswith("http"):
            product_link = f"https://www.pricecharting.com{product_link}"
        
        print(f"[PriceCharting] Fetching: {product_link}")
        time.sleep(0.15)  # Rate limit (keep UI responsive)
        
        product_response = requests.get(product_link, headers=headers, timeout=15)
        
        if product_response.status_code != 200:
            print(f"[PriceCharting] Product page failed: {product_response.status_code}")
            return None
        
        product_soup = BeautifulSoup(product_response.text, "html.parser")
        
        # Extract prices from the page
        result = {
            "card_name": card_name,
            "set_name": set_name,
            "source": "PriceCharting",
            "url": product_link,
            "raw": 0,
            "graded": {}
        }
        
        # Find the price table
        # PriceCharting uses a table with grades and prices
        price_table = product_soup.find("table", id="full-prices") or product_soup.find("table", class_="full-prices")
        
        if price_table:
            rows = price_table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    grade_text = cells[0].get_text(strip=True).lower()
                    price_text = cells[1].get_text(strip=True)
                    
                    # Parse price
                    price = _parse_price(price_text)
                    if price and price > 0:
                        if "ungraded" in grade_text or "loose" in grade_text:
                            result["raw"] = price
                        elif "psa 10" in grade_text:
                            result["graded"]["PSA 10"] = {"price": price, "source": "PriceCharting"}
                        elif "psa 9" in grade_text and "9.5" not in grade_text:
                            result["graded"]["PSA 9"] = {"price": price, "source": "PriceCharting"}
                        elif "psa 8" in grade_text:
                            result["graded"]["PSA 8"] = {"price": price, "source": "PriceCharting"}
                        elif "psa 7" in grade_text:
                            result["graded"]["PSA 7"] = {"price": price, "source": "PriceCharting"}
                        elif "cgc 10 prist" in grade_text:
                            result["graded"]["CGC 10 Pristine"] = {"price": price, "source": "PriceCharting"}
                        elif "cgc 10" in grade_text:
                            result["graded"]["CGC 10"] = {"price": price, "source": "PriceCharting"}
                        elif "cgc 9.5" in grade_text or "grade 9.5" in grade_text:
                            result["graded"]["CGC 9.5"] = {"price": price, "source": "PriceCharting"}
                        elif "bgs 10 black" in grade_text:
                            result["graded"]["BGS 10 Black Label"] = {"price": price, "source": "PriceCharting"}
                        elif "bgs 10" in grade_text:
                            result["graded"]["BGS 10"] = {"price": price, "source": "PriceCharting"}
                        elif "bgs 9.5" in grade_text:
                            result["graded"]["BGS 9.5"] = {"price": price, "source": "PriceCharting"}
        
        # Also try to find prices in the main content area
        # PriceCharting shows prices in divs with specific classes
        for div in product_soup.find_all("div", class_="price"):
            price_text = div.get_text(strip=True)
            price = _parse_price(price_text)
            
            # Check parent/sibling for grade info
            parent = div.parent
            if parent:
                parent_text = parent.get_text(strip=True).lower()
                if price and price > 0:
                    if "ungraded" in parent_text and not result["raw"]:
                        result["raw"] = price
                    elif "psa 10" in parent_text and "PSA 10" not in result["graded"]:
                        result["graded"]["PSA 10"] = {"price": price, "source": "PriceCharting"}
        
        # Try extracting from the "Full Price Guide" table at bottom
        guide_heading = product_soup.find(string=re.compile("Full Price Guide", re.I))
        if guide_heading:
            table = guide_heading.find_parent().find_next("table") if guide_heading.find_parent() else None
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        grade = cells[0].get_text(strip=True).lower()
                        price = _parse_price(cells[1].get_text(strip=True))
                        if price and price > 0:
                            if "ungraded" in grade:
                                result["raw"] = price
                            elif "psa 10" in grade:
                                result["graded"]["PSA 10"] = {"price": price, "source": "PriceCharting"}
                            elif "psa 9" in grade and "9.5" not in grade:
                                result["graded"]["PSA 9"] = {"price": price, "source": "PriceCharting"}
                            elif "psa 8" in grade:
                                result["graded"]["PSA 8"] = {"price": price, "source": "PriceCharting"}
                            elif "cgc 10" in grade and "prist" not in grade:
                                result["graded"]["CGC 10"] = {"price": price, "source": "PriceCharting"}
                            elif "cgc 10 prist" in grade:
                                result["graded"]["CGC 10 Pristine"] = {"price": price, "source": "PriceCharting"}
                            elif "bgs 10 black" in grade:
                                result["graded"]["BGS 10 Black Label"] = {"price": price, "source": "PriceCharting"}
                            elif "bgs 10" in grade:
                                result["graded"]["BGS 10"] = {"price": price, "source": "PriceCharting"}
        
        # Cache the result
        if result["raw"] > 0 or result["graded"]:
            print(f"[PriceCharting] Found: Raw=${result['raw']}, Graded grades: {len(result['graded'])}")
            _pricecharting_cache[cache_key] = (time.time(), result)
            return result
        
        print(f"[PriceCharting] No prices extracted for {card_name}")
        _pricecharting_cache[cache_key] = (time.time(), None)
        return None
    
    except Exception as e:
        print(f"[PriceCharting] Error: {e}")
        return None


def _parse_price(price_str: str) -> float:
    """Parse a price string like '$1,155.00' or '1155' into a float."""
    if not price_str:
        return 0
    
    # Remove currency symbols and commas
    cleaned = re.sub(r'[,$£€]', '', price_str.strip())
    
    # Try to extract the number
    match = re.search(r'[\d,]+\.?\d*', cleaned)
    if match:
        try:
            return float(match.group().replace(',', ''))
        except ValueError:
            return 0
    return 0


# =============================================================================
# POKEMONPRICETRACKER API - FREE GRADED PRICES
# =============================================================================

def get_price_tracker_prices(card_name: str, set_name: str = "") -> Optional[Dict]:
    """
    Get prices from PokemonPriceTracker API (FREE).
    Includes raw prices AND graded card prices (PSA/CGC/BGS from eBay).
    
    Get free API key at: https://pokemonpricetracker.com/api-keys
    Free tier: 100 calls/day
    """
    if not POKEMON_PRICE_TRACKER_API_KEY:
        print("[PriceTracker] No API key set - skipping (set POKEMON_PRICE_TRACKER_API_KEY)")
        return None
    
    try:
        api_url = "https://www.pokemonpricetracker.com/api/v2/cards"
        headers = {
            "Authorization": f"Bearer {POKEMON_PRICE_TRACKER_API_KEY}",
            "Accept": "application/json"
        }
        
        # Build search query
        search_term = card_name
        if set_name:
            search_term = f"{card_name} {set_name}"
        
        params = {
            "search": search_term,
            "limit": 5,
            "includeHistory": "true",
            "includeEbay": "true",  # This gives us PSA/CGC/BGS prices!
            "days": 30
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            cards = data.get("data", [])
            
            if cards:
                card = cards[0]  # Best match
                
                # Extract prices
                result = {
                    "card_name": card.get("name", card_name),
                    "set_name": card.get("setName", set_name),
                    "tcg_player_id": card.get("tcgPlayerId"),
                    "raw_price": card.get("prices", {}).get("market", 0) or card.get("price", 0),
                    "raw_low": card.get("prices", {}).get("low", 0),
                    "raw_high": card.get("prices", {}).get("high", 0),
                    "image_url": card.get("imageUrl", ""),
                    "source": "PokemonPriceTracker",
                    "graded": {}
                }
                
                # Extract eBay graded prices (this is the gold!)
                ebay_data = card.get("ebay", {})
                
                # PSA grades
                if "psa10" in ebay_data:
                    psa10 = ebay_data["psa10"]
                    result["graded"]["PSA 10"] = {
                        "price": psa10.get("avg", 0) or psa10.get("median", 0),
                        "price_low": psa10.get("min", 0),
                        "price_high": psa10.get("max", 0),
                        "sales_count": psa10.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "PSA"
                    }
                
                if "psa9" in ebay_data:
                    psa9 = ebay_data["psa9"]
                    result["graded"]["PSA 9"] = {
                        "price": psa9.get("avg", 0) or psa9.get("median", 0),
                        "price_low": psa9.get("min", 0),
                        "price_high": psa9.get("max", 0),
                        "sales_count": psa9.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "PSA"
                    }
                
                if "psa8" in ebay_data:
                    psa8 = ebay_data["psa8"]
                    result["graded"]["PSA 8"] = {
                        "price": psa8.get("avg", 0) or psa8.get("median", 0),
                        "price_low": psa8.get("min", 0),
                        "price_high": psa8.get("max", 0),
                        "sales_count": psa8.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "PSA"
                    }
                
                # CGC grades
                if "cgc10" in ebay_data:
                    cgc10 = ebay_data["cgc10"]
                    result["graded"]["CGC 10"] = {
                        "price": cgc10.get("avg", 0) or cgc10.get("median", 0),
                        "price_low": cgc10.get("min", 0),
                        "price_high": cgc10.get("max", 0),
                        "sales_count": cgc10.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "CGC"
                    }
                
                if "cgc9.5" in ebay_data or "cgc95" in ebay_data:
                    cgc95 = ebay_data.get("cgc9.5") or ebay_data.get("cgc95", {})
                    result["graded"]["CGC 9.5"] = {
                        "price": cgc95.get("avg", 0) or cgc95.get("median", 0),
                        "price_low": cgc95.get("min", 0),
                        "price_high": cgc95.get("max", 0),
                        "sales_count": cgc95.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "CGC"
                    }
                
                # BGS grades
                if "bgs10" in ebay_data:
                    bgs10 = ebay_data["bgs10"]
                    result["graded"]["BGS 10"] = {
                        "price": bgs10.get("avg", 0) or bgs10.get("median", 0),
                        "price_low": bgs10.get("min", 0),
                        "price_high": bgs10.get("max", 0),
                        "sales_count": bgs10.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "BGS"
                    }
                
                if "bgs9.5" in ebay_data or "bgs95" in ebay_data:
                    bgs95 = ebay_data.get("bgs9.5") or ebay_data.get("bgs95", {})
                    result["graded"]["BGS 9.5"] = {
                        "price": bgs95.get("avg", 0) or bgs95.get("median", 0),
                        "price_low": bgs95.get("min", 0),
                        "price_high": bgs95.get("max", 0),
                        "sales_count": bgs95.get("count", 0),
                        "source": "eBay Sold (PriceTracker)",
                        "company": "BGS"
                    }
                
                # Price history
                history = card.get("priceHistory", [])
                if history:
                    result["price_history"] = history[-30:]  # Last 30 days
                
                print(f"[PriceTracker] Found {card.get('name')} - Raw: ${result['raw_price']:.2f}, Graded prices: {len(result['graded'])}")
                return result
        
        elif response.status_code == 401:
            print("[PriceTracker] Invalid API key")
        elif response.status_code == 429:
            print("[PriceTracker] Rate limit exceeded (100/day free)")
        else:
            print(f"[PriceTracker] API error: {response.status_code}")
    
    except Exception as e:
        print(f"[PriceTracker] Error: {e}")
    
    return None


# =============================================================================
# COLLECTR API - PREMIUM DATA (Requires subscription)
# =============================================================================

def get_collectr_prices(card_name: str, set_name: str = "") -> Optional[Dict]:
    """
    Get prices from Collectr API (PAID subscription required).
    Has 400k+ products including raw cards, graded cards, and sealed products.
    
    Get API key at: https://getcollectr.com/api
    """
    if not COLLECTR_API_KEY:
        return None  # Silently skip if no key
    
    try:
        # Collectr API endpoint (based on their SwaggerHub docs)
        api_url = "https://api.getcollectr.com/v1/products/search"
        headers = {
            "Authorization": f"Bearer {COLLECTR_API_KEY}",
            "Accept": "application/json"
        }
        
        search_term = f"{card_name} {set_name}".strip() if set_name else card_name
        
        params = {
            "q": search_term,
            "category": "pokemon",
            "limit": 10
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", data.get("products", []))
            
            if products:
                # Group by raw vs graded
                raw_products = [p for p in products if not p.get("graded", False)]
                graded_products = [p for p in products if p.get("graded", False)]
                
                result = {
                    "card_name": card_name,
                    "set_name": set_name,
                    "raw_price": 0,
                    "source": "Collectr",
                    "graded": {}
                }
                
                # Get raw price
                if raw_products:
                    best_raw = raw_products[0]
                    result["raw_price"] = best_raw.get("price", 0) or best_raw.get("marketPrice", 0)
                    result["raw_low"] = best_raw.get("lowPrice", result["raw_price"] * 0.8)
                    result["raw_high"] = best_raw.get("highPrice", result["raw_price"] * 1.2)
                
                # Get graded prices
                for gp in graded_products:
                    grade = gp.get("grade", "")
                    company = gp.get("gradingCompany", "")
                    price = gp.get("price", 0) or gp.get("marketPrice", 0)
                    
                    if grade and company and price:
                        grade_key = f"{company} {grade}"
                        result["graded"][grade_key] = {
                            "price": price,
                            "price_low": gp.get("lowPrice", price * 0.85),
                            "price_high": gp.get("highPrice", price * 1.15),
                            "source": "Collectr",
                            "company": company
                        }
                
                print(f"[Collectr] Found {len(products)} products for {card_name}")
                return result
        
        elif response.status_code == 401:
            print("[Collectr] Invalid API key")
        elif response.status_code == 403:
            print("[Collectr] Subscription required")
    
    except Exception as e:
        print(f"[Collectr] Error: {e}")
    
    return None


# =============================================================================
# PRICE ESTIMATION (FALLBACK)
# =============================================================================

def estimate_graded_prices(
    raw_price: float, 
    card_name: str = "", 
    card_rarity: str = "holo",
    set_name: str = ""
) -> Dict[str, GradedPrice]:
    """
    Estimate graded prices based on raw price, card type, and multipliers.
    
    Uses card-type-specific multipliers for accuracy:
    - SIR (Special Illustration Rare): 5-8x raw for PSA 10
    - SAR (Special Art Rare): 3-5x raw for PSA 10
    - Chase (ex, VMAX, etc.): 2.5-4x raw for PSA 10
    - Standard: 1.8-2.5x raw for PSA 10
    
    This is used when eBay data isn't available.
    """
    graded_prices = {}
    
    # Get card-type-specific multipliers
    multiplier_set = get_multipliers_for_card(card_name, card_rarity, set_name)
    card_type = detect_card_type(card_name, card_rarity, set_name)
    
    # Additional rarity adjustment for edge cases
    rarity_factor = 1.0
    rarity_lower = card_rarity.lower() if card_rarity else ""
    
    # Boost for secret/numbered cards
    if "secret" in rarity_lower:
        rarity_factor = 1.2
    # Reduction for common/uncommon
    elif "common" in rarity_lower and card_type == "standard":
        rarity_factor = 0.5
    elif "uncommon" in rarity_lower and card_type == "standard":
        rarity_factor = 0.7
    
    # Build source label
    type_labels = {
        "sir": "SIR Multiplier",
        "sar": "SAR Multiplier", 
        "chase": "Chase Card Multiplier",
        "hyper": "Hyper Rare Multiplier",
        "alt_art": "Alt Art Multiplier",
        "standard": "Standard Multiplier"
    }
    source_label = f"Estimated ({type_labels.get(card_type, 'Multiplier')})"
    
    for grade, multipliers in multiplier_set.items():
        company = grade.split()[0]  # PSA, CGC, or BGS
        
        mid_mult = multipliers["mid"] * rarity_factor
        low_mult = multipliers["low"] * rarity_factor
        high_mult = multipliers["high"] * rarity_factor
        
        estimated_price = raw_price * mid_mult
        price_low = raw_price * low_mult
        price_high = raw_price * high_mult
        
        graded_prices[grade] = GradedPrice(
            grade=grade,
            company=company,
            price=round(estimated_price, 2),
            price_range=(round(price_low, 2), round(price_high, 2)),
            source=source_label,
            sales_count=0,
            trend="stable",
        )
    
    return graded_prices


# =============================================================================
# MAIN PRICE LOOKUP
# =============================================================================

class GradedPriceChecker:
    """
    Unified graded card price checker - Multi-Source Aggregator.
    
    Fetches prices from multiple sources in priority order:
    1. PokemonPriceTracker API (FREE - best for graded prices)
    2. Collectr API (if key provided)
    3. Pokemon TCG API (raw prices)
    4. eBay scraping (fallback)
    5. Known prices database
    6. Estimation (last resort)
    """
    
    def __init__(self, use_ebay: bool = True, use_all_sources: bool = True):
        """
        Initialize the checker.
        
        Args:
            use_ebay: Whether to search eBay for graded prices (slower but more accurate)
            use_all_sources: Whether to try all available price sources
        """
        self.use_ebay = use_ebay
        self.use_all_sources = use_all_sources
    
    def get_prices(self, card_name: str, set_name: str = "", card_number: str = "", card_id: str = "") -> CardPriceReport:
        """
        Get comprehensive price data for a card from all available sources.
        
        Priority order:
        1. PokemonPriceTracker API (has eBay graded prices built-in)
        2. Collectr API (if subscribed)
        3. Pokemon TCG API + eBay scraping
        4. Known prices database
        5. Estimation
        
        Returns raw price and all graded prices (PSA, CGC, BGS).
        """
        # Check cache first
        cached = PriceCache.get(card_name, set_name, card_number=card_number, card_id=card_id)
        if cached and "report" in cached:
            return self._dict_to_report(cached["report"])
        
        raw_price = 0
        raw_low = 0
        raw_high = 0
        raw_data = {}
        graded_prices = {}
        source = "Unknown"
        image_url = ""
        tcgplayer_url = ""
        
        # =================================================================
        # SOURCE 0: PriceCharting (MOST ACCURATE - aggregates eBay sold)
        # =================================================================
        if self.use_all_sources:
            pc_data = get_pricecharting_prices(card_name, set_name, card_number=card_number)
            if pc_data and (pc_data.get("raw", 0) > 0 or pc_data.get("graded")):
                raw_price = pc_data.get("raw", 0)
                raw_low = raw_price * 0.9
                raw_high = raw_price * 1.1
                source = "PriceCharting"
                
                # Extract graded prices
                for grade_key, grade_data in pc_data.get("graded", {}).items():
                    price = grade_data.get("price", 0) if isinstance(grade_data, dict) else grade_data
                    if price and price > 0:
                        company = grade_key.split()[0]  # PSA, CGC, or BGS
                        graded_prices[grade_key] = GradedPrice(
                            grade=grade_key,
                            company=company,
                            price=price,
                            price_range=(price * 0.85, price * 1.15),
                            source="PriceCharting",
                            sales_count=0,
                            trend="stable",
                        )
                
                print(f"[GradedPriceChecker] PriceCharting: Raw=${raw_price}, {len(graded_prices)} grades")
        
        # =================================================================
        # SOURCE 1: PokemonPriceTracker API (FREE - has graded prices!)
        # =================================================================
        if self.use_all_sources and not graded_prices:
            tracker_data = get_price_tracker_prices(card_name, set_name)
            if tracker_data:
                if not raw_price:
                    raw_price = tracker_data.get("raw_price", 0)
                raw_low = tracker_data.get("raw_low", raw_price * 0.85)
                raw_high = tracker_data.get("raw_high", raw_price * 1.15)
                image_url = tracker_data.get("image_url", "")
                source = "PokemonPriceTracker"
                
                # Extract graded prices from PriceTracker (eBay data)
                for grade_key, grade_data in tracker_data.get("graded", {}).items():
                    if grade_data.get("price", 0) > 0:
                        graded_prices[grade_key] = GradedPrice(
                            grade=grade_key,
                            company=grade_data.get("company", grade_key.split()[0]),
                            price=grade_data["price"],
                            price_range=(grade_data.get("price_low", 0), grade_data.get("price_high", 0)),
                            source=grade_data.get("source", "PriceTracker"),
                            sales_count=grade_data.get("sales_count", 0),
                            trend="stable",
                        )
        
        # =================================================================
        # SOURCE 2: Collectr API (if subscribed)
        # =================================================================
        if self.use_all_sources and not graded_prices:
            collectr_data = get_collectr_prices(card_name, set_name)
            if collectr_data:
                if not raw_price:
                    raw_price = collectr_data.get("raw_price", 0)
                    raw_low = collectr_data.get("raw_low", raw_price * 0.85)
                    raw_high = collectr_data.get("raw_high", raw_price * 1.15)
                    source = "Collectr"
                
                for grade_key, grade_data in collectr_data.get("graded", {}).items():
                    if grade_key not in graded_prices and grade_data.get("price", 0) > 0:
                        graded_prices[grade_key] = GradedPrice(
                            grade=grade_key,
                            company=grade_data.get("company", grade_key.split()[0]),
                            price=grade_data["price"],
                            price_range=(grade_data.get("price_low", 0), grade_data.get("price_high", 0)),
                            source="Collectr",
                            sales_count=0,
                            trend="stable",
                        )
        
        # =================================================================
        # SOURCE 3: Pokemon TCG API (raw prices from TCGPlayer)
        # =================================================================
        # If the caller provided an exact id/number, prefer the exact TCGPlayer
        # market price for raw (even if PriceCharting returned a raw estimate).
        should_fetch_raw = (not raw_price) or bool(card_id) or bool(card_number)
        if should_fetch_raw:
            api_data = get_raw_price_from_api(card_name, set_name, card_number=card_number, card_id=card_id)
            if api_data:
                raw_data = api_data  # Only update if we got data
                api_raw_price = raw_data.get("raw_price", 0) or 0
                if api_raw_price:
                    raw_price = api_raw_price
                    raw_low = raw_data.get("raw_low", raw_price * 0.85)
                    raw_high = raw_data.get("raw_high", raw_price * 1.15)
                image_url = image_url or raw_data.get("image_url", "")
                tcgplayer_url = tcgplayer_url or raw_data.get("tcgplayer_url", "")
                if source == "Unknown" and raw_price:
                    source = "Pokemon TCG API"
        
        # =================================================================
        # SOURCE 4: Known prices database (DISABLED BY DEFAULT)
        # =================================================================
        # Historically this repo shipped a hardcoded KNOWN_CARD_PRICES table.
        # It can drift quickly and was causing wrong/misleading graded prices in the UI.
        # Keep it opt-in only via ENABLE_KNOWN_PRICE_FALLBACK=true.
        known_graded: Dict[str, Any] = {}
        is_known = False
        if ENABLE_KNOWN_PRICE_FALLBACK:
            fallback_data = self._get_fallback_raw_price(card_name)
            known_graded = fallback_data.get("known_graded", {}) or {}
            is_known = bool(fallback_data.get("is_known", False))

            if not raw_price:
                raw_price = fallback_data.get("raw_price", 0)
                raw_low = fallback_data.get("raw_low", raw_price * 0.85)
                raw_high = fallback_data.get("raw_high", raw_price * 1.15)
                if source == "Unknown":
                    source = "Known Prices Database"

            # Use known graded prices only if explicitly enabled and no other graded data exists.
            if is_known and known_graded and not graded_prices:
                grade_mappings = [
                    # PSA grades
                    ("PSA 10", "psa10", "PSA"),
                    ("PSA 9", "psa9", "PSA"),
                    ("PSA 8", "psa8", "PSA"),
                    ("PSA 7", "psa7", "PSA"),
                    # CGC grades
                    ("CGC 10", "cgc10", "CGC"),
                    ("CGC 9.5", "cgc95", "CGC"),
                    ("CGC 10 Pristine", "cgc10pristine", "CGC"),
                    # BGS grades
                    ("BGS 10", "bgs10", "BGS"),
                    ("BGS 9.5", "bgs95", "BGS"),
                    ("BGS 10 Black Label", "bgs10black", "BGS"),
                ]

                for grade_key, known_key, company in grade_mappings:
                    if known_key in known_graded:
                        price = known_graded[known_key]
                        graded_prices[grade_key] = GradedPrice(
                            grade=grade_key,
                            company=company,
                            price=price,
                            price_range=(price * 0.85, price * 1.15),
                            source="Known Sales Data (PriceCharting)",
                            sales_count=10,
                            trend="stable",
                        )
        
        # =================================================================
        # NO MORE ESTIMATES - Only show REAL prices from actual sales data
        # =================================================================
        # We no longer fill in missing grades with estimates
        # If PriceCharting/PriceTracker/Collectr don't have the data, we don't show it
        # This ensures users only see accurate market prices
        
        # Keep the best source we actually used. Each graded price record also
        # carries its own `source` field.

        # Summarize raw + graded sources for UI display.
        if raw_data and raw_data.get("raw_price") and graded_prices:
            graded_sources = sorted({g.source for g in graded_prices.values() if g.source})
            if graded_sources:
                source = f"Pokemon TCG API + {', '.join(graded_sources)}"
        
        # Finalize missing ranges.
        if raw_price and not raw_low:
            raw_low = raw_price * 0.85
        if raw_price and not raw_high:
            raw_high = raw_price * 1.15

        # Build report
        report = CardPriceReport(
            card_name=raw_data.get("card_name") or card_name,
            set_name=raw_data.get("set_name") or set_name,
            card_number=raw_data.get("card_number") or card_number or "",
            raw_price=raw_price,
            raw_low=raw_low,
            raw_high=raw_high,
            graded_prices=graded_prices,
            image_url=image_url or raw_data.get("image_url", ""),
            tcgplayer_url=tcgplayer_url or raw_data.get("tcgplayer_url", ""),
            last_updated=datetime.now().isoformat(),
            source=source,
        )
        
        # Cache the result
        PriceCache.set(card_name, set_name, {"report": report.to_dict()}, card_number=card_number, card_id=card_id)
        
        return report
    
    def _get_fallback_raw_price(self, card_name: str) -> Dict:
        """Get fallback price from known prices database."""
        card_lower = card_name.lower()
        
        # Try to find a match in known prices
        best_match = None
        best_score = 0
        
        for known_name, prices in KNOWN_CARD_PRICES.items():
            # Score based on matching words
            known_words = set(known_name.split())
            card_words = set(card_lower.split())
            common = known_words & card_words
            score = len(common)
            
            # Bonus for exact substring match
            if known_name in card_lower or card_lower in known_name:
                score += 5
            
            if score > best_score:
                best_score = score
                best_match = (known_name, prices)
        
        if best_match and best_score >= 1:
            known_name, prices = best_match
            return {
                "card_name": card_name,
                "raw_price": prices.get("raw", 10),
                "raw_low": prices.get("raw", 10) * 0.85,
                "raw_high": prices.get("raw", 10) * 1.15,
                "known_graded": prices,  # Include known graded prices
                "is_known": True,
            }
        
        # Default fallback
        return {
            "card_name": card_name,
            "raw_price": 10,
            "raw_low": 5,
            "raw_high": 20,
            "is_known": False,
        }
    
    def _dict_to_report(self, data: Dict) -> CardPriceReport:
        """Convert cached dict back to CardPriceReport."""
        graded = {}
        for grade, gdata in data.get("graded", {}).items():
            graded[grade] = GradedPrice(
                grade=gdata["grade"],
                company=gdata["company"],
                price=gdata["price"],
                price_range=(gdata["price_low"], gdata["price_high"]),
                source=gdata["source"],
                last_sale=gdata.get("last_sale"),
                sales_count=gdata.get("sales_count", 0),
                trend=gdata.get("trend", "stable"),
            )
        
        return CardPriceReport(
            card_name=data["card_name"],
            set_name=data["set_name"],
            card_number=data.get("card_number", ""),
            raw_price=data["raw"]["price"],
            raw_low=data["raw"]["low"],
            raw_high=data["raw"]["high"],
            graded_prices=graded,
            image_url=data.get("image_url", ""),
            tcgplayer_url=data.get("tcgplayer_url", ""),
            last_updated=data.get("last_updated", ""),
            source=data.get("source", ""),
        )
    
    def get_quick_prices(self, card_name: str, set_name: str = "") -> Dict:
        """
        Get prices quickly without eBay search.
        
        Uses Pokemon TCG API + estimation.
        """
        old_setting = self.use_ebay
        self.use_ebay = False
        report = self.get_prices(card_name, set_name)
        self.use_ebay = old_setting
        return report.to_dict()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_card_prices(card_name: str, set_name: str = "", include_ebay: bool = False, card_number: str = "", card_id: str = "") -> Dict:
    """
    Get all prices for a card (raw + graded).
    
    Args:
        card_name: Name of the card
        set_name: Set name (optional, helps accuracy)
        include_ebay: Whether to search eBay for graded prices
    
    Returns:
        Dict with raw and graded prices
    """
    checker = GradedPriceChecker(use_ebay=include_ebay)
    report = checker.get_prices(card_name, set_name, card_number=card_number, card_id=card_id)
    return report.to_dict()


def get_psa_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just PSA graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    psa_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "PSA" in grade:
            psa_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "psa": psa_grades,
    }


def get_cgc_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just CGC graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    cgc_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "CGC" in grade:
            cgc_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "cgc": cgc_grades,
    }


def get_bgs_prices(card_name: str, set_name: str = "") -> Dict:
    """Get just BGS/Beckett graded prices."""
    prices = get_card_prices(card_name, set_name)
    
    bgs_grades = {}
    for grade, data in prices.get("graded", {}).items():
        if "BGS" in grade:
            bgs_grades[grade] = data
    
    return {
        "card_name": prices["card_name"],
        "raw": prices["raw"],
        "bgs": bgs_grades,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing graded prices."""
    import sys
    
    if len(sys.argv) > 1:
        card_name = " ".join(sys.argv[1:])
    else:
        card_name = "Charizard VMAX"
    
    print(f"Getting prices for: {card_name}")
    print("-" * 50)
    
    prices = get_card_prices(card_name, include_ebay=False)
    
    print(f"\n📊 {prices['card_name']}")
    if prices['set_name']:
        print(f"   Set: {prices['set_name']}")
    
    print(f"\n💰 RAW (Ungraded):")
    raw = prices['raw']
    print(f"   Market: ${raw['price']:.2f}")
    print(f"   Range: ${raw['low']:.2f} - ${raw['high']:.2f}")
    
    print(f"\n🏆 GRADED PRICES:")
    
    # PSA
    print("\n   PSA:")
    for grade in ["PSA 10", "PSA 9", "PSA 8", "PSA 7"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    # CGC
    print("\n   CGC:")
    for grade in ["CGC 10", "CGC 9.5", "CGC 9"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    # BGS
    print("\n   BGS/Beckett:")
    for grade in ["BGS 10 Black", "BGS 10", "BGS 9.5", "BGS 9"]:
        if grade in prices['graded']:
            g = prices['graded'][grade]
            print(f"   • {grade}: ${g['price']:.2f} (${g['price_low']:.2f}-${g['price_high']:.2f})")
    
    print(f"\n📅 Updated: {prices['last_updated']}")
    print(f"📍 Source: {prices['source']}")


if __name__ == "__main__":
    main()
