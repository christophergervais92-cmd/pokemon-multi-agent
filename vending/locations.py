"""
Pokemon TCG vending machine location directory.

Static curated list. Haversine distance for ZIP / lat-lng filtering.
To add a location: append to LOCATIONS and redeploy.
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional


LOCATIONS: List[Dict[str, Any]] = [
    {
        "id": "westfield-sf",
        "name": "Westfield Mall",
        "address": "1 Westfield Pl",
        "city": "San Francisco", "state": "CA", "zip": "94103",
        "lat": 37.7849, "lng": -122.4094,
        "verified": True, "last_verified": "2026-04-17",
        "products": ["Booster Packs", "Promo Cards", "Pin Collections"],
    },
    {
        "id": "south-coast-plaza",
        "name": "South Coast Plaza",
        "address": "3333 Bristol St",
        "city": "Costa Mesa", "state": "CA", "zip": "92626",
        "lat": 33.6914, "lng": -117.8827,
        "verified": True, "last_verified": "2026-04-12",
        "products": ["Booster Packs", "ETBs", "Tins"],
    },
    {
        "id": "king-of-prussia",
        "name": "King of Prussia Mall",
        "address": "160 N Gulph Rd",
        "city": "King of Prussia", "state": "PA", "zip": "19406",
        "lat": 40.0878, "lng": -75.3930,
        "verified": True, "last_verified": "2026-04-16",
        "products": ["Booster Packs", "Promo Cards"],
    },
    {
        "id": "mall-of-america",
        "name": "Mall of America",
        "address": "60 E Broadway",
        "city": "Bloomington", "state": "MN", "zip": "55425",
        "lat": 44.8549, "lng": -93.2422,
        "verified": True, "last_verified": "2026-04-14",
        "products": ["Booster Packs", "Mini Tins", "Promo Cards"],
    },
    {
        "id": "galleria-dallas",
        "name": "Galleria Dallas",
        "address": "13350 Dallas Pkwy",
        "city": "Dallas", "state": "TX", "zip": "75240",
        "lat": 32.9309, "lng": -96.8220,
        "verified": False, "last_verified": "2026-04-05",
        "products": ["Booster Packs"],
    },
    {
        "id": "aventura-mall",
        "name": "Aventura Mall",
        "address": "19501 Biscayne Blvd",
        "city": "Aventura", "state": "FL", "zip": "33180",
        "lat": 25.9569, "lng": -80.1421,
        "verified": True, "last_verified": "2026-04-18",
        "products": ["Booster Packs", "ETBs", "Promo Cards", "Blister Packs"],
    },
    {
        "id": "fashion-show-lv",
        "name": "Fashion Show Mall",
        "address": "3200 Las Vegas Blvd",
        "city": "Las Vegas", "state": "NV", "zip": "89109",
        "lat": 36.1280, "lng": -115.1710,
        "verified": True, "last_verified": "2026-04-15",
        "products": ["Booster Packs", "Tins", "Pin Collections"],
    },
    {
        "id": "tysons-corner",
        "name": "Tysons Corner Center",
        "address": "1961 Chain Bridge Rd",
        "city": "McLean", "state": "VA", "zip": "22102",
        "lat": 38.9187, "lng": -77.2271,
        "verified": False, "last_verified": "2026-03-28",
        "products": ["Booster Packs"],
    },
    {
        "id": "roosevelt-field-ny",
        "name": "Roosevelt Field",
        "address": "630 Old Country Rd",
        "city": "Garden City", "state": "NY", "zip": "11530",
        "lat": 40.7414, "lng": -73.6080,
        "verified": True, "last_verified": "2026-04-13",
        "products": ["Booster Packs", "ETBs"],
    },
    {
        "id": "water-tower-chi",
        "name": "Water Tower Place",
        "address": "835 N Michigan Ave",
        "city": "Chicago", "state": "IL", "zip": "60611",
        "lat": 41.8988, "lng": -87.6238,
        "verified": True, "last_verified": "2026-04-11",
        "products": ["Booster Packs", "Tins"],
    },
    {
        "id": "lenox-square-atl",
        "name": "Lenox Square",
        "address": "3393 Peachtree Rd NE",
        "city": "Atlanta", "state": "GA", "zip": "30326",
        "lat": 33.8464, "lng": -84.3619,
        "verified": False, "last_verified": "2026-03-30",
        "products": ["Booster Packs", "Promo Cards"],
    },
    {
        "id": "south-center-sea",
        "name": "Westfield Southcenter",
        "address": "2800 Southcenter Mall",
        "city": "Tukwila", "state": "WA", "zip": "98188",
        "lat": 47.4597, "lng": -122.2582,
        "verified": True, "last_verified": "2026-04-10",
        "products": ["Booster Packs", "ETBs", "Promo Cards"],
    },
]


# ZIP → (lat, lng) for distance filtering. Only hot ZIPs needed; extend as users request.
_ZIP_CENTROIDS: Dict[str, tuple] = {
    "94103": (37.7749, -122.4194), "92626": (33.6690, -117.9146),
    "19406": (40.0850, -75.3950), "55425": (44.8549, -93.2422),
    "75240": (32.9309, -96.8220), "33180": (25.9569, -80.1421),
    "89109": (36.1280, -115.1710), "22102": (38.9187, -77.2271),
    "11530": (40.7268, -73.6343), "60611": (41.8989, -87.6228),
    "30326": (33.8464, -84.3619), "98188": (47.4638, -122.2729),
    "90210": (34.0901, -118.4065), "10001": (40.7484, -73.9967),
    "94105": (37.7898, -122.3942), "02101": (42.3584, -71.0598),
}


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 3958.8
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def list_locations(
    zip_code: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    radius_miles: Optional[float] = None,
    verified_only: bool = False,
) -> List[Dict[str, Any]]:
    """Return vending locations, optionally filtered."""
    items = list(LOCATIONS)

    if verified_only:
        items = [i for i in items if i["verified"]]

    if state:
        items = [i for i in items if i["state"].lower() == state.lower()]

    if city:
        items = [i for i in items if city.lower() in i["city"].lower()]

    if zip_code:
        zip_code = zip_code.strip()
        if radius_miles and zip_code in _ZIP_CENTROIDS:
            clat, clng = _ZIP_CENTROIDS[zip_code]
            with_distance = [
                {**i, "distance_miles": round(_haversine_miles(clat, clng, i["lat"], i["lng"]), 1)}
                for i in items
            ]
            items = [i for i in with_distance if i["distance_miles"] <= radius_miles]
            items.sort(key=lambda i: i["distance_miles"])
        else:
            # Fallback: ZIP prefix match
            items = [i for i in items if i["zip"].startswith(zip_code)]

    return items


def get_location(location_id: str) -> Optional[Dict[str, Any]]:
    for loc in LOCATIONS:
        if loc["id"] == location_id:
            return loc
    return None


def vending_stats() -> Dict[str, Any]:
    return {
        "total_locations": len(LOCATIONS),
        "verified": sum(1 for i in LOCATIONS if i["verified"]),
        "states_covered": len({i["state"] for i in LOCATIONS}),
    }
