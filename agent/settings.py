"""
Agent settings manager for autonomous purchasing rules.
"""
from typing import Optional, Dict, Any
from db.connection import get_connection


def get_settings() -> Optional[Dict[str, Any]]:
    """Get current agent settings. Returns dict or None if not initialized."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM agent_settings WHERE id = 1").fetchone()
        if row:
            return {
                "autonomy_level": row["autonomy_level"],
                "daily_budget": row["daily_budget"],
                "per_card_max": row["per_card_max"],
                "deal_threshold_percent": row["deal_threshold_percent"],
                "psa10_only": bool(row["psa10_only"]),
                "raw_allowed": bool(row["raw_allowed"]),
                "modern_only": bool(row["modern_only"]),
                "ebay_allowed": bool(row["ebay_allowed"]),
                "tcgplayer_allowed": bool(row["tcgplayer_allowed"]),
                "facebook_allowed": bool(row["facebook_allowed"]),
                "notification_discord": bool(row["notification_discord"]),
                "notification_telegram": bool(row["notification_telegram"]),
                "updated_at": row["updated_at"],
            }
        return None
    finally:
        conn.close()


def update_settings(settings: Dict[str, Any]) -> bool:
    """
    Update agent settings.
    
    Args:
        settings: Dict with keys like autonomy_level, daily_budget, etc.
    
    Returns:
        True if successful
    """
    conn = get_connection()
    try:
        # Build dynamic update query
        allowed_fields = [
            "autonomy_level", "daily_budget", "per_card_max", "deal_threshold_percent",
            "psa10_only", "raw_allowed", "modern_only",
            "ebay_allowed", "tcgplayer_allowed", "facebook_allowed",
            "notification_discord", "notification_telegram"
        ]
        
        updates = []
        params = []
        for field in allowed_fields:
            if field in settings:
                updates.append(f"{field} = ?")
                val = settings[field]
                # Convert bool to int for SQLite
                if isinstance(val, bool):
                    val = 1 if val else 0
                params.append(val)
        
        if not updates:
            return False
        
        params.append(1)  # for WHERE id = 1
        query = f"UPDATE agent_settings SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        conn.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        return False
    finally:
        conn.close()


def can_auto_purchase(price: float, market_price: float) -> bool:
    """
    Check if a purchase can be auto-executed based on current settings.
    
    Args:
        price: Current listing price
        market_price: Market price for comparison
    
    Returns:
        True if agent can auto-purchase
    """
    settings = get_settings()
    if not settings:
        return False
    
    # Must be Level 2 (Execute) or higher
    if settings["autonomy_level"] < 2:
        return False
    
    # Check price limits
    if price > settings["per_card_max"]:
        return False
    
    # Check deal threshold
    if market_price > 0:
        discount_percent = ((market_price - price) / market_price) * 100
        if discount_percent < settings["deal_threshold_percent"]:
            return False
    
    return True


def get_daily_spent() -> float:
    """Get total spent today (placeholder - would track actual purchases)."""
    # TODO: Implement purchase tracking
    return 0.0


def get_remaining_budget() -> float:
    """Get remaining daily budget."""
    settings = get_settings()
    if not settings:
        return 0.0
    return max(0, settings["daily_budget"] - get_daily_spent())
