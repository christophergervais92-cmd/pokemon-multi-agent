"""
Card search functionality with fuzzy matching.
"""
from __future__ import annotations

from typing import List, Optional
import re
from difflib import SequenceMatcher

from db.connection import get_connection


def _normalize(text: str) -> str:
    """Normalize text for search: lowercase, remove special chars."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def _similarity(a: str, b: str) -> float:
    """Calculate string similarity (0-1)."""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def search_cards(
    query: str,
    set_id: Optional[str] = None,
    rarity: Optional[str] = None,
    limit: int = 20
) -> List[dict]:
    """
    Search cards by name with fuzzy matching.
    
    Args:
        query: Search query string
        set_id: Optional set filter
        rarity: Optional rarity filter
        limit: Maximum results
    
    Returns:
        List of matching cards sorted by relevance
    """
    conn = get_connection()
    try:
        # Build query
        sql = """SELECT id, set_id, name, rarity, supertype, subtype, 
                        image_url, small_image_url, tcgplayer_market
                 FROM cards WHERE 1=1"""
        params = []
        
        if set_id:
            sql += " AND set_id = ?"
            params.append(set_id)
        
        if rarity:
            sql += " AND (rarity LIKE ? OR rarity = ?)"
            params.extend([f"%{rarity}%", rarity])
        
        # If query is short, do prefix match
        if len(query) < 3:
            sql += " AND name LIKE ?"
            params.append(f"{query}%")
            sql += f" ORDER BY tcgplayer_market DESC NULLS LAST LIMIT ?"
            params.append(limit)
            
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
        
        # For longer queries, fetch candidates and rank by similarity
        sql += f" ORDER BY tcgplayer_market DESC NULLS LAST LIMIT 200"
        cur = conn.execute(sql, params)
        candidates = [dict(row) for row in cur.fetchall()]
        
        # Score by similarity
        normalized_query = _normalize(query)
        scored = []
        for card in candidates:
            name = card.get("name", "")
            score = _similarity(name, query)
            
            # Boost exact matches and starts-with
            if _normalize(name) == normalized_query:
                score += 0.5
            elif _normalize(name).startswith(normalized_query):
                score += 0.3
            
            if score > 0.3:  # Threshold
                scored.append((score, card))
        
        # Sort by score and return top results
        scored.sort(key=lambda x: x[0], reverse=True)
        return [card for _, card in scored[:limit]]
    finally:
        conn.close()


def search_by_card_number(set_id: str, number: str) -> Optional[dict]:
    """Find card by set ID and card number (e.g., "sv8", "161")."""
    conn = get_connection()
    try:
        # Try exact match on id pattern
        card_id = f"{set_id}-{number}"
        row = conn.execute(
            """SELECT id, set_id, name, rarity, image_url, tcgplayer_market 
               FROM cards WHERE id = ?""",
            (card_id,)
        ).fetchone()
        
        if row:
            return dict(row)
        
        # Try partial match
        row = conn.execute(
            """SELECT id, set_id, name, rarity, image_url, tcgplayer_market 
               FROM cards WHERE id LIKE ? AND set_id = ?""",
            (f"%{set_id}-{number}%", set_id)
        ).fetchone()
        
        return dict(row) if row else None
    finally:
        conn.close()


def get_card_by_id(card_id: str) -> Optional[dict]:
    """Get full card details by ID."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT c.*, s.name as set_name, s.series as set_series
               FROM cards c
               JOIN sets s ON c.set_id = s.id
               WHERE c.id = ?""",
            (card_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_related_cards(card_id: str, limit: int = 8) -> List[dict]:
    """Get related cards (same set, similar rarity/price)."""
    card = get_card_by_id(card_id)
    if not card:
        return []
    
    conn = get_connection()
    try:
        # Same set, similar price range
        price = card.get("tcgplayer_market") or card.get("tcgplayer_mid") or 0
        set_id = card.get("set_id")
        
        cur = conn.execute(
            """SELECT id, set_id, name, rarity, image_url, tcgplayer_market
               FROM cards 
               WHERE set_id = ? AND id != ?
               ORDER BY ABS(COALESCE(tcgplayer_market, 0) - ?) ASC
               LIMIT ?""",
            (set_id, card_id, price, limit)
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
