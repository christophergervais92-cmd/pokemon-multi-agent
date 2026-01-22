#!/usr/bin/env python3
"""
Alert Ingestion System

Automatically ingests alerts/notifications and converts them to signals.
- Monitors multiple alert sources
- Converts alerts to stock check signals
- Auto-triggers SKU lookups
- Categorizes and deduplicates alerts
"""
import json
import re
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from agents.utils.logger import get_logger
from agents.scanners.stock_signals import (
    request_stock_check,
    stock_found,
    stock_lost,
    price_changed,
)

logger = get_logger("alert_ingestion")


# =============================================================================
# ALERT TYPES
# =============================================================================

@dataclass
class Alert:
    """Alert/notification data."""
    source: str  # reddit, twitter, discord, email, etc.
    title: str
    content: str
    url: Optional[str] = None
    timestamp: str = ""
    confidence: float = 0.5  # 0-1, how confident this is a real stock alert
    extracted_skus: List[Dict] = None  # [{"sku": "...", "retailer": "..."}]
    extracted_query: Optional[str] = None
    
    def __post_init__(self):
        if self.extracted_skus is None:
            self.extracted_skus = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self):
        return asdict(self)


# =============================================================================
# ALERT PROCESSING
# =============================================================================

class AlertProcessor:
    """Processes alerts and converts them to signals."""
    
    def __init__(self):
        self.processed_alerts: Dict[str, datetime] = {}  # alert_id -> processed_time
        self.alert_history: List[Alert] = []
    
    def _make_alert_id(self, alert: Alert) -> str:
        """Create unique ID for alert."""
        import hashlib
        content = f"{alert.source}_{alert.title}_{alert.content}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def extract_skus_from_alert(self, alert: Alert) -> List[Dict]:
        """
        Extract SKUs and product info from alert text.
        
        Returns:
            List of {"sku": "...", "retailer": "...", "confidence": 0.0-1.0}
        """
        extracted = []
        text = f"{alert.title} {alert.content}".lower()
        
        # Pattern matching for SKUs
        # Target TCIN: 8-9 digits
        target_tcins = re.findall(r'\b(\d{8,9})\b', text)
        for tcin in target_tcins:
            extracted.append({
                "sku": tcin,
                "retailer": "target",
                "confidence": 0.7,
            })
        
        # Best Buy SKU: Usually 8 digits
        bestbuy_skus = re.findall(r'sku[:\s]+(\d{8,})', text, re.IGNORECASE)
        for sku in bestbuy_skus:
            extracted.append({
                "sku": sku,
                "retailer": "bestbuy",
                "confidence": 0.8,
            })
        
        # Product URLs
        url_patterns = {
            "target": (r'target\.com/p/-/A-(\d+)', "target"),
            "bestbuy": (r'bestbuy\.com.*skuId=(\d+)', "bestbuy"),
            "gamestop": (r'gamestop\.com/products/([^/\s]+)', "gamestop"),
            "pokemoncenter": (r'pokemoncenter\.com/product/([^/\s]+)', "pokemoncenter"),
        }
        
        for pattern, retailer in url_patterns.values():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                extracted.append({
                    "sku": match,
                    "retailer": retailer,
                    "confidence": 0.9,  # URLs are high confidence
                })
        
        return extracted
    
    def extract_query_from_alert(self, alert: Alert) -> Optional[str]:
        """Extract search query from alert text."""
        text = f"{alert.title} {alert.content}"
        
        # Look for product names
        pokemon_keywords = [
            "pokemon 151", "paldean fates", "obsidian flames",
            "paradox rift", "temporal forces", "stellar crown",
            "surging sparks", "prismatic evolutions", "destined rivals",
            "booster box", "elite trainer box", "etb",
        ]
        
        for keyword in pokemon_keywords:
            if keyword.lower() in text.lower():
                return keyword
        
        # Fallback: extract first meaningful phrase
        words = text.split()
        if len(words) >= 2:
            return " ".join(words[:3])
        
        return None
    
    def categorize_alert(self, alert: Alert) -> str:
        """Categorize alert type."""
        text = f"{alert.title} {alert.content}".lower()
        
        if any(word in text for word in ["in stock", "available", "restock", "back in stock"]):
            return "stock_alert"
        elif any(word in text for word in ["price drop", "sale", "discount", "deal"]):
            return "price_alert"
        elif any(word in text for word in ["preorder", "pre-order", "coming soon"]):
            return "preorder_alert"
        elif any(word in text for word in ["out of stock", "sold out", "unavailable"]):
            return "out_of_stock_alert"
        else:
            return "general_alert"
    
    def process_alert(self, alert: Alert) -> Dict:
        """
        Process an alert and convert to signals.
        
        Returns:
            Dict with processing results
        """
        alert_id = self._make_alert_id(alert)
        
        # Check if already processed
        if alert_id in self.processed_alerts:
            return {"status": "duplicate", "alert_id": alert_id}
        
        # Extract information
        extracted_skus = self.extract_skus_from_alert(alert)
        extracted_query = self.extract_query_from_alert(alert)
        category = self.categorize_alert(alert)
        
        alert.extracted_skus = extracted_skus
        alert.extracted_query = extracted_query
        
        # Convert to signals
        signals_triggered = []
        
        # If SKUs found, lookup directly
        if extracted_skus:
            from agents.scanners.sku_discovery import lookup_by_sku
            
            for sku_info in extracted_skus:
                try:
                    product = lookup_by_sku(
                        sku_info["sku"],
                        sku_info["retailer"],
                        zip_code="90210"
                    )
                    
                    if product:
                        # Emit stock signal
                        if product.stock:
                            stock_found.send(
                                None,
                                product=product,
                                source="alert_ingestion",
                                alert=alert.to_dict()
                            )
                            signals_triggered.append("stock_found")
                        else:
                            stock_lost.send(
                                None,
                                product=product,
                                source="alert_ingestion",
                                alert=alert.to_dict()
                            )
                            signals_triggered.append("stock_lost")
                
                except Exception as e:
                    logger.error(f"Error looking up SKU {sku_info['sku']}: {e}")
        
        # If query found, trigger stock check
        elif extracted_query:
            def callback(result):
                # Process results and emit signals
                products = result.get("products", [])
                for product in products:
                    if product.get("stock"):
                        stock_found.send(
                            None,
                            product=product,
                            source="alert_ingestion",
                            alert=alert.to_dict()
                        )
            
            request_stock_check(
                extracted_query,
                callback=callback
            )
            signals_triggered.append("stock_check_requested")
        
        # Mark as processed
        self.processed_alerts[alert_id] = datetime.now()
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        return {
            "status": "processed",
            "alert_id": alert_id,
            "category": category,
            "extracted_skus": len(extracted_skus),
            "extracted_query": extracted_query,
            "signals_triggered": signals_triggered,
        }


