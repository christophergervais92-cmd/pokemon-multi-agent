#!/usr/bin/env python3
"""
Stock Checker Signal System

Event-driven stock checking using Flask signals instead of endpoints.
More efficient and real-time than polling endpoints.
"""
import json
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from flask import Flask, request
from blinker import Namespace

from agents.utils.logger import get_logger

logger = get_logger("stock_signals")

# Create signal namespace
signals = Namespace()

# =============================================================================
# SIGNAL DEFINITIONS
# =============================================================================

# Stock check signals
stock_check_requested = signals.signal('stock-check-requested')
stock_check_completed = signals.signal('stock-check-completed')
stock_check_failed = signals.signal('stock-check-failed')

# SKU discovery signals
sku_discovery_requested = signals.signal('sku-discovery-requested')
sku_discovery_completed = signals.signal('sku-discovery-completed')

# Stock change signals
stock_found = signals.signal('stock-found')
stock_lost = signals.signal('stock-lost')
price_changed = signals.signal('price-changed')

# Retailer status signals
retailer_blocked = signals.signal('retailer-blocked')
retailer_unblocked = signals.signal('retailer-unblocked')

# =============================================================================
# SIGNAL HANDLERS
# =============================================================================

class StockSignalHandler:
    """
    Handles stock checking via signals instead of endpoints.
    """
    
    def __init__(self):
        self.active_checks: Dict[str, Dict] = {}
        self.sku_watchlist: Dict[str, List[Dict]] = {}  # retailer -> [{"sku": "...", "callback": ...}]
        self.subscribers: List[Callable] = []
    
    def register_subscriber(self, callback: Callable):
        """Register a subscriber to receive stock updates."""
        self.subscribers.append(callback)
    
    def on_stock_check_requested(self, sender, **kwargs):
        """Handle stock check request signal."""
        query = kwargs.get('query')
        retailer = kwargs.get('retailer')
        zip_code = kwargs.get('zip_code', '90210')
        callback = kwargs.get('callback')
        
        check_id = f"{retailer}_{query}_{int(time.time())}"
        self.active_checks[check_id] = {
            "query": query,
            "retailer": retailer,
            "zip_code": zip_code,
            "callback": callback,
            "started": datetime.now(),
        }
        
        logger.info(f"Stock check requested: {check_id}")
        
        # Trigger actual stock check
        self._perform_stock_check(check_id, query, retailer, zip_code, callback)
    
    def on_sku_discovery_requested(self, sender, **kwargs):
        """Handle SKU discovery request signal."""
        retailer = kwargs.get('retailer')
        category = kwargs.get('category', 'pokemon')
        callback = kwargs.get('callback')
        
        logger.info(f"SKU discovery requested: {retailer} - {category}")
        
        # Trigger SKU discovery
        self._perform_sku_discovery(retailer, category, callback)
    
    def _perform_stock_check(self, check_id: str, query: str, retailer: str, zip_code: str, callback: Optional[Callable]):
        """Perform the actual stock check."""
        try:
            from scanners.stock_checker import StockChecker
            
            checker = StockChecker(zip_code=zip_code)
            
            if retailer:
                result = checker.scan_retailer(retailer, query)
            else:
                result = checker.scan_all(query=query, parallel=False)  # Sequential to reduce blocking
            
            # Emit completion signal
            stock_check_completed.send(
                self,
                check_id=check_id,
                result=result,
                success=True
            )
            
            # Call callback if provided
            if callback:
                callback(result)
            
            # Check for stock changes and emit signals
            self._check_stock_changes(result)
            
            # Remove from active checks
            self.active_checks.pop(check_id, None)
            
        except Exception as e:
            logger.error(f"Stock check failed: {e}")
            
            # Emit failure signal
            stock_check_failed.send(
                self,
                check_id=check_id,
                error=str(e)
            )
            
            if callback:
                callback({"error": str(e)})
            
            self.active_checks.pop(check_id, None)
    
    def _perform_sku_discovery(self, retailer: str, category: str, callback: Optional[Callable]):
        """Perform SKU discovery."""
        try:
            # This would crawl sitemaps, category pages, etc.
            # For now, placeholder
            discovered_skus = []
            
            # Emit completion signal
            sku_discovery_completed.send(
                self,
                retailer=retailer,
                category=category,
                skus=discovered_skus
            )
            
            if callback:
                callback(discovered_skus)
                
        except Exception as e:
            logger.error(f"SKU discovery failed: {e}")
            if callback:
                callback({"error": str(e)})
    
    def _check_stock_changes(self, result: Dict):
        """Check for stock changes and emit appropriate signals."""
        products = result.get("products", [])
        previous_state = getattr(self, '_previous_state', {})
        
        for product in products:
            product_key = f"{product.get('retailer')}_{product.get('sku')}"
            previous = previous_state.get(product_key)
            
            if previous:
                # Check for stock changes
                if previous.get('stock') != product.get('stock'):
                    if product.get('stock'):
                        stock_found.send(
                            self,
                            product=product,
                            previous=previous
                        )
                    else:
                        stock_lost.send(
                            self,
                            product=product,
                            previous=previous
                        )
                
                # Check for price changes
                if previous.get('price') != product.get('price'):
                    price_changed.send(
                        self,
                        product=product,
                        previous=previous,
                        price_change=product.get('price') - previous.get('price')
                    )
            
            # Update state
            previous_state[product_key] = product
        
        self._previous_state = previous_state
    
    def watch_sku(self, sku: str, retailer: str, callback: Callable):
        """Watch a specific SKU for stock changes."""
        if retailer not in self.sku_watchlist:
            self.sku_watchlist[retailer] = []
        
        self.sku_watchlist[retailer].append({
            "sku": sku,
            "callback": callback,
            "last_check": None,
        })
        
        logger.info(f"Watching SKU: {sku} on {retailer}")
    
    def check_watched_skus(self):
        """Check all watched SKUs."""
        from scanners.sku_discovery import lookup_by_sku
        
        for retailer, watches in self.sku_watchlist.items():
            for watch in watches:
                try:
                    product = lookup_by_sku(watch["sku"], retailer)
                    
                    if product:
                        # Check if stock changed
                        last_state = watch.get("last_state")
                        if last_state and last_state.stock != product.stock:
                            watch["callback"](product, last_state)
                        
                        watch["last_state"] = product
                        watch["last_check"] = datetime.now()
                        
                except Exception as e:
                    logger.error(f"Error checking watched SKU {watch['sku']}: {e}")


