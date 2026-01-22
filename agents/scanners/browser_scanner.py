#!/usr/bin/env python3
"""
Browser-Based Stock Scanner (Fallback for Blocked Retailers)

Uses Selenium with undetected-chromedriver to scrape retailers
that block regular HTTP requests. Slower but much more reliable.

Only used when requests-based scraping fails or is blocked.
"""
import os
import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# CAPTCHA solving
try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False

try:
    from python3_anticaptcha import AntiCaptchaControl, ImageToTextTask
    ANTICAPTCHA_AVAILABLE = True
except ImportError:
    ANTICAPTCHA_AVAILABLE = False

try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False
    print("⚠️ Browser automation not available. Install: pip install undetected-chromedriver selenium")

# Import Product from stock_checker (same directory)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from stock_checker import Product
except ImportError:
    # Fallback: define Product if import fails
    from dataclasses import dataclass
    @dataclass
    class Product:
        name: str
        retailer: str
        price: float
        url: str
        sku: str = ""
        stock: bool = False
        stock_status: str = "Unknown"
        image_url: str = ""
        category: str = "TCG"
        last_checked: str = ""
        confidence: float = 0.0
        detection_method: str = "browser_automation"


# =============================================================================
# CAPTCHA SOLVING
# =============================================================================

def solve_captcha(driver: webdriver.Chrome) -> bool:
    """
    Detect and solve CAPTCHA if present.
    
    Returns True if CAPTCHA was solved, False otherwise.
    """
    if not BROWSER_AVAILABLE:
        return False
    
    try:
        # Check for common CAPTCHA indicators
        captcha_indicators = [
            "captcha",
            "recaptcha",
            "hcaptcha",
            "cloudflare",
            "i'm not a robot",
            "verify you are human"
        ]
        
        page_text = driver.page_source.lower()
        has_captcha = any(indicator in page_text for indicator in captcha_indicators)
        
        if not has_captcha:
            return False
        
        print("🔒 CAPTCHA detected, attempting to solve...")
        
        # Try 2Captcha first
        twocaptcha_key = os.environ.get("TWOCAPTCHA_API_KEY", "")
        if twocaptcha_key and TWOCAPTCHA_AVAILABLE:
            try:
                solver = TwoCaptcha(twocaptcha_key)
                
                # Check for reCAPTCHA
                if "recaptcha" in page_text:
                    # Find sitekey
                    sitekey = None
                    try:
                        recaptcha_elem = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                        sitekey = recaptcha_elem.get_attribute("data-sitekey")
                    except:
                        # Try to extract from page source
                        import re
                        match = re.search(r'data-sitekey="([^"]+)"', driver.page_source)
                        if match:
                            sitekey = match.group(1)
                    
                    if sitekey:
                        result = solver.recaptcha(
                            sitekey=sitekey,
                            url=driver.current_url
                        )
                        
                        # Inject solution
                        driver.execute_script(f"""
                            document.getElementById('g-recaptcha-response').innerHTML='{result['code']}';
                            var callback = window.__recaptchaCallback || function(){{}};
                            callback('{result['code']}');
                        """)
                        print("✅ reCAPTCHA solved with 2Captcha")
                        time.sleep(2)
                        return True
                
                # Check for hCaptcha
                if "hcaptcha" in page_text:
                    sitekey = None
                    try:
                        hcaptcha_elem = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                        sitekey = hcaptcha_elem.get_attribute("data-sitekey")
                    except:
                        import re
                        match = re.search(r'data-sitekey="([^"]+)"', driver.page_source)
                        if match:
                            sitekey = match.group(1)
                    
                    if sitekey:
                        result = solver.hcaptcha(
                            sitekey=sitekey,
                            url=driver.current_url
                        )
                        driver.execute_script(f"""
                            document.querySelector('[name="h-captcha-response"]').value='{result['code']}';
                        """)
                        print("✅ hCaptcha solved with 2Captcha")
                        time.sleep(2)
                        return True
                        
            except Exception as e:
                print(f"⚠️ 2Captcha error: {e}")
        
        # Try Anti-Captcha
        anticaptcha_key = os.environ.get("ANTICAPTCHA_API_KEY", "")
        if anticaptcha_key and ANTICAPTCHA_AVAILABLE:
            try:
                # Similar logic for Anti-Captcha
                print("⚠️ Anti-Captcha integration pending")
            except Exception as e:
                print(f"⚠️ Anti-Captcha error: {e}")
        
        print("❌ Could not solve CAPTCHA automatically")
        return False
        
    except Exception as e:
        print(f"❌ CAPTCHA solving error: {e}")
        return False


