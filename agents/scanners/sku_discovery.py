#!/usr/bin/env python3
"""
SKU Discovery and Direct Stock Lookup

Enables stock checking by SKU/product ID directly instead of search queries.
More efficient and accurate than search-based methods.
"""
import os
import sys
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from agents.scanners.stock_checker import Product
try:
    from agents.stealth.anti_detect import get_stealth_headers, get_random_delay, get_random_proxy
except ImportError:
    def get_stealth_headers():
        return {"User-Agent": "Mozilla/5.0"}
    def get_random_delay():
        return 1.0
    def get_random_proxy():
        return None
from agents.utils.logger import get_logger

logger = get_logger("sku_discovery")


# =============================================================================
# SKU-BASED STOCK LOOKUP
# =============================================================================

def lookup_by_sku_target(tcin: str, zip_code: str = "90210") -> Optional[Product]:
    """
    Look up Target product by TCIN (Target Catalog Item Number).
    
    Args:
        tcin: Target TCIN (product ID)
        zip_code: ZIP code for local inventory
    
    Returns:
        Product if found, None otherwise
    """
    if not requests:
        return None
    
    try:
        api_url = "https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"
        
        params = {
            "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
            "tcin": tcin,
            "pricing_store_id": "911",
            "zip": zip_code,
        }
        
        headers = get_stealth_headers()
        headers["Accept"] = "application/json"
        
        time.sleep(get_random_delay())
        resp = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            product_data = data.get("data", {}).get("product", {})
            
            if not product_data:
                return None
            
            item = product_data.get("item", {})
            title = item.get("product_description", {}).get("title", "")
            
            price_data = product_data.get("price", {})
            fulfillment = product_data.get("fulfillment", {})
            
            # Check stock
            ship_ok = fulfillment.get("shipping_options", {}).get("availability_status", "") == "IN_STOCK"
            pickup_ok = "IN_STOCK" in str(fulfillment.get("store_options", []))
            in_stock = ship_ok or pickup_ok
            
            price = price_data.get("current_retail", 0) or price_data.get("reg_retail", 0) or 0
            
            buy_url = item.get('enrichment', {}).get('buy_url', '')
            if buy_url.startswith('http'):
                product_url = buy_url
            elif buy_url:
                product_url = f"https://www.target.com{buy_url}"
            else:
                product_url = f"https://www.target.com/p/-/A-{tcin}"
            
            return Product(
                name=title,
                retailer="Target",
                price=price,
                url=product_url,
                sku=tcin,
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                image_url=item.get("enrichment", {}).get("images", {}).get("primary_image_url", ""),
                last_checked=datetime.now().isoformat(),
                confidence=95.0 if in_stock else 5.0,
                detection_method="target_api_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Target SKU lookup error: {e}")
        return None


def lookup_by_sku_bestbuy(sku: str) -> Optional[Product]:
    """
    Look up Best Buy product by SKU.
    
    Args:
        sku: Best Buy SKU
    
    Returns:
        Product if found, None otherwise
    """
    if not requests:
        return None
    
    api_key = os.environ.get("BESTBUY_API_KEY", "")
    
    if not api_key:
        # Fallback to scraping product page
        return _scrape_bestbuy_sku(sku)
    
    try:
        url = f"https://api.bestbuy.com/v1/products/{sku}.json"
        params = {
            "apiKey": api_key,
            "show": "sku,name,salePrice,url,inStoreAvailability,onlineAvailability,image",
        }
        
        time.sleep(get_random_delay())
        resp = requests.get(url, params=params, timeout=15)
        
        if resp.status_code == 200:
            item = resp.json()
            
            if "pokemon" not in item.get("name", "").lower():
                return None
            
            in_stock = item.get("onlineAvailability", False)
            
            return Product(
                name=item.get("name", ""),
                retailer="Best Buy",
                price=item.get("salePrice", 0),
                url=item.get("url", ""),
                sku=str(sku),
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                image_url=item.get("image", ""),
                last_checked=datetime.now().isoformat(),
                confidence=90.0 if in_stock else 10.0,
                detection_method="bestbuy_api_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Best Buy SKU lookup error: {e}")
        return None


def _scrape_bestbuy_sku(sku: str) -> Optional[Product]:
    """Fallback: Scrape Best Buy product page by SKU."""
    if not BS4_AVAILABLE:
        return None
    
    try:
        url = f"https://www.bestbuy.com/site/.p?skuId={sku}"
        headers = get_stealth_headers()
        proxies = get_random_proxy()
        
        time.sleep(get_random_delay())
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract product info
            name_elem = soup.select_one('h1[data-testid="product-title"]')
            price_elem = soup.select_one('[data-testid="customer-price"]')
            stock_elem = soup.select_one('[data-testid="fulfillment-messaging"]')
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            price = 0
            if price_elem:
                price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                try:
                    price = float(price_text) if price_text else 0
                except:
                    pass
            
            # Check stock
            stock_text = stock_elem.get_text(strip=True).lower() if stock_elem else ""
            in_stock = "sold out" not in stock_text and "unavailable" not in stock_text
            
            return Product(
                name=name,
                retailer="Best Buy",
                price=price,
                url=url,
                sku=str(sku),
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                last_checked=datetime.now().isoformat(),
                confidence=70.0 if in_stock else 30.0,
                detection_method="bestbuy_scrape_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Best Buy SKU scrape error: {e}")
        return None


