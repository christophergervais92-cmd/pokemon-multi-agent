# PokeAgent - Agent Registry

## Backend Agents (`agents/`)

### Scanner Agent
**Module**: `agents/scanners/stock_checker.py`
**API**: `POST /scanner/unified`
**Purpose**: Checks product availability across major retailers (Target, Walmart, Best Buy, GameStop, Pokemon Center, Amazon, Barnes & Noble, Costco).
**Features**: SKU discovery, delta-based scanning, browser-based fallback, anti-blocking stealth layer.
**Dependencies**: `agents/stealth/`, `agents/scanners/sku_builder.py`, `agents/scanners/stock_signals.py`

### Price Agent
**Module**: `agents/price_agent.py`, `agents/market/graded_prices.py`
**API**: `GET /prices/card/{name}`
**Purpose**: Fetches raw and graded (PSA/CGC/BGS) prices from market sources. Provides price history and trend data.
**Dependencies**: `agents/market/price_trends.py`

### Market Agent
**Module**: `agents/market/market_analysis_agent.py`, `agents/market/flip_calculator.py`
**API**: `GET /market/analysis/{card}`, `POST /market/flip`
**Purpose**: ROI calculations for grading decisions, market trend analysis, investment recommendations.

### Grading Agent
**Module**: `agents/grading_agent.py`, `agents/graders/visual_grading_agent.py`
**API**: `POST /grader/analyze`
**Purpose**: AI-powered card condition assessment. Accepts card images (base64 or URL), returns predicted grades (PSA/CGC/BGS), subgrades, defect list, and estimated values.
**Dependencies**: Vision model API, `agents/graders/grading_standards.py`

### Vision Agent
**Module**: `agents/vision/card_scanner.py`
**Purpose**: Card identification from photos. Extracts card name, set, number from images.

### Notifications Agent
**Module**: `agents/notifications/multi_channel.py`
**API**: `POST /notify`
**Purpose**: Sends alerts via Discord webhooks, push notifications, and in-app toasts when stock is found or prices change.

### TCG Proxy
**Module**: Built into `agents_server.py`
**API**: `GET /api/tcg/*`
**Purpose**: Proxies requests to `api.pokemontcg.io` to avoid CORS restrictions and share API keys.

### Drops Agent
**Module**: Intel aggregation in `agents_server.py`
**API**: `GET /drops/intel/*`
**Purpose**: Aggregates release intel from Reddit, PokeBeach, Twitter/X, Instagram, and TikTok.

### Assistant Agent
**Module**: `agents_server.py` + `/ai/status`
**Purpose**: AI-powered Q&A about TCG investing, grading decisions, and market strategy.

## Frontend Tab Modules (`dashboard/js/tabs/`)

| Tab | File | Key Functions |
|-----|------|---------------|
| Drops & Intel | `drops.js` | `initDrops()`, `loadLiveIntel()`, `renderUpcomingDrops()` |
| Vending Map | `vending.js` | `initVendingMap()`, `searchVendingMap()` |
| Stock Checker | `stock.js` | `findStock()`, `quickSearch()`, `renderStockResults()` |
| Monitors | `monitors.js` | `initMonitors()`, `loadMonitors()`, `createMonitorTask()` |
| Set Database | `database.js` | `loadAllSets()`, `loadSetChaseCards()`, `showChaseCardDetail()` |
| Card Lookup | `cards.js` | `lookupCard()`, `searchCardsOrProducts()`, `displayCardDetail()` |
| Flip Calculator | `flip.js` | `calculateFlip()`, `renderFlipResults()` |
| Card Grading | `grading.js` | `gradeCard()`, `renderGradeResults()` |
| AI Assistant | `assistant.js` | `askAI()`, `addAutoBuyRule()` |
| Portfolio | `portfolio.js` | `addToPortfolio()`, `renderPortfolio()` |
| Analytics | `analytics.js` | `logPurchase()`, `renderAnalyticsStats()`, `runBacktest()` |
| Settings | `settings.js` | `loadSettings()`, `saveZip()`, `connectStripe()` |