# =============================================================================
# SESSION WARMING
# =============================================================================

def warm_session(driver: webdriver.Chrome, retailer: str) -> bool:
    """
    Warm up session by visiting homepage and browsing.
    Makes the browser look more like a real user.
    
    Returns True if successful.
    """
    if not BROWSER_AVAILABLE or not driver:
        return False
    
    retailer_urls = {
        "gamestop": {
            "homepage": "https://www.gamestop.com",
            "category": "https://www.gamestop.com/toys-games/trading-cards",
        },
        "pokemoncenter": {
            "homepage": "https://www.pokemoncenter.com",
            "category": "https://www.pokemoncenter.com/category/trading-cards",
        },
        "costco": {
            "homepage": "https://www.costco.com",
            "category": "https://www.costco.com/toys-games.html",
        },
        "amazon": {
            "homepage": "https://www.amazon.com",
            "category": "https://www.amazon.com/s?k=trading+cards",
        },
        "barnesandnoble": {
            "homepage": "https://www.barnesandnoble.com",
            "category": "https://www.barnesandnoble.com/b/toys-games/trading-cards/_/N-1p0i",
        },
    }
    
    if retailer.lower() not in retailer_urls:
        return True  # No warming needed
    
    urls = retailer_urls[retailer.lower()]
    
    try:
        print(f"🔥 Warming session for {retailer}...")
        
        # Visit homepage
        driver.get(urls["homepage"])
        time.sleep(random.uniform(2, 4))  # Mimic reading page
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        # Visit category page
        if "category" in urls:
            driver.get(urls["category"])
            time.sleep(random.uniform(2, 4))
            
            # Check for CAPTCHA again
            solve_captcha(driver)
        
        # Random mouse movements (optional, makes it more human-like)
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
        
        print(f"✅ Session warmed for {retailer}")
        return True
        
    except Exception as e:
        print(f"⚠️ Session warming error for {retailer}: {e}")
        return False


# =============================================================================
# BROWSER POOL - Reuse browsers to avoid startup cost
# =============================================================================

_browser_pool: Dict[str, webdriver.Chrome] = {}
_browser_lock = False


def get_browser(headless: bool = True) -> Optional[webdriver.Chrome]:
    """Get or create a browser instance (reused for efficiency)."""
    global _browser_pool, _browser_lock
    
    if not BROWSER_AVAILABLE:
        return None
    
    # Use a single browser instance (pool size = 1 for now)
    pool_key = "default"
    
    if pool_key in _browser_pool:
        try:
            # Check if browser is still alive
            _browser_pool[pool_key].current_url
            return _browser_pool[pool_key]
        except:
            # Browser died, remove from pool
            _browser_pool.pop(pool_key, None)
    
    # Create new browser
    try:
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument('--headless')
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Randomize window size
        width = random.randint(1920, 2560)
        height = random.randint(1080, 1440)
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent is handled by undetected-chromedriver
        
        driver = uc.Chrome(options=options, version_main=None)
        
        # Execute script to hide webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        _browser_pool[pool_key] = driver
        return driver
        
    except Exception as e:
        print(f"❌ Failed to create browser: {e}")
        return None


def close_browsers():
    """Close all browsers in pool."""
    global _browser_pool
    for driver in _browser_pool.values():
        try:
            driver.quit()
        except:
            pass
    _browser_pool.clear()


# =============================================================================
# RETAILER-SPECIFIC BROWSER SCRAPERS
# =============================================================================

