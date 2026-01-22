#!/usr/bin/env python3
"""
Proxy Rotation System

Automatically rotates between multiple proxy IPs to avoid blocking.
- Tracks which proxies are blocked
- Rotates to new proxy when block detected
- Supports multiple proxy providers
- Automatic failover
"""
import os
import random
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import threading

from agents.utils.logger import get_logger

logger = get_logger("proxy_rotation")


# =============================================================================
# PROXY POOL MANAGEMENT
# =============================================================================

class ProxyPool:
    """
    Manages a pool of proxy IPs with rotation and health tracking.
    """
    
    def __init__(self):
        self.proxies: List[Dict] = []  # List of proxy configs
        self.current_index = 0
        self.blocked_proxies: Dict[str, datetime] = {}  # proxy_id -> blocked_until
        self.proxy_stats: Dict[str, Dict] = {}  # proxy_id -> stats
        self.lock = threading.Lock()
        self.block_duration = timedelta(hours=1)  # How long to consider a proxy blocked
        
        # Load saved state
        self._load_state()
    
    def _load_state(self):
        """Load proxy state from disk."""
        state_file = Path(__file__).parent.parent.parent / ".stock_cache" / "proxy_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    self.blocked_proxies = {
                        k: datetime.fromisoformat(v)
                        for k, v in data.get("blocked_proxies", {}).items()
                    }
                    self.proxy_stats = data.get("proxy_stats", {})
            except:
                pass
    
    def _save_state(self):
        """Save proxy state to disk."""
        state_file = Path(__file__).parent.parent.parent / ".stock_cache" / "proxy_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "blocked_proxies": {
                        k: v.isoformat()
                        for k, v in self.blocked_proxies.items()
                    },
                    "proxy_stats": self.proxy_stats,
                }, f)
        except:
            pass
    
    def add_proxy(self, proxy_config: Dict):
        """
        Add a proxy to the pool.
        
        Args:
            proxy_config: Dict with 'id', 'url', 'provider', etc.
        """
        with self.lock:
            proxy_id = proxy_config.get("id") or self._generate_id(proxy_config["url"])
            proxy_config["id"] = proxy_id
            
            # Check if already exists
            existing = next((p for p in self.proxies if p["id"] == proxy_id), None)
            if existing:
                return
            
            self.proxies.append(proxy_config)
            
            # Initialize stats
            if proxy_id not in self.proxy_stats:
                self.proxy_stats[proxy_id] = {
                    "success_count": 0,
                    "failure_count": 0,
                    "last_used": None,
                    "last_success": None,
                    "last_failure": None,
                }
            
            logger.info(f"Added proxy: {proxy_id} ({proxy_config.get('provider', 'unknown')})")
            self._save_state()
    
    def _generate_id(self, proxy_url: str) -> str:
        """Generate a unique ID for a proxy."""
        return hashlib.md5(proxy_url.encode()).hexdigest()[:12]
    
    def get_next_proxy(self, exclude_blocked: bool = True) -> Optional[Dict]:
        """
        Get the next available proxy.
        
        Args:
            exclude_blocked: If True, skip blocked proxies
        
        Returns:
            Proxy config dict or None if no proxies available
        """
        with self.lock:
            if not self.proxies:
                return None
            
            # Filter out blocked proxies
            available = []
            now = datetime.now()
            
            for proxy in self.proxies:
                proxy_id = proxy["id"]
                
                # Check if blocked
                if exclude_blocked and proxy_id in self.blocked_proxies:
                    blocked_until = self.blocked_proxies[proxy_id]
                    if now < blocked_until:
                        continue  # Still blocked
                    else:
                        # Unblocked - remove from blocked list
                        self.blocked_proxies.pop(proxy_id, None)
                        logger.info(f"Proxy {proxy_id} unblocked (was blocked until {blocked_until})")
                
                available.append(proxy)
            
            if not available:
                # All proxies blocked - return least recently blocked
                if self.blocked_proxies:
                    least_blocked = min(self.blocked_proxies.items(), key=lambda x: x[1])
                    proxy_id = least_blocked[0]
                    proxy = next((p for p in self.proxies if p["id"] == proxy_id), None)
                    if proxy:
                        logger.warning(f"All proxies blocked, using least blocked: {proxy_id}")
                        return proxy
                return None
            
            # Round-robin selection
            proxy = available[self.current_index % len(available)]
            self.current_index += 1
            
            # Update last used
            proxy_id = proxy["id"]
            if proxy_id in self.proxy_stats:
                self.proxy_stats[proxy_id]["last_used"] = datetime.now().isoformat()
            
            return proxy
    
    def mark_blocked(self, proxy_id: str, duration: Optional[timedelta] = None):
        """
        Mark a proxy as blocked.
        
        Args:
            proxy_id: ID of the blocked proxy
            duration: How long to consider it blocked (default: 1 hour)
        """
        with self.lock:
            if duration is None:
                duration = self.block_duration
            
            blocked_until = datetime.now() + duration
            self.blocked_proxies[proxy_id] = blocked_until
            
            # Update stats
            if proxy_id in self.proxy_stats:
                self.proxy_stats[proxy_id]["failure_count"] = \
                    self.proxy_stats[proxy_id].get("failure_count", 0) + 1
                self.proxy_stats[proxy_id]["last_failure"] = datetime.now().isoformat()
            
            logger.warning(f"Proxy {proxy_id} marked as blocked until {blocked_until}")
            self._save_state()
    
    def mark_success(self, proxy_id: str):
        """Mark a proxy as successful."""
        with self.lock:
            if proxy_id in self.proxy_stats:
                self.proxy_stats[proxy_id]["success_count"] = \
                    self.proxy_stats[proxy_id].get("success_count", 0) + 1
                self.proxy_stats[proxy_id]["last_success"] = datetime.now().isoformat()
            
            # Remove from blocked if it was blocked
            if proxy_id in self.blocked_proxies:
                self.blocked_proxies.pop(proxy_id, None)
                logger.info(f"Proxy {proxy_id} unblocked after success")
                self._save_state()
    
    def get_proxy_url(self, proxy: Dict) -> str:
        """Get the proxy URL for requests."""
        return proxy["url"]
    
    def get_stats(self) -> Dict:
        """Get statistics about proxy usage."""
        with self.lock:
            return {
                "total_proxies": len(self.proxies),
                "blocked_proxies": len(self.blocked_proxies),
                "available_proxies": len(self.proxies) - len(self.blocked_proxies),
                "proxy_stats": self.proxy_stats.copy(),
            }


