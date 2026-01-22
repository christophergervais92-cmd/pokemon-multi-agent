#!/usr/bin/env python3
"""
Quick blocking detection test for all retailers.
Tests if you're currently blocked or rate limited.
"""
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get proxy from environment (no rotation)
PROXY_URL = os.environ.get("PROXY_SERVICE_URL", "")
PROXIES = None
if PROXY_URL:
    # Use configured proxy directly (no rotation)
    PROXIES = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }
    proxy_display = PROXY_URL.split('@')[1] if '@' in PROXY_URL else 'configured'
    print(f"🔒 Using proxy: {proxy_display}\n")

# Test URLs for each retailer
RETAILERS = {
    "Target": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&channel=WEB&keyword=pokemon&count=5",
    "Best Buy": "https://www.bestbuy.com/site/searchpage.jsp?st=pokemon",
    "GameStop": "https://www.gamestop.com/search/?q=pokemon",
    "Pokemon Center": "https://www.pokemoncenter.com/search/pokemon",
    "TCGPlayer (API)": "https://api.pokemontcg.io/v2/cards?q=name:charizard&pageSize=1",
}

def check_blocking(url, retailer_name):
    """Check if a retailer is blocking requests."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    result = {
        "retailer": retailer_name,
        "url": url,
        "status": "unknown",
        "blocked": False,
        "status_code": None,
        "response_time": None,
        "indicators": [],
        "error": None
    }
    
    try:
        start_time = time.time()
        resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=15, allow_redirects=True)
        response_time = time.time() - start_time
        
        result["status_code"] = resp.status_code
        result["response_time"] = round(response_time, 2)
        text_lower = resp.text.lower()
        
        # Check status codes
        if resp.status_code == 200:
            result["status"] = "✅ OK"
        elif resp.status_code == 429:
            result["status"] = "⚠️ RATE LIMITED"
            result["blocked"] = True
            result["indicators"].append(f"HTTP 429 - Too many requests")
        elif resp.status_code == 403:
            result["status"] = "🚫 FORBIDDEN"
            result["blocked"] = True
            result["indicators"].append(f"HTTP 403 - IP likely blocked")
        elif resp.status_code == 503:
            result["status"] = "🔒 SERVICE UNAVAILABLE"
            result["blocked"] = True
            result["indicators"].append(f"HTTP 503 - May be blocking")
        elif resp.status_code == 401:
            result["status"] = "🔐 UNAUTHORIZED"
            result["blocked"] = True
            result["indicators"].append(f"HTTP 401 - Authentication required")
        else:
            result["status"] = f"⚠️ UNEXPECTED ({resp.status_code})"
            result["indicators"].append(f"Unexpected status code: {resp.status_code}")
        
        # Check for CAPTCHA
        captcha_indicators = [
            ("cloudflare", "Cloudflare challenge"),
            ("recaptcha", "reCAPTCHA detected"),
            ("hcaptcha", "hCaptcha detected"),
            ("captcha", "CAPTCHA detected"),
            ("checking your browser", "Cloudflare browser check"),
            ("i'm not a robot", "reCAPTCHA challenge"),
            ("access denied", "Access denied message"),
            ("blocked", "Blocking message"),
            ("too many requests", "Rate limit message"),
        ]
        
        for keyword, message in captcha_indicators:
            if keyword in text_lower:
                result["blocked"] = True
                result["indicators"].append(message)
        
        # Check response size (suspiciously small = likely blocked)
        if len(resp.text) < 500 and resp.status_code == 200:
            result["indicators"].append(f"Suspiciously small response ({len(resp.text)} bytes)")
        
        # Check for redirects to error pages
        if "error" in resp.url.lower() or "blocked" in resp.url.lower():
            result["blocked"] = True
            result["indicators"].append(f"Redirected to error page: {resp.url}")
        
    except requests.exceptions.Timeout:
        result["status"] = "⏱️ TIMEOUT"
        result["blocked"] = True
        result["error"] = "Request timed out"
    except requests.exceptions.ConnectionError:
        result["status"] = "🔌 CONNECTION ERROR"
        result["blocked"] = True
        result["error"] = "Connection failed"
    except Exception as e:
        result["status"] = "❌ ERROR"
        result["error"] = str(e)
    
    return result

def main():
    print("=" * 70)
    print("🔍 BLOCKING DETECTION TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    for retailer, url in RETAILERS.items():
        print(f"Testing {retailer}...", end=" ", flush=True)
        result = check_blocking(url, retailer)
        results.append(result)
        
        if result["blocked"]:
            print(f"🚫 BLOCKED")
        elif result["error"]:
            print(f"❌ ERROR: {result['error']}")
        else:
            print(f"✅ OK ({result['response_time']}s)")
        
        time.sleep(1)  # Be nice, don't hammer servers
    
    print("\n" + "=" * 70)
    print("📊 DETAILED RESULTS")
    print("=" * 70)
    
    blocked_count = sum(1 for r in results if r["blocked"])
    total_count = len(results)
    
    for result in results:
        print(f"\n{result['retailer']}:")
        print(f"  Status: {result['status']}")
        print(f"  Code: {result['status_code']}")
        print(f"  Time: {result['response_time']}s" if result['response_time'] else "  Time: N/A")
        
        if result["blocked"]:
            print(f"  ⚠️  BLOCKING INDICATORS:")
            for indicator in result["indicators"]:
                print(f"     - {indicator}")
        
        if result["error"]:
            print(f"  ❌ Error: {result['error']}")
    
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"Total Retailers: {total_count}")
    print(f"Blocked: {blocked_count}")
    print(f"OK: {total_count - blocked_count}")
    
    if blocked_count == 0:
        print("\n✅ All retailers are accessible! No blocking detected.")
    elif blocked_count < total_count:
        print(f"\n⚠️  {blocked_count} retailer(s) showing blocking signs.")
        print("   Consider: Increasing delays, using proxies, or waiting.")
    else:
        print("\n🚫 All retailers appear to be blocking.")
        print("   Recommendation: Wait 1-24 hours or use proxy service.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
