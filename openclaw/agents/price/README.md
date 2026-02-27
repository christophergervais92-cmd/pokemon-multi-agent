# Price Agent

**Backend**: `agents/price_agent.py` + `agents/market/graded_prices.py`

## Purpose
Real-time card pricing engine fetching raw and graded card prices from PokemonPriceTracker, TCGPlayer, eBay, and Pokemon TCG API.

## API Endpoints
- `POST /price/estimate` - Get market price estimate for a card
- `POST /price/graded` - Fetch PSA/CGC/BGS graded card prices

## Inputs / Outputs
**Input**: Card name, set name, condition/grade
**Output**: Raw price, graded prices (PSA 10/9/8/7), market confidence scores

## Key Dependencies
- `market/graded_prices.py` - Multi-source price aggregation
- `stealth/anti_detect.py` - Request obfuscation
- `db.py` - Price snapshot caching
