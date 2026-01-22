#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "pokemon_cards.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        # Basic product catalog
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_name TEXT NOT NULL,
                name TEXT NOT NULL,
                retailer TEXT NOT NULL,
                url TEXT,
                UNIQUE (set_name, name, retailer, url)
            )
            """
        )

        # Price history snapshots
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                listed_price REAL NOT NULL,
                market_price REAL,
                delta_pct REAL,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )

        conn.commit()


def get_or_create_product(
    set_name: str, name: str, retailer: str, url: Optional[str]
) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO products (set_name, name, retailer, url)
            VALUES (?, ?, ?, ?)
            """,
            (set_name, name, retailer, url),
        )
        conn.commit()

        cur.execute(
            """
            SELECT id FROM products
            WHERE set_name = ? AND name = ? AND retailer = ? AND (url IS ? OR url = ?)
            """,
            (set_name, name, retailer, url, url),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to fetch or create product record")
        return int(row["id"])


def record_price_snapshot(
    product_id: int,
    listed_price: float,
    market_price: Optional[float],
    delta_pct: Optional[float],
    confidence: Optional[float],
) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO prices (product_id, listed_price, market_price, delta_pct, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, listed_price, market_price, delta_pct, confidence),
        )
        conn.commit()


def get_latest_price_snapshot(product_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM prices
            WHERE product_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_price_history(product_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM prices
            WHERE product_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (product_id, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# Ensure schema exists on import
init_db()

