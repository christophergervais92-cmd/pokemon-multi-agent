# Vision Agent

**Backend**: `agents/vision/card_scanner.py`

## Purpose
AI photo card scanner using GPT-4/Claude Vision to identify Pokemon cards from images and return market prices plus grade estimates.

## API Endpoints
- `POST /vision/scan` - Identify card from image
- `POST /vision/batch-scan` - Scan multiple card photos
- `GET /vision/demo` - Demo mode without API keys

## Inputs / Outputs
**Input**: Card image (base64, URL, or file upload)
**Output**: Card name/set/number, rarity, raw price, graded prices (PSA 9/10)

## Key Dependencies
- `market/graded_prices.py` - Price lookup by card ID
- `stealth/anti_detect.py` - Request obfuscation
- OpenAI GPT-4 Vision or Anthropic Claude Vision APIs