def scan_gamestop_browser(query: str = "pokemon cards") -> List[Product]:
    """Scan GameStop using browser automation."""
    products = []
    
    if not BROWSER_AVAILABLE:
        return products
    
    driver = get_browser(headless=True)
    if not driver:
        return products
    
    try:
        # Warm session first
        warm_session(driver, "gamestop")
        
        search_url = f"https://www.gamestop.com/search/?q={query.replace(' ', '+')}"
        
        # Visit page
        driver.get(search_url)
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        # Wait for products to load (up to 10 seconds)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-tile, [data-product-tile], .product"))
            )
        except TimeoutException:
            print("⚠️ GameStop: Products didn't load in time")
            return products
        
        # Random delay to mimic human behavior
        time.sleep(random.uniform(1, 3))
        
        # Find product elements
        items = driver.find_elements(By.CSS_SELECTOR, ".product-tile, [data-product-tile], .product")
        
        for item in items[:20]:
            try:
                # Extract product info
                name_elem = item.find_element(By.CSS_SELECTOR, "h3, .product-title, [data-product-title]")
                name = name_elem.text.strip()
                
                if "pokemon" not in name.lower():
                    continue
                
                # Price
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".price, .product-price, [data-price]")
                    price_text = ''.join(c for c in price_elem.text if c.isdigit() or c == '.')
                    price = float(price_text) if price_text else 0
                except:
                    price = 0
                
                # URL
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute("href")
                except:
                    url = search_url
                
                # Stock check
                try:
                    add_to_cart = item.find_element(By.CSS_SELECTOR, ".add-to-cart, button:contains('Add')")
                    in_stock = True
                except:
                    in_stock = False
                
                products.append(Product(
                    name=name,
                    retailer="GameStop",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=85.0,  # Browser = high confidence
                    detection_method="browser_automation",
                    last_checked=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ GameStop browser scan error: {e}")
    finally:
        # Don't close browser - keep it for reuse
        pass
    
    return products


def scan_pokemoncenter_browser(query: str = "trading cards") -> List[Product]:
    """Scan Pokemon Center using browser automation."""
    products = []
    
    if not BROWSER_AVAILABLE:
        return products
    
    driver = get_browser(headless=True)
    if not driver:
        return products
    
    try:
        # Warm session first
        warm_session(driver, "pokemoncenter")
        
        search_url = f"https://www.pokemoncenter.com/search?q={query.replace(' ', '+')}"
        
        driver.get(search_url)
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        # Wait for products
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-card'], .product-card, .product-tile"))
            )
        except TimeoutException:
            print("⚠️ Pokemon Center: Products didn't load in time")
            return products
        
        time.sleep(random.uniform(2, 4))
        
        items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='product-card'], .product-card, .product-tile")
        
        for item in items[:20]:
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, "h2, h3, .product-name, [data-testid='product-name']")
                name = name_elem.text.strip()
                
                if "pokemon" not in name.lower():
                    continue
                
                # Price
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".price, .product-price, [data-price]")
                    price_text = ''.join(c for c in price_elem.text if c.isdigit() or c == '.')
                    price = float(price_text) if price_text else 0
                except:
                    price = 0
                
                # URL
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute("href")
                except:
                    url = search_url
                
                # Stock - Pokemon Center shows "Add to Cart" if available
                try:
                    add_to_cart = item.find_element(By.CSS_SELECTOR, "button:contains('Add to Cart'), [aria-label*='Add to Cart']")
                    oos = item.find_element(By.CSS_SELECTOR, ".out-of-stock, [aria-label*='out of stock']")
                    in_stock = False  # Found OOS indicator
                except:
                    # No OOS indicator = might be in stock
                    try:
                        item.find_element(By.CSS_SELECTOR, "button, .add-to-cart")
                        in_stock = True
                    except:
                        in_stock = False
                
                products.append(Product(
                    name=name,
                    retailer="Pokemon Center",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=85.0,
                    detection_method="browser_automation",
                    last_checked=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Pokemon Center browser scan error: {e}")
    
    return products


def scan_costco_browser(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Costco using browser automation."""
    products = []
    
    if not BROWSER_AVAILABLE:
        return products
    
    driver = get_browser(headless=True)
    if not driver:
        return products
    
    try:
        # Warm session first
        warm_session(driver, "costco")
        
        search_url = f"https://www.costco.com/CatalogSearch?keyword={query.replace(' ', '+')}"
        
        driver.get(search_url)
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-automation-id='productTile'], .product-tile, .product"))
            )
        except TimeoutException:
            print("⚠️ Costco: Products didn't load in time")
            return products
        
        time.sleep(random.uniform(2, 4))
        
        items = driver.find_elements(By.CSS_SELECTOR, "[data-automation-id='productTile'], .product-tile, .product")
        
        for item in items[:20]:
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, "[data-automation-id='productTitle'], .product-title a, h3 a")
                name = name_elem.text.strip()
                
                if "pokemon" not in name.lower():
                    continue
                
                # Price
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, "[data-automation-id='productPrice'], .price")
                    price_text = ''.join(c for c in price_elem.text if c.isdigit() or c == '.')
                    price = float(price_text) if price_text else 0
                except:
                    price = 0
                
                # URL
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/product.']")
                    url = link_elem.get_attribute("href")
                except:
                    url = search_url
                
                # Stock
                try:
                    item.find_element(By.CSS_SELECTOR, "[data-automation-id='addToCartButton'], .add-to-cart")
                    oos = item.find_element(By.CSS_SELECTOR, ".out-of-stock")
                    in_stock = False
                except:
                    in_stock = True
                
                products.append(Product(
                    name=name,
                    retailer="Costco",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=85.0,
                    detection_method="browser_automation",
                    last_checked=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Costco browser scan error: {e}")
    
    return products


def scan_amazon_browser(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Amazon using browser automation."""
    products = []
    
    if not BROWSER_AVAILABLE:
        return products
    
    driver = get_browser(headless=True)
    if not driver:
        return products
    
    try:
        # Warm session first
        warm_session(driver, "amazon")
        
        search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        
        driver.get(search_url)
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result'], .s-result-item"))
            )
        except TimeoutException:
            print("⚠️ Amazon: Products didn't load in time")
            return products
        
        time.sleep(random.uniform(2, 4))
        
        items = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result'], .s-result-item")
        
        for item in items[:20]:
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, "h2 a span, .s-title-instructions-style h2 a")
                name = name_elem.text.strip()
                
                if "pokemon" not in name.lower():
                    continue
                
                # Price
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen, .a-price-whole")
                    price_text = ''.join(c for c in price_elem.text if c.isdigit() or c == '.')
                    price = float(price_text) if price_text else 0
                except:
                    price = 0
                
                # URL
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "h2 a")
                    url = link_elem.get_attribute("href")
                except:
                    url = search_url
                
                # Stock
                try:
                    item.find_element(By.CSS_SELECTOR, "[aria-label*='Add to Cart']")
                    unavailable = item.find_element(By.CSS_SELECTOR, ".a-color-state, [aria-label*='unavailable']")
                    in_stock = False
                except:
                    in_stock = True
                
                products.append(Product(
                    name=name,
                    retailer="Amazon",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Check Site",
                    confidence=80.0,  # Amazon is tricky even with browser
                    detection_method="browser_automation",
                    last_checked=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Amazon browser scan error: {e}")
    
    return products


def scan_barnesandnoble_browser(query: str = "pokemon trading cards") -> List[Product]:
    """Scan Barnes & Noble using browser automation."""
    products = []
    
    if not BROWSER_AVAILABLE:
        return products
    
    driver = get_browser(headless=True)
    if not driver:
        return products
    
    try:
        # Warm session first
        warm_session(driver, "barnesandnoble")
        
        search_url = f"https://www.barnesandnoble.com/s/{query.replace(' ', '+')}"
        
        driver.get(search_url)
        
        # Check for CAPTCHA
        solve_captcha(driver)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='productCard'], .product-shelf-item, .product-item"))
            )
        except TimeoutException:
            print("⚠️ Barnes & Noble: Products didn't load in time")
            return products
        
        time.sleep(random.uniform(2, 4))
        
        items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='productCard'], .product-shelf-item, .product-item")
        
        for item in items[:20]:
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='productTitle'], .product-title a, h3 a")
                name = name_elem.text.strip()
                
                if "pokemon" not in name.lower():
                    continue
                
                # Price
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='price'], .price, .product-price")
                    price_text = ''.join(c for c in price_elem.text if c.isdigit() or c == '.')
                    price = float(price_text) if price_text else 0
                except:
                    price = 0
                
                # URL
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                    url = link_elem.get_attribute("href")
                except:
                    url = search_url
                
                # Stock
                try:
                    item.find_element(By.CSS_SELECTOR, "[data-testid='addToCart'], .add-to-cart-button")
                    oos = item.find_element(By.CSS_SELECTOR, ".out-of-stock")
                    in_stock = False
                except:
                    in_stock = True
                
                products.append(Product(
                    name=name,
                    retailer="Barnes & Noble",
                    price=price,
                    url=url,
                    stock=in_stock,
                    stock_status="In Stock" if in_stock else "Out of Stock",
                    confidence=85.0,
                    detection_method="browser_automation",
                    last_checked=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Barnes & Noble browser scan error: {e}")
    
    return products


# =============================================================================
# BROWSER SCANNER MAP
# =============================================================================

BROWSER_SCANNERS = {
    "gamestop": scan_gamestop_browser,
    "pokemoncenter": scan_pokemoncenter_browser,
    "costco": scan_costco_browser,
    "amazon": scan_amazon_browser,
    "barnesandnoble": scan_barnesandnoble_browser,
}


def scan_with_browser(retailer: str, query: str) -> List[Product]:
    """
    Scan a retailer using browser automation (fallback method).
    
    Args:
        retailer: Retailer name (e.g., "gamestop", "pokemoncenter")
        query: Search query
    
    Returns:
        List of Product objects
    """
    if not BROWSER_AVAILABLE:
        print("⚠️ Browser automation not available")
        return []
    
    scanner_func = BROWSER_SCANNERS.get(retailer.lower())
    if not scanner_func:
        print(f"⚠️ No browser scanner for {retailer}")
        return []
    
    print(f"🌐 Using browser automation for {retailer}...")
    return scanner_func(query)
