# TCG Proxy Agent

**Backend**: `agents/agents_server.py` (routes `/tcg/*`)

## Purpose
TCG API proxy server providing CORS-enabled access to Pokemon TCG API data, bypassing browser same-origin restrictions for frontend applications.

## API Endpoints
- `GET /tcg/cards` - Proxy Pokemon TCG cards endpoint
- `GET /tcg/sets` - Proxy sets data
- `GET /tcg/products` - Proxy products endpoint
- `GET /tcg/rarities` - Proxy rarities reference

## Inputs / Outputs
**Input**: TCG API query parameters (name, set, q filter, etc.)
**Output**: Card JSON data from Pokemon TCG API with CORS headers

## Key Dependencies
- `agents_server.py` - Flask routing and caching
- Pokemon TCG API (https://api.pokemontcg.io/v2)
- In-memory market cache with 5-10min TTL
