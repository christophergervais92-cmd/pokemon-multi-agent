# 🎴 LO TCG - Pokemon Multi-Agent System

A **high-speed, stealth** multi-agent system for scanning Pokemon card stock across retailers, analyzing prices, and auto-buying deals.

## ⚡ Key Features

- **Stealth Scanning** - User-agent rotation, request jitter, anti-detection
- **ZIP Code Local Alerts** - Get alerts for stock at stores near you
- **Multi-User Discord Bot** - Each member gets personalized watchlists & auto-buy
- **1-Minute Scan Intervals** - Lightning fast stock detection
- **6 Retailer Support** - Target, Walmart, Best Buy, GameStop, Costco, **Pokemon Center**
- **CAPTCHA Detection** - Detects and handles bot protection (CloudFlare, DataDome, reCAPTCHA)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RETAILER SCANNERS                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │  Target  │ │ Walmart  │ │ Best Buy │ │ GameStop │ │ Costco │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       └────────────┴────────────┴────────────┴───────────┘      │
│                              ↓                                   │
│                    ┌─────────────────┐                          │
│                    │  Merge Results  │                          │
│                    └────────┬────────┘                          │
└─────────────────────────────┼───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING AGENTS                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │  Price Agent   │→ │ Grading Agent  │→ │ Auto-Buy Agent │     │
│  │ (Market Data)  │  │   (ROI Calc)   │  │  (Purchases)   │     │
│  └────────────────┘  └────────────────┘  └────────────────┘     │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DISCORD NOTIFICATIONS                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐ │
│  │  Stock Alert   │  │   Deal Alert   │  │ Purchase Confirm   │ │
│  └────────────────┘  └────────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
pokemon_multi_agent/
├── agents/
│   ├── scanners/               # Retailer-specific scanners
│   │   ├── target_scanner.py
│   │   ├── walmart_scanner.py
│   │   ├── bestbuy_scanner.py
│   │   ├── gamestop_scanner.py
│   │   └── costco_scanner.py
│   ├── buyers/                 # Auto-buy functionality
│   │   └── auto_buyer.py
│   ├── graders/                # AI visual grading
│   │   ├── visual_grading_agent.py
│   │   └── grading_standards.py
│   ├── market/                 # Market analysis
│   │   └── market_analysis_agent.py
│   ├── discord_bot/            # 🆕 Multi-user Discord bot
│   │   ├── bot.py              # Main Discord bot with slash commands
│   │   ├── user_db.py          # User database (watchlists, payments)
│   │   └── notifier.py         # Real-time notification service
│   ├── price_agent.py          # Market price analysis
│   ├── grading_agent.py        # ROI & grading evaluation
│   ├── db.py                   # SQLite database layer
│   └── agents_server.py        # Flask HTTP server
├── workflows/
│   └── pokemon_multi_agent_workflow.json  # n8n workflow
├── config.json                 # Configuration file
└── README.md
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Core dependencies
pip install flask requests

# For Discord bot with multi-user support
pip install discord.py aiohttp cryptography
```

### 2. Set Environment Variables

```bash
export POKEMON_PRICE_API_URL="https://www.pokemonpricetracker.com/api/v2/cards"
export POKEMON_PRICE_API_KEY="your_api_key_here"
export DISCORD_CHANNEL_ID="your_discord_channel_id"

# Optional: For real auto-buy (disabled by default)
export POKEMON_AUTOBUY_ENABLED="false"
export POKEMON_SIMULATION_MODE="true"
export POKEMON_MAX_PURCHASE_PRICE="100"
export POKEMON_MAX_DAILY_SPEND="500"
```

### 3. Start the Agent Server

```bash
cd pokemon_multi_agent
python3 agents/agents_server.py
```

You should see:
```
🎴 Pokemon Multi-Agent Server Starting...
📡 Endpoints available at http://127.0.0.1:5000
```

### 4. Import Workflow into n8n

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows → Import from file**
3. Select `workflows/pokemon_multi_agent_workflow.json`
4. Click **Execute Workflow** to test

## 🔌 API Endpoints

### Retailer Scanners
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scanner/target` | POST | Scan Target for Pokemon cards |
| `/scanner/walmart` | POST | Scan Walmart |
| `/scanner/bestbuy` | POST | Scan Best Buy |
| `/scanner/gamestop` | POST | Scan GameStop |
| `/scanner/costco` | POST | Scan Costco |
| `/scanner/all` | POST | Scan ALL retailers at once |

