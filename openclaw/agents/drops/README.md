# Drops Agent

**Backend**: `agents/agents_server.py` (routes `/drops/*`)

## Purpose
Aggregates Pokemon TCG product drop intel from Reddit, PokeBeach, Twitter/X, Instagram, and TikTok for upcoming release alerts.

## API Endpoints
- `GET /drops/reddit` - Fetch Reddit TCG drop discussions
- `GET /drops/pokebeach` - PokeBeach set release intel
- `GET /drops/twitter` - Twitter/X TCG mentions
- `GET /drops/instagram` - Instagram Pokemon drops
- `GET /drops/tiktok` - TikTok unboxing trends
- `GET /drops/all` - Combined drop intel feed

## Inputs / Outputs
**Input**: Source type, optional search filters
**Output**: Drop announcements, release dates, retailer availability, community sentiment

## Key Dependencies
- `agents_server.py` - Intel aggregation routing
- BeautifulSoup4 for web scraping
- Reddit/social media APIs (unauthenticated crawling)
