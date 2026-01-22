# Automated SKU Discovery and Alert System

## ✅ Implemented Features

### 1. **Daily SKU List Builder** ✅
**Automatically discovers and builds Pokemon SKU database daily.**

**Discovery Methods:**
- **Sitemap crawling** - Extracts SKUs from retailer sitemaps
- **Category pages** - Scans product category pages
- **Search results** - Discovers SKUs from search queries

**Features:**
- Auto-deduplication (no duplicate SKUs)
- Auto-categorization (booster_box, etb, booster_pack, etc.)
- Set name detection (151, Paldean Fates, etc.)
- Confidence scoring (0-1)
- Persistent database (survives restarts)

**Schedule:** Runs daily at 2:00 AM

### 2. **Auto-Deduplication & Categorization** ✅
**Automatically deduplicates and categorizes stock results.**

**Deduplication:**
- Removes duplicate products (same SKU/retailer)
- Prefers in-stock over out-of-stock
- Prefers higher confidence
- Prefers lower price (better deals)

**Categorization:**
- **booster_box** - Booster boxes (36 packs)
- **etb** - Elite Trainer Boxes
- **booster_bundle** - 6-pack bundles
- **booster_pack** - Individual packs
- **collection_box** - Collection boxes
- **tin** - Tins
- **single_card** - Individual cards
- **other** - Other products

**Set Detection:**
- Automatically detects set names (151, Paldean Fates, etc.)
- Extracts from product names
- Links SKUs to sets

### 3. **Alert Ingestion & Signal Conversion** ✅
**Automatically ingests alerts and converts them to signals.**

**Supported Sources:**
- Reddit posts
- Twitter/X posts
- Discord messages
- Webhook alerts
- Custom alerts

**Processing:**
- Extracts SKUs from alert text
- Extracts search queries
- Categorizes alerts (stock_alert, price_alert, etc.)
- Converts to stock check signals
- Auto-triggers SKU lookups
- Emits stock_found/stock_lost signals

## 🔄 How It Works

### Daily SKU Build Flow

```
1. Scheduler triggers at 2:00 AM
2. For each retailer:
   - Crawl sitemap → Extract SKUs
   - Scan category pages → Extract SKUs
   - Search queries → Extract SKUs
3. Deduplicate (same SKU/retailer = one entry)
4. Categorize (booster_box, etb, etc.)
5. Detect set names
6. Save to database
```

### Alert Ingestion Flow

```
1. Alert received (Reddit/Twitter/Discord/Webhook)
2. Extract SKUs from text (regex patterns)
3. Extract search query (keyword matching)
4. If SKU found → Direct lookup → Emit signal
5. If query found → Stock check → Emit signal
6. Categorize alert type
7. Store in history
```

### Stock Deduplication Flow

```
1. Stock check returns products
2. For each product:
   - Categorize (booster_box, etb, etc.)
   - Detect set name
   - Add to SKU database (if has SKU)
3. Deduplicate products:
   - Same SKU/retailer = one product
   - Prefer in-stock
   - Prefer higher confidence
   - Prefer lower price
4. Return deduplicated results
```

## 📊 SKU Database

### Statistics
```bash
GET /sku/stats
```

Returns:
- Total SKUs
- SKUs by retailer
- SKUs by category
- SKUs by set

### List SKUs
```bash
GET /sku/list?retailer=target
GET /sku/list?category=booster_box
GET /sku/list?set=151
```

## 🚨 Alert Ingestion

### Ingest Alert
```bash
POST /alerts/ingest
{
  "source": "reddit",
  "title": "Pokemon 151 in stock at Target!",
  "content": "Just saw it at target.com/p/-/A-12345678",
  "url": "https://reddit.com/r/pokemon/..."
}
```

**Auto-processing:**
1. Extracts SKU: `12345678` (Target)
2. Looks up product by SKU
3. Emits `stock_found` signal if in stock
4. Returns processing results

## ⏰ Scheduler

### Daily Jobs
- **2:00 AM** - SKU list build
- **Every 5 minutes** - Check watched SKUs (if implemented)

### Manual Trigger
```bash
POST /sku/build-daily?force=true
```

## 📈 Benefits

| Feature | Benefit |
|---------|---------|
| Daily SKU Build | Always up-to-date product list |
| Auto-Deduplication | Clean results, no duplicates |
| Auto-Categorization | Organized by product type |
| Alert Ingestion | Real-time stock alerts |
| Signal Conversion | Event-driven updates |

## 🎯 Usage Examples

### Check SKU Database
```python
from agents.scanners.sku_builder import SKUDatabase

db = SKUDatabase()
skus = db.get_by_category("booster_box")
print(f"Found {len(skus)} booster boxes")
```

### Ingest Alert
```python
from agents.scanners.alert_ingestion import ingest_alert

result = ingest_alert("reddit", {
    "title": "Pokemon 151 restock!",
    "content": "Check target.com/p/-/A-12345678",
})

print(result)  # Shows extracted SKUs and signals triggered
```

### Manual SKU Build
```python
from agents.scanners.sku_builder import build_sku_list_daily

result = build_sku_list_daily(force=True)
print(f"Built {result['total_skus']} SKUs")
```

## 📝 Notes

- SKU database persists across restarts
- Daily build runs automatically at 2 AM
- Alerts are deduplicated (same alert = processed once)
- Stock results auto-categorized and deduplicated
- All alerts converted to signals automatically
