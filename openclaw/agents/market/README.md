# Market Agent

**Backend**: `agents/market/market_analysis_agent.py` + `agents/market/flip_calculator.py`

## Purpose
Pokemon TCG market analysis with ROI/flip calculations, grading cost breakdowns, and market sentiment analysis for sealed, raw, and graded cards.

## API Endpoints
- `GET /market/analysis` - Market sentiment and trends
- `POST /market/flip-calc` - Calculate ROI for grading a card
- `GET /market/gainers` - Top price movers and gainers

## Inputs / Outputs
**Input**: Card details, raw price, target grade
**Output**: Flip ROI %, grading costs, break-even analysis, market sentiment

## Key Dependencies
- `market/flip_calculator.py` - Grading ROI analysis
- `market/price_trends.py` - Historical trend analysis
- `market/graded_prices.py` - Price source integration
