#!/usr/bin/env python3
"""
Automated Pokemon SKU List Builder

Daily job that discovers and builds a comprehensive SKU list:
- Crawls retailer sitemaps
- Scans category pages
- Extracts SKUs from search results
- Auto-deduplicates
- Categorizes by product type
"""
import os
import json
import time
import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from agents.utils.logger import get_logger
try:
    from agents.stealth.anti_detect import get_stealth_headers, get_random_delay, get_random_proxy
except ImportError:
    def get_stealth_headers():
        return {"User-Agent": "Mozilla/5.0"}
    def get_random_delay():
        return 1.0
    def get_random_proxy():
        return None

logger = get_logger("sku_builder")


# =============================================================================
# SKU DATABASE
# =============================================================================

SKU_DB_FILE = Path(__file__).parent.parent.parent / ".stock_cache" / "sku_database.json"

@dataclass
class SKUEntry:
    """SKU database entry."""
    sku: str
    retailer: str
    name: str
    category: str  # booster_box, etb, booster_pack, single_card, etc.
    set_name: Optional[str] = None
    price: float = 0.0
    url: str = ""
    image_url: str = ""
    first_seen: str = ""
    last_updated: str = ""
    discovery_method: str = ""  # sitemap, category, search, manual
    confidence: float = 0.5  # 0-1, how confident we are this is correct
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class SKUDatabase:
    """Manages the SKU database with deduplication and categorization."""
    
    def __init__(self):
        self.skus: Dict[str, SKUEntry] = {}  # key: retailer_sku -> SKUEntry
        self.load()
    
    def _make_key(self, retailer: str, sku: str) -> str:
        """Create unique key for SKU."""
        return f"{retailer.lower()}_{sku.lower()}"
    
    def load(self):
        """Load SKU database from disk."""
        if SKU_DB_FILE.exists():
            try:
                with open(SKU_DB_FILE) as f:
                    data = json.load(f)
                    for key, entry_data in data.get("skus", {}).items():
                        self.skus[key] = SKUEntry.from_dict(entry_data)
                logger.info(f"Loaded {len(self.skus)} SKUs from database")
            except Exception as e:
                logger.error(f"Error loading SKU database: {e}")
    
    def save(self):
        """Save SKU database to disk."""
        try:
            SKU_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SKU_DB_FILE, 'w') as f:
                json.dump({
                    "skus": {k: v.to_dict() for k, v in self.skus.items()},
                    "last_updated": datetime.now().isoformat(),
                }, f, indent=2)
            logger.info(f"Saved {len(self.skus)} SKUs to database")
        except Exception as e:
            logger.error(f"Error saving SKU database: {e}")
    
    def add_sku(self, entry: SKUEntry, dedupe: bool = True) -> bool:
        """
        Add SKU to database with deduplication.
        
        Returns:
            True if added (new or updated), False if duplicate
        """
        key = self._make_key(entry.retailer, entry.sku)
        
        if key in self.skus:
            existing = self.skus[key]
            
            # Update if new entry has more info or higher confidence
            if entry.confidence > existing.confidence or not existing.name:
                existing.name = entry.name or existing.name
                existing.category = entry.category or existing.category
                existing.set_name = entry.set_name or existing.set_name
                existing.price = entry.price or existing.price
                existing.url = entry.url or existing.url
                existing.image_url = entry.image_url or existing.image_url
                existing.last_updated = datetime.now().isoformat()
                existing.confidence = max(existing.confidence, entry.confidence)
                return True
            return False  # Duplicate, no update needed
        else:
            # New SKU
            entry.first_seen = datetime.now().isoformat()
            entry.last_updated = datetime.now().isoformat()
            self.skus[key] = entry
            return True
    
    def get_sku(self, retailer: str, sku: str) -> Optional[SKUEntry]:
        """Get SKU entry."""
        key = self._make_key(retailer, sku)
        return self.skus.get(key)
    
    def get_by_category(self, category: str) -> List[SKUEntry]:
        """Get all SKUs in a category."""
        return [entry for entry in self.skus.values() if entry.category == category]
    
    def get_by_retailer(self, retailer: str) -> List[SKUEntry]:
        """Get all SKUs for a retailer."""
        return [entry for entry in self.skus.values() if entry.retailer.lower() == retailer.lower()]
    
    def get_by_set(self, set_name: str) -> List[SKUEntry]:
        """Get all SKUs for a set."""
        set_lower = set_name.lower()
        return [entry for entry in self.skus.values() 
                if entry.set_name and set_name.lower() in entry.set_name.lower()]