### Processing Agents
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent/price` | POST | Analyze prices (needs product JSON) |
| `/agent/grading` | POST | Evaluate ROI & grading potential |
| `/agent/autobuy` | POST | Process auto-buy decisions |

### 🆕 AI Visual Grading
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/grader/analyze` | POST | Submit card image for AI grading prediction |
| `/grader/standards` | GET | Get PSA/CGC/Beckett grading criteria reference |
| `/grader/batch` | POST | Grade multiple cards at once |

### Pipelines & Utilities
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pipeline/full` | POST | Run entire pipeline at once |
| `/health` | GET | Health check |
| `/agents` | GET | List all available endpoints |

## 📊 n8n Workflow Nodes

The workflow includes **18+ nodes**:

**Scanning:**
1. **⏰ Schedule Trigger** - Runs every **1 minute** ⚡
2. **🎯 Target Scanner** - HTTP Request to `/scanner/target`
3. **🏪 Walmart Scanner** - HTTP Request to `/scanner/walmart`
4. **💻 Best Buy Scanner** - HTTP Request to `/scanner/bestbuy`
5. **🎮 GameStop Scanner** - HTTP Request to `/scanner/gamestop`
6. **📦 Costco Scanner** - HTTP Request to `/scanner/costco`
7. **🔀 Merge All Results** - Combines all scanner outputs

**Processing:**
8. **💰 Price Analysis Agent** - Adds market pricing
9. **📊 Grading & ROI Agent** - Evaluates deals
10. **🛒 Auto-Buy Agent** - Processes single-user purchases

**Discord Notifications:**
11. **📢 Discord: Stock Alert** - Summary notification
12. **🤔 Has Deals?** - Checks for deal alerts
13. **🔥 Discord: Deal Alerts** - Deal notifications
14. **💳 Has Purchases?** - Checks for purchases
15. **✅ Discord: Purchase Confirmation** - Purchase notifications

**Multi-User (NEW!):**
16. **👥 Multi-User Notify** - Sends personalized DMs based on watchlists
17. **👥 Multi-User Auto-Buy** - Purchases for all eligible users
18. **🎉 Discord: User Purchases** - Reports multi-user purchases

## 🔒 Stealth Scanning (Anti-Detection)

The system includes advanced anti-detection to avoid IP bans:

| Feature | Description |
|---------|-------------|
| **User-Agent Rotation** | Mimics Chrome, Safari, Firefox, Edge across Windows, Mac, iOS, Android |
| **Request Jitter** | Random delays (1.5-4 sec) between requests to appear human |
| **Header Spoofing** | Realistic Accept-Language, Referer, Sec-Fetch headers |
| **Adaptive Rate Limiting** | Slows down automatically if detecting rate limits |
| **Proxy Support** | Optional residential proxy rotation (Bright Data, Oxylabs) |

### Configure Stealth Settings

```bash
# Optional: Use proxy rotation for extra protection
export PROXY_SERVICE_URL="http://your-proxy-service.com:port"