def lookup_by_sku_gamestop(sku: str) -> Optional[Product]:
    """
    Look up GameStop product by SKU/product ID.
    
    Args:
        sku: GameStop product ID/SKU
    
    Returns:
        Product if found, None otherwise
    """
    if not BS4_AVAILABLE:
        return None
    
    try:
        # GameStop product URLs typically use product ID
        url = f"https://www.gamestop.com/products/{sku}"
        headers = get_stealth_headers()
        proxies = get_random_proxy()
        
        time.sleep(get_random_delay())
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            name_elem = soup.select_one('h1.product-name, .product-title')
            price_elem = soup.select_one('.price, .product-price')
            stock_elem = soup.select_one('.add-to-cart, .availability-message')
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            price = 0
            if price_elem:
                price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                try:
                    price = float(price_text) if price_text else 0
                except:
                    pass
            
            in_stock = stock_elem is not None and 'unavailable' not in (stock_elem.get_text() or '').lower()
            
            return Product(
                name=name,
                retailer="GameStop",
                price=price,
                url=url,
                sku=str(sku),
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                last_checked=datetime.now().isoformat(),
                confidence=70.0 if in_stock else 30.0,
                detection_method="gamestop_scrape_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"GameStop SKU lookup error: {e}")
        return None


def lookup_by_sku_pokemoncenter(product_id: str) -> Optional[Product]:
    """
    Look up Pokemon Center product by product ID.
    
    Args:
        product_id: Pokemon Center product ID
    
    Returns:
        Product if found, None otherwise
    """
    if not BS4_AVAILABLE:
        return None
    
    try:
        url = f"https://www.pokemoncenter.com/product/{product_id}"
        headers = get_stealth_headers()
        proxies = get_random_proxy()
        
        time.sleep(get_random_delay())
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            name_elem = soup.select_one('h1.product-name, .product-title')
            price_elem = soup.select_one('.price, .product-price')
            stock_elem = soup.select_one('.out-of-stock, [data-testid="out-of-stock"]')
            add_to_cart = soup.select_one('button[data-testid="add-to-cart"]')
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            price = 0
            if price_elem:
                price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                try:
                    price = float(price_text) if price_text else 0
                except:
                    pass
            
            # Multiple indicators for stock
            in_stock = stock_elem is None and add_to_cart is not None
            confidence = 0.8 if in_stock else 0.3
            
            return Product(
                name=name,
                retailer="Pokemon Center",
                price=price,
                url=url,
                sku=str(product_id),
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                last_checked=datetime.now().isoformat(),
                confidence=confidence * 100,
                detection_method="pokemoncenter_scrape_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Pokemon Center SKU lookup error: {e}")
        return None


# =============================================================================
# UNIFIED SKU LOOKUP
# =============================================================================

def lookup_by_sku_walmart(sku: str) -> Optional[Product]:
    """
    Look up Walmart product by SKU/product ID.
    
    Args:
        sku: Walmart product ID/SKU
    
    Returns:
        Product if found, None otherwise
    """
    if not BS4_AVAILABLE:
        return None
    
    try:
        # Walmart product URLs typically use product ID
        url = f"https://www.walmart.com/ip/{sku}"
        headers = get_stealth_headers()
        proxies = get_random_proxy()
        
        time.sleep(get_random_delay())
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            name_elem = soup.select_one('h1[itemprop="name"], .prod-product-title')
            price_elem = soup.select_one('[itemprop="price"], .price-current')
            stock_elem = soup.select_one('[data-automation-id="add-to-cart-button"]')
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            price = 0
            if price_elem:
                price_text = ''.join(c for c in price_elem.get_text() if c.isdigit() or c == '.')
                try:
                    price = float(price_text) if price_text else 0
                except:
                    pass
            
            in_stock = stock_elem is not None and 'disabled' not in (stock_elem.get('class', []) or [])
            
            return Product(
                name=name,
                retailer="Walmart",
                price=price,
                url=url,
                sku=str(sku),
                stock=in_stock,
                stock_status="In Stock" if in_stock else "Out of Stock",
                last_checked=datetime.now().isoformat(),
                confidence=70.0 if in_stock else 30.0,
                detection_method="walmart_scrape_sku",
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Walmart SKU lookup error: {e}")
        return None


def lookup_by_sku(sku: str, retailer: str, zip_code: str = "90210") -> Optional[Product]:
    """
    Look up product by SKU for any retailer.
    
    Args:
        sku: Product SKU/ID
        retailer: Retailer name (target, bestbuy, gamestop, pokemoncenter, walmart)
        zip_code: ZIP code (for Target)
    
    Returns:
        Product if found, None otherwise
    """
    retailer_lower = retailer.lower()
    
    if retailer_lower == "target":
        return lookup_by_sku_target(sku, zip_code)
    elif retailer_lower == "bestbuy" or retailer_lower == "best buy":
        return lookup_by_sku_bestbuy(sku)
    elif retailer_lower == "gamestop":
        return lookup_by_sku_gamestop(sku)
    elif retailer_lower == "pokemoncenter" or retailer_lower == "pokemon center":
        return lookup_by_sku_pokemoncenter(sku)
    elif retailer_lower == "walmart":
        return lookup_by_sku_walmart(sku)
    else:
        logger.warning(f"SKU lookup not supported for retailer: {retailer}")
        return None


def lookup_multiple_skus(skus: List[Tuple[str, str]], zip_code: str = "90210") -> List[Product]:
    """
    Look up multiple SKUs across retailers.
    
    Args:
        skus: List of (sku, retailer) tuples
        zip_code: ZIP code (for Target)
    
    Returns:
        List of found products
    """
    products = []
    
    for sku, retailer in skus:
        product = lookup_by_sku(sku, retailer, zip_code)
        if product:
            products.append(product)
        time.sleep(get_random_delay())  # Delay between lookups
    
    return products
