"""
Collection/Portfolio management for tracking owned cards.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum

from db.connection import get_connection
from market.prices import get_price


class CardCondition(Enum):
    MINT = "Mint"
    NEAR_MINT = "NM"
    EXCELLENT = "EX"
    GOOD = "Good"
    LIGHT_PLAYED = "LP"
    PLAYED = "Played"
    POOR = "Poor"


@dataclass
class CollectionItem:
    id: Optional[int]
    user_id: str
    card_id: str
    quantity: int
    condition: str
    purchase_price: Optional[float]
    purchase_date: Optional[datetime]
    notes: Optional[str]
    date_added: datetime


def init_collection_tables() -> None:
    """Create collection tables if not exists."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                condition TEXT DEFAULT 'NM',
                purchase_price REAL,
                purchase_date TEXT,
                notes TEXT,
                date_added TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES cards(id),
                UNIQUE(user_id, card_id, condition)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collection_user ON user_collections(user_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collection_card ON user_collections(card_id)
        """)
        
        # Portfolio value history
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                total_value REAL NOT NULL,
                total_cards INTEGER NOT NULL,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_history(user_id)
        """)
        conn.commit()
    finally:
        conn.close()


def add_to_collection(
    user_id: str,
    card_id: str,
    quantity: int = 1,
    condition: str = "NM",
    purchase_price: Optional[float] = None,
    purchase_date: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Add card to collection. Updates quantity if already exists."""
    init_collection_tables()
    
    conn = get_connection()
    try:
        # Check if already exists
        existing = conn.execute(
            "SELECT id, quantity FROM user_collections WHERE user_id = ? AND card_id = ? AND condition = ?",
            (user_id, card_id, condition)
        ).fetchone()
        
        if existing:
            # Update quantity
            new_qty = existing[1] + quantity
            conn.execute(
                "UPDATE user_collections SET quantity = ? WHERE id = ?",
                (new_qty, existing[0])
            )
        else:
            # Insert new
            conn.execute(
                """INSERT INTO user_collections 
                   (user_id, card_id, quantity, condition, purchase_price, purchase_date, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, card_id, quantity, condition, purchase_price, purchase_date, notes)
            )
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding to collection: {e}")
        return False
    finally:
        conn.close()


def remove_from_collection(user_id: str, card_id: str, condition: Optional[str] = None) -> bool:
    """Remove card from collection."""
    conn = get_connection()
    try:
        if condition:
            conn.execute(
                "DELETE FROM user_collections WHERE user_id = ? AND card_id = ? AND condition = ?",
                (user_id, card_id, condition)
            )
        else:
            conn.execute(
                "DELETE FROM user_collections WHERE user_id = ? AND card_id = ?",
                (user_id, card_id)
            )
        conn.commit()
        return True
    finally:
        conn.close()


def update_quantity(user_id: str, card_id: str, condition: str, quantity: int) -> bool:
    """Update card quantity in collection."""
    if quantity <= 0:
        return remove_from_collection(user_id, card_id, condition)
    
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE user_collections SET quantity = ? WHERE user_id = ? AND card_id = ? AND condition = ?",
            (quantity, user_id, card_id, condition)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_collection(user_id: str, set_id: Optional[str] = None) -> List[dict]:
    """Get user's collection with current prices."""
    conn = get_connection()
    try:
        sql = """SELECT c.*, cr.name as card_name, cr.rarity, cr.set_id, 
                        cr.tcgplayer_market, cr.tcgplayer_mid, cr.image_url
                 FROM user_collections c
                 JOIN cards cr ON c.card_id = cr.id
                 WHERE c.user_id = ?"""
        params = [user_id]
        
        if set_id:
            sql += " AND cr.set_id = ?"
            params.append(set_id)
        
        sql += " ORDER BY c.date_added DESC"
        
        cur = conn.execute(sql, params)
        items = []
        for row in cur.fetchall():
            item = dict(row)
            current_price = item.get("tcgplayer_market") or item.get("tcgplayer_mid") or 0
            quantity = item.get("quantity", 1)
            purchase_price = item.get("purchase_price") or 0
            
            item["current_value"] = current_price * quantity
            item["profit_loss"] = (current_price - purchase_price) * quantity if purchase_price else None
            items.append(item)
        
        return items
    finally:
        conn.close()


def get_portfolio_summary(user_id: str) -> dict:
    """Get portfolio summary with total value and stats."""
    items = get_collection(user_id)
    
    total_value = 0.0
    total_cost = 0.0
    total_cards = 0
    set_counts: Dict[str, int] = {}
    rarity_counts: Dict[str, int] = {}
    
    for item in items:
        qty = item.get("quantity", 1)
        current_price = item.get("tcgplayer_market") or item.get("tcgplayer_mid") or 0
        purchase_price = item.get("purchase_price") or 0
        
        total_value += current_price * qty
        total_cost += purchase_price * qty
        total_cards += qty
        
        set_id = item.get("set_id", "unknown")
        rarity = item.get("rarity", "unknown")
        
        set_counts[set_id] = set_counts.get(set_id, 0) + qty
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + qty
    
    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2) if total_cost > 0 else None,
        "profit_loss": round(total_value - total_cost, 2) if total_cost > 0 else None,
        "total_cards": total_cards,
        "unique_cards": len(items),
        "sets": set_counts,
        "rarities": rarity_counts,
        "roi_percent": round(((total_value - total_cost) / total_cost) * 100, 2) if total_cost > 0 else None
    }


def record_portfolio_value(user_id: str) -> bool:
    """Record current portfolio value for historical tracking."""
    summary = get_portfolio_summary(user_id)
    
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO portfolio_history (user_id, total_value, total_cards)
               VALUES (?, ?, ?)""",
            (user_id, summary["total_value"], summary["total_cards"])
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_portfolio_history(user_id: str, days: int = 30) -> List[dict]:
    """Get portfolio value history."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT total_value, total_cards, recorded_at
               FROM portfolio_history
               WHERE user_id = ? AND recorded_at >= datetime('now', '-{} days')
               ORDER BY recorded_at ASC""".format(days),
            (user_id,)
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_collection_stats() -> dict:
    """Get global collection statistics."""
    conn = get_connection()
    try:
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_collections").fetchone()[0]
        total_cards = conn.execute("SELECT SUM(quantity) FROM user_collections").fetchone()[0] or 0
        unique_cards = conn.execute("SELECT COUNT(DISTINCT card_id) FROM user_collections").fetchone()[0]
        
        return {
            "total_users": users,
            "total_cards": total_cards,
            "unique_cards_tracked": unique_cards
        }
    finally:
        conn.close()
