#!/usr/bin/env python3
"""
Detailed blocking detection - tests multiple times with different methods.
"""
import requests
import time
from datetime import datetime

def test_retailer_detailed(url, retailer_name, test_method="direct"):
    """Detailed test with multiple checks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    if test_method == "with_referer":
        headers["Referer"] = "https://www.google.com/"
    
    print(f"\n  Testing {retailer_name} ({test_method})...")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Save first 2000 chars for analysis
        preview = resp.text[:2000].lower()
        
        result = {
            "status_code": resp.status_code,
            "url_final": resp.url,
            "content_length": len(resp.text),
            "has_captcha": False,
            "has_cloudflare": False,
            "has_block_message": False,
            "preview_snippet": resp.text[:500],
        }
        
        # Detailed checks
        captcha_keywords = [
            "captcha", "recaptcha", "hcaptcha", "cloudflare",
            "checking your browser", "i'm not a robot",
            "access denied", "blocked", "forbidden"
        ]
        
        for keyword in captcha_keywords:
            if keyword in preview:
                if "cloudflare" in keyword or "checking" in keyword:
                    result["has_cloudflare"] = True
                if "captcha" in keyword:
                    result["has_captcha"] = True
                if "blocked" in keyword or "denied" in keyword or "forbidden" in keyword:
                    result["has_block_message"] = True
        
        # Check for specific blocking patterns
        if resp.status_code == 403:
            result["definitely_blocked"] = True
            result["reason"] = "HTTP 403 Forbidden"
        elif resp.status_code == 429:
            result["definitely_blocked"] = True
            result["reason"] = "HTTP 429 Rate Limited"
        elif resp.status_code == 503 and "cloudflare" in preview:
            result["definitely_blocked"] = True
            result["reason"] = "HTTP 503 with Cloudflare"
        elif resp.status_code == 200 and (result["has_captcha"] or result["has_cloudflare"]):
            result["definitely_blocked"] = True
            result["reason"] = "CAPTCHA/Cloudflare challenge on page"
        elif resp.status_code == 200 and len(resp.text) < 1000:
            result["definitely_blocked"] = True
            result["reason"] = "Suspiciously short response"
        else:
            result["definitely_blocked"] = False
            result["reason"] = "Appears accessible"
        
        return result
        
    except requests.exceptions.Timeout:
        return {
            "definitely_blocked": True,
            "reason": "Request timeout (likely blocking)",
            "status_code": None,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "definitely_blocked": True,
            "reason": f"Connection error: {str(e)[:50]}",
            "status_code": None,
        }
    except Exception as e:
        return {
            "definitely_blocked": False,
            "reason": f"Error: {str(e)[:50]}",
            "status_code": None,
        }

def main():
    print("=" * 70)
    print("🔍 DETAILED BLOCKING VERIFICATION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    retailers = {
        "GameStop": "https://www.gamestop.com/search/?q=pokemon",
        "Pokemon Center": "https://www.pokemoncenter.com/search/pokemon",
        "Best Buy": "https://www.bestbuy.com/site/searchpage.jsp?st=pokemon",
    }
    
    results = {}
    
    for retailer, url in retailers.items():
        print(f"\n{'='*70}")
        print(f"Testing: {retailer}")
        print(f"{'='*70}")
        
        # Test 1: Direct request
        result1 = test_retailer_detailed(url, retailer, "direct")
        time.sleep(2)
        
        # Test 2: With referer
        result2 = test_retailer_detailed(url, retailer, "with_referer")
        time.sleep(2)
        
        # Analyze results
        blocked_count = sum([r.get("definitely_blocked", False) for r in [result1, result2]])
        
        print(f"\n  📊 Results:")
        print(f"     Test 1 (direct): Status {result1.get('status_code', 'N/A')} - {result1.get('reason', 'N/A')}")
        print(f"     Test 2 (referer): Status {result2.get('status_code', 'N/A')} - {result2.get('reason', 'N/A')}")
        
        if result1.get("status_code"):
            print(f"     Content length: {result1.get('content_length', 0)} bytes")
            if result1.get("has_cloudflare"):
                print(f"     ⚠️  Cloudflare detected")
            if result1.get("has_captcha"):
                print(f"     ⚠️  CAPTCHA detected")
            if result1.get("has_block_message"):
                print(f"     ⚠️  Block message detected")
        
        # Show preview if blocked
        if result1.get("definitely_blocked") and result1.get("preview_snippet"):
            preview = result1["preview_snippet"][:300]
            print(f"\n     Response preview:")
            print(f"     {preview}...")
        
        # Final verdict
        if blocked_count == 2:
            verdict = "🚫 DEFINITELY BLOCKED"
            confidence = "100%"
        elif blocked_count == 1:
            verdict = "⚠️  LIKELY BLOCKED"
            confidence = "50-75%"
        else:
            verdict = "✅ NOT BLOCKED"
            confidence = "0%"
        
        results[retailer] = {
            "verdict": verdict,
            "confidence": confidence,
            "blocked": blocked_count >= 1,
            "details": [result1, result2]
        }
        
        print(f"\n     Verdict: {verdict} (Confidence: {confidence})")
    
    print("\n" + "=" * 70)
    print("📈 FINAL SUMMARY")
    print("=" * 70)
    
    for retailer, result in results.items():
        print(f"{retailer}: {result['verdict']} ({result['confidence']} confidence)")
    
    blocked_retailers = [r for r, data in results.items() if data["blocked"]]
    
    if blocked_retailers:
        print(f"\n🚫 Blocked Retailers: {', '.join(blocked_retailers)}")
        print("\nRecommendations:")
        print("  1. Wait 1-24 hours (temporary blocks may expire)")
        print("  2. Use proxy service (Smartproxy $75/mo recommended)")
        print("  3. Increase delays (SCAN_MIN_DELAY=3.0, SCAN_MAX_DELAY=8.0)")
    else:
        print("\n✅ No blocking detected! All retailers accessible.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
