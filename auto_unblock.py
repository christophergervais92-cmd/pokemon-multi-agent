#!/usr/bin/env python3
"""
Automatic Retailer Unblocking Script

Periodically checks if blocked retailers are available again and unblocks them.
Runs in the background and automatically tests blocked retailers.
"""
import json
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# Import stock checker
try:
    from agents.scanners.stock_checker import (
        load_blocked_retailers,
        save_blocked_retailers,
        is_retailer_blocked,
        StockChecker,
    )
except ImportError:
    print("❌ Could not import stock checker")
    sys.exit(1)

# Configuration
CHECK_INTERVAL = 300  # Check every 5 minutes
BLOCK_DURATION_HOURS = 1  # How long to wait before retrying

def test_retailer(retailer_name: str) -> tuple[bool, str]:
    """
    Test if a retailer is accessible.
    
    Returns:
        (is_accessible, message)
    """
    try:
        checker = StockChecker()
        
        # Try a simple scan
        if retailer_name == "target":
            from agents.scanners.stock_checker import scan_target
            products = scan_target("pokemon", "90210")
        elif retailer_name == "bestbuy":
            from agents.scanners.stock_checker import scan_bestbuy
            products = scan_bestbuy("pokemon")
        elif retailer_name == "gamestop":
            from agents.scanners.stock_checker import scan_gamestop
            products = scan_gamestop("pokemon")
        elif retailer_name == "pokemoncenter":
            from agents.scanners.stock_checker import scan_pokemoncenter
            products = scan_pokemoncenter("pokemon")
        elif retailer_name == "costco":
            from agents.scanners.stock_checker import scan_costco
            products = scan_costco("pokemon")
        elif retailer_name == "barnesandnoble":
            from agents.scanners.stock_checker import scan_barnesandnoble
            products = scan_barnesandnoble("pokemon")
        elif retailer_name == "amazon":
            from agents.scanners.stock_checker import scan_amazon
            products = scan_amazon("pokemon")
        else:
            return False, "Unknown retailer"
        
        # If we got products (even empty list), retailer is accessible
        if products is not None:
            return True, f"Accessible ({len(products)} products found)"
        else:
            return False, "No products returned"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_and_unblock():
    """Check blocked retailers and unblock if accessible."""
    blocked = load_blocked_retailers()
    
    if not blocked:
        return 0  # Nothing to check
    
    now = datetime.now()
    unblocked_count = 0
    
    for retailer, blocked_time in list(blocked.items()):
        elapsed = now - blocked_time
        
        # Check if enough time has passed
        if elapsed >= timedelta(hours=BLOCK_DURATION_HOURS):
            print(f"🔄 Testing {retailer} (blocked {elapsed.total_seconds()/3600:.1f}h ago)...")
            
            # Test if accessible
            is_accessible, message = test_retailer(retailer)
            
            if is_accessible:
                # Unblock it
                blocked.pop(retailer, None)
                save_blocked_retailers(blocked)
                unblocked_count += 1
                print(f"✅ {retailer} is accessible again - UNBLOCKED")
                print(f"   {message}")
            else:
                print(f"🚫 {retailer} still blocked - {message}")
                # Update blocked time to now (extend block)
                blocked[retailer] = now
                save_blocked_retailers(blocked)
    
    return unblocked_count

def main():
    """Main loop - periodically check and unblock."""
    print("=" * 70)
    print("🔄 AUTOMATIC RETAILER UNBLOCKING")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60:.1f} minutes)")
    print(f"Block duration: {BLOCK_DURATION_HOURS} hour(s)")
    print("=" * 70)
    print("\n💡 This script will run in the background and automatically")
    print("   test blocked retailers every 5 minutes.")
    print("   Press Ctrl+C to stop.\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Check #{iteration}")
            print("-" * 70)
            
            unblocked = check_and_unblock()
            
            if unblocked > 0:
                print(f"\n✅ Unblocked {unblocked} retailer(s)!")
            else:
                blocked = load_blocked_retailers()
                if blocked:
                    print(f"\n📊 Currently blocked: {len(blocked)} retailer(s)")
                    for retailer, blocked_time in blocked.items():
                        elapsed = datetime.now() - blocked_time
                        remaining = timedelta(hours=BLOCK_DURATION_HOURS) - elapsed
                        if remaining.total_seconds() > 0:
                            remaining_min = int(remaining.total_seconds() / 60)
                            print(f"   - {retailer}: Unblocks in ~{remaining_min} min")
                        else:
                            print(f"   - {retailer}: Ready to test")
                else:
                    print("\n✅ No retailers currently blocked!")
            
            print(f"\n⏳ Waiting {CHECK_INTERVAL} seconds until next check...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
        print("=" * 70)

if __name__ == "__main__":
    main()
