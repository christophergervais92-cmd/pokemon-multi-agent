#!/usr/bin/env python3
"""
User Database for Discord Bot

Stores user preferences, watchlists, and encrypted payment info.
Uses SQLite for simplicity - can be upgraded to PostgreSQL for production.
"""
import sqlite3
import json
import hashlib
import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from cryptography.fernet import Fernet

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "pokemon_users.db"

# Encryption key for sensitive data (generate once and store securely)
ENCRYPTION_KEY = os.environ.get("POKEMON_ENCRYPTION_KEY", "")

def get_cipher():
    """Get Fernet cipher for encryption/decryption."""
    if not ENCRYPTION_KEY:
        # Generate a key if not set (should be set in production)
        return None
    try:
        return Fernet(ENCRYPTION_KEY.encode() if len(ENCRYPTION_KEY) == 44 else Fernet.generate_key())
    except:
        return None


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    cipher = get_cipher()
    if cipher and data:
        return cipher.encrypt(data.encode()).decode()
    return data  # Return as-is if no encryption available


def decrypt_data(data: str) -> str:
    """Decrypt sensitive data."""
    cipher = get_cipher()
    if cipher and data:
        try:
            return cipher.decrypt(data.encode()).decode()
        except:
            return data
    return data


def init_db():
    """Initialize the user database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            discord_username TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            is_premium INTEGER DEFAULT 0,
            notification_enabled INTEGER DEFAULT 1,
            autobuy_enabled INTEGER DEFAULT 0,
            max_price_limit REAL DEFAULT 100.0,
            daily_spend_limit REAL DEFAULT 500.0,
            daily_spent REAL DEFAULT 0.0,
            last_spend_reset DATE,
            zip_code TEXT DEFAULT '',
            search_radius_miles INTEGER DEFAULT 25,
            local_alerts_only INTEGER DEFAULT 0
        )
    """)
    
    # Try to add new columns if they don't exist (for existing DBs)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN zip_code TEXT DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN search_radius_miles INTEGER DEFAULT 25")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN local_alerts_only INTEGER DEFAULT 0")
    except:
        pass
    
    # User watchlists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            item_type TEXT,
            item_name TEXT,
            target_price REAL,
            notify_on_stock INTEGER DEFAULT 1,
            autobuy_on_deal INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (discord_id) REFERENCES users(discord_id)
        )
    """)
    
    # User payment info (encrypted)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_info (
            discord_id TEXT PRIMARY KEY,
            retailer TEXT,
            encrypted_email TEXT,
            encrypted_password TEXT,
            shipping_name TEXT,
            shipping_address TEXT,
            shipping_city TEXT,
            shipping_state TEXT,
            shipping_zip TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (discord_id) REFERENCES users(discord_id)
        )
    """)
    
    # Purchase history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            product_name TEXT,
            retailer TEXT,
            price REAL,
            purchase_id TEXT,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (discord_id) REFERENCES users(discord_id)
        )
    """)
    
    # Alert history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            alert_type TEXT,
            product_name TEXT,
            retailer TEXT,
            price REAL,
            url TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# Initialize on import
init_db()


def get_user(discord_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Discord ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def create_user(discord_id: str, discord_username: str) -> Dict[str, Any]:
    """Create a new user."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO users (discord_id, discord_username, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (discord_id, discord_username))
    
    conn.commit()
    conn.close()
    
    return get_user(discord_id)


