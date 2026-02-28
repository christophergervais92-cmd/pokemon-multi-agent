# Card Dashboard Migration (from pokemon-card-agent)

This document describes what was brought in from **pokemon-card-agent** and how it fits with **pokemon-multi-agent**.

## What was transferred

These top-level packages and UI were copied from `pokemon-card-agent` into `pokemon-multi-agent`:

| Path | Purpose |
|------|--------|
| `api/` | Flask app: sets, cards, search, collection, alerts, grading, agent settings |
| `db/` | SQLite schema and connection for sets, collection, alerts, agent_settings |
| `market/` | Set/card prices (TCGdex, live prices) for dashboard |
| `search/` | Card search by name/set/rarity |
| `collection/` | Collection manager, portfolio summary |
| `alerts/` | Price alert tracker (above/below/change %) |
| `grading/` | Grade estimator, condition assessment |
| `agent/` | Agent settings (budget, autonomy, deal threshold) |
| `ui/` | Dashboard HTML/frontend |

## What was not transferred (DEX)

**DEX / perpetual trading** is **not** in this repo. It lives in a separate repository (e.g. `pokemon_perp_dex`). This repo has no `agents/dex` or oracle/perpetual code.

## Running the card dashboard

From **pokemon-multi-agent** root:

```bash
# Install deps if needed
pip install -r requirements.txt

# Run the card dashboard API (port 5000)
flask --app api.app run
# or
python -m flask --app api.app run
```

Then open **http://localhost:5000**. The API creates `pokemon_tcg.db` in the project root on first use.

## Coexistence with agents server

- **agents_server.py** – multi-agent system (scanners, stock, Discord, etc.). Run with `python3 agents/agents_server.py` (different port if configured).
- **api/app.py** – card dashboard (sets, search, collection, alerts). Run with `flask --app api.app run` (default port 5000).

You can run both: start the agents server on one port and the card dashboard on 5000.
