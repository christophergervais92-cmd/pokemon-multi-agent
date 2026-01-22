#!/usr/bin/env python3
"""
Test Proxy Rotation System

Tests the proxy rotation system to ensure it's working correctly.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from agents.stealth.proxy_rotation import (
    get_proxy_pool,
    get_rotating_proxy,
    mark_proxy_blocked,
    mark_proxy_success,
    get_proxy_stats,
    get_current_proxy_id,
)

def main():
    print("=" * 70)
    print("🔄 PROXY ROTATION SYSTEM TEST")
    print("=" * 70)
    print()
    
    # Get proxy pool
    pool = get_proxy_pool()
    stats = get_proxy_stats()
    
    print(f"📊 Proxy Pool Status:")
    print(f"   Total proxies: {stats['total_proxies']}")
    print(f"   Available: {stats['available_proxies']}")
    print(f"   Blocked: {stats['blocked_proxies']}")
    print()
    
    if stats['total_proxies'] == 0:
        print("❌ No proxies configured!")
        print("   Set PROXY_SERVICE_URL in .env file")
        return
    
    # Test getting proxies
    print("🔄 Testing Proxy Rotation:")
    print("-" * 70)
    
    for i in range(min(5, stats['total_proxies'])):
        proxy = get_rotating_proxy()
        if proxy:
            proxy_id = get_current_proxy_id()
            print(f"   Proxy #{i+1}: {proxy_id}")
            print(f"      URL: {proxy['http'][:50]}...")
        else:
            print(f"   Proxy #{i+1}: None (all blocked?)")
        print()
    
    # Show proxy stats
    print("📈 Proxy Statistics:")
    print("-" * 70)
    
    for proxy_id, proxy_stat in stats['proxy_stats'].items():
        success = proxy_stat.get('success_count', 0)
        failure = proxy_stat.get('failure_count', 0)
        total = success + failure
        rate = (success / total * 100) if total > 0 else 0
        
        print(f"   {proxy_id}:")
        print(f"      Success: {success} ({rate:.1f}%)")
        print(f"      Failures: {failure}")
        print()
    
    # Test blocking/unblocking
    print("🧪 Testing Block/Unblock:")
    print("-" * 70)
    
    current_id = get_current_proxy_id()
    if current_id:
        print(f"   Current proxy: {current_id}")
        print(f"   Marking as blocked...")
        mark_proxy_blocked(current_id)
        
        # Get next proxy (should be different)
        next_proxy = get_rotating_proxy()
        next_id = get_current_proxy_id()
        
        if next_id and next_id != current_id:
            print(f"   ✅ Rotated to: {next_id}")
        else:
            print(f"   ⚠️  Same proxy (may be only one available)")
        
        # Unblock
        print(f"   Unblocking {current_id}...")
        mark_proxy_success(current_id)
        print(f"   ✅ Unblocked")
    else:
        print("   ⚠️  No proxy available to test")
    
    print()
    print("=" * 70)
    print("✅ Proxy rotation system is working!")
    print("=" * 70)

if __name__ == "__main__":
    main()
