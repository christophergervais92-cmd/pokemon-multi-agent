#!/usr/bin/env python3
import json
import os
import sys
from typing import Any, Dict, Optional

import requests

from db import (
    get_latest_price_snapshot,
    get_or_create_product,
    record_price_snapshot,
)


EXTERNAL_PRICE_API_URL = os.environ.get("POKEMON_PRICE_API_URL", "").strip()
EXTERNAL_PRICE_API_KEY = os.environ.get("POKEMON_PRICE_API_KEY", "").strip()


def fetch_external_market_price(product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call an external Pokemon price API (e.g. PokemonPriceTracker) to get
    a real market price for this product.

    This is intentionally generic so you can point it at any compatible API by
    setting:
      - POKEMON_PRICE_API_URL
      - POKEMON_PRICE_API_KEY

    Expected (but adaptable) response contract:
      {
        "market_price": 42.0,
        ... any other fields ...
      }
    If your API uses a different shape, just adjust the parsing below.
    """
    if not EXTERNAL_PRICE_API_URL or not EXTERNAL_PRICE_API_KEY:
        return None

    try:
        params = {
            # These names are generic; map them to whatever your API expects
            "set_name": product.get("set_name"),
            "name": product.get("name"),
            "retailer": product.get("retailer"),
        }
        # For PokemonPriceTracker (and similar APIs), use Bearer auth:
        #   Authorization: Bearer <API_KEY>
        headers = {
            "Authorization": f"Bearer {EXTERNAL_PRICE_API_KEY}",
            "Accept": "application/json",
        }

        resp = requests.get(EXTERNAL_PRICE_API_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        # Try common field names first; fall back if needed.
        market_price = (
            payload.get("market_price")
            or payload.get("tcgplayer_market")
            or payload.get("prices", {}).get("tcgplayer", {}).get("market")
        )

        if market_price is None:
            return None

        return {
            "market_price": float(market_price),
            "raw": payload,
        }
    except Exception:
        # Fail soft: we can still use our DB heuristic
        return None


def estimate_market_price(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate market price using a combination of:
      - live data from an external Pokemon price API (if configured)
      - historical data stored in the local SQLite database
    """
    set_name = product.get("set_name") or product.get("set") or ""
    product_id = product.get("product_id")

    if product_id is None:
        product_id = get_or_create_product(
            set_name=set_name,
            name=product["name"],
            retailer=product["retailer"],
            url=product.get("url"),
        )
        product["product_id"] = product_id

    latest = get_latest_price_snapshot(product_id)
    listed_price = float(product["price"])

    # 1) Try real external market data first
    external = fetch_external_market_price(product)

    if external and external.get("market_price") is not None:
        market_price = float(external["market_price"])
        delta_pct = (listed_price - market_price) / market_price if market_price else 0.0
        confidence = 0.95
    else:
        # 2) Fallback: use the latest DB snapshot if we have one
        if latest and latest.get("market_price") is not None:
            ref_market = float(latest["market_price"])
            market_price = ref_market
            delta_pct = (listed_price - ref_market) / ref_market if ref_market else 0.0
            confidence = 0.9
        else:
            # 3) Last resort: simple heuristic multiplier
            market_price = listed_price * 1.4
            delta_pct = -0.285
            confidence = 0.7

    record_price_snapshot(
        product_id=product_id,
        listed_price=listed_price,
        market_price=market_price,
        delta_pct=delta_pct,
        confidence=confidence,
    )

    pricing: Dict[str, Any] = {
        "listed_price": listed_price,
        "market_price": market_price,
        "delta_pct": delta_pct,
        "confidence": confidence,
    }

    if latest:
        pricing["previous_snapshot"] = {
            "listed_price": latest.get("listed_price"),
            "market_price": latest.get("market_price"),
            "delta_pct": latest.get("delta_pct"),
            "created_at": latest.get("created_at"),
        }

    if external:
        # expose raw external data for debugging / downstream use
        pricing["external_source"] = external.get("raw")

    return pricing


input_data = sys.stdin.read() or "{}"
data = json.loads(input_data)

set_name = data.get("set_name", "")

for p in data.get("products", []):
    # make sure downstream has the set info for this product
    p.setdefault("set_name", set_name)
    p["pricing"] = estimate_market_price(p)

print(json.dumps(data))
