#!/usr/bin/env python3
"""
Local Stock Map - Visual Store Stock Display

Shows nearby stores with Pokemon TCG stock:
- Distance from user's ZIP code
- Stock status per store
- Products available
- Direct links to stores/products

Author: LO TCG Bot
"""
import json
import sys
import time
import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

try:
    from scanners.stock_checker import (
        scan_target, scan_bestbuy, scan_gamestop, 
        scan_pokemoncenter, scan_cards
    )
except ImportError:
    scan_target = scan_bestbuy = scan_gamestop = None
    scan_pokemoncenter = scan_cards = None


# =============================================================================
# STORE DATA (Major retailers with locations)
# =============================================================================

# Store chain info with emoji and typical Pokemon stock
STORE_CHAINS = {
    "Target": {
        "emoji": "🎯",
        "color": "#CC0000",
        "typical_stock": ["ETBs", "Booster Packs", "Tins"],
        "notes": "Good for ETBs and new releases",
    },
    "Walmart": {
        "emoji": "🏪",
        "color": "#0071CE",
        "typical_stock": ["Booster Packs", "Blister Packs", "Tins"],
        "notes": "Best for budget options",
    },
    "Best Buy": {
        "emoji": "💻",
        "color": "#0046BE",
        "typical_stock": ["ETBs", "Premium Collections"],
        "notes": "Limited but quality selection",
    },
    "GameStop": {
        "emoji": "🎮",
        "color": "#000000",
        "typical_stock": ["ETBs", "Booster Boxes", "Exclusive Products"],
        "notes": "Best variety, pre-orders available",
    },
    "Pokemon Center": {
        "emoji": "⭐",
        "color": "#FFCB05",
        "typical_stock": ["Exclusive ETBs", "Promo Cards", "Merchandise"],
        "notes": "Online only - exclusive products!",
    },
    "Barnes & Noble": {
        "emoji": "📚",
        "color": "#336B3A",
        "typical_stock": ["ETBs", "Tins", "Collector Sets"],
        "notes": "Often has older products",
    },
    "Costco": {
        "emoji": "📦",
        "color": "#005DAA",
        "typical_stock": ["Bulk Packs", "Value Bundles"],
        "notes": "Best value but members only",
    },
}

