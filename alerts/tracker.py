"""
Price alert system for tracking card price changes.
Stores alerts in SQLite; checks for price thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum
import sqlite3

from db.connection import get_connection
from market.prices import get_price
from market.live_prices import get_live_market_price


class AlertCondition(Enum):
    ABOVE = "above"
    BELOW = "below"
    CHANGE_PERCENT = "change_percent"


@dataclass
class PriceAlert:
    id: Optional[int]
    user_id: str  # Discord user ID or API user identifier
    card_id: str
    condition: AlertCondition
    threshold: float
    created_at: datetime
    last_triggered: Optional[datetime]
    is_active: bool


def init_alerts_table() -> None:
    """Create price alerts table if not exists."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                condition TEXT NOT NULL,  -- 'above', 'below', 'change_percent'
                threshold REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_triggered TEXT,
                last_seen_price REAL,
                last_checked TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (card_id) REFERENCES cards(id)
            )
        """)
        # Lightweight migrations for existing DBs.
        for stmt in (
            "ALTER TABLE price_alerts ADD COLUMN last_seen_price REAL",
            "ALTER TABLE price_alerts ADD COLUMN last_checked TEXT",
        ):
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_user ON price_alerts(user_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_card ON price_alerts(card_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_active ON price_alerts(is_active)
        """)
        conn.commit()
    finally:
        conn.close()


def create_alert(
    user_id: str,
    card_id: str,
    condition: str,
    threshold: float
) -> PriceAlert:
    """Create a new price alert."""
    init_alerts_table()
    
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO price_alerts (user_id, card_id, condition, threshold, created_at, is_active)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)""",
            (user_id, card_id, condition, threshold)
        )
        alert_id = cursor.lastrowid
        conn.commit()
        
        return PriceAlert(
            id=alert_id,
            user_id=user_id,
            card_id=card_id,
            condition=AlertCondition(condition),
            threshold=threshold,
            created_at=datetime.now(),
            last_triggered=None,
            is_active=True
        )
    finally:
        conn.close()


def get_user_alerts(user_id: str) -> List[PriceAlert]:
    """Get all alerts for a user."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT id, user_id, card_id, condition, threshold, created_at, last_triggered, is_active
               FROM price_alerts WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,)
        )
        alerts = []
        for row in cur.fetchall():
            alerts.append(PriceAlert(
                id=row[0],
                user_id=row[1],
                card_id=row[2],
                condition=AlertCondition(row[3]),
                threshold=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_triggered=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7])
            ))
        return alerts
    finally:
        conn.close()


def delete_alert(alert_id: int, user_id: str) -> bool:
    """Delete an alert (must belong to user)."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM price_alerts WHERE id = ? AND user_id = ?",
            (alert_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def toggle_alert(alert_id: int, user_id: str, is_active: bool) -> bool:
    """Enable/disable an alert."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE price_alerts SET is_active = ? WHERE id = ? AND user_id = ?",
            (1 if is_active else 0, alert_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def check_alerts(user_id: Optional[str] = None, use_live: bool = False) -> List[dict]:
    """
    Check all active alerts and return triggered ones.
    If user_id provided, only check that user's alerts.
    """
    # Backwards-compatible wrapper.
    return check_alerts_with_options(user_id=user_id, use_live=use_live)


def check_alerts_with_options(user_id: Optional[str] = None, use_live: bool = False) -> List[dict]:
    """
    Check all active alerts and return triggered ones.

    Trigger semantics:
    - First observation (last_seen_price is NULL): triggers if current condition is met.
    - Subsequent checks: triggers only on threshold crossing (prevents spam).
    - change_percent: triggers when abs(percent change vs last_seen_price) >= threshold.
    """
    init_alerts_table()
    conn = get_connection()
    try:
        query = """SELECT id, user_id, card_id, condition, threshold, last_triggered, last_seen_price
                   FROM price_alerts WHERE is_active = 1"""
        params = ()
        if user_id:
            query += " AND user_id = ?"
            params = (user_id,)
        
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        
        triggered = []
        for row in rows:
            alert_id, uid, card_id, condition, threshold, last_triggered, last_seen_price = row

            current_price = (
                (get_live_market_price(card_id) if use_live else None)
                or get_price(card_id)
            )
            
            if current_price is None:
                continue
            
            should_trigger = False
            message = ""
            
            if condition == "above":
                if last_seen_price is None:
                    should_trigger = current_price > threshold
                else:
                    should_trigger = (last_seen_price <= threshold) and (current_price > threshold)
                if should_trigger:
                    message = f"📈 {card_id} is now ${current_price:.2f} (above ${threshold:.2f})"
            elif condition == "below":
                if last_seen_price is None:
                    should_trigger = current_price < threshold
                else:
                    should_trigger = (last_seen_price >= threshold) and (current_price < threshold)
                if should_trigger:
                    message = f"📉 {card_id} is now ${current_price:.2f} (below ${threshold:.2f})"
            elif condition == "change_percent":
                if last_seen_price is not None and float(last_seen_price) != 0:
                    pct = ((current_price - float(last_seen_price)) / float(last_seen_price)) * 100.0
                    if abs(pct) >= threshold:
                        should_trigger = True
                        direction = "📈" if pct > 0 else "📉"
                        message = (
                            f"{direction} {card_id} moved {pct:+.1f}% to ${current_price:.2f} "
                            f"(threshold {threshold:.1f}%)"
                        )
            
            if should_trigger:
                triggered.append({
                    "alert_id": alert_id,
                    "user_id": uid,
                    "card_id": card_id,
                    "current_price": current_price,
                    "threshold": threshold,
                    "message": message
                })
                
                # Update last_triggered
                conn.execute(
                    "UPDATE price_alerts SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?",
                    (alert_id,)
                )

            # Always update last_seen_price/last_checked so we can detect crossings.
            conn.execute(
                "UPDATE price_alerts SET last_seen_price = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                (float(current_price), alert_id),
            )
        
        conn.commit()
        return triggered
    finally:
        conn.close()


def get_alert_stats() -> dict:
    """Get statistics about alerts."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM price_alerts").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM price_alerts WHERE is_active = 1").fetchone()[0]
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM price_alerts").fetchone()[0]
        
        return {
            "total_alerts": total,
            "active_alerts": active,
            "unique_users": users
        }
    finally:
        conn.close()