# =============================================================================
# GLOBAL HANDLER
# =============================================================================

_handler = StockSignalHandler()

# Connect signal handlers
stock_check_requested.connect(_handler.on_stock_check_requested, weak=False)
sku_discovery_requested.connect(_handler.on_sku_discovery_requested, weak=False)


# =============================================================================
# PUBLIC API
# =============================================================================

def request_stock_check(query: str, retailer: Optional[str] = None, zip_code: str = "90210", callback: Optional[Callable] = None):
    """
    Request a stock check via signal (non-blocking).
    
    Args:
        query: Search query
        retailer: Specific retailer (optional)
        zip_code: ZIP code
        callback: Callback function to receive results
    """
    stock_check_requested.send(
        None,
        query=query,
        retailer=retailer,
        zip_code=zip_code,
        callback=callback
    )


def request_sku_discovery(retailer: str, category: str = "pokemon", callback: Optional[Callable] = None):
    """
    Request SKU discovery via signal.
    
    Args:
        retailer: Retailer to discover SKUs from
        category: Product category
        callback: Callback function to receive discovered SKUs
    """
    sku_discovery_requested.send(
        None,
        retailer=retailer,
        category=category,
        callback=callback
    )


def watch_sku(sku: str, retailer: str, callback: Callable):
    """Watch a specific SKU for stock changes."""
    _handler.watch_sku(sku, retailer, callback)


def subscribe_to_stock_updates(callback: Callable):
    """Subscribe to all stock update signals."""
    def on_stock_found(sender, **kwargs):
        callback("stock_found", kwargs.get('product'))
    
    def on_stock_lost(sender, **kwargs):
        callback("stock_lost", kwargs.get('product'))
    
    def on_price_changed(sender, **kwargs):
        callback("price_changed", kwargs.get('product'))
    
    stock_found.connect(on_stock_found, weak=False)
    stock_lost.connect(on_stock_lost, weak=False)
    price_changed.connect(on_price_changed, weak=False)


def get_signal_handler() -> StockSignalHandler:
    """Get the global signal handler."""
    return _handler
