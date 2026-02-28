"""
Market prices and TCG set data — backed by pokemon_tcg.db.
Run scripts/seed_db.py to populate from Pokémon TCG API.
"""
from __future__ import annotations

from typing import Optional

from db.connection import get_connection
from db.queries import (
    get_sets as db_get_sets,
    get_set_by_id,
    get_pull_rates as db_get_pull_rates,
    get_chase_cards as db_get_chase_cards,
    get_graded_prices as db_get_graded_prices,
    resolve_set_id as db_resolve_set_id,
)


def get_price(card_id: str) -> Optional[float]:
    """Return current market price for card from DB (tcgplayer_market or tcgplayer_mid)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT tcgplayer_market, tcgplayer_mid FROM cards WHERE id = ?",
            (card_id.strip(),),
        ).fetchone()
        if not row:
            return None
        market, mid = row[0], row[1]
        return float(market) if market is not None else (float(mid) if mid is not None else None)
    finally:
        conn.close()


def get_trends(card_id: str) -> list:
    """Return price trend data. Placeholder: empty until trend history is stored."""
    return []


def get_sets(series_filter: Optional[str] = None) -> list:
    """Return sets for SELECT SET dropdown. Filter by series (e.g. 'Scarlet & Violet') or None for all."""
    return db_get_sets(series_filter=series_filter)


def get_set(set_id: str) -> Optional[dict]:
    """Return one set by id (for Set Logo, SET VALUE INDEX)."""
    return get_set_by_id(set_id)


def get_pull_rates(set_id: str) -> list[dict]:
    """Return pull rates (per pack) for a set. For Pull Rates (Per Pack) section."""
    return db_get_pull_rates(set_id)


def get_chase_cards(
    set_id: str,
    rarity_filter: Optional[str] = None,
    limit: int = 24,
) -> list:
    """Return high-value (chase) cards for a set. rarity_filter: All, Illustration Rare, Special Art, Holo, etc."""
    return db_get_chase_cards(set_id=set_id, rarity_filter=rarity_filter, limit=limit)


def resolve_set_id(identifier: str) -> Optional[str]:
    """Resolve set identifier (id, name, or slug) to canonical set_id so prices/chase cards are for the correct set."""
    return db_resolve_set_id(identifier)


def get_graded_prices(card_id: str) -> dict:
    """
    Return graded prices (PSA, CGC, Beckett/BGS) for a card.
    Returns dict keyed by grader: {"psa": {...}, "cgc": {...}, "bgs": {...}}.
    """
    rows = db_get_graded_prices(card_id.strip())
    out = {}
    for r in rows:
        grader = (r.get("grader") or "").strip().upper()
        key = "bgs" if grader == "BGS" else grader.lower() if grader in ("PSA", "CGC") else grader.lower()
        out[key] = {
            "grader": r.get("grader"),
            "grade": r.get("grade"),
            "grade_label": r.get("grade_label"),
            "market": r.get("market"),
            "low": r.get("low"),
            "high": r.get("high"),
            "source": r.get("source"),
            "updated_at": r.get("updated_at"),
        }
    return out
