# Proxy Setup Guide - Quick Start

## Step 1: Sign Up for Proxy Service

### Option A: Smartproxy (Recommended - $75/month, 7-day free trial)
1. Go to: https://smartproxy.com/
2. Click "Start Free Trial"
3. Sign up with email
4. Choose "Residential Proxies" plan
5. Get your credentials from dashboard:
   - Username
   - Password
   - Endpoint (usually: `gate.smartproxy.com:10000`)

### Option B: ProxyMesh (Budget - $25/month, 14-day money-back guarantee)
1. Go to: https://proxymesh.com/
2. Click "Sign Up"
3. Choose "Residential Proxies" plan
4. Get your credentials:
   - Username
   - Password
   - Endpoint (usually: `rotating-residential.proxymesh.com:31280`)

### Option C: ScraperAPI (Easy - $49/month, 5,000 free requests)
1. Go to: https://www.scraperapi.com/
2. Sign up for free account
3. Get API key from dashboard
4. Uses different format (API-based, not proxy)

## Step 2: Get Your Credentials

After signing up, you'll get:
- **Username** (or API key for ScraperAPI)
- **Password** (if applicable)
- **Endpoint/Proxy URL** (format: `http://username:password@proxy.example.com:port`)

## Step 3: Configure in Your App

### For Smartproxy or ProxyMesh:

1. Open your `.env` file (or create it from `env.example`)

2. Add these lines:
```bash
# Proxy Configuration
PROXY_SERVICE_URL=http://your_username:your_password@gate.smartproxy.com:10000
PROXY_SERVICE_KEY=
```

**OR for ProxyMesh:**
```bash
PROXY_SERVICE_URL=http://your_username:your_password@rotating-residential.proxymesh.com:31280
PROXY_SERVICE_KEY=
```

3. Replace:
   - `your_username` with your actual username
   - `your_password` with your actual password

### For ScraperAPI (Different Format):

```bash
# ScraperAPI uses API key, not proxy URL
SCRAPERAPI_KEY=your_api_key_here
```

## Step 4: Test the Proxy

Run the blocking test again:
```bash
python3 test_blocking.py
```

You should see:
- ✅ All retailers accessible
- No more 403 errors
- Faster response times

## Step 5: Restart Your Server

After adding proxy config:
```bash
# Restart your Flask server
# The proxy will be used automatically
```

## Troubleshooting

### Proxy not working?
1. Check credentials are correct
2. Verify proxy endpoint URL
3. Test proxy manually:
   ```bash
   curl -x http://username:password@proxy.example.com:port https://httpbin.org/ip
   ```

### Still getting blocked?
1. Make sure proxy is enabled in code
2. Check proxy service dashboard for usage/limits
3. Try different proxy endpoint (some services have multiple)

### Free trial expired?
- Most services auto-renew
- Cancel before trial ends if you don't want to pay
- Or upgrade to paid plan

## Cost Comparison

| Service | Monthly Cost | Trial | Best For |
|---------|-------------|-------|----------|
| Smartproxy | $75 | 7 days free | Most users |
| ProxyMesh | $25 | 14-day guarantee | Budget users |
| ScraperAPI | $49 | 5,000 free requests | Easy setup |

## Next Steps

1. ✅ Sign up for trial
2. ✅ Get credentials
3. ✅ Add to `.env` file
4. ✅ Test with `test_blocking.py`
5. ✅ Enjoy unblocked scraping!