# =============================================================================
# CATEGORIZATION
# =============================================================================

def categorize_product(name: str, set_name: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Categorize a product based on name and set.
    
    Returns:
        (category, detected_set_name)
    """
    name_lower = name.lower()
    
    # Detect set names
    detected_set = None
    known_sets = [
        "151", "paldean fates", "obsidian flames", "paradox rift",
        "temporal forces", "stellar crown", "surging sparks",
        "prismatic evolutions", "destined rivals", "shrouded fable",
        "ancient roar", "future flash", "twilight masquerade",
    ]
    
    for set_name_check in known_sets:
        if set_name_check in name_lower:
            detected_set = set_name_check.title()
            break
    
    # Use provided set name if available
    if set_name:
        detected_set = set_name
    
    # Categorize by product type
    if "booster box" in name_lower or "36 pack" in name_lower:
        return ("booster_box", detected_set)
    elif "elite trainer box" in name_lower or "etb" in name_lower:
        return ("etb", detected_set)
    elif "booster bundle" in name_lower or "6 pack" in name_lower:
        return ("booster_bundle", detected_set)
    elif "booster pack" in name_lower and "box" not in name_lower:
        return ("booster_pack", detected_set)
    elif "collection box" in name_lower or "collection" in name_lower:
        return ("collection_box", detected_set)
    elif "tin" in name_lower:
        return ("tin", detected_set)
    elif "binder" in name_lower:
        return ("binder", detected_set)
    elif "sleeves" in name_lower:
        return ("sleeves", detected_set)
    elif "deck box" in name_lower:
        return ("deck_box", detected_set)
    elif "playmat" in name_lower:
        return ("playmat", detected_set)
    elif "single" in name_lower or "card" in name_lower:
        return ("single_card", detected_set)
    elif "premium collection" in name_lower:
        return ("premium_collection", detected_set)
    else:
        return ("other", detected_set)


# =============================================================================
# SKU DISCOVERY METHODS
# =============================================================================

def discover_from_sitemap(retailer: str) -> List[SKUEntry]:
    """Discover SKUs from retailer sitemap."""
    entries = []
    
    if not requests:
        return entries
    
    sitemap_urls = {
        "target": "https://www.target.com/sitemap_index.xml",
        "bestbuy": "https://www.bestbuy.com/sitemap.xml",
        "gamestop": "https://www.gamestop.com/sitemap.xml",
        "pokemoncenter": "https://www.pokemoncenter.com/sitemap.xml",
    }
    
    sitemap_url = sitemap_urls.get(retailer.lower())
    if not sitemap_url:
        return entries
    
    try:
        headers = get_stealth_headers()
        proxies = get_random_proxy()
        
        resp = requests.get(sitemap_url, headers=headers, proxies=proxies, timeout=15)
        
        if resp.status_code == 200:
            # Parse sitemap (simplified - would need proper XML parsing)
            # For now, extract product URLs
            if BS4_AVAILABLE:
                soup = BeautifulSoup(resp.text, 'xml')
                urls = soup.find_all('loc')
                
                for url_elem in urls[:100]:  # Limit to first 100
                    url = url_elem.text if url_elem else ""
                    if "pokemon" in url.lower() and ("/p/" in url or "/product/" in url):
                        # Extract SKU from URL
                        sku = _extract_sku_from_url(url, retailer)
                        if sku:
                            category, set_name = categorize_product(url)
                            entries.append(SKUEntry(
                                sku=sku,
                                retailer=retailer,
                                name=url.split('/')[-1].replace('-', ' ').title(),
                                category=category,
                                set_name=set_name,
                                url=url,
                                discovery_method="sitemap",
                                confidence=0.6,
                            ))
        
        time.sleep(get_random_delay())
        
    except Exception as e:
        logger.error(f"Error discovering from sitemap ({retailer}): {e}")
    
    return entries


def discover_from_category_pages(retailer: str) -> List[SKUEntry]:
    """Discover SKUs by crawling category pages."""
    entries = []
    
    if not requests or not BS4_AVAILABLE:
        return entries
    
    category_urls = {
        "target": [
            "https://www.target.com/c/trading-cards-games-toys/-/N-5xt8l",
            "https://www.target.com/s/pokemon+trading+cards",
        ],
        "bestbuy": [
            "https://www.bestbuy.com/site/searchpage.jsp?st=pokemon+trading+cards",
        ],
        "gamestop": [
            "https://www.gamestop.com/toys-games/trading-cards",
        ],
        "pokemoncenter": [
            "https://www.pokemoncenter.com/category/trading-card-games",
        ],
    }
    
    urls = category_urls.get(retailer.lower(), [])
    
    for url in urls:
        try:
            headers = get_stealth_headers()
            proxies = get_random_proxy()
            
            time.sleep(get_random_delay())
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find product links
                product_links = soup.select('a[href*="/p/"], a[href*="/product/"], a[href*="skuId"]')
                
                for link in product_links[:50]:  # Limit per page
                    href = link.get('href', '')
                    full_url = href if href.startswith('http') else f"https://{retailer}.com{href}"
                    
                    sku = _extract_sku_from_url(full_url, retailer)
                    if sku:
                        name = link.get_text(strip=True) or href.split('/')[-1]
                        category, set_name = categorize_product(name)
                        
                        entries.append(SKUEntry(
                            sku=sku,
                            retailer=retailer,
                            name=name,
                            category=category,
                            set_name=set_name,
                            url=full_url,
                            discovery_method="category_page",
                            confidence=0.7,
                        ))
        
        except Exception as e:
            logger.error(f"Error discovering from category ({retailer}): {e}")
    
    return entries


def discover_from_search_results(retailer: str, queries: List[str]) -> List[SKUEntry]:
    """Discover SKUs from search results."""
    entries = []
    
    if not requests:
        return entries
    
    from agents.scanners.stock_checker import StockChecker
    
    checker = StockChecker()
    
    for query in queries:
        try:
            if retailer == "target":
                from agents.scanners.stock_checker import scan_target
                products = scan_target(query, "90210")
            elif retailer == "bestbuy":
                from agents.scanners.stock_checker import scan_bestbuy
                products = scan_bestbuy(query)
            elif retailer == "gamestop":
                from agents.scanners.stock_checker import scan_gamestop
                products = scan_gamestop(query)
            elif retailer == "pokemoncenter":
                from agents.scanners.stock_checker import scan_pokemoncenter
                products = scan_pokemoncenter(query)
            else:
                continue
            
            for product in products:
                if product.sku:
                    category, set_name = categorize_product(product.name)
                    entries.append(SKUEntry(
                        sku=product.sku,
                        retailer=retailer,
                        name=product.name,
                        category=category,
                        set_name=set_name,
                        price=product.price,
                        url=product.url,
                        image_url=product.image_url,
                        discovery_method="search",
                        confidence=0.8,
                    ))
            
            time.sleep(get_random_delay())
            
        except Exception as e:
            logger.error(f"Error discovering from search ({retailer}, {query}): {e}")
    
    return entries


def _extract_sku_from_url(url: str, retailer: str) -> Optional[str]:
    """Extract SKU from product URL."""
    retailer_lower = retailer.lower()
    
    if retailer_lower == "target":
        # Target: /p/-/A-{TCIN}
        match = re.search(r'/p/-/A-(\d+)', url)
        if match:
            return match.group(1)
    elif retailer_lower == "bestbuy":
        # Best Buy: ?skuId={SKU}
        match = re.search(r'skuId=(\d+)', url)
        if match:
            return match.group(1)
    elif retailer_lower == "gamestop":
        # GameStop: /products/{ID}
        match = re.search(r'/products/([^/]+)', url)
        if match:
            return match.group(1)
    elif retailer_lower == "pokemoncenter":
        # Pokemon Center: /product/{ID}
        match = re.search(r'/product/([^/]+)', url)
        if match:
            return match.group(1)
    
    return None


# =============================================================================
# DAILY BUILD JOB
# =============================================================================

def build_sku_list_daily(retailers: List[str] = None, force: bool = False):
    """
    Daily job to build and update SKU list.
    
    Args:
        retailers: List of retailers to scan (default: all)
        force: Force rebuild even if done today
    """
    if retailers is None:
        retailers = ["target", "bestbuy", "gamestop", "pokemoncenter"]
    
    db = SKUDatabase()
    
    # Check if already run today
    if not force:
        last_run_file = SKU_DB_FILE.parent / "sku_build_last_run.txt"
        if last_run_file.exists():
            try:
                with open(last_run_file) as f:
                    last_run = datetime.fromisoformat(f.read().strip())
                    if (datetime.now() - last_run).total_seconds() < 86400:  # 24 hours
                        logger.info("SKU build already run today, skipping")
                        return
            except:
                pass
    
    logger.info("Starting daily SKU list build...")
    
    all_entries = []
    
    # Discovery queries for search-based discovery
    discovery_queries = [
        "pokemon 151",
        "pokemon paldean fates",
        "pokemon obsidian flames",
        "pokemon paradox rift",
        "pokemon temporal forces",
        "pokemon stellar crown",
        "pokemon surging sparks",
        "pokemon prismatic evolutions",
        "pokemon destined rivals",
        "pokemon booster box",
        "pokemon elite trainer box",
    ]
    
    for retailer in retailers:
        logger.info(f"Discovering SKUs from {retailer}...")
        
        # Method 1: Sitemap
        try:
            sitemap_entries = discover_from_sitemap(retailer)
            all_entries.extend(sitemap_entries)
            logger.info(f"  Found {len(sitemap_entries)} SKUs from sitemap")
        except Exception as e:
            logger.error(f"  Sitemap discovery failed: {e}")
        
        # Method 2: Category pages
        try:
            category_entries = discover_from_category_pages(retailer)
            all_entries.extend(category_entries)
            logger.info(f"  Found {len(category_entries)} SKUs from category pages")
        except Exception as e:
            logger.error(f"  Category discovery failed: {e}")
        
        # Method 3: Search results
        try:
            search_entries = discover_from_search_results(retailer, discovery_queries[:3])  # Limit queries
            all_entries.extend(search_entries)
            logger.info(f"  Found {len(search_entries)} SKUs from search")
        except Exception as e:
            logger.error(f"  Search discovery failed: {e}")
        
        time.sleep(get_random_delay())
    
    # Deduplicate and add to database
    added_count = 0
    for entry in all_entries:
        if db.add_sku(entry, dedupe=True):
            added_count += 1
    
    # Save database
    db.save()
    
    # Mark as run
    last_run_file = SKU_DB_FILE.parent / "sku_build_last_run.txt"
    with open(last_run_file, 'w') as f:
        f.write(datetime.now().isoformat())
    
    logger.info(f"SKU build complete: {added_count} new/updated SKUs, {len(db.skus)} total")
    
    return {
        "total_skus": len(db.skus),
        "new_skus": added_count,
        "by_retailer": {r: len(db.get_by_retailer(r)) for r in retailers},
        "by_category": {c: len([e for e in db.skus.values() if e.category == c]) 
                       for c in set(e.category for e in db.skus.values())},
    }


# =============================================================================
# STATISTICS
# =============================================================================

def get_sku_stats() -> Dict:
    """Get SKU database statistics."""
    db = SKUDatabase()
    
    stats = {
        "total_skus": len(db.skus),
        "by_retailer": {},
        "by_category": {},
        "by_set": {},
    }
    
    for retailer in ["target", "bestbuy", "gamestop", "pokemoncenter"]:
        stats["by_retailer"][retailer] = len(db.get_by_retailer(retailer))
    
    categories = set(e.category for e in db.skus.values())
    for category in categories:
        stats["by_category"][category] = len(db.get_by_category(category))
    
    sets = set(e.set_name for e in db.skus.values() if e.set_name)
    for set_name in sets:
        stats["by_set"][set_name] = len(db.get_by_set(set_name))
    
    return stats
