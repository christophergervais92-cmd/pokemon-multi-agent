#!/usr/bin/env python3
"""
Check if proxy IP is flagged/blocked.

Tests the proxy IP against various services to see if it's flagged.
"""
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Get proxy configuration
PROXY_URL = os.environ.get("PROXY_SERVICE_URL", "")
PROXIES = None

if PROXY_URL:
    if "@gate.decodo.com:" in PROXY_URL or "@gate.smartproxy.com:" in PROXY_URL:
        base_url = PROXY_URL.split("@")[0] + "@"
        host = PROXY_URL.split("@")[1].split(":")[0]
        port = PROXY_URL.split("@")[1].split(":")[1] if ":" in PROXY_URL.split("@")[1] else "10001"
        PROXIES = {
            "http": f"{base_url}{host}:{port}",
            "https": f"{base_url}{host}:{port}"
        }
    else:
        PROXIES = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }

def get_proxy_ip():
    """Get the actual IP address through the proxy."""
    try:
        # Use multiple IP check services
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://ipinfo.io/json",
            "https://api.myip.com",
        ]
        
        for service in ip_services:
            try:
                resp = requests.get(service, proxies=PROXIES, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if "ip" in data:
                        return data["ip"], data
                    elif "query" in data:
                        return data["query"], data
            except:
                continue
        
        return None, None
    except Exception as e:
        print(f"❌ Error getting IP: {e}")
        return None, None

def check_ip_reputation(ip_address):
    """Check IP reputation using various services."""
    results = {
        "ip": ip_address,
        "checks": {},
        "flagged": False,
        "flags": []
    }
    
    # Check 1: AbuseIPDB (free tier)
    try:
        # Note: Would need API key for full check
        # For now, just check if IP is in common blocklists
        pass
    except:
        pass
    
    # Check 2: IPInfo.io (free tier - limited)
    try:
        resp = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results["checks"]["ipinfo"] = {
                "country": data.get("country", "Unknown"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "org": data.get("org", "Unknown"),
                "hosting": data.get("org", "").lower().find("hosting") != -1 or 
                          data.get("org", "").lower().find("datacenter") != -1,
            }
            
            # Check if it's a datacenter/hosting IP (more likely to be blocked)
            if results["checks"]["ipinfo"]["hosting"]:
                results["flagged"] = True
                results["flags"].append("Datacenter/Hosting IP (more likely blocked)")
    except Exception as e:
        results["checks"]["ipinfo"] = {"error": str(e)}
    
    # Check 3: Test against retailers directly
    test_urls = {
        "Target API": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&channel=WEB&keyword=test&count=1",
        "Best Buy": "https://www.bestbuy.com/",
        "GameStop": "https://www.gamestop.com/",
        "Pokemon Center": "https://www.pokemoncenter.com/",
    }
    
    results["checks"]["retailer_tests"] = {}
    
    for name, url in test_urls.items():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            start_time = datetime.now()
            resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=10, allow_redirects=True)
            response_time = (datetime.now() - start_time).total_seconds()
            
            is_blocked = False
            indicators = []
            
            if resp.status_code == 403:
                is_blocked = True
                indicators.append("HTTP 403 - Forbidden")
            elif resp.status_code == 429:
                is_blocked = True
                indicators.append("HTTP 429 - Rate Limited")
            elif resp.status_code == 503:
                is_blocked = True
                indicators.append("HTTP 503 - Service Unavailable")
            elif "captcha" in resp.text.lower() or "cloudflare" in resp.text.lower():
                is_blocked = True
                indicators.append("CAPTCHA/Cloudflare challenge")
            elif len(resp.text) < 500:
                is_blocked = True
                indicators.append("Suspiciously small response")
            
            if is_blocked:
                results["flagged"] = True
                results["flags"].append(f"{name}: {', '.join(indicators)}")
            
            results["checks"]["retailer_tests"][name] = {
                "status_code": resp.status_code,
                "response_time": round(response_time, 2),
                "blocked": is_blocked,
                "indicators": indicators,
            }
        except requests.exceptions.Timeout:
            results["checks"]["retailer_tests"][name] = {
                "status_code": None,
                "response_time": None,
                "blocked": True,
                "indicators": ["Timeout"],
            }
            results["flagged"] = True
            results["flags"].append(f"{name}: Timeout")
        except Exception as e:
            results["checks"]["retailer_tests"][name] = {
                "error": str(e),
                "blocked": None,
            }
    
    return results

def main():
    print("=" * 70)
    print("🔍 PROXY IP FLAGGING CHECK")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not PROXIES:
        print("❌ No proxy configured!")
        print("   Set PROXY_SERVICE_URL in .env file")
        return
    
    print("📡 Getting proxy IP address...")
    ip_address, ip_data = get_proxy_ip()
    
    if not ip_address:
        print("❌ Could not get IP address through proxy")
        print("   Proxy may be down or misconfigured")
        return
    
    print(f"✅ Proxy IP: {ip_address}\n")
    
    if ip_data:
        print("📍 IP Information:")
        if "country" in ip_data:
            print(f"   Country: {ip_data.get('country', 'Unknown')}")
        if "region" in ip_data:
            print(f"   Region: {ip_data.get('region', 'Unknown')}")
        if "city" in ip_data:
            print(f"   City: {ip_data.get('city', 'Unknown')}")
        if "org" in ip_data:
            print(f"   Organization: {ip_data.get('org', 'Unknown')}")
        print()
    
    print("🔍 Checking IP reputation and retailer access...")
    results = check_ip_reputation(ip_address)
    
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    # IP Info
    if "ipinfo" in results["checks"]:
        ipinfo = results["checks"]["ipinfo"]
        if "error" not in ipinfo:
            print(f"\n📍 IP Details:")
            print(f"   Country: {ipinfo.get('country', 'Unknown')}")
            print(f"   Region: {ipinfo.get('region', 'Unknown')}")
            print(f"   City: {ipinfo.get('city', 'Unknown')}")
            print(f"   Organization: {ipinfo.get('org', 'Unknown')}")
            if ipinfo.get("hosting"):
                print(f"   ⚠️  Type: Datacenter/Hosting (more likely to be blocked)")
            else:
                print(f"   ✅ Type: Residential (less likely to be blocked)")
    
    # Retailer Tests
    print(f"\n🛒 Retailer Access Tests:")
    blocked_count = 0
    total_count = 0
    
    for name, test_result in results["checks"]["retailer_tests"].items():
        total_count += 1
        if "error" in test_result:
            print(f"   {name}: ❌ Error - {test_result['error']}")
        elif test_result.get("blocked"):
            blocked_count += 1
            indicators = ", ".join(test_result.get("indicators", []))
            print(f"   {name}: 🚫 BLOCKED ({indicators})")
        else:
            status = test_result.get("status_code", "N/A")
            time = test_result.get("response_time", "N/A")
            print(f"   {name}: ✅ OK (Status: {status}, Time: {time}s)")
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    
    if results["flagged"]:
        print(f"\n🚫 PROXY IP APPEARS TO BE FLAGGED")
        print(f"\n⚠️  Flags Detected:")
        for flag in results["flags"]:
            print(f"   - {flag}")
        
        print(f"\n💡 Recommendations:")
        print(f"   1. Try rotating to a different proxy port (10001-10010)")
        print(f"   2. Wait 1-24 hours for IP to be unblocked")
        print(f"   3. Contact proxy provider to request IP rotation")
        print(f"   4. Use browser automation fallback for blocked retailers")
    else:
        print(f"\n✅ PROXY IP APPEARS CLEAN")
        print(f"   No major blocking indicators detected")
        print(f"   {total_count - blocked_count}/{total_count} retailers accessible")
    
    if blocked_count > 0:
        print(f"\n⚠️  {blocked_count}/{total_count} retailers are blocking this IP")
        print(f"   This may be temporary or IP-specific")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