# Adjust scan delays (default: 1.5-4 seconds)
export SCAN_MIN_DELAY="1.5"
export SCAN_MAX_DELAY="4.0"
export SCAN_MAX_RPM="15"
```

## 🔐 CAPTCHA Detection & Handling

The system detects various bot protection systems:

| Protection | Detection | Strategy |
|------------|-----------|----------|
| **CloudFlare** | CF-Ray headers, challenge pages | Wait + retry, session rotation |
| **DataDome** | dd_p cookies, captcha.datadome.co | Slow down, behavioral analysis |
| **PerimeterX** | _px cookies, px-captcha | Session rotation, change IP |
| **reCAPTCHA v2/v3** | g-recaptcha class, grecaptcha | Manual solve or service |
| **hCaptcha** | h-captcha class | Manual solve |
| **Akamai** | _abck, bm_sz cookies | Fingerprint rotation |

### API Endpoints

```bash
# Check CAPTCHA stats
curl http://127.0.0.1:5001/scanner/captcha-stats

# Check security config
curl http://127.0.0.1:5001/security/config
```

### When CAPTCHA is Detected

1. System automatically slows down
2. Exponential backoff applied
3. Alerts logged for monitoring
4. Falls back to cached/demo data

## 🛡️ Security Features

| Feature | Description |
|---------|-------------|
| **Input Sanitization** | All inputs validated and sanitized |
| **SQL Injection Prevention** | Query parameters cleaned |
| **XSS Prevention** | HTML entities escaped |
| **Rate Limiting** | 100 requests/minute default |
| **Anonymized Logging** | IPs hashed for privacy |
| **API Key Support** | Optional auth for endpoints |

### Enable API Key Protection

```bash
export POKEMON_API_KEY="your-secret-key"
export POKEMON_API_KEY_REQUIRED="true"
```

## 📍 ZIP Code Local Scanning

Users can set their location to get alerts only for nearby stores:

### How It Works

1. User sets ZIP code via `/setlocation 90210`
2. System finds nearest stores within radius (default 25 miles)
3. Scans inventory at those specific stores
4. Alerts include store address and distance

### API Endpoint

```bash
curl -X POST http://127.0.0.1:5001/scanner/local \
  -H "Content-Type: application/json" \
  -d '{"zip_code": "90210", "search": "pokemon 151", "radius": 25}'
```

Returns:
```json
{
  "zip_code": "90210",
  "total_stores_checked": 15,
  "total_in_stock": 8,
  "retailers": {
    "Target": {
      "in_stock": 2,
      "results": [
        {
          "product_name": "Pokemon 151 ETB",
          "price": 49.99,
          "store_address": "123 Main St, Beverly Hills, CA",
          "distance_miles": 2.3,
          "url": "https://target.com/..."
        }
      ]
    }
  }
}
```

## 👥 Multi-User Discord Bot

The system includes a full-featured Discord bot that allows **multiple users** to:

- ✅ Register and manage their own accounts
- 📋 Create personalized watchlists
- 💳 Store encrypted payment info for auto-buy
- 🔔 Get instant personalized deal notifications
- 🛒 Auto-buy when deals match their watchlist

### Discord Slash Commands

| Command | Description |
|---------|-------------|
| `/register` | Create your account |
| `/setlocation <zip>` | Set your ZIP for local stock alerts |
| `/location` | View your location settings |
| `/scan <search>` | Manually scan nearby stores |
| `/settings` | View/update notifications, limits, auto-buy |
| `/watchlist add` | Add an item to your watchlist |
| `/watchlist view` | View your watchlist |
| `/watchlist remove` | Remove an item |
| `/payment setup` | Get payment setup instructions |
| `/payment add` | Add retailer payment info |
| `/payment status` | Check which retailers are set up |
| `/history` | View your purchase history |
| `/help` | Show all commands |

### Start the Discord Bot

```bash
# Set your bot token (get from Discord Developer Portal)
export DISCORD_BOT_TOKEN="your_discord_bot_token"
export DISCORD_GUILD_ID="your_server_id"  # Optional, for faster command sync

# Optional: Encryption key for payment data
export POKEMON_ENCRYPTION_KEY="your_32_char_fernet_key"

