"""
Live price lookups from the Pokemon TCG API (v2).

This repo primarily uses the local SQLite snapshot (pokemon_tcg.db), but alerts
and other workflows may want to fetch the latest TCGPlayer market price for a
specific card id.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple

import httpx

API_BASE = "https://api.pokemontcg.io/v2"

POKEMON_TCG_TIMEOUT_SECONDS = float(os.environ.get("POKEMON_TCG_TIMEOUT_SECONDS", "15"))
LIVE_PRICE_CACHE_TTL_SECONDS = int(os.environ.get("LIVE_PRICE_CACHE_TTL_SECONDS", "60"))

_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # card_id -> (ts, card_json)


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/json", "User-Agent": "pokemon-card-agent/1.0"}
    api_key = (os.environ.get("POKEMON_TCG_API_KEY") or "").strip()
    if api_key:
        h["X-Api-Key"] = api_key
    return h


def fetch_card_by_id(card_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a PokemonTCG card by id (e.g. sv8pt5-161). Returns raw card JSON."""
    cid = (card_id or "").strip()
    if not cid:
        return None

    now = time.time()
    cached = _cache.get(cid)
    if cached and (now - cached[0]) < LIVE_PRICE_CACHE_TTL_SECONDS:
        return cached[1]

    url = f"{API_BASE}/cards/{cid}"
    try:
        with httpx.Client(timeout=POKEMON_TCG_TIMEOUT_SECONDS, headers=_headers()) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return None
        payload = resp.json() or {}
        card = payload.get("data")
        if not isinstance(card, dict):
            return None
        _cache[cid] = (now, card)
        return card
    except Exception:
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_tcgplayer_prices(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract TCGPlayer price tier from PokemonTCG card JSON.

    Returns:
        {market, low, mid, high, url}
    """
    tcg = (card or {}).get("tcgplayer") or {}
    prices = tcg.get("prices") or {}

    tier = (
        prices.get("holofoil")
        or prices.get("1stEditionHolofoil")
        or prices.get("unlimitedHolofoil")
        or prices.get("reverseHolofoil")
        or prices.get("normal")
        or {}
    )
    if not isinstance(tier, dict):
        tier = {}

    market = _to_float(tier.get("market")) or _to_float(prices.get("market"))
    low = _to_float(tier.get("low")) or _to_float(prices.get("low"))
    mid = _to_float(tier.get("mid")) or _to_float(prices.get("mid"))
    high = _to_float(tier.get("high")) or _to_float(prices.get("high"))

    return {
        "market": market,
        "low": low,
        "mid": mid,
        "high": high,
        "url": tcg.get("url") or "",
    }


def get_live_market_price(card_id: str) -> Optional[float]:
    """Convenience helper: fetch + extract the current TCGPlayer market price."""
    card = fetch_card_by_id(card_id)
    if not card:
        return None
    prices = extract_tcgplayer_prices(card)
    return prices.get("market")