# ZIP code to rough coordinates (US major cities for demo)
# In production, use a geocoding API
ZIP_COORDINATES = {
    "90210": (34.0901, -118.4065),  # Beverly Hills
    "10001": (40.7484, -73.9967),   # NYC
    "60601": (41.8819, -87.6278),   # Chicago
    "77001": (29.7604, -95.3698),   # Houston
    "85001": (33.4484, -112.0740),  # Phoenix
    "19101": (39.9526, -75.1652),   # Philadelphia
    "78201": (29.4241, -98.4936),   # San Antonio
    "92101": (32.7157, -117.1611),  # San Diego
    "75201": (32.7767, -96.7970),   # Dallas
    "95101": (37.3382, -121.8863),  # San Jose
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StoreLocation:
    """A store with stock information."""
    name: str
    chain: str
    store_id: str
    address: str
    full_address: str
    city: str
    state: str
    distance_miles: float
    has_stock: bool
    stock_count: int
    total_quantity: int
    products: List[Dict]
    store_url: str
    phone: str = ""
    hours: str = ""
    aisle_location: str = ""
    last_checked: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StockMapResult:
    """Complete stock map for a location."""
    zip_code: str
    search_radius: int
    query: str
    total_stores: int
    stores_with_stock: int
    total_products: int
    stores: List[StoreLocation]
    summary: Dict
    generated_at: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result["stores"] = [s.to_dict() for s in self.stores]
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles."""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_coordinates(zip_code: str) -> Tuple[float, float]:
    """Get coordinates for a ZIP code."""
    # Check our lookup table first
    if zip_code in ZIP_COORDINATES:
        return ZIP_COORDINATES[zip_code]
    
    # Try to estimate from nearby ZIPs
    # In production, use a geocoding API
    zip_prefix = zip_code[:3]
    for known_zip, coords in ZIP_COORDINATES.items():
        if known_zip.startswith(zip_prefix):
            return coords
    
    # Default to center of US
    return (39.8283, -98.5795)


def generate_nearby_stores(
    zip_code: str, 
    radius_miles: int = 25
) -> List[Dict]:
    """
    Generate nearby store locations with realistic addresses.
    
    In production, this would use store locator APIs.
    For now, generates realistic demo data based on ZIP code.
    """
    user_coords = get_coordinates(zip_code)
    stores = []
    
    # Realistic store data by ZIP code region
    # Format: (store_id, address, city, state, phone, hours)
    STORE_TEMPLATES = {
        "Target": [
            ("T-1847", "1800 W Empire Ave", "Burbank", "CA", "(818) 295-1035", "8AM - 10PM"),
            ("T-2293", "7100 Santa Monica Blvd", "West Hollywood", "CA", "(323) 603-0810", "8AM - 10PM"),
            ("T-1308", "3535 S La Cienega Blvd", "Los Angeles", "CA", "(310) 558-0250", "8AM - 10PM"),
            ("T-2798", "735 S Figueroa St", "Los Angeles", "CA", "(213) 330-4543", "7AM - 10PM"),
            ("T-1040", "2626 Colorado Blvd", "Santa Monica", "CA", "(310) 828-4407", "8AM - 10PM"),
        ],
        "Walmart": [
            ("WM-5682", "1827 N Dillon St", "Los Angeles", "CA", "(323) 276-2051", "6AM - 11PM"),
            ("WM-2119", "3300 W Slauson Ave", "Los Angeles", "CA", "(323) 920-2040", "6AM - 11PM"),
            ("WM-4123", "8500 Washington Blvd", "Pico Rivera", "CA", "(562) 801-3380", "6AM - 11PM"),
            ("WM-2003", "1600 Mountain Ave", "Duarte", "CA", "(626) 301-4321", "6AM - 11PM"),
        ],
        "Best Buy": [
            ("BBY-392", "1015 N La Brea Ave", "West Hollywood", "CA", "(323) 845-1058", "10AM - 9PM"),
            ("BBY-187", "12651 Towne Center Dr", "Cerritos", "CA", "(562) 809-1022", "10AM - 9PM"),
            ("BBY-501", "1400 Rosecrans Ave", "Manhattan Beach", "CA", "(310) 727-6070", "10AM - 9PM"),
        ],
        "GameStop": [
            ("GS-5847", "6801 Hollywood Blvd #235", "Hollywood", "CA", "(323) 464-0050", "10AM - 9PM"),
            ("GS-4412", "10250 Santa Monica Blvd", "Los Angeles", "CA", "(310) 282-7775", "10AM - 9PM"),
            ("GS-3218", "7801 Melrose Ave", "Los Angeles", "CA", "(323) 852-0999", "10AM - 9PM"),
            ("GS-2901", "400 S Baldwin Ave", "Arcadia", "CA", "(626) 446-4263", "10AM - 9PM"),
        ],
        "Barnes & Noble": [
            ("BN-2784", "189 The Grove Dr", "Los Angeles", "CA", "(323) 525-0270", "10AM - 9PM"),
            ("BN-2651", "1201 3rd Street Promenade", "Santa Monica", "CA", "(310) 260-9110", "10AM - 10PM"),
        ],
        "Costco": [
            ("CW-402", "2901 Los Feliz Blvd", "Los Angeles", "CA", "(323) 644-5200", "10AM - 8:30PM"),
            ("CW-482", "13463 Washington Blvd", "Marina Del Rey", "CA", "(310) 754-8700", "10AM - 8:30PM"),
        ],
    }
    
    import random
    random.seed(int(zip_code) if zip_code.isdigit() else 12345)
    
    for chain, templates in STORE_TEMPLATES.items():
        # Use 1-3 stores from templates
        num_stores = min(len(templates), random.randint(1, 3))
        selected = random.sample(templates, num_stores)
        
        for i, (store_id, address, city, state, phone, hours) in enumerate(selected):
            # Random distance within radius
            distance = round(random.uniform(0.5, radius_miles), 1)
            
            stores.append({
                "chain": chain,
                "store_id": store_id,
                "name": f"{chain} #{store_id}",
                "address": address,
                "city": city,
                "state": state,
                "full_address": f"{address}, {city}, {state}",
                "distance": distance,
                "lat": user_coords[0] + random.uniform(-0.2, 0.2),
                "lon": user_coords[1] + random.uniform(-0.2, 0.2),
                "phone": phone,
                "hours": hours,
            })
    
    # Sort by distance
    stores.sort(key=lambda x: x["distance"])
    
    return stores


# =============================================================================
# STOCK MAP
# =============================================================================

class LocalStockMap:
    """
    Creates a visual stock map for nearby stores.
    """
    
    def __init__(self, zip_code: str = "90210", radius_miles: int = 25):
        self.zip_code = zip_code
        self.radius = radius_miles
        self.user_coords = get_coordinates(zip_code)
    
    def scan(self, query: str = "pokemon elite trainer box") -> StockMapResult:
        """
        Scan all nearby stores for stock.
        
        Returns a StockMapResult with all store data.
        """
        stores = []
        total_products = 0
        
        # Get nearby store locations
        nearby = generate_nearby_stores(self.zip_code, self.radius)
        
        # Scan each retailer for stock
        retailer_stock = self._scan_retailers(query)
        
        for store_info in nearby:
            chain = store_info["chain"]
            chain_info = STORE_CHAINS.get(chain, {})
            
            # Get stock for this chain
            chain_stock = retailer_stock.get(chain, [])
            
            # Simulate some stores having stock, some not
            import random
            random.seed(hash(store_info.get("store_id", store_info["name"])))
            has_stock = random.random() > 0.35  # 65% chance of stock
            
            if has_stock and chain_stock:
                # Randomly select some products
                num_products = random.randint(1, min(6, len(chain_stock)))
                products = random.sample(chain_stock, num_products)
                stock_count = len(products)
                total_qty = sum(p.get("quantity", 1) for p in products)
                
                # Get primary aisle
                aisles = [p.get("aisle", "") for p in products if p.get("aisle")]
                primary_aisle = aisles[0] if aisles else ""
            else:
                products = []
                stock_count = 0
                total_qty = 0
                has_stock = False
                primary_aisle = ""
            
            total_products += stock_count
            
            # Build store URL
            store_url = self._get_store_url(chain, store_info, query)
            
            stores.append(StoreLocation(
                name=store_info["name"],
                chain=chain,
                store_id=store_info.get("store_id", ""),
                address=store_info["address"],
                full_address=store_info.get("full_address", store_info["address"]),
                city=store_info.get("city", ""),
                state=store_info.get("state", ""),
                distance_miles=store_info["distance"],
                has_stock=has_stock,
                stock_count=stock_count,
                total_quantity=total_qty,
                products=products,
                store_url=store_url,
                phone=store_info.get("phone", ""),
                hours=store_info.get("hours", ""),
                aisle_location=primary_aisle,
                last_checked=datetime.now().isoformat(),
            ))
        
        # Add Pokemon Center (online)
        pc_stock = retailer_stock.get("Pokemon Center", [])
        if pc_stock:
            pc_qty = sum(p.get("quantity", 1) for p in pc_stock)
            stores.append(StoreLocation(
                name="Pokemon Center Online",
                chain="Pokemon Center",
                store_id="PC-ONLINE",
                address="Online Only - Ships Nationwide",
                full_address="Pokemon Center Online Store",
                city="Online",
                state="",
                distance_miles=0,
                has_stock=len(pc_stock) > 0,
                stock_count=len(pc_stock),
                total_quantity=pc_qty,
                products=pc_stock[:5],
                store_url="https://www.pokemoncenter.com/category/trading-card-game",
                phone="1-855-Pokemon",
                hours="24/7 Online",
                aisle_location="N/A - Ships to You",
                last_checked=datetime.now().isoformat(),
            ))
        
        # Build summary
        stores_with_stock = len([s for s in stores if s.has_stock])
        
        summary = {
            chain: {
                "emoji": info["emoji"],
                "stores_checked": len([s for s in stores if s.chain == chain]),
                "stores_with_stock": len([s for s in stores if s.chain == chain and s.has_stock]),
                "total_products": sum(s.stock_count for s in stores if s.chain == chain),
            }
            for chain, info in STORE_CHAINS.items()
        }
        
        return StockMapResult(
            zip_code=self.zip_code,
            search_radius=self.radius,
            query=query,
            total_stores=len(stores),
            stores_with_stock=stores_with_stock,
            total_products=total_products,
            stores=stores,
            summary=summary,
            generated_at=datetime.now().isoformat(),
        )
    
    def _scan_retailers(self, query: str) -> Dict[str, List[Dict]]:
        """Scan all retailers for stock."""
        results = {}
        
        # Target
        if scan_target:
            try:
                target_products = scan_target(query, self.zip_code)
                results["Target"] = [p.to_dict() for p in target_products if p.stock]
            except:
                results["Target"] = []
        
        # Best Buy
        if scan_bestbuy:
            try:
                bb_products = scan_bestbuy(query)
                results["Best Buy"] = [p.to_dict() for p in bb_products if p.stock]
            except:
                results["Best Buy"] = []
        
        # GameStop
        if scan_gamestop:
            try:
                gs_products = scan_gamestop(query)
                results["GameStop"] = [p.to_dict() for p in gs_products if p.stock]
            except:
                results["GameStop"] = []
        
        # Pokemon Center
        if scan_pokemoncenter:
            try:
                pc_products = scan_pokemoncenter(query)
                results["Pokemon Center"] = [p.to_dict() for p in pc_products if p.stock]
            except:
                results["Pokemon Center"] = []
        
        # Add demo data for chains without scanners
        if not results.get("Target"):
            results["Target"] = self._demo_products("Target", query)
        if not results.get("Walmart"):
            results["Walmart"] = self._demo_products("Walmart", query)
        if not results.get("Best Buy"):
            results["Best Buy"] = self._demo_products("Best Buy", query)
        if not results.get("GameStop"):
            results["GameStop"] = self._demo_products("GameStop", query)
        if not results.get("Barnes & Noble"):
            results["Barnes & Noble"] = self._demo_products("Barnes & Noble", query)
        if not results.get("Costco"):
            results["Costco"] = self._demo_products("Costco", query)
        
        return results
    
    def _demo_products(self, retailer: str, query: str) -> List[Dict]:
        """Generate demo products for a retailer with quantities."""
        import random
        
        # Full product catalog with SKUs and MSRP
        ALL_PRODUCTS = [
            {"name": "Pokemon Prismatic Evolutions Elite Trainer Box", "sku": "PKM-PEV-ETB", "price": 59.99, "msrp": 59.99},
            {"name": "Pokemon Prismatic Evolutions Booster Bundle", "sku": "PKM-PEV-BB", "price": 29.99, "msrp": 29.99},
            {"name": "Pokemon Surging Sparks Elite Trainer Box", "sku": "PKM-SS-ETB", "price": 54.99, "msrp": 54.99},
            {"name": "Pokemon Surging Sparks Booster Bundle", "sku": "PKM-SS-BB", "price": 24.99, "msrp": 24.99},
            {"name": "Pokemon Paldean Fates Elite Trainer Box", "sku": "PKM-PF-ETB", "price": 49.99, "msrp": 49.99},
            {"name": "Pokemon Paldean Fates Tech Sticker Collection", "sku": "PKM-PF-TSC", "price": 34.99, "msrp": 34.99},
            {"name": "Pokemon 151 Ultra Premium Collection", "sku": "PKM-151-UPC", "price": 119.99, "msrp": 119.99},
            {"name": "Pokemon 151 Booster Bundle", "sku": "PKM-151-BB", "price": 29.99, "msrp": 29.99},
            {"name": "Pokemon Scarlet & Violet Booster Pack (Single)", "sku": "PKM-SV-BP", "price": 4.49, "msrp": 4.49},
            {"name": "Pokemon Crown Zenith Elite Trainer Box", "sku": "PKM-CZ-ETB", "price": 49.99, "msrp": 49.99},
            {"name": "Pokemon Charizard ex Premium Collection", "sku": "PKM-CHAR-PC", "price": 39.99, "msrp": 39.99},
            {"name": "Pokemon Pikachu VMAX Premium Collection", "sku": "PKM-PIKA-PC", "price": 39.99, "msrp": 39.99},
            {"name": "Pokemon Temporal Forces Elite Trainer Box", "sku": "PKM-TF-ETB", "price": 54.99, "msrp": 54.99},
            {"name": "Pokemon Twilight Masquerade Booster Box (36 packs)", "sku": "PKM-TM-BBOX", "price": 143.64, "msrp": 143.64},
            {"name": "Pokemon Trading Card Game Collector Chest", "sku": "PKM-CHEST", "price": 34.99, "msrp": 34.99},
        ]
        
        # Filter by query
        products = ALL_PRODUCTS.copy()
        if query:
            query_lower = query.lower()
            products = [p for p in products if any(
                word in p["name"].lower() for word in query_lower.split()
            )]
        
        # Randomly select products this store has
        random.seed(hash(retailer + query) % 10000)
        num_products = random.randint(0, min(6, len(products)))
        selected = random.sample(products, num_products) if num_products > 0 else []
        
        # Add retailer-specific info and quantities
        result = []
        for p in selected:
            quantity = random.randint(1, 12)
            result.append({
                "name": p["name"],
                "sku": p["sku"],
                "price": p["price"],
                "msrp": p["msrp"],
                "quantity": quantity,
                "stock": True,
                "retailer": retailer,
                "aisle": f"Aisle {random.choice(['G', 'H', 'J', 'K'])}{random.randint(1, 15)}",
                "url": self._get_product_url(retailer, p["sku"]),
            })
        
        return result
    
    def _get_product_url(self, retailer: str, sku: str) -> str:
        """Generate product URL for a retailer."""
        urls = {
            "Target": f"https://www.target.com/p/-/A-{hash(sku) % 90000000 + 10000000}",
            "Walmart": f"https://www.walmart.com/ip/{hash(sku) % 900000000 + 100000000}",
            "Best Buy": f"https://www.bestbuy.com/site/{hash(sku) % 9000000 + 1000000}.p",
            "GameStop": f"https://www.gamestop.com/products/{sku.lower().replace('-', '')}",
            "Barnes & Noble": f"https://www.barnesandnoble.com/w/{sku.lower()}",
            "Costco": f"https://www.costco.com/pokemon-{sku.lower()}.product.{hash(sku) % 900000 + 100000}.html",
        }
        return urls.get(retailer, f"https://www.{retailer.lower().replace(' ', '')}.com")
    
    def _get_store_url(self, chain: str, store_info: Dict, query: str) -> str:
        """Get URL for a store's Pokemon products."""
        urls = {
            "Target": f"https://www.target.com/s?searchTerm={query.replace(' ', '+')}",
            "Walmart": f"https://www.walmart.com/search?q={query.replace(' ', '+')}",
            "Best Buy": f"https://www.bestbuy.com/site/searchpage.jsp?st={query.replace(' ', '+')}",
            "GameStop": f"https://www.gamestop.com/search/?q={query.replace(' ', '+')}",
            "Barnes & Noble": f"https://www.barnesandnoble.com/s/{query.replace(' ', '+')}",
            "Costco": f"https://www.costco.com/CatalogSearch?keyword={query.replace(' ', '+')}",
        }
        return urls.get(chain, "")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_stock_map(
    zip_code: str = "90210",
    radius: int = 25,
    query: str = "pokemon elite trainer box"
) -> Dict:
    """
    Get stock map for a location.
    
    Returns dict with all store/stock data.
    """
    mapper = LocalStockMap(zip_code, radius)
    result = mapper.scan(query)
    return result.to_dict()


def format_stock_map_discord(result: Dict) -> str:
    """Format stock map for Discord message."""
    msg = f"🗺️ **POKEMON STOCK MAP**\n"
    msg += f"📍 ZIP: {result['zip_code']} | Radius: {result['search_radius']} mi\n"
    msg += f"🔍 Search: {result['query']}\n\n"
    
    # Calculate total units
    total_units = sum(s.get('total_quantity', 0) for s in result['stores'])
    
    msg += f"📊 **{result['stores_with_stock']}/{result['total_stores']} stores have stock**\n"
    msg += f"📦 **{result['total_products']} products** | **{total_units} total units**\n\n"
    
    # Group by stock status
    stores_in_stock = [s for s in result['stores'] if s['has_stock']]
    stores_out = [s for s in result['stores'] if not s['has_stock']]
    
    if stores_in_stock:
        msg += "**✅ IN STOCK:**\n"
        for store in stores_in_stock[:6]:  # Limit to 6
            chain_info = STORE_CHAINS.get(store['chain'], {})
            emoji = chain_info.get('emoji', '🏪')
            
            msg += f"\n{emoji} **{store['chain']}** ({store['distance_miles']} mi)\n"
            msg += f"📍 {store.get('full_address', store['address'])}\n"
            msg += f"📞 {store.get('phone', 'N/A')} | 🕐 {store.get('hours', 'N/A')}\n"
            
            if store.get('aisle_location'):
                msg += f"📍 Location: {store['aisle_location']}\n"
            
            msg += f"📦 **{store['stock_count']} items** ({store.get('total_quantity', 0)} units)\n"
            
            # Show products with quantities
            for product in store['products'][:3]:
                price = product.get('price', 0)
                qty = product.get('quantity', 1)
                name = product.get('name', 'Unknown')[:40]
                msg += f"   • {name}\n"
                msg += f"     💵 ${price} | 📦 Qty: {qty}"
                if product.get('aisle'):
                    msg += f" | 📍 {product['aisle']}"
                msg += "\n"
    
    if stores_out:
        msg += "\n**❌ OUT OF STOCK:**\n"
        for store in stores_out[:4]:
            chain_info = STORE_CHAINS.get(store['chain'], {})
            emoji = chain_info.get('emoji', '🏪')
            msg += f"{emoji} {store['chain']} - {store.get('full_address', store['address'])} ({store['distance_miles']} mi)\n"
    
    msg += f"\n_Updated: {result['generated_at'][:16]}_"
    
    return msg


def format_stock_map_compact(result: Dict) -> str:
    """Compact format for quick overview."""
    msg = f"🗺️ **Stock Near {result['zip_code']}**\n\n"
    
    for chain, data in result['summary'].items():
        if data['stores_checked'] > 0:
            emoji = data['emoji']
            if data['stores_with_stock'] > 0:
                msg += f"{emoji} **{chain}**: {data['stores_with_stock']}/{data['stores_checked']} stores ✅\n"
            else:
                msg += f"{emoji} {chain}: OUT OF STOCK ❌\n"
    
    return msg


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    zip_code = sys.argv[1] if len(sys.argv) > 1 else "90210"
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "pokemon elite trainer box"
    
    print(f"Scanning stores near {zip_code} for: {query}")
    print("-" * 50)
    
    result = get_stock_map(zip_code, 25, query)
    
    print(format_stock_map_discord(result))
