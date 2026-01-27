#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache
from contextlib import contextmanager

# Try to use connection pooling if available
try:
    from agents.utils.db_pool import get_pool
    USE_POOLING = True
except ImportError:
    USE_POOLING = False

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "pokemon_cards.db"

# Cache for connection pool
_pool = None

def _get_pool():
    """Get or create connection pool."""
    global _pool
    if _pool is None and USE_POOLING:
        _pool = get_pool("pokemon_cards", DB_PATH)
    return _pool

@contextmanager
def get_connection():
    """Get database connection (with pooling if available)."""
    if USE_POOLING and _get_pool():
        with _get_pool().get_connection() as conn:
            yield conn
    else:
        # Fallback to direct connection
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        try:
            yield conn
        finally:
            conn.close()


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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
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

        # Create indexes for better query performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_set_name ON products(set_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_retailer ON products(retailer)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_created_at ON prices(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_product_created ON prices(product_id, created_at DESC)")

        conn.commit()


@lru_cache(maxsize=1000)
def _get_product_id_cached(set_name: str, name: str, retailer: str, url: Optional[str]) -> Optional[int]:
    """Cached lookup for product ID (cache cleared on insert)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM products
            WHERE set_name = ? AND name = ? AND retailer = ? AND (url IS ? OR url = ?)
            LIMIT 1
            """,
            (set_name, name, retailer, url, url),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else None

def get_or_create_product(
    set_name: str, name: str, retailer: str, url: Optional[str]
) -> int:
    # Check cache first
    cached_id = _get_product_id_cached(set_name, name, retailer, url)
    if cached_id:
        return cached_id
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO products (set_name, name, retailer, url, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (set_name, name, retailer, url),
        )
        conn.commit()

        # Clear cache for this lookup
        _get_product_id_cached.cache_clear()
        
        cur.execute(
            """
            SELECT id FROM products
            WHERE set_name = ? AND name = ? AND retailer = ? AND (url IS ? OR url = ?)
            LIMIT 1
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

def record_price_snapshots_batch(
    snapshots: List[Dict[str, Any]]
) -> None:
    """Batch insert multiple price snapshots for better performance."""
    if not snapshots:
        return
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO prices (product_id, listed_price, market_price, delta_pct, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (s["product_id"], s["listed_price"], s.get("market_price"), 
                 s.get("delta_pct"), s.get("confidence"))
                for s in snapshots
            ],
        )
        conn.commit()


@lru_cache(maxsize=500)
def get_latest_price_snapshot(product_id: int) -> Optional[Dict[str, Any]]:
    """Get latest price snapshot with caching."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM prices
            WHERE product_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

def clear_price_cache():
    """Clear price snapshot cache (call after recording new prices)."""
    get_latest_price_snapshot.cache_clear()


def get_price_history(product_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get price history with optimized query using index."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM prices
            WHERE product_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (product_id, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_products_by_set(set_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all products for a set (optimized with index)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM products
            WHERE set_name = ?
            ORDER BY name
            LIMIT ?
            """,
            (set_name, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# Ensure schema exists on import
init_db()

