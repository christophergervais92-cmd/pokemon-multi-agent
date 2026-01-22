# Signals and SKU Discovery System

## ✅ Implemented Features

### 1. **Signal-Based Stock Checking** ✅
**Replaces endpoint polling with event-driven signals.**

**Benefits:**
- Non-blocking requests
- Real-time updates
- Better scalability
- Reduced server load

**How it works:**
- Client sends signal request
- Server processes asynchronously
- Results sent via callback/webhook
- No blocking HTTP requests

### 2. **SKU-Based Stock Discovery** ✅
**Direct product lookup by SKU instead of search queries.**

**Benefits:**
- More accurate (exact product match)
- Faster (no search needed)
- More reliable (direct API calls)
- Better for monitoring specific products

**Supported Retailers:**
- **Target**: TCIN (Target Catalog Item Number)
- **Best Buy**: SKU
- **GameStop**: Product ID
- **Pokemon Center**: Product ID

## 📡 Signal System

### Available Signals

1. **`stock-check-requested`** - Stock check requested
2. **`stock-check-completed`** - Stock check finished
3. **`stock-check-failed`** - Stock check failed
4. **`sku-discovery-requested`** - SKU discovery requested
5. **`sku-discovery-completed`** - SKU discovery finished
6. **`stock-found`** - Product came in stock
7. **`stock-lost`** - Product went out of stock
8. **`price-changed`** - Product price changed
9. **`retailer-blocked`** - Retailer got blocked
10. **`retailer-unblocked`** - Retailer unblocked

### Usage

#### Request Stock Check via Signal
```python
from agents.scanners.stock_signals import request_stock_check

def callback(result):
    print(f"Stock check result: {result}")

# Non-blocking request
request_stock_check(
    query="pokemon 151",
    retailer="target",
    zip_code="90210",
    callback=callback
)
```

#### Watch SKU for Changes
```python
from agents.scanners.stock_signals import watch_sku

def on_stock_change(product, previous):
    if product.stock and not previous.stock:
        print(f"✅ {product.name} is now in stock!")

# Watch specific SKU
watch_sku("12345678", "target", on_stock_change)
```

#### Subscribe to All Updates
```python
from agents.scanners.stock_signals import subscribe_to_stock_updates

def handle_update(event_type, product):
    print(f"{event_type}: {product['name']}")

subscribe_to_stock_updates(handle_update)
```

## 🔍 SKU Discovery

### Direct SKU Lookup

```python
from agents.scanners.sku_discovery import lookup_by_sku

# Look up by SKU
product = lookup_by_sku("12345678", "target", zip_code="90210")

if product:
    print(f"Found: {product.name}")
    print(f"Stock: {product.stock}")
    print(f"Price: ${product.price}")
```

### Multiple SKU Lookup

```python
from agents.scanners.sku_discovery import lookup_multiple_skus

skus = [
    ("12345678", "target"),
    ("87654321", "bestbuy"),
    ("11223344", "gamestop"),
]

products = lookup_multiple_skus(skus)
```

## 🌐 HTTP API (Signal Endpoints)

### Request Stock Check via Signal
```bash
POST /signals/stock-check
{
  "query": "pokemon 151",
  "retailer": "target",
  "zip_code": "90210",
  "callback_url": "https://your-webhook.com/stock-update"
}
```

### Lookup by SKU
```bash
POST /signals/sku-lookup
{
  "sku": "12345678",
  "retailer": "target",
  "zip_code": "90210"
}
```

### Watch SKU
```bash
POST /signals/watch-sku
{
  "sku": "12345678",
  "retailer": "target",
  "callback_url": "https://your-webhook.com/stock-change"
}
```

## 🔄 Migration from Endpoints

### Old Way (Endpoints)
```python
# Blocking request
response = requests.get("http://localhost:5001/scanner/unified?q=pokemon")
result = response.json()
```

### New Way (Signals)
```python
# Non-blocking request
request_stock_check("pokemon", callback=handle_result)
```

## 📊 Benefits

| Feature | Endpoints | Signals |
|---------|-----------|---------|
| Blocking | Yes | No |
| Real-time | No | Yes |
| Scalability | Limited | High |
| Server Load | High | Low |
| Webhook Support | No | Yes |

## 🎯 Use Cases

### 1. **Real-Time Stock Monitoring**
```python
# Watch multiple SKUs
watch_sku("TCIN123", "target", notify_user)
watch_sku("SKU456", "bestbuy", notify_user)
watch_sku("PROD789", "gamestop", notify_user)
```

### 2. **Webhook Integration**
```python
# Send updates to external service
request_stock_check(
    "pokemon 151",
    callback_url="https://discord.com/api/webhooks/..."
)
```

### 3. **Batch SKU Checking**
```python
# Check multiple SKUs efficiently
skus = load_watchlist()  # From database
products = lookup_multiple_skus(skus)
```

## 🚀 Next Steps

1. **SKU Discovery Automation**
   - Crawl sitemaps to find new SKUs
   - Monitor category pages for new products
   - Extract SKUs from search results

2. **WebSocket Support**
   - Real-time bidirectional communication
   - Push updates to connected clients
   - Lower latency than webhooks

3. **SKU Database**
   - Store discovered SKUs
   - Track product metadata
   - Build product catalog

## 📝 Notes

- Signals are non-blocking (async)
- SKU lookup is more accurate than search
- Webhook callbacks supported
- Backward compatible (endpoints still work)
- Install `blinker` for signal support: `pip install blinker`
