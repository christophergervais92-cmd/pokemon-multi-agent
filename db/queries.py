"""
Query helpers for sets, cards, pull rates, and chase cards.
"""
from __future__ import annotations

import re
from typing import Optional

from db.connection import get_connection


def _slug(s: str) -> str:
    """Normalize to slug: lowercase, non-alnum to hyphen, collapse hyphens."""
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9]+", "-", s.strip().lower())
    return re.sub(r"-+", "-", s).strip("-")


def resolve_set_id(identifier: str) -> Optional[str]:
    """
    Resolve a set identifier to canonical set_id so prices and chase cards are always for the correct set.
    Tries: exact id -> case-insensitive id -> exact name -> slug (name normalized) -> slug match on name.
    Returns canonical set_id or None if not found.
    """
    if not identifier or not identifier.strip():
        return None
    raw = identifier.strip()
    conn = get_connection()
    try:
        # 1. Exact id
        row = conn.execute("SELECT id FROM sets WHERE id = ?", (raw,)).fetchone()
        if row:
            return row[0]
        # 2. Case-insensitive id
        row = conn.execute("SELECT id FROM sets WHERE LOWER(id) = LOWER(?)", (raw,)).fetchone()
        if row:
            return row[0]
        # 3. Exact name
        row = conn.execute("SELECT id FROM sets WHERE name = ?", (raw,)).fetchone()
        if row:
            return row[0]
        # 4. Case-insensitive name
        row = conn.execute("SELECT id FROM sets WHERE LOWER(name) = LOWER(?)", (raw,)).fetchone()
        if row:
            return row[0]
        # 5. Slug match: identifier as slug vs slug(name)
        slug_raw = _slug(raw)
        if slug_raw:
            for row in conn.execute("SELECT id, name FROM sets").fetchall():
                if _slug(row[1]) == slug_raw:
                    return row[0]
        return None
    finally:
        conn.close()


def get_sets(series_filter: Optional[str] = None) -> list:
    """Return all sets, optionally filtered by series. For SELECT SET dropdown."""
    conn = get_connection()
    try:
        if series_filter and series_filter.lower() != "all series":
            cur = conn.execute(
                "SELECT id, name, series, release_date, logo_url, total, value_index FROM sets WHERE series = ? ORDER BY release_date DESC",
                (series_filter,),
            )
        else:
            cur = conn.execute(
                "SELECT id, name, series, release_date, logo_url, total, value_index FROM sets ORDER BY release_date DESC"
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_set_by_id(set_id: str) -> Optional[dict]:
    """Return one set by id, or None."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, series, release_date, logo_url, total, value_index FROM sets WHERE id = ?",
            (set_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_cards_by_set(set_id: str) -> list[dict]:
    """Return all cards for a set."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT id, set_id, name, rarity, supertype, subtype, image_url, small_image_url,
                      tcgplayer_market, tcgplayer_low, tcgplayer_mid, tcgplayer_high
               FROM cards WHERE set_id = ? ORDER BY tcgplayer_market DESC, name""",
            (set_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_pull_rates(set_id: str) -> list[dict]:
    """Return pull rates (per pack) for a set. For Pull Rates (Per Pack) section."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, set_id, category, label, rate_per_pack, notes FROM pull_rates WHERE set_id = ? ORDER BY category, id",
            (set_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_chase_cards(
    set_id: str,
    rarity_filter: Optional[str] = None,
    limit: int = 24,
) -> list:
    """
    Return high-value (chase) cards for a set only. Uses set_id strictly so prices are correct for that set.
    rarity_filter: 'All' | 'Illustration Rare' | 'Special Art' | 'Holo' etc. Uses simple LIKE so filters work like before.
    """
    conn = get_connection()
    try:
        if rarity_filter and rarity_filter.strip().lower() != "all":
            r = rarity_filter.strip()
            cur = conn.execute(
                """SELECT id, set_id, name, rarity, image_url, small_image_url,
                          tcgplayer_market, tcgplayer_low, tcgplayer_mid, tcgplayer_high
                   FROM cards
                   WHERE set_id = ? AND (tcgplayer_market IS NOT NULL OR tcgplayer_mid IS NOT NULL)
                     AND (rarity LIKE ? OR rarity = ?)
                   ORDER BY COALESCE(tcgplayer_market, tcgplayer_mid) DESC
                   LIMIT ?""",
                (set_id, f"%{r}%", r, limit),
            )
        else:
            cur = conn.execute(
                """SELECT id, set_id, name, rarity, image_url, small_image_url,
                          tcgplayer_market, tcgplayer_low, tcgplayer_mid, tcgplayer_high
                   FROM cards
                   WHERE set_id = ? AND (tcgplayer_market IS NOT NULL OR tcgplayer_mid IS NOT NULL)
                   ORDER BY COALESCE(tcgplayer_market, tcgplayer_mid) DESC
                   LIMIT ?""",
                (set_id, limit),
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_graded_prices(card_id: str) -> list:
    """Return graded prices (PSA, CGC, BGS) for a card. For Graded Prices section."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT grader, grade, grade_label, market, low, high, source, updated_at
               FROM graded_prices WHERE card_id = ? ORDER BY grader""",
            (card_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