# =============================================================================
# PROXY PROVIDER CONFIGURATIONS
# =============================================================================

class ProxyProvider:
    """Base class for proxy providers."""
    
    @staticmethod
    def create_proxies_from_config() -> List[Dict]:
        """Create proxy configs from environment variables."""
        proxies = []
        
        # Smartproxy/Decodo - rotate ports
        proxy_url = os.environ.get("PROXY_SERVICE_URL", "")
        if proxy_url:
            provider = "smartproxy" if "smartproxy" in proxy_url.lower() else "decodo"
            
            # Extract base URL
            if "@" in proxy_url:
                base_auth = proxy_url.split("@")[0] + "@"
                host_part = proxy_url.split("@")[1]
                host = host_part.split(":")[0]
                
                # Create proxies for multiple ports (10001-10010)
                for port in range(10001, 10011):
                    proxy_id = f"{provider}_{host}_{port}"
                    proxies.append({
                        "id": proxy_id,
                        "url": f"{base_auth}{host}:{port}",
                        "provider": provider,
                        "host": host,
                        "port": port,
                        "type": "residential" if "residential" in proxy_url.lower() else "datacenter",
                    })
            else:
                # Single proxy
                proxy_id = hashlib.md5(proxy_url.encode()).hexdigest()[:12]
                proxies.append({
                    "id": proxy_id,
                    "url": proxy_url,
                    "provider": provider,
                    "type": "unknown",
                })
        
        # Additional proxy sources
        additional_proxies = os.environ.get("ADDITIONAL_PROXY_URLS", "")
        if additional_proxies:
            for proxy_url in additional_proxies.split(","):
                proxy_url = proxy_url.strip()
                if proxy_url:
                    proxy_id = hashlib.md5(proxy_url.encode()).hexdigest()[:12]
                    proxies.append({
                        "id": proxy_id,
                        "url": proxy_url,
                        "provider": "custom",
                        "type": "unknown",
                    })
        
        return proxies


# =============================================================================
# GLOBAL PROXY POOL
# =============================================================================

_proxy_pool: Optional[ProxyPool] = None
_pool_lock = threading.Lock()

def get_proxy_pool() -> ProxyPool:
    """Get or create the global proxy pool."""
    global _proxy_pool
    
    with _pool_lock:
        if _proxy_pool is None:
            _proxy_pool = ProxyPool()
            
            # Initialize with proxies from config
            proxy_configs = ProxyProvider.create_proxies_from_config()
            for config in proxy_configs:
                _proxy_pool.add_proxy(config)
            
            logger.info(f"Initialized proxy pool with {len(proxy_configs)} proxies")
        
        return _proxy_pool


def get_rotating_proxy() -> Optional[Dict[str, str]]:
    """
    Get the next available proxy for requests.
    
    Returns:
        Dict with 'http' and 'https' keys, or None if no proxies available
    """
    pool = get_proxy_pool()
    proxy = pool.get_next_proxy(exclude_blocked=True)
    
    if not proxy:
        return None
    
    proxy_url = pool.get_proxy_url(proxy)
    
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_current_proxy_id() -> Optional[str]:
    """Get the ID of the currently active proxy."""
    pool = get_proxy_pool()
    proxy = pool.get_next_proxy(exclude_blocked=False)
    return proxy["id"] if proxy else None


def mark_proxy_blocked(proxy_id: Optional[str] = None, duration: Optional[timedelta] = None):
    """
    Mark the current (or specified) proxy as blocked.
    
    Args:
        proxy_id: Specific proxy ID to block, or None for current
        duration: How long to block (default: 1 hour)
    """
    if proxy_id is None:
        proxy_id = get_current_proxy_id()
    
    if proxy_id:
        pool = get_proxy_pool()
        pool.mark_blocked(proxy_id, duration)
        logger.warning(f"Marked proxy {proxy_id} as blocked")
    else:
        logger.warning("No proxy ID available to mark as blocked")


def mark_proxy_success(proxy_id: Optional[str] = None):
    """Mark the current (or specified) proxy as successful."""
    if proxy_id is None:
        proxy_id = get_current_proxy_id()
    
    if proxy_id:
        pool = get_proxy_pool()
        pool.mark_success(proxy_id)
        logger.info(f"Marked proxy {proxy_id} as successful")


def get_proxy_stats() -> Dict:
    """Get proxy pool statistics."""
    pool = get_proxy_pool()
    return pool.get_stats()


def reset_proxy_pool():
    """Reset the proxy pool (for testing)."""
    global _proxy_pool
    with _pool_lock:
        _proxy_pool = None
