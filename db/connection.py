"""
Database connection and schema.
Uses SQLite; DB file is in project root: pokemon_tcg.db
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "pokemon_tcg.db"

SCHEMA = """
-- Agent settings for autonomous purchasing rules
CREATE TABLE IF NOT EXISTS agent_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    autonomy_level INTEGER NOT NULL DEFAULT 0,
    daily_budget REAL DEFAULT 0,
    per_card_max REAL DEFAULT 0,
    deal_threshold_percent REAL DEFAULT 15,
    psa10_only INTEGER DEFAULT 1,
    raw_allowed INTEGER DEFAULT 0,
    modern_only INTEGER DEFAULT 1,
    ebay_allowed INTEGER DEFAULT 1,
    tcgplayer_allowed INTEGER DEFAULT 1,
    facebook_allowed INTEGER DEFAULT 0,
    notification_discord INTEGER DEFAULT 1,
    notification_telegram INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings if not exists
INSERT OR IGNORE INTO agent_settings (id, autonomy_level, daily_budget, per_card_max, deal_threshold_percent)
VALUES (1, 0, 500, 200, 15);

-- Sets from Pokémon TCG API (id, name, series, releaseDate, images.logo, total, value_index)
CREATE TABLE IF NOT EXISTS sets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    series TEXT,
    release_date TEXT,
    logo_url TEXT,
    total INTEGER,
    value_index REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Cards: id, name, set_id, rarity, images, tcgplayer prices
CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    set_id TEXT NOT NULL,
    name TEXT NOT NULL,
    rarity TEXT,
    supertype TEXT,
    subtype TEXT,
    image_url TEXT,
    small_image_url TEXT,
    tcgplayer_market REAL,
    tcgplayer_low REAL,
    tcgplayer_mid REAL,
    tcgplayer_high REAL,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (set_id) REFERENCES sets(id)
);

CREATE INDEX IF NOT EXISTS idx_cards_set_id ON cards(set_id);
CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity);
CREATE INDEX IF NOT EXISTS idx_cards_tcgplayer_market ON cards(tcgplayer_market DESC);
-- Chase cards per set: fast "top N by price for this set"
CREATE INDEX IF NOT EXISTS idx_cards_set_market ON cards(set_id, tcgplayer_market DESC);

-- Pull rates per pack (community estimates): set_id, rarity/card_type, rate, source
CREATE TABLE IF NOT EXISTS pull_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_id TEXT NOT NULL,
    category TEXT NOT NULL,
    label TEXT,
    rate_per_pack REAL,
    notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (set_id) REFERENCES sets(id)
);

CREATE INDEX IF NOT EXISTS idx_pull_rates_set_id ON pull_rates(set_id);

-- Graded prices (PSA, CGC, Beckett/BGS) per card — PriceCharting/eBay style
CREATE TABLE IF NOT EXISTS graded_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT NOT NULL,
    grader TEXT NOT NULL,
    grade TEXT NOT NULL,
    grade_label TEXT,
    market REAL,
    low REAL,
    high REAL,
    source TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, grader),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);

CREATE INDEX IF NOT EXISTS idx_graded_prices_card_id ON graded_prices(card_id);
"""


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite DB; creates file and schema if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create DB file and tables if they do not exist. Runs migrations for existing DBs."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        # Migration: add value_index to sets if missing (existing DBs)
        try:
            conn.execute("ALTER TABLE sets ADD COLUMN value_index REAL")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    finally:
        conn.close()
