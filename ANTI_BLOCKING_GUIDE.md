# Anti-Blocking Strategies Guide

## Current Protection (Already Implemented)

✅ **User-Agent Rotation** - Different browser signatures  
✅ **Random Delays** - 1-4 seconds between requests  
✅ **Referer Spoofing** - Realistic referer headers  
✅ **Cookie Persistence** - Maintains sessions  
✅ **Adaptive Rate Limiting** - Slows down on detection  
✅ **Retry Logic** - Handles temporary blocks  

## Additional Strategies

### 1. **Use Official APIs** (Best - No Blocking)
- ✅ Target Redsky API (already using)
- ✅ Best Buy API (if you have key)
- ✅ Pokemon TCG API (already using)
- ❌ Pokemon Center - No official API (must scrape)

### 2. **Proxy Rotation** (High Protection)
**Free Options:**
- Scrape public proxy lists (unreliable)
- Use VPN rotation (manual)

**Paid Options (Recommended):**
- **Bright Data** ($500/month) - Residential IPs
- **Oxylabs** ($300/month) - Datacenter + Residential
- **Smartproxy** ($75/month) - Budget option
- **ProxyMesh** ($25/month) - Basic rotation

**Setup:**
```bash
export PROXY_SERVICE_URL="http://user:pass@proxy.example.com:8080"
```

### 3. **StealthSession Integration** (Medium Protection)
- Better headers (Sec-Fetch-*, DNT)
- Cookie management
- Realistic request patterns
- **Already available, just need to use it**

### 4. **Browser Automation** (High Protection, Slower)
- Selenium with undetected-chromedriver
- Playwright with stealth plugins
- Mimics real browser behavior
- **Trade-off:** 5-10x slower

### 5. **CAPTCHA Solving Services** (When Needed)
- **2Captcha** ($2.99/1000 solves)
- **Anti-Captcha** ($1.00/1000 solves)
- **CapSolver** ($0.80/1000 solves)
- Only use when absolutely necessary

### 6. **Request Distribution** (Reduce Load)
- Spread requests across time
- Cache aggressively (30s → 5min for stable data)
- Batch requests when possible

### 7. **IP Rotation Strategies**
- **Residential Proxies** - Best (looks like home users)
- **Datacenter Proxies** - Cheaper (easier to detect)
- **Mobile Proxies** - Expensive (hardest to detect)

## Recommended Setup (Free)

1. **Use StealthSession** (already have it)
2. **Increase delays** (2-5 seconds)
3. **Cache longer** (5 minutes)
4. **Use official APIs** when possible

## Recommended Setup (Paid - $25-75/month)

1. **ProxyMesh or Smartproxy** - Basic rotation
2. **StealthSession** - Better headers
3. **Adaptive rate limiting** - Auto-adjust
4. **CAPTCHA solving** - Only when needed

## Best Practices

### ✅ DO:
- Respect robots.txt
- Cache results aggressively
- Use official APIs when available
- Rotate IPs (if using proxies)
- Add realistic delays
- Monitor for blocks and slow down

### ❌ DON'T:
- Scrape too frequently (max 1 request/2 seconds)
- Ignore rate limit headers (429 errors)
- Use same IP for all requests
- Scrape during peak hours
- Ignore CAPTCHAs (solve or stop)

## Legal Considerations

- **Public data** - Generally OK to scrape
- **Terms of Service** - Check each site's ToS
- **Rate limits** - Stay within reasonable bounds
- **Personal use** - Lower risk than commercial

## Current Risk Level

**Without Proxies:** Medium-High (can get IP banned)  
**With Free Proxies:** Medium (unreliable)  
**With Paid Proxies:** Low (residential IPs)  
**With StealthSession:** Medium-Low (better headers)
