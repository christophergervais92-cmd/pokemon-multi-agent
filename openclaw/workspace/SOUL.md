# PokeAgent - Project Soul

## Identity
**PokeAgent** is a Pokemon TCG market intelligence platform that combines real-time stock scanning, price tracking, card grading, and portfolio management into a single dashboard.

## Architecture

### Frontend (`dashboard/`)
Modular vanilla JS SPA. No framework, no bundler, no build step.
- `index.html` - Shell with section-based navigation
- `js/` - Core modules + `tabs/` for each feature
- `css/` - Variables, base, components, nav

### Backend (`agents/`)
Python Flask server (`agents_server.py`) with specialized agent modules:
- **Scanners** - Stock checking across Target, Walmart, Best Buy, GameStop, etc.
- **Market** - Price analysis, flip calculator, graded price lookups
- **Graders** - AI-powered card condition grading via vision models
- **Notifications** - Multi-channel alerts (Discord, webhooks, push)
- **Tasks** - Scheduled monitoring jobs with a background runner

### Data Flow
```
Dashboard (JS) --> Flask API --> Agent Modules --> External APIs
                                                   |-> Pokemon TCG API
                                                   |-> Retailer websites
                                                   |-> Discord OAuth
                                                   |-> Price services
```

## Principles
1. **No build step** - Dashboard loads directly from files, deploys to any static host
2. **Progressive enhancement** - Works without backend, degrades gracefully
3. **Demo-first** - Generate realistic demo data when APIs are unavailable
4. **Mobile-ready** - Dashboard designed for phone-first use
5. **Stealth-aware** - Scanner agents use anti-detection, proxy rotation, rate limiting

## Key APIs
- `api.pokemontcg.io/v2` - Card data, images, sets
- Backend proxy at `/api/tcg/*` - Avoids CORS and rate limits
- `/scanner/unified` - Multi-retailer stock check
- `/prices/card/{name}` - Graded + raw price lookup
- `/grader/analyze` - Vision-based card grading
- `/auth/discord` - OAuth login flow

## Deployment
- **Frontend**: Vercel (static) or served from Flask
- **Backend**: Render (via `render.yaml` + `Procfile`)
- **Config**: `config.json` for API keys, `env.example` for env vars
