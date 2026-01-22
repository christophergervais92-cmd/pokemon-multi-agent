#!/usr/bin/env python3
"""
Pokemon Card Auto-Buy Agent

Handles automated purchasing across multiple retailers.
Supports both simulation mode and real purchases (when credentials provided).

IMPORTANT: Real auto-buy requires:
- Retailer account credentials (stored securely in env vars)
- Payment method on file with retailer
- Shipping address configured
"""
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Auto-buy configuration from environment
AUTOBUY_ENABLED = os.environ.get("POKEMON_AUTOBUY_ENABLED", "false").lower() == "true"
MAX_PURCHASE_PRICE = float(os.environ.get("POKEMON_MAX_PURCHASE_PRICE", "100"))
MAX_DAILY_SPEND = float(os.environ.get("POKEMON_MAX_DAILY_SPEND", "500"))
SIMULATION_MODE = os.environ.get("POKEMON_SIMULATION_MODE", "true").lower() == "true"

# Retailer credentials (for real purchases)
RETAILER_CREDENTIALS = {
    "Target": {
        "username": os.environ.get("TARGET_USERNAME", ""),
        "password": os.environ.get("TARGET_PASSWORD", ""),
    },
    "Walmart": {
        "username": os.environ.get("WALMART_USERNAME", ""),
        "password": os.environ.get("WALMART_PASSWORD", ""),
    },
    "Best Buy": {
        "username": os.environ.get("BESTBUY_USERNAME", ""),
        "password": os.environ.get("BESTBUY_PASSWORD", ""),
    },
    "GameStop": {
        "username": os.environ.get("GAMESTOP_USERNAME", ""),
        "password": os.environ.get("GAMESTOP_PASSWORD", ""),
    },
    "Costco": {
        "username": os.environ.get("COSTCO_USERNAME", ""),
        "password": os.environ.get("COSTCO_PASSWORD", ""),
    },
}

# Track daily spending
daily_spend_tracker: Dict[str, float] = {}


def get_today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_daily_spend() -> float:
    return daily_spend_tracker.get(get_today_key(), 0.0)


def add_to_daily_spend(amount: float):
    key = get_today_key()
    daily_spend_tracker[key] = daily_spend_tracker.get(key, 0.0) + amount


def can_purchase(price: float) -> tuple[bool, str]:
    """Check if purchase is allowed based on rules."""
    if not AUTOBUY_ENABLED:
        return False, "Auto-buy is disabled"
    
    if price > MAX_PURCHASE_PRICE:
        return False, f"Price ${price} exceeds max ${MAX_PURCHASE_PRICE}"
    
    if get_daily_spend() + price > MAX_DAILY_SPEND:
        return False, f"Would exceed daily spend limit of ${MAX_DAILY_SPEND}"
    
    return True, "OK"