# Start the bot
python3 agents/discord_bot/bot.py
```

### How Multi-User Auto-Buy Works

1. **User registers** via `/register`
2. **User sets up watchlist** via `/watchlist add Pokemon 151 UPC target_price:120`
3. **User adds payment** via `/payment add retailer:Target email:user@email.com`
4. **User enables auto-buy** via `/settings autobuy:true max_price:150`
5. **System scans every minute** and checks each user's watchlist
6. **When a deal is found**, users are notified instantly via DM
7. **If auto-buy is enabled**, the system purchases for them automatically

### Multi-User API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/notify` | POST | Send alerts to users by watchlist |
| `/users/autobuy` | POST | Execute auto-buy for all eligible users |
| `/users/stats` | GET | Get user registration statistics |

## 🔬 AI Visual Grading

The system includes an AI-powered visual grading agent that analyzes card images and predicts PSA, CGC, and Beckett grades.

### How It Works

1. **Submit a card image** (base64 or URL)
2. **AI analyzes** centering, corners, edges, and surface
3. **Returns predicted grades** for PSA, CGC, and Beckett
4. **Calculates ROI** to determine if grading is worth it

### Grading Criteria Used

Based on official standards from:

- **PSA (Professional Sports Authenticator)** - 1-10 scale
  - PSA 10 Gem Mint: 55/45 centering, perfect corners/edges/surface
  - PSA 9 Mint: 60/40 centering, one minor flaw allowed
  
- **CGC (Certified Guaranty Company)** - 1-10 scale with subgrades
  - CGC 10 Pristine: Perfect in every way
  - CGC 9.5 Gem Mint: Virtually perfect
  
- **BGS/Beckett** - 1-10 with subgrades and labels
  - BGS 10 Black Label: All four subgrades = 10 (extremely rare)
  - BGS 9.5 Gold Label: No subgrade below 9

### Example API Call

```bash
curl -X POST http://127.0.0.1:5000/grader/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/my-card.jpg",
    "raw_value": 25.00,
    "card_name": "Charizard VMAX"
  }'
```

### Response

```json
{
  "success": true,
  "card_name": "Charizard VMAX",
  "subgrades": {
    "centering": 9.0,
    "corners": 8.5,
    "edges": 9.0,
    "surface": 8.5
  },
  "predicted_grades": {
    "PSA": 8,
    "CGC": 8.5,
    "BGS": 8.5
  },
  "value_analysis": {
    "PSA": {
      "graded_value": 62.50,
      "grading_cost": 25,
      "net_value": 37.50,
      "worth_grading": true
    }
  },
  "worth_grading": true,
  "recommendations": "Consider PSA for Pokemon cards"
}
```

### Enable Real AI Analysis

For real AI-powered analysis, set one of these API keys:

```bash
# OpenAI GPT-4 Vision
export OPENAI_API_KEY="your_openai_key"

# OR Anthropic Claude Vision
export ANTHROPIC_API_KEY="your_anthropic_key"
```

Without an API key, the system runs in **demo mode** with simulated grading results.

## ⚙️ Configuration

Edit `config.json` to customize:

- **Watchlist**: Which Pokemon sets/products to track
- **Price thresholds**: What % discount = good deal
- **Auto-buy settings**: Enable/disable, limits, retailers
- **Discord notifications**: Channel IDs, mentions
- **Scan schedule**: How often to check

## 🔒 Auto-Buy Safety

Auto-buy is **disabled by default** and runs in **simulation mode**.

To enable real purchases:

1. Set retailer credentials in env vars:
   ```bash
   export TARGET_USERNAME="your_email"
   export TARGET_PASSWORD="your_password"
   # ... same for other retailers
   ```

2. Enable auto-buy:
   ```bash
   export POKEMON_AUTOBUY_ENABLED="true"
   export POKEMON_SIMULATION_MODE="false"
   ```

3. Set spending limits:
   ```bash
   export POKEMON_MAX_PURCHASE_PRICE="100"
   export POKEMON_MAX_DAILY_SPEND="500"
   ```

## 📝 License

MIT
