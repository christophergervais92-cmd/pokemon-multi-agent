# Scanner Agent

**Backend**: `agents/scanners/stock_checker.py`

## Purpose
Multi-retailer stock scanner for Pokemon products with real-time availability tracking across Target, Walmart, Best Buy, GameStop, Pokemon Center, and TCGPlayer.

## API Endpoints
- `POST /live/scanner/start` - Start background stock scanning
- `POST /live/scanner/stop` - Stop background scanner
- `GET /live/history` - Retrieve scan history

## Inputs / Outputs
**Input**: Configured retail sources and SKU targets
**Output**: Stock status, availability timestamps, price data per retailer

## Key Dependencies
- `scanners/sku_builder.py` - SKU construction
- `scanners/sku_discovery.py` - Product discovery
- `scanners/stock_signals.py` - Alert signal generation
- `stealth/anti_detect.py` - Anti-blocking measures
