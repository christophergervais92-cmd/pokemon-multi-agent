#!/usr/bin/env python3
"""
Test if proxy is configured and working.
Run this after setting up proxy credentials.
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_proxy():
    """Test if proxy is working."""
    proxy_url = os.environ.get("PROXY_SERVICE_URL", "")
    
    if not proxy_url:
        print("❌ No proxy configured!")
        print("\nTo set up proxy:")
        print("1. Add PROXY_SERVICE_URL to your .env file")
        print("2. Format: http://username:password@proxy.example.com:port")
        print("\nSee PROXY_SETUP_GUIDE.md for details")
        return False
    
    print("=" * 70)
    print("🔍 TESTING PROXY CONFIGURATION")
    print("=" * 70)
    print(f"Proxy URL: {proxy_url.split('@')[1] if '@' in proxy_url else 'Hidden'}\n")
    
    # Test 1: Check IP through proxy
    print("Test 1: Checking IP address through proxy...")
    try:
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        resp = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Proxy working! Your IP: {data.get('origin', 'Unknown')}")
        else:
            print(f"⚠️  Unexpected status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False
    
    # Test 2: Test blocked retailer through proxy
    print("\nTest 2: Testing blocked retailer (GameStop) through proxy...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        resp = requests.get(
            "https://www.gamestop.com/search/?q=pokemon",
            headers=headers,
            proxies=proxies,
            timeout=15
        )
        
        if resp.status_code == 200:
            print(f"✅ GameStop accessible through proxy! (Status: 200)")
            if "captcha" in resp.text.lower() or "cloudflare" in resp.text.lower():
                print("   ⚠️  But CAPTCHA detected - may need better proxy or wait")
            else:
                print("   ✅ No CAPTCHA - proxy is working well!")
        elif resp.status_code == 403:
            print(f"⚠️  Still getting 403 - proxy may not be working or IP still blocked")
        else:
            print(f"Status: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    # Test 3: Test Pokemon Center
    print("\nTest 3: Testing Pokemon Center through proxy...")
    try:
        resp = requests.get(
            "https://www.pokemoncenter.com/search/pokemon",
            headers=headers,
            proxies=proxies,
            timeout=15
        )
        
        if resp.status_code == 200:
            print(f"✅ Pokemon Center accessible! (Status: 200)")
        elif resp.status_code == 403:
            print(f"⚠️  Still getting 403")
        else:
            print(f"Status: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print("✅ Proxy is configured and working!")
    print("\nNext steps:")
    print("1. Restart your Flask server")
    print("2. Run: python3 test_blocking.py")
    print("3. All retailers should now be accessible")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    test_proxy()