# =============================================================================
# ALERT SOURCES
# =============================================================================

def ingest_reddit_alert(post_data: Dict) -> Alert:
    """Convert Reddit post to alert."""
    return Alert(
        source="reddit",
        title=post_data.get("title", ""),
        content=post_data.get("selftext", "") or post_data.get("body", ""),
        url=post_data.get("url", ""),
        timestamp=datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
    )


def ingest_twitter_alert(tweet_data: Dict) -> Alert:
    """Convert Twitter/X post to alert."""
    return Alert(
        source="twitter",
        title="",  # Twitter doesn't have titles
        content=tweet_data.get("text", "") or tweet_data.get("content", ""),
        url=tweet_data.get("url", ""),
        timestamp=tweet_data.get("created_at", datetime.now().isoformat()),
    )


def ingest_discord_alert(message_data: Dict) -> Alert:
    """Convert Discord message to alert."""
    return Alert(
        source="discord",
        title=message_data.get("channel_name", ""),
        content=message_data.get("content", ""),
        url=message_data.get("message_url", ""),
        timestamp=message_data.get("timestamp", datetime.now().isoformat()),
    )


def ingest_webhook_alert(webhook_data: Dict) -> Alert:
    """Convert webhook payload to alert."""
    return Alert(
        source=webhook_data.get("source", "webhook"),
        title=webhook_data.get("title", ""),
        content=webhook_data.get("content", "") or webhook_data.get("message", ""),
        url=webhook_data.get("url", ""),
        timestamp=webhook_data.get("timestamp", datetime.now().isoformat()),
    )


# =============================================================================
# GLOBAL PROCESSOR
# =============================================================================

_processor = AlertProcessor()

def process_alert(alert: Alert) -> Dict:
    """Process an alert and convert to signals."""
    return _processor.process_alert(alert)

def ingest_alert(source: str, data: Dict) -> Dict:
    """
    Ingest alert from various sources.
    
    Args:
        source: Source type (reddit, twitter, discord, webhook)
        data: Alert data
    
    Returns:
        Processing results
    """
    if source == "reddit":
        alert = ingest_reddit_alert(data)
    elif source == "twitter":
        alert = ingest_twitter_alert(data)
    elif source == "discord":
        alert = ingest_discord_alert(data)
    elif source == "webhook":
        alert = ingest_webhook_alert(data)
    else:
        alert = Alert(
            source=source,
            title=data.get("title", ""),
            content=data.get("content", "") or data.get("message", ""),
            url=data.get("url", ""),
        )
    
    return process_alert(alert)
