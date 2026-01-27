# Orderbook Configuration - Charizard Base Set PSA 10 Fix

## Problem
When viewing "Charizard Base Set PSA 10" in the orderbook, the system was showing **Celebrations Charizard** sales ($400-$600) instead of **Base Set Charizard** sales (~$42,000). This happened because (1) the matching logic only checked `card_name` and `grade`, but ignored `set_name`, and (2) Celebrations reprints often include "Base Set" in the title, so we also exclude titles containing "celebration" or "25th" when matching vintage Base Set.

## Solution

### Backend Changes (✅ Complete)

1. **Fixed `_listing_matches_asset` in `agents/market/graded_prices.py`**
   - Now requires `set_name` significant words in listing titles for slabs
   - "Charizard Base Set PSA 10" now requires "base" and "set" in the title
   - **Celebrations exclusion:** When matching vintage Base Set, titles containing "celebration" or "25th" are excluded (Celebrations reprints often say "Base Set" in the title)

2. **Enhanced `search_ebay_sold` in `agents/market/graded_prices.py`**
   - Added optional `set_name` parameter
   - Search query now includes set name: `"Charizard Base Set PSA 10 pokemon"`
   - Filters results by set name before returning

3. **Updated `get_orderbook_sources` in `agents/market/graded_prices.py`**
   - Passes `set_name` to `search_ebay_sold` for slabs

4. **Added Asset Configuration in `agents/agents_server.py`**
   - Created `ASSET_CONFIG` dictionary mapping `asset_id` → `{card_name, set_name, category, grade}`
   - Added `/market/asset/<asset_id>` endpoint to get asset metadata
   - Updated `/market/orderbook` to accept `asset_id` parameter (auto-looks up metadata)

### Frontend Changes (📝 Required)

Update your frontend (e.g., `preview.html` in `pokemon_perp_dex`) to use the new `asset_id` parameter:

**Before:**
```javascript
// Missing set_name - causes wrong matches!
const params = new URLSearchParams({
    card_name: 'Charizard',
    category: 'slabs',
    grade: 'PSA 10'
});
```

**After:**
```javascript
// Use asset_id - automatically includes set_name!
const response = await fetch(
    `${ORACLE_URL}/market/orderbook?asset_id=charizard-base-psa10`
);
```

See `ORDERBOOK_FRONTEND_EXAMPLE.js` for complete examples.

## Asset Configuration

The following assets are configured in the backend:

| Asset ID | Card Name | Set Name | Category | Grade |
|----------|-----------|----------|----------|-------|
| `charizard-base-psa10` | Charizard | Base Set | slabs | PSA 10 |
| `umbreon-vmax-alt-psa10` | Umbreon VMAX | Evolving Skies | slabs | PSA 10 |
| `charizard-vmax-rainbow-psa10` | Charizard VMAX | Champion's Path | slabs | PSA 10 |
| `charizard-ex-sar-raw` | Charizard ex | Obsidian Flames | raw | - |
| `moonbreon-raw` | Umbreon V | Evolving Skies | raw | - |
| `pikachu-vmax-rainbow-raw` | Pikachu VMAX | Vivid Voltage | raw | - |
| `151-upc` | - | - | sealed | - |
| `evolving-skies-bb` | - | - | sealed | - |
| `crown-zenith-etb` | - | - | sealed | - |

## API Endpoints

### Get Asset Metadata
```
GET /market/asset/<asset_id>
```
Returns: `{success: true, asset_id: "...", card_name: "...", set_name: "...", category: "...", grade: "..."}`

### Get Orderbook (with asset_id)
```
GET /market/orderbook?asset_id=charizard-base-psa10
```
Automatically uses the asset configuration to fetch orderbook data with correct `set_name`.

### Get Orderbook (explicit params)
```
GET /market/orderbook?card_name=Charizard&set_name=Base Set&category=slabs&grade=PSA 10
```
Still works for custom queries.

## Testing

1. Restart the agents server
2. Test the asset metadata endpoint:
   ```bash
   curl http://localhost:5001/market/asset/charizard-base-psa10
   ```
3. Test the orderbook with asset_id:
   ```bash
   curl "http://localhost:5001/market/orderbook?asset_id=charizard-base-psa10"
   ```
4. Verify that eBay transactions only show Base Set Charizard (not Celebrations)

## Next Steps

1. Update frontend `fetchOrderBook()` to use `asset_id` parameter
2. Add more assets to `ASSET_CONFIG` as needed
3. Clear orderbook cache (or wait 5 minutes) to see fresh results