def update_user_settings(discord_id: str, settings: Dict[str, Any]) -> bool:
    """Update user settings."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    allowed_fields = [
        'notification_enabled', 'autobuy_enabled', 
        'max_price_limit', 'daily_spend_limit',
        'zip_code', 'search_radius_miles', 'local_alerts_only'
    ]
    
    for key, value in settings.items():
        if key in allowed_fields:
            cursor.execute(f"""
                UPDATE users SET {key} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            """, (value, discord_id))
    
    conn.commit()
    conn.close()
    return True


def set_user_location(
    discord_id: str,
    zip_code: str,
    radius_miles: int = 25,
    local_only: bool = False
) -> bool:
    """
    Set user's location for local inventory scanning.
    
    Args:
        discord_id: User's Discord ID
        zip_code: US zip code (5 digits)
        radius_miles: Search radius in miles (default 25)
        local_only: If True, only notify about local stock
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users 
        SET zip_code = ?, search_radius_miles = ?, local_alerts_only = ?, 
            updated_at = CURRENT_TIMESTAMP
        WHERE discord_id = ?
    """, (zip_code, radius_miles, 1 if local_only else 0, discord_id))
    
    conn.commit()
    conn.close()
    return True


def get_user_location(discord_id: str) -> Optional[Dict[str, Any]]:
    """Get user's location settings."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT zip_code, search_radius_miles, local_alerts_only 
        FROM users WHERE discord_id = ?
    """, (discord_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "zip_code": row["zip_code"] or "",
            "radius_miles": row["search_radius_miles"] or 25,
            "local_only": bool(row["local_alerts_only"]),
        }
    return None


def get_users_by_zip(zip_code: str) -> List[Dict[str, Any]]:
    """Get all active users with a specific zip code."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM users 
        WHERE is_active = 1 AND zip_code = ?
    """, (zip_code,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_users_with_location() -> List[Dict[str, Any]]:
    """Get all active users who have set a location."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM users 
        WHERE is_active = 1 AND zip_code IS NOT NULL AND zip_code != ''
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def save_payment_info(
    discord_id: str,
    retailer: str,
    email: str,
    password: str,
    shipping: Dict[str, str]
) -> bool:
    """Save encrypted payment/shipping info for a user."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO payment_info 
        (discord_id, retailer, encrypted_email, encrypted_password,
         shipping_name, shipping_address, shipping_city, shipping_state, shipping_zip,
         updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        discord_id,
        retailer,
        encrypt_data(email),
        encrypt_data(password),
        shipping.get('name', ''),
        shipping.get('address', ''),
        shipping.get('city', ''),
        shipping.get('state', ''),
        shipping.get('zip', ''),
    ))
    
    conn.commit()
    conn.close()
    return True


def get_payment_info(discord_id: str, retailer: str = None) -> Optional[Dict[str, Any]]:
    """Get decrypted payment info for a user."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if retailer:
        cursor.execute(
            "SELECT * FROM payment_info WHERE discord_id = ? AND retailer = ?",
            (discord_id, retailer)
        )
    else:
        cursor.execute(
            "SELECT * FROM payment_info WHERE discord_id = ?",
            (discord_id,)
        )
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        info = dict(row)
        info['email'] = decrypt_data(info.get('encrypted_email', ''))
        info['password'] = decrypt_data(info.get('encrypted_password', ''))
        del info['encrypted_email']
        del info['encrypted_password']
        return info
    
    return None


def add_to_watchlist(
    discord_id: str,
    item_type: str,
    item_name: str,
    target_price: float = None,
    notify_on_stock: bool = True,
    autobuy_on_deal: bool = False
) -> int:
    """Add item to user's watchlist."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO watchlists 
        (discord_id, item_type, item_name, target_price, notify_on_stock, autobuy_on_deal)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (discord_id, item_type, item_name, target_price, notify_on_stock, autobuy_on_deal))
    
    watchlist_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return watchlist_id


def get_watchlist(discord_id: str) -> List[Dict[str, Any]]:
    """Get user's watchlist."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM watchlists WHERE discord_id = ? ORDER BY created_at DESC",
        (discord_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def remove_from_watchlist(discord_id: str, watchlist_id: int) -> bool:
    """Remove item from watchlist."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM watchlists WHERE id = ? AND discord_id = ?",
        (watchlist_id, discord_id)
    )
    
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    
    return deleted


def log_purchase(
    discord_id: str,
    product_name: str,
    retailer: str,
    price: float,
    purchase_id: str,
    status: str
) -> int:
    """Log a purchase."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO purchase_history 
        (discord_id, product_name, retailer, price, purchase_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (discord_id, product_name, retailer, price, purchase_id, status))
    
    # Update daily spent
    cursor.execute("""
        UPDATE users SET daily_spent = daily_spent + ?
        WHERE discord_id = ?
    """, (price, discord_id))
    
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return log_id


def get_purchase_history(discord_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user's purchase history."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM purchase_history 
        WHERE discord_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (discord_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_all_users_with_autobuy() -> List[Dict[str, Any]]:
    """Get all users who have auto-buy enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM users 
        WHERE is_active = 1 AND autobuy_enabled = 1
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_users_watching(product_name: str) -> List[Dict[str, Any]]:
    """Get users who are watching a specific product."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.*, w.target_price, w.autobuy_on_deal
        FROM users u
        JOIN watchlists w ON u.discord_id = w.discord_id
        WHERE u.is_active = 1 
        AND u.notification_enabled = 1
        AND (w.item_name LIKE ? OR ? LIKE '%' || w.item_name || '%')
    """, (f"%{product_name}%", product_name))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def reset_daily_spend():
    """Reset daily spend for all users (run at midnight)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    today = datetime.now().date().isoformat()
    
    cursor.execute("""
        UPDATE users 
        SET daily_spent = 0, last_spend_reset = ?
        WHERE last_spend_reset IS NULL OR last_spend_reset < ?
    """, (today, today))
    
    conn.commit()
    conn.close()
