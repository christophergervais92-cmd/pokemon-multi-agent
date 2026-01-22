#!/usr/bin/env python3
"""
Safe Blocking Status Checker

Checks blocking status WITHOUT making HTTP requests.
Only reads the local blocked_retailers.json file.
This is safe to run even if you're already blocked.
"""
import json
from datetime import datetime
from pathlib import Path

# Path to blocked retailers file
BLOCKED_RETAILERS_FILE = Path(__file__).parent / ".stock_cache" / "blocked_retailers.json"

def load_blocked_retailers():
    """Load blocked retailers from local file (no HTTP requests)."""
    if not BLOCKED_RETAILERS_FILE.exists():
        return {}
    
    try:
        with open(BLOCKED_RETAILERS_FILE) as f:
            data = json.load(f)
            # Convert ISO strings back to datetime
            return {
                k: datetime.fromisoformat(v) 
                for k, v in data.items()
            }
    except Exception as e:
        print(f"⚠️  Error reading blocked retailers file: {e}")
        return {}

def get_all_configured_retailers():
    """Get list of all configured retailers in the system."""
    try:
        from agents.scanners.stock_checker import StockChecker
        checker = StockChecker()
        return list(checker.RETAILERS.keys())
    except:
        # Fallback list if import fails
        return ["target", "bestbuy", "gamestop", "pokemoncenter", "costco", "barnesandnoble", "amazon", "tcgplayer"]

def check_blocking_status(retailer: str = None, retry_after_hours: int = 1):
    """
    Check blocking status for a retailer or all retailers.
    
    Args:
        retailer: Specific retailer to check (None = all retailers)
        retry_after_hours: How many hours before retry (default: 1)
    
    Returns:
        Dict with blocking status information
    """
    blocked = load_blocked_retailers()
    all_retailers = get_all_configured_retailers()
    
    if retailer:
        # Check specific retailer
        if retailer not in blocked:
            return {
                "retailer": retailer,
                "blocked": False,
                "status": "✅ NOT BLOCKED",
                "message": "Retailer is not in blocked list"
            }
        
        blocked_time = blocked[retailer]
        hours_since_block = (datetime.now() - blocked_time).total_seconds() / 3600
        
        if hours_since_block >= retry_after_hours:
            return {
                "retailer": retailer,
                "blocked": False,
                "status": "✅ UNBLOCKED",
                "blocked_at": blocked_time.isoformat(),
                "hours_since_block": round(hours_since_block, 2),
                "message": f"Block expired {hours_since_block:.1f} hours ago (will be retried)"
            }
        else:
            hours_remaining = retry_after_hours - hours_since_block
            return {
                "retailer": retailer,
                "blocked": True,
                "status": "🚫 BLOCKED",
                "blocked_at": blocked_time.isoformat(),
                "hours_since_block": round(hours_since_block, 2),
                "hours_remaining": round(hours_remaining, 2),
                "message": f"Blocked {hours_since_block:.1f} hours ago, {hours_remaining:.1f} hours remaining"
            }
    else:
        # Check all retailers (both blocked and configured)
        results = {}
        now = datetime.now()
        
        # First, check all configured retailers
        for retailer_name in all_retailers:
            if retailer_name in blocked:
                # Retailer is in blocked list
                blocked_time = blocked[retailer_name]
                hours_since_block = (now - blocked_time).total_seconds() / 3600
                
                if hours_since_block >= retry_after_hours:
                    results[retailer_name] = {
                        "blocked": False,
                        "status": "✅ UNBLOCKED",
                        "blocked_at": blocked_time.isoformat(),
                        "hours_since_block": round(hours_since_block, 2),
                    }
                else:
                    hours_remaining = retry_after_hours - hours_since_block
                    results[retailer_name] = {
                        "blocked": True,
                        "status": "🚫 BLOCKED",
                        "blocked_at": blocked_time.isoformat(),
                        "hours_since_block": round(hours_since_block, 2),
                        "hours_remaining": round(hours_remaining, 2),
                    }
            else:
                # Retailer is not blocked
                results[retailer_name] = {
                    "blocked": False,
                    "status": "✅ NOT BLOCKED",
                    "message": "Never been blocked"
                }
        
        # Also include any retailers in blocked list that aren't in configured list
        for retailer_name, blocked_time in blocked.items():
            if retailer_name not in all_retailers:
                hours_since_block = (now - blocked_time).total_seconds() / 3600
                if hours_since_block >= retry_after_hours:
                    results[retailer_name] = {
                        "blocked": False,
                        "status": "✅ UNBLOCKED (not in active config)",
                        "blocked_at": blocked_time.isoformat(),
                        "hours_since_block": round(hours_since_block, 2),
                    }
                else:
                    hours_remaining = retry_after_hours - hours_since_block
                    results[retailer_name] = {
                        "blocked": True,
                        "status": "🚫 BLOCKED (not in active config)",
                        "blocked_at": blocked_time.isoformat(),
                        "hours_since_block": round(hours_since_block, 2),
                        "hours_remaining": round(hours_remaining, 2),
                    }
        
        return {
            "total_configured": len(all_retailers),
            "total_in_blocked_list": len(blocked),
            "currently_blocked": sum(1 for r in results.values() if r.get("blocked", False)),
            "unblocked": sum(1 for r in results.values() if not r.get("blocked", False)),
            "retailers": results
        }

def main():
    """CLI interface for checking blocking status."""
    import sys
    
    print("=" * 70)
    print("🔍 SAFE BLOCKING STATUS CHECK")
    print("=" * 70)
    print("(No HTTP requests made - only reads local file)\n")
    
    # Check if specific retailer requested
    if len(sys.argv) > 1:
        retailer = sys.argv[1]
        result = check_blocking_status(retailer)
        
        print(f"Retailer: {result['retailer']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        
        if result.get('blocked_at'):
            print(f"Blocked At: {result['blocked_at']}")
            print(f"Hours Since Block: {result.get('hours_since_block', 'N/A')}")
            if result.get('hours_remaining'):
                print(f"Hours Remaining: {result['hours_remaining']}")
    else:
        # Check all retailers
        result = check_blocking_status()
        
        print(f"Total Configured Retailers: {result['total_configured']}")
        print(f"Total in Blocked List: {result['total_in_blocked_list']}")
        print(f"Currently Blocked: {result['currently_blocked']}")
        print(f"Not Blocked: {result['unblocked']}\n")
        
        if result['retailers']:
            print("Retailer Status:")
            print("-" * 70)
            for retailer, status in sorted(result['retailers'].items()):
                print(f"\n{retailer}:")
                print(f"  Status: {status['status']}")
                if status.get('blocked_at'):
                    print(f"  Blocked At: {status['blocked_at']}")
                    print(f"  Hours Since Block: {status['hours_since_block']}")
                    if status.get('hours_remaining'):
                        print(f"  Hours Remaining: {status['hours_remaining']}")
                elif status.get('message'):
                    print(f"  {status['message']}")
        else:
            print("✅ No retailers in blocked list!")
    
    print("\n" + "=" * 70)
    print("💡 TIP: This check is safe - it doesn't make HTTP requests")
    print("=" * 70)

if __name__ == "__main__":
    main()