def simulate_purchase(product: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate a purchase (no real transaction)."""
    return {
        "success": True,
        "simulation": True,
        "product": product["name"],
        "retailer": product["retailer"],
        "price": product["price"],
        "url": product["url"],
        "purchase_id": f"SIM-{product['retailer'][:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "message": "SIMULATION: Would have purchased this item",
        "timestamp": datetime.now().isoformat(),
    }


def real_purchase_target(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real purchase from Target using their API/checkout flow.
    REQUIRES: Valid Target account with payment method on file.
    """
    creds = RETAILER_CREDENTIALS["Target"]
    if not creds["username"] or not creds["password"]:
        return {
            "success": False,
            "error": "Target credentials not configured",
            "product": product["name"],
            "retailer": "Target",
        }
    
    # TODO: Implement real Target checkout
    # This would involve:
    # 1. Login to Target account
    # 2. Add item to cart
    # 3. Apply any Circle offers
    # 4. Complete checkout with saved payment
    
    return simulate_purchase(product)  # For now, simulate


def real_purchase_walmart(product: Dict[str, Any]) -> Dict[str, Any]:
    """Real purchase from Walmart."""
    creds = RETAILER_CREDENTIALS["Walmart"]
    if not creds["username"] or not creds["password"]:
        return {
            "success": False,
            "error": "Walmart credentials not configured",
            "product": product["name"],
            "retailer": "Walmart",
        }
    
    # TODO: Implement real Walmart checkout
    return simulate_purchase(product)


def real_purchase_bestbuy(product: Dict[str, Any]) -> Dict[str, Any]:
    """Real purchase from Best Buy."""
    creds = RETAILER_CREDENTIALS["Best Buy"]
    if not creds["username"] or not creds["password"]:
        return {
            "success": False,
            "error": "Best Buy credentials not configured",
            "product": product["name"],
            "retailer": "Best Buy",
        }
    
    # TODO: Implement real Best Buy checkout
    return simulate_purchase(product)


def real_purchase_gamestop(product: Dict[str, Any]) -> Dict[str, Any]:
    """Real purchase from GameStop."""
    creds = RETAILER_CREDENTIALS["GameStop"]
    if not creds["username"] or not creds["password"]:
        return {
            "success": False,
            "error": "GameStop credentials not configured",
            "product": product["name"],
            "retailer": "GameStop",
        }
    
    # TODO: Implement real GameStop checkout
    return simulate_purchase(product)


def real_purchase_costco(product: Dict[str, Any]) -> Dict[str, Any]:
    """Real purchase from Costco."""
    creds = RETAILER_CREDENTIALS["Costco"]
    if not creds["username"] or not creds["password"]:
        return {
            "success": False,
            "error": "Costco credentials not configured (membership required)",
            "product": product["name"],
            "retailer": "Costco",
        }
    
    # TODO: Implement real Costco checkout
    return simulate_purchase(product)


PURCHASE_HANDLERS = {
    "Target": real_purchase_target,
    "Walmart": real_purchase_walmart,
    "Best Buy": real_purchase_bestbuy,
    "GameStop": real_purchase_gamestop,
    "Costco": real_purchase_costco,
}


def attempt_purchase(
    product: Dict[str, Any],
    credentials: Dict[str, str] = None,
    shipping: Dict[str, str] = None,
    skip_limits: bool = False
) -> Dict[str, Any]:
    """
    Attempt to purchase a product.
    
    Args:
        product: Product to purchase
        credentials: Optional user-specific credentials (email, password)
        shipping: Optional user-specific shipping info
        skip_limits: If True, skip the global can_purchase limits (for multi-user)
    
    Returns purchase result with success/failure info.
    """
    price = product.get("price", 0)
    retailer = product.get("retailer", "Unknown")
    
    # Check if purchase is allowed (skip for multi-user which has its own limits)
    if not skip_limits:
        allowed, reason = can_purchase(price)
        if not allowed:
            return {
                "success": False,
                "blocked": True,
                "reason": reason,
                "product": product.get("name", "Unknown"),
                "retailer": retailer,
                "price": price,
            }
    
    # Simulation mode just logs what would happen
    if SIMULATION_MODE:
        result = simulate_purchase(product)
        if result["success"] and not skip_limits:
            add_to_daily_spend(price)
        return result
    
    # Real purchase - use provided credentials or fall back to global ones
    if credentials:
        # Multi-user mode: use user-specific credentials
        result = execute_purchase_with_credentials(product, credentials, shipping)
    else:
        # Single-user mode: use global credentials
        handler = PURCHASE_HANDLERS.get(retailer)
        if not handler:
            return {
                "success": False,
                "error": f"No purchase handler for retailer: {retailer}",
                "product": product.get("name", "Unknown"),
            }
        result = handler(product)
    
    if result.get("success") and not skip_limits:
        add_to_daily_spend(price)
    
    return result


def execute_purchase_with_credentials(
    product: Dict[str, Any],
    credentials: Dict[str, str],
    shipping: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Execute a purchase using user-provided credentials.
    This is the entry point for multi-user auto-buy.
    """
    retailer = product.get("retailer", "Unknown")
    
    # For now, all retailers use simulation
    # TODO: Implement real checkout flows with user credentials
    result = simulate_purchase(product)
    result["credentials_provided"] = True
    result["shipping_provided"] = bool(shipping)
    
    # Add shipping info to the simulation
    if shipping:
        result["shipping_to"] = f"{shipping.get('name', 'N/A')}, {shipping.get('city', 'N/A')}, {shipping.get('state', 'N/A')}"
    
    return result


def process_buy_decisions(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process products that have been approved for purchase.
    Only buys items where should_buy=True in evaluation.
    """
    purchases = []
    skipped = []
    
    products = data.get("products", [])
    decision = data.get("decision", {})
    max_qty = decision.get("max_quantity", 2)
    
    purchased_count = 0
    
    for product in products:
        evaluation = product.get("evaluation", {})
        should_buy = evaluation.get("should_buy", False)
        in_stock = product.get("stock", False)
        
        if not should_buy:
            skipped.append({
                "product": product["name"],
                "retailer": product.get("retailer", "Unknown"),
                "reason": evaluation.get("reason", "Not recommended"),
            })
            continue
        
        if not in_stock:
            skipped.append({
                "product": product["name"],
                "retailer": product.get("retailer", "Unknown"),
                "reason": "Out of stock",
            })
            continue
        
        if purchased_count >= max_qty:
            skipped.append({
                "product": product["name"],
                "retailer": product.get("retailer", "Unknown"),
                "reason": f"Max quantity ({max_qty}) reached",
            })
            continue
        
        # Attempt the purchase
        result = attempt_purchase(product)
        purchases.append(result)
        
        if result.get("success"):
            purchased_count += 1
    
    return {
        "success": True,
        "simulation_mode": SIMULATION_MODE,
        "autobuy_enabled": AUTOBUY_ENABLED,
        "purchase_count": len([p for p in purchases if p.get("success")]),
        "purchases": purchases,
        "skipped": skipped,
        "daily_spend": get_daily_spend(),
        "daily_limit": MAX_DAILY_SPEND,
        # Pass through other data
        "set_name": data.get("set_name"),
        "products": products,
        "decision": decision,
        "alerts": data.get("alerts", []),
    }


if __name__ == "__main__":
    input_data = sys.stdin.read() or "{}"
    data = json.loads(input_data)
    result = process_buy_decisions(data)
    print(json.dumps(result))
