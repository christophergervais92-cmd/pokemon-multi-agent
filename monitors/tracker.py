"""
Stock/price monitors — persisted user-owned watch tasks.

Each monitor is a query + retailer + interval tuple scoped to a user.
A future background worker can poll each monitor and fire Discord webhooks
on stock hits; for now we support CRUD + manual hit tracking.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from db.connection import get_connection


def init_monitors_table() -> None:
    """Create monitors table if missing. Idempotent."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                retailer TEXT NOT NULL DEFAULT 'all',
                zip_code TEXT,
                interval_seconds INTEGER NOT NULL DEFAULT 60,
                webhook_url TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                last_hit_at TEXT,
                last_hit_summary TEXT,
                hit_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_monitors_user ON monitors(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_monitors_active ON monitors(active)")
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "query": row["query"],
        "retailer": row["retailer"],
        "zip_code": row["zip_code"],
        "interval_seconds": row["interval_seconds"],
        "webhook_url": row["webhook_url"],
        "active": bool(row["active"]),
        "last_hit_at": row["last_hit_at"],
        "last_hit_summary": row["last_hit_summary"],
        "hit_count": row["hit_count"],
        "created_at": row["created_at"],
    }


def list_monitors(user_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM monitors WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def create_monitor(
    user_id: str,
    query: str,
    retailer: str = "all",
    zip_code: Optional[str] = None,
    interval_seconds: int = 60,
    webhook_url: Optional[str] = None,
    active: bool = True,
) -> Dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("query is required")
    interval_seconds = max(15, min(int(interval_seconds), 3600))
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            INSERT INTO monitors (user_id, query, retailer, zip_code, interval_seconds, webhook_url, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, query.strip(), retailer or "all", zip_code, interval_seconds, webhook_url, 1 if active else 0),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monitors WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_monitor(user_id: str, monitor_id: int, **updates: Any) -> Optional[Dict[str, Any]]:
    """Partial update. Only whitelisted fields are written."""
    allowed = {"query", "retailer", "zip_code", "interval_seconds", "webhook_url", "active"}
    sets, vals = [], []
    for k, v in updates.items():
        if k not in allowed:
            continue
        if k == "active":
            v = 1 if v else 0
        if k == "interval_seconds":
            v = max(15, min(int(v), 3600))
        sets.append(f"{k} = ?")
        vals.append(v)
    if not sets:
        return get_monitor(user_id, monitor_id)

    vals.extend([monitor_id, user_id])
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            f"UPDATE monitors SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            tuple(vals),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ? AND user_id = ?",
            (monitor_id, user_id),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def delete_monitor(user_id: str, monitor_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM monitors WHERE id = ? AND user_id = ?",
            (monitor_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_monitor(user_id: str, monitor_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ? AND user_id = ?",
            (monitor_id, user_id),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def record_hit(monitor_id: int, summary: str) -> None:
    """Mark that a monitor fired. Called from scanner / worker."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """UPDATE monitors
               SET last_hit_at = ?, last_hit_summary = ?, hit_count = hit_count + 1
               WHERE id = ?""",
            (now, summary, monitor_id),
        )
        conn.commit()
    finally:
        conn.close()


def monitor_stats(user_id: str) -> Dict[str, Any]:
    rows = list_monitors(user_id)
    return {
        "total": len(rows),
        "active": sum(1 for r in rows if r["active"]),
        "paused": sum(1 for r in rows if not r["active"]),
        "total_hits": sum(r["hit_count"] for r in rows),
    }
