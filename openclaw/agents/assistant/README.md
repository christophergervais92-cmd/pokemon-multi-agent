# Assistant Agent

**Backend**: `agents/agents_server.py` (route `/ai/chat`)

## Purpose
AI-powered TCG investment Q&A assistant providing expert guidance on card pricing, grading decisions, market trends, and portfolio optimization.

## API Endpoints
- `POST /ai/chat` - Ask TCG investment questions
- `GET /ai/features` - List available assistant capabilities

## Inputs / Outputs
**Input**: User query (natural language), optional context (cards, prices, grades)
**Output**: Expert response with market data, pricing recommendations, grading ROI analysis

## Key Dependencies
- `agents_server.py` - Chat routing
- OpenAI GPT-4 API (requires OPENAI_API_KEY)
- System prompt contextualizes assistant as TCG expert
- Integrates grading, pricing, and market analysis agents
