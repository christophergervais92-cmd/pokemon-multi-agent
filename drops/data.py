"""
Static drop calendar, rumors, and live intel data.

Curated release calendar for upcoming Pokemon TCG products.
For updates, edit this file and redeploy — no admin UI yet.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


CONFIRMED_DROPS: List[Dict[str, Any]] = [
    {
        "id": "pe-wave3-2026-03",
        "title": "Prismatic Evolutions Wave 3",
        "date": "2026-03-14",
        "date_label": "Mar 14, 2026",
        "retailers": ["Target", "Walmart", "Pokemon Center", "Best Buy", "GameStop"],
        "type": "restock",
        "border_color": "border-l-accent",
        "products": [
            {"name": "Elite Trainer Box", "msrp": 59.99, "packs": 9, "type": "etb"},
            {"name": "Booster Bundle", "msrp": 29.99, "packs": 6, "type": "booster_bundle"},
            {"name": "Mini Tin (Random)", "msrp": 7.99, "packs": 2, "type": "tin"},
            {"name": "3-Pack Blister", "msrp": 14.99, "packs": 3, "type": "blister"},
        ],
        "top_chase_cards": [
            "Umbreon ex SAR", "Pikachu ex SAR", "Eevee Illustration Rare", "Sylveon ex SAR",
        ],
        "estimated_pull_rates": [
            {"rarity": "Special Art Rare", "rate": "1 in 60 packs"},
            {"rarity": "Illustration Rare", "rate": "1 in 18 packs"},
            {"rarity": "Holo Rare", "rate": "1 in 3 packs"},
        ],
    },
    {
        "id": "journey-together-2026-03",
        "title": "Journey Together",
        "date": "2026-03-28",
        "date_label": "Mar 28, 2026",
        "retailers": ["All Retailers"],
        "type": "new_set",
        "border_color": "border-l-success",
        "products": [
            {"name": "Booster Box", "msrp": 143.64, "packs": 36, "type": "booster_box"},
            {"name": "Elite Trainer Box", "msrp": 49.99, "packs": 9, "type": "etb"},
            {"name": "Booster Bundle", "msrp": 29.99, "packs": 6, "type": "booster_bundle"},
            {"name": "Build & Battle Box", "msrp": 14.99, "packs": 4, "type": "collection_box"},
            {"name": "3-Pack Blister", "msrp": 14.99, "packs": 3, "type": "blister"},
        ],
        "top_chase_cards": [
            "Ash & Pikachu SAR", "Red & Charizard SAR", "N & Reshiram SAR", "Cynthia & Garchomp SAR",
        ],
        "estimated_pull_rates": [
            {"rarity": "Special Art Rare", "rate": "1 in 55 packs"},
            {"rarity": "Illustration Rare", "rate": "1 in 20 packs"},
            {"rarity": "Ultra Rare", "rate": "1 in 9 packs"},
            {"rarity": "Holo Rare", "rate": "1 in 3 packs"},
        ],
    },
    {
        "id": "pokecenter-eeveelution-2026-04",
        "title": "Pokemon Center Exclusive: Eeveelution Collection",
        "date": "2026-04-05",
        "date_label": "Apr 5, 2026",
        "retailers": ["Pokemon Center"],
        "type": "exclusive",
        "border_color": "border-l-[#ffcb05]",
        "products": [
            {"name": "Premium Collection Box", "msrp": 79.99, "packs": 10, "type": "collection_box"},
        ],
        "top_chase_cards": ["Exclusive Eeveelution Promo Cards (8 total)"],
        "estimated_pull_rates": [],
    },
    {
        "id": "surging-sparks-reprint-2026-03",
        "title": "Surging Sparks Reprint Wave",
        "date": "2026-03-07",
        "date_label": "Mar 7, 2026",
        "retailers": ["Target", "Walmart"],
        "type": "restock",
        "border_color": "border-l-info",
        "products": [
            {"name": "Elite Trainer Box", "msrp": 49.99, "packs": 9, "type": "etb"},
            {"name": "Booster Box", "msrp": 143.64, "packs": 36, "type": "booster_box"},
        ],
        "top_chase_cards": ["Charizard ex SAR", "Pikachu ex IR", "Arceus VSTAR"],
        "estimated_pull_rates": [],
    },
    {
        "id": "sv09-astral-crown-2026-05",
        "title": "SV09: Astral Crown",
        "date": "2026-05-23",
        "date_label": "May 23, 2026",
        "retailers": ["All Retailers"],
        "type": "new_set",
        "border_color": "border-l-warning",
        "products": [
            {"name": "Booster Box", "msrp": 143.64, "packs": 36, "type": "booster_box"},
            {"name": "Elite Trainer Box", "msrp": 49.99, "packs": 9, "type": "etb"},
            {"name": "Booster Bundle", "msrp": 29.99, "packs": 6, "type": "booster_bundle"},
            {"name": "Ultra Premium Collection", "msrp": 119.99, "packs": 16, "type": "ultra_premium"},
        ],
        "top_chase_cards": ["TBD — set list not yet revealed"],
        "estimated_pull_rates": [
            {"rarity": "Special Art Rare", "rate": "TBD"},
            {"rarity": "Illustration Rare", "rate": "TBD"},
        ],
    },
    {
        "id": "pe-blisters-tins-2026-03",
        "title": "Prismatic Evolutions Blisters & Tins",
        "date": "2026-03-01",
        "date_label": "Mar 1, 2026",
        "retailers": ["Target", "Walmart", "Best Buy"],
        "type": "restock",
        "border_color": "border-l-accent",
        "products": [
            {"name": "3-Pack Blister", "msrp": 14.99, "packs": 3, "type": "blister"},
            {"name": "Collector Tin", "msrp": 29.99, "packs": 5, "type": "tin"},
        ],
        "top_chase_cards": [],
        "estimated_pull_rates": [],
    },
    {
        "id": "destined-rivals-2026-06",
        "title": "Destined Rivals",
        "date": "2026-06-13",
        "date_label": "Jun 13, 2026",
        "retailers": ["All Retailers"],
        "type": "new_set",
        "border_color": "border-l-purple-400",
        "products": [
            {"name": "Booster Box", "msrp": 143.64, "packs": 36, "type": "booster_box"},
            {"name": "Elite Trainer Box", "msrp": 49.99, "packs": 9, "type": "etb"},
            {"name": "Booster Bundle", "msrp": 29.99, "packs": 6, "type": "booster_bundle"},
        ],
        "top_chase_cards": ["TBD — expected to feature rival trainers"],
        "estimated_pull_rates": [],
    },
    {
        "id": "jt-build-battle-2026-03",
        "title": "Journey Together Build & Battle Stadium",
        "date": "2026-03-21",
        "date_label": "Mar 21, 2026",
        "retailers": ["Game Stores", "Pokemon Center"],
        "type": "special",
        "border_color": "border-l-success",
        "products": [
            {"name": "Build & Battle Stadium", "msrp": 44.99, "packs": 12, "type": "collection_box"},
        ],
        "top_chase_cards": [],
        "estimated_pull_rates": [],
    },
]


RUMORS: List[Dict[str, Any]] = [
    {
        "id": "sv10-mega-evolutions",
        "title": "SV10 to feature Mega Evolutions",
        "source": "PokeBeach",
        "reliability": "high",
        "description": "Reliable sources suggest SV10 may reintroduce Mega Evolution mechanics with a new card type. Expected announcement in Q3 2026.",
        "date": "Q3 2026",
        "impact": "Major hype — Mega Charizard X/Y would drive massive demand",
    },
    {
        "id": "gold-star-reprints",
        "title": "Gold Star reprints in special collection",
        "source": "Reddit r/PokemonTCG",
        "reliability": "medium",
        "description": "Multiple leakers hint at a premium collection featuring reprints of classic Gold Star cards from the EX era.",
        "date": "Summer 2026",
        "impact": "Collectors would pay premium — Gold Star Rayquaza is iconic",
    },
    {
        "id": "target-pikachu-promo",
        "title": "Target exclusive Pikachu promo wave",
        "source": "Twitter @PokeLeaks",
        "reliability": "medium",
        "description": "A Target-exclusive Pikachu promo card may be included with ETB purchases during a spring promotional event.",
        "date": "Spring 2026",
        "impact": "Moderate — exclusive promos always drive foot traffic",
    },
    {
        "id": "25th-anniversary-part2",
        "title": "25th Anniversary Part 2 celebration set",
        "source": "PokeBeach",
        "reliability": "low",
        "description": "Speculation about a second 25th anniversary-style celebration set with reprints of iconic cards from every generation.",
        "date": "Late 2026",
        "impact": "Would be massive if true — original Celebrations was a phenomenon",
    },
    {
        "id": "pokecenter-grading-service",
        "title": "Pokemon Center to launch grading service",
        "source": "Industry Insider",
        "reliability": "low",
        "description": "Rumors of TPC partnering with a grading company for an official Pokemon Card Grading service, potentially disrupting PSA/BGS/CGC market.",
        "date": "Unknown",
        "impact": "Could significantly shift the grading market dynamics",
    },
]


LIVE_INTEL: List[Dict[str, Any]] = [
    {
        "id": "intel-pe-dallas",
        "source": "Reddit",
        "content": "Prismatic Evolutions ETBs spotted at Target in Dallas, TX. Full shelves reported — DPCI 087-35-0214.",
        "timestamp": "12m ago",
        "verified": True,
        "location": "Dallas, TX",
        "product": "Prismatic Evolutions ETB",
    },
    {
        "id": "intel-jt-setlist",
        "source": "PokeBeach",
        "content": "Journey Together official set list leaked — 198 cards including 15 Illustration Rares and 6 Special Art Rares.",
        "timestamp": "1h ago",
        "verified": True,
        "location": None,
        "product": None,
    },
    {
        "id": "intel-pokecenter-pe-bundles",
        "source": "Twitter",
        "content": "Pokemon Center just added Prismatic Evolutions booster bundles back in stock. Limited quantities!",
        "timestamp": "2h ago",
        "verified": False,
        "location": None,
        "product": "Prismatic Evolutions Booster Bundle",
    },
    {
        "id": "intel-costco-socal",
        "source": "Discord",
        "content": "Multiple Costco warehouses in SoCal region restocked Pokemon tins and booster bundles at clearance prices.",
        "timestamp": "3h ago",
        "verified": True,
        "location": "Southern California",
        "product": None,
    },
    {
        "id": "intel-walmart-surging",
        "source": "Reddit",
        "content": "Walmart online restocked Surging Sparks booster boxes at MSRP $143.64. Ships free with Walmart+.",
        "timestamp": "5h ago",
        "verified": True,
        "location": None,
        "product": "Surging Sparks BB",
    },
    {
        "id": "intel-lcs-jt",
        "source": "Instagram",
        "content": "Local card shop showing off Journey Together pre-release kits. Product looks clean — new trainer cards confirmed.",
        "timestamp": "6h ago",
        "verified": False,
        "location": None,
        "product": None,
    },
    {
        "id": "intel-bestbuy-pe-blisters",
        "source": "Twitter",
        "content": "Best Buy added Prismatic Evolutions 3-pack blisters online. $14.99 MSRP — limit 2 per customer.",
        "timestamp": "8h ago",
        "verified": True,
        "location": None,
        "product": "Prismatic Evolutions Blister",
    },
]


def _days_until(date_str: str) -> int:
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (target - now).days
        return max(0, delta)
    except (ValueError, TypeError):
        return 0


def list_drops(time_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return drops, optionally filtered by time window.

    time_filter values: 'all', 'this_week', 'this_month', 'next_month', 'q2_2026'
    """
    drops = [{**d, "days_until": _days_until(d["date"])} for d in CONFIRMED_DROPS]

    if not time_filter or time_filter.lower() in ("all", ""):
        return sorted(drops, key=lambda d: d["date"])

    now = datetime.now(timezone.utc)
    tf = time_filter.lower().replace(" ", "_")

    def _keep(d: Dict[str, Any]) -> bool:
        try:
            dd = datetime.strptime(d["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        if tf == "this_week":
            return 0 <= (dd - now).days <= 7
        if tf == "this_month":
            return dd.month == now.month and dd.year == now.year
        if tf == "next_month":
            nm = now.month % 12 + 1
            ny = now.year + (1 if now.month == 12 else 0)
            return dd.month == nm and dd.year == ny
        if tf == "q2_2026":
            return datetime(2026, 4, 1, tzinfo=timezone.utc) <= dd < datetime(2026, 7, 1, tzinfo=timezone.utc)
        return True

    return sorted([d for d in drops if _keep(d)], key=lambda d: d["date"])


def list_rumors(reliability: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return rumors, optionally filtered by reliability ('high'|'medium'|'low')."""
    if reliability and reliability.lower() in ("high", "medium", "low"):
        return [r for r in RUMORS if r["reliability"] == reliability.lower()]
    return list(RUMORS)


def list_live_intel(source: Optional[str] = None, verified_only: bool = False) -> List[Dict[str, Any]]:
    """Return live intel items, optionally filtered by source / verified."""
    items = list(LIVE_INTEL)
    if source:
        items = [i for i in items if i["source"].lower() == source.lower()]
    if verified_only:
        items = [i for i in items if i["verified"]]
    return items


def get_calendar_events() -> List[Dict[str, Any]]:
    """Flat calendar view — one entry per drop with minimal fields."""
    color_for_type = {
        "new_set": "#ef4444",
        "restock": "#dc2626",
        "exclusive": "#ffcb05",
        "special": "#a855f7",
        "prerelease": "#f97316",
    }
    events = []
    for d in CONFIRMED_DROPS:
        events.append({
            "date": d["date"],
            "title": d["title"],
            "type": d["type"],
            "color": color_for_type.get(d["type"], "#ef4444"),
            "drop_id": d["id"],
        })
    return sorted(events, key=lambda e: e["date"])


def drops_summary() -> Dict[str, Any]:
    """Summary stats for the dashboard."""
    drops = list_drops()
    next_drop = drops[0] if drops else None
    return {
        "total_drops": len(CONFIRMED_DROPS),
        "new_sets": sum(1 for d in CONFIRMED_DROPS if d["type"] == "new_set"),
        "restocks": sum(1 for d in CONFIRMED_DROPS if d["type"] == "restock"),
        "exclusives": sum(1 for d in CONFIRMED_DROPS if d["type"] == "exclusive"),
        "verified_sightings": sum(1 for i in LIVE_INTEL if i["verified"]),
        "active_rumors": len(RUMORS),
        "days_until_next": next_drop["days_until"] if next_drop else None,
        "next_drop_title": next_drop["title"] if next_drop else None,
    }
