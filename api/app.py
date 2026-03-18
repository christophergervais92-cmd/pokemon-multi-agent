"""
Flask API for Pokemon TCG Set Database UI.
Run from project root: flask --app api.app run  (or python -m api.app)
"""
import os
import sys
# Ensure repo root is in path (needed for Vercel serverless function context)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
import hashlib
import threading
from pathlib import Path
from flask import Flask, jsonify, request, Response, send_file

from market.prices import (
    get_sets,
    get_set,
    get_pull_rates,
    get_chase_cards,
    get_graded_prices,
    resolve_set_id,
)
from search.cards import search_cards, search_by_card_number, get_card_by_id, get_related_cards
from db.queries import (
    get_card_price_history,
    get_sealed_products,
    get_sealed_product_by_id,
    get_sealed_price_history,
    get_graded_prices_structured,
    get_trending_cards,
)
from collection.manager import (
    add_to_collection,
    remove_from_collection,
    update_quantity,
    get_collection,
    get_portfolio_summary,
    get_portfolio_history,
    get_collection_stats,
    record_portfolio_value,
)
from alerts.tracker import (
    create_alert,
    get_user_alerts,
    delete_alert,
    toggle_alert,
    check_alerts,
    get_alert_stats,
)
from grading.estimator import estimate_grade, assess_condition, get_grading_cost_estimate
from agent.settings import get_settings, update_settings, can_auto_purchase, get_remaining_budget
from api.ebay_client import search_sold_listings


def _auto_seed_if_empty():
    """Seed the database on startup if it's empty (Render's ephemeral filesystem)."""
    try:
        from db.connection import get_connection
        conn = get_connection()
        card_count = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        sealed_count = conn.execute("SELECT COUNT(*) FROM sealed_products").fetchone()[0]
        if card_count == 0 and sealed_count == 0:
            import logging
            logging.getLogger(__name__).info("Empty database detected — auto-seeding...")
            from scripts.seed_database import seed_sealed_products, generate_price_history, sync_sets_from_api, seed_card_price_history
            sync_sets_from_api()
            seed_sealed_products()
            generate_price_history(days=90)
            seed_card_price_history(days=30)
            logging.getLogger(__name__).info("Auto-seed complete.")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Auto-seed failed: %s", e)


def create_app() -> Flask:
    app = Flask(__name__)

    # Ensure all required tables exist
    from db.connection import init_db
    from alerts.tracker import init_alerts_table
    init_db()
    init_alerts_table()

    # Auto-seed if database is empty (handles Render's ephemeral filesystem)
    _auto_seed_if_empty()

    # ===== In-memory cache =====
    _cache: dict = {}
    _cache_stats = {"hits": 0, "misses": 0}

    def _cached(key: str, ttl_seconds: int, fn):
        """Simple TTL cache with stats tracking."""
        now = time.time()
        if key in _cache:
            data, ts = _cache[key]
            if now - ts < ttl_seconds:
                _cache_stats["hits"] += 1
                return data
        _cache_stats["misses"] += 1
        result = fn()
        _cache[key] = (result, now)
        return result

    @app.after_request
    def add_response_headers(response):
        """Add cache-control, ETag, CORS, and Vary headers to all responses."""
        # If endpoint set X-Cache-TTL, add browser caching headers
        ttl = response.headers.get('X-Cache-TTL')
        if ttl:
            response.headers['Cache-Control'] = f'public, max-age={ttl}'
            del response.headers['X-Cache-TTL']
            # Add weak ETag based on response content hash
            etag = hashlib.md5(response.get_data()).hexdigest()[:16]
            response.headers['ETag'] = f'W/"{etag}"'
            # Handle If-None-Match for 304 Not Modified
            if_none_match = request.headers.get('If-None-Match')
            if if_none_match:
                # Strip W/ prefix and quotes for comparison
                client_etag = if_none_match.strip('"').lstrip('W/').strip('"')
                if client_etag == etag:
                    response.status_code = 304
                    response.set_data(b'')
        else:
            response.headers.setdefault('Cache-Control', 'no-cache')
        # CORS fallback in case flask-cors isn't loaded
        response.headers.setdefault('Access-Control-Allow-Origin', '*')
        response.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, If-None-Match')
        # Vary header for proper proxy/CDN caching
        response.headers['Vary'] = 'Accept-Encoding'
        return response

    @app.route("/api/sets", methods=["GET"])
    def list_sets():
        """GET /api/sets?series=Scarlet%20%26%20Violet — list sets (for SELECT SET dropdown)."""
        series = request.args.get("series")
        if series and series.strip().lower() in ("all", "all series", ""):
            series = None
        raw_sets = _cached(f"sets:{series}", 300, lambda: get_sets(series_filter=series))
        # Map 'total' to 'total_cards' for frontend
        sets_list = []
        for s in raw_sets:
            sets_list.append({
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "series": s.get("series", ""),
                "release_date": s.get("release_date", ""),
                "total_cards": s.get("total", 0),
                "logo_url": s.get("logo_url", ""),
                "value_index": s.get("value_index"),
            })
        resp = jsonify({"data": sets_list})
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    def _resolve_set(set_id: str):
        """Resolve set identifier to canonical set_id; return (set_id, 404_response) or (resolved_id, None)."""
        resolved = resolve_set_id(set_id)
        if resolved is None:
            return None, (jsonify({"error": "Set not found", "identifier": set_id}), 404)
        return resolved, None

    @app.route("/api/sets/<set_id>", methods=["GET"])
    def get_set_by_id(set_id: str):
        """GET /api/sets/<set_id> — single set (logo, value index). Accepts id, name, or slug."""
        resolved, err = _resolve_set(set_id)
        if err is not None:
            return err
        s = _cached(f"set:{resolved}", 300, lambda: get_set(resolved))
        if s is None:
            return jsonify({"error": "Set not found", "identifier": set_id}), 404
        resp = jsonify(s)
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    @app.route("/api/sets/<set_id>/pull-rates", methods=["GET"])
    def pull_rates(set_id: str):
        """GET /api/sets/<set_id>/pull-rates — pull rates per pack. set_id can be id, name, or slug."""
        resolved, err = _resolve_set(set_id)
        if err is not None:
            return err
        raw_rates = _cached(f"pull_rates:{resolved}", 300, lambda: get_pull_rates(resolved))
        # Map DB fields (category, label, rate_per_pack) to frontend fields (rarity, rate)
        rates = [
            {"rarity": r.get("label") or r.get("category", ""), "rate": r.get("rate_per_pack", 0), **r}
            for r in raw_rates
        ]
        resp = jsonify({"data": rates, "set_id": resolved})
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    @app.route("/api/sets/<set_id>/chase-cards", methods=["GET"])
    def chase_cards(set_id: str):
        """GET /api/sets/<set_id>/chase-cards?rarity=Illustration%20Rare&limit=24 — chase cards for this set only."""
        resolved, err = _resolve_set(set_id)
        if err is not None:
            return err
        rarity = request.args.get("rarity")
        if rarity and rarity.strip().lower() == "all":
            rarity = None
        try:
            limit = int(request.args.get("limit", 24))
        except (TypeError, ValueError):
            limit = 24
        limit = min(max(1, limit), 100)
        cards_list = _cached(
            f"chase_cards:{resolved}:{rarity}:{limit}",
            120,
            lambda: get_chase_cards(set_id=resolved, rarity_filter=rarity, limit=limit),
        )
        resp = jsonify({"data": cards_list, "set_id": resolved})
        resp.headers['X-Cache-TTL'] = '120'
        return resp

    @app.route("/api/cards/<card_id>/graded-prices", methods=["GET"])
    def graded_prices(card_id: str):
        """GET /api/cards/<card_id>/graded-prices — PSA, CGC, Beckett (BGS) graded prices."""
        prices = _cached(f"graded_prices:{card_id}", 120, lambda: get_graded_prices(card_id))
        resp = jsonify(prices)
        resp.headers['X-Cache-TTL'] = '120'
        return resp

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    # ===== Search Endpoints =====
    
    @app.route("/api/search/cards", methods=["GET"])
    def search_cards_endpoint():
        """GET /api/search/cards?q=charizard&set=sv8&limit=20 - Search cards by name."""
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        set_id = request.args.get("set")
        rarity = request.args.get("rarity")
        limit = min(int(request.args.get("limit", 20)), 50)

        raw = _cached(
            f"search:{query}:{set_id}:{rarity}:{limit}",
            120,
            lambda: search_cards(query, set_id=set_id, rarity=rarity, limit=limit),
        )
        # Map DB fields to frontend-expected fields
        results = []
        for card in raw:
            card_id = card.get("id", "")
            parts = card_id.split("-", 1)
            number = parts[1] if len(parts) > 1 else ""
            results.append({
                "id": card_id,
                "name": card.get("name", ""),
                "set": card.get("set_name") or card.get("set_id", ""),
                "number": number,
                "rarity": card.get("rarity", ""),
                "image": card.get("small_image_url") or card.get("image_url", ""),
                "price": card.get("tcgplayer_market"),
                "supertype": card.get("supertype", ""),
            })
        resp = jsonify({"data": results, "query": query, "count": len(results)})
        resp.headers['X-Cache-TTL'] = '120'
        return resp
    
    @app.route("/api/cards/<card_id>", methods=["GET"])
    def get_card_details(card_id: str):
        """GET /api/cards/<card_id> - Get detailed card info with related cards."""
        raw_card = _cached(f"card:{card_id}", 120, lambda: get_card_by_id(card_id))
        if not raw_card:
            return jsonify({"error": "Card not found", "card_id": card_id}), 404

        raw_related = _cached(f"related:{card_id}", 120, lambda: get_related_cards(card_id, limit=8))

        # Map DB fields to frontend CardDetail type
        parts = card_id.split("-", 1)
        number = parts[1] if len(parts) > 1 else ""
        card = {
            "id": raw_card.get("id", ""),
            "name": raw_card.get("name", ""),
            "set": raw_card.get("set_name") or raw_card.get("set_id", ""),
            "set_id": raw_card.get("set_id", ""),
            "set_name": raw_card.get("set_name", ""),
            "set_series": raw_card.get("set_series", ""),
            "number": number,
            "rarity": raw_card.get("rarity", ""),
            "supertype": raw_card.get("supertype", ""),
            "subtype": raw_card.get("subtype", ""),
            "image": raw_card.get("image_url", ""),
            "image_url": raw_card.get("image_url", ""),
            "small_image_url": raw_card.get("small_image_url", ""),
            "tcgplayer_market": raw_card.get("tcgplayer_market"),
            "tcgplayer_low": raw_card.get("tcgplayer_low"),
            "tcgplayer_mid": raw_card.get("tcgplayer_mid"),
            "tcgplayer_high": raw_card.get("tcgplayer_high"),
            "price": raw_card.get("tcgplayer_market"),
            "updated_at": raw_card.get("updated_at"),
        }

        related = []
        for r in raw_related:
            r_id = r.get("id", "")
            r_parts = r_id.split("-", 1)
            related.append({
                "id": r_id,
                "name": r.get("name", ""),
                "set": r.get("set_name") or r.get("set_id", ""),
                "number": r_parts[1] if len(r_parts) > 1 else "",
                "rarity": r.get("rarity", ""),
                "image": r.get("small_image_url") or r.get("image_url", ""),
                "price": r.get("tcgplayer_market"),
            })

        resp = jsonify({"card": card, "related": related})
        resp.headers['X-Cache-TTL'] = '120'
        return resp
    
    # ===== Collection Endpoints =====
    
    @app.route("/api/collection/<user_id>", methods=["GET"])
    def get_user_collection(user_id: str):
        """GET /api/collection/<user_id>?set=sv8 - Get user's collection."""
        set_id = request.args.get("set")
        items = _cached(f"collection:{user_id}:{set_id}", 30, lambda: get_collection(user_id, set_id=set_id))
        summary = _cached(f"portfolio_summary:{user_id}", 30, lambda: get_portfolio_summary(user_id))
        resp = jsonify({
            "user_id": user_id,
            "items": items,
            "summary": summary,
            "count": len(items)
        })
        resp.headers['X-Cache-TTL'] = '30'
        return resp
    
    @app.route("/api/collection/<user_id>", methods=["POST"])
    def add_to_collection_endpoint(user_id: str):
        """POST /api/collection/<user_id> - Add card to collection.
        Body: {card_id, quantity=1, condition="NM", purchase_price?, purchase_date?, notes?}
        """
        data = request.get_json() or {}
        card_id = data.get("card_id")
        
        if not card_id:
            return jsonify({"error": "card_id is required"}), 400
        
        success = add_to_collection(
            user_id=user_id,
            card_id=card_id,
            quantity=data.get("quantity", 1),
            condition=data.get("condition", "NM"),
            purchase_price=data.get("purchase_price"),
            purchase_date=data.get("purchase_date"),
            notes=data.get("notes")
        )
        
        if success:
            return jsonify({"success": True, "message": f"Added {card_id} to collection"})
        return jsonify({"error": "Failed to add to collection"}), 500
    
    @app.route("/api/collection/<user_id>/<card_id>", methods=["DELETE"])
    def remove_from_collection_endpoint(user_id: str, card_id: str):
        """DELETE /api/collection/<user_id>/<card_id>?condition=NM - Remove card."""
        condition = request.args.get("condition")
        success = remove_from_collection(user_id, card_id, condition)
        
        if success:
            return jsonify({"success": True, "message": f"Removed {card_id}"})
        return jsonify({"error": "Failed to remove"}), 500
    
    @app.route("/api/collection/<user_id>/portfolio", methods=["GET"])
    def get_portfolio(user_id: str):
        """GET /api/collection/<user_id>/portfolio?days=30 - Get portfolio value history."""
        try:
            days = int(request.args.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        summary = _cached(f"portfolio_summary:{user_id}", 30, lambda: get_portfolio_summary(user_id))
        history = _cached(f"portfolio_history:{user_id}:{days}", 60, lambda: get_portfolio_history(user_id, days=days))
        resp = jsonify({
            "user_id": user_id,
            "summary": summary,
            "history": history
        })
        resp.headers['X-Cache-TTL'] = '60'
        return resp
    
    @app.route("/api/collection/stats", methods=["GET"])
    def collection_stats():
        """GET /api/collection/stats - Get global collection statistics."""
        stats = _cached("collection_stats", 60, get_collection_stats)
        resp = jsonify(stats)
        resp.headers['X-Cache-TTL'] = '60'
        return resp
    
    # ===== Alert Endpoints =====
    
    @app.route("/api/alerts/<user_id>", methods=["GET"])
    def get_alerts(user_id: str):
        """GET /api/alerts/<user_id> - Get user's price alerts."""
        alerts = get_user_alerts(user_id)
        resp = jsonify({
            "user_id": user_id,
            "alerts": [{
                "id": a.id,
                "card_id": a.card_id,
                "condition": a.condition.value,
                "threshold": a.threshold,
                "is_active": a.is_active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "last_triggered": a.last_triggered.isoformat() if a.last_triggered else None
            } for a in alerts]
        })
        resp.headers['X-Cache-TTL'] = '30'
        return resp
    
    @app.route("/api/alerts/<user_id>", methods=["POST"])
    def create_alert_endpoint(user_id: str):
        """POST /api/alerts/<user_id> - Create price alert.
        Body: {card_id, condition="above|below|change_percent", threshold}
        """
        data = request.get_json() or {}
        card_id = data.get("card_id")
        condition = data.get("condition")
        threshold = data.get("threshold")
        
        if not all([card_id, condition, threshold is not None]):
            return jsonify({"error": "card_id, condition, and threshold are required"}), 400
        
        try:
            alert = create_alert(user_id, card_id, condition, float(threshold))
            return jsonify({
                "success": True,
                "alert": {
                    "id": alert.id,
                    "card_id": alert.card_id,
                    "condition": alert.condition.value,
                    "threshold": alert.threshold
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/alerts/<user_id>/<int:alert_id>", methods=["DELETE"])
    def delete_alert_endpoint(user_id: str, alert_id: int):
        """DELETE /api/alerts/<user_id>/<alert_id> - Delete an alert."""
        success = delete_alert(alert_id, user_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Alert not found"}), 404
    
    @app.route("/api/alerts/<user_id>/<int:alert_id>/toggle", methods=["PATCH"])
    def toggle_alert_endpoint(user_id: str, alert_id: int):
        """PATCH /api/alerts/<user_id>/<alert_id>/toggle - Toggle alert active/inactive."""
        success = toggle_alert(alert_id, user_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Alert not found"}), 404

    @app.route("/api/alerts/<user_id>/check", methods=["POST"])
    def check_user_alerts(user_id: str):
        """POST /api/alerts/<user_id>/check - Check and return triggered alerts."""
        triggered = check_alerts(user_id)
        return jsonify({
            "user_id": user_id,
            "triggered": triggered,
            "count": len(triggered)
        })
    
    @app.route("/api/alerts/stats", methods=["GET"])
    def alerts_stats():
        """GET /api/alerts/stats - Get alert system statistics."""
        stats = _cached("alert_stats", 60, get_alert_stats)
        resp = jsonify(stats)
        resp.headers['X-Cache-TTL'] = '60'
        return resp
    
    # ===== Grading Endpoints =====
    
    @app.route("/api/grading/estimate", methods=["POST"])
    def grade_estimate_endpoint():
        """POST /api/grading/estimate - Estimate card grade from condition.
        Body: {condition_notes: "light edge wear, NM"}
        """
        data = request.get_json() or {}
        notes = data.get("condition_notes", "")
        
        if not notes:
            return jsonify({"error": "condition_notes is required"}), 400
        
        result = assess_condition(notes)
        return jsonify(result)
    
    @app.route("/api/grading/cost-estimate", methods=["POST"])
    def grading_cost_endpoint():
        """POST /api/grading/cost-estimate - Estimate grading costs vs value.
        Body: {card_value: 100.0, estimated_grade: 9}
        """
        data = request.get_json() or {}
        card_value = data.get("card_value")
        estimated_grade = data.get("estimated_grade")
        
        if card_value is None or estimated_grade is None:
            return jsonify({"error": "card_value and estimated_grade are required"}), 400
        
        result = get_grading_cost_estimate(float(card_value), float(estimated_grade))
        return jsonify(result)
    
    # ===== Agent Settings Endpoints =====

    @app.route("/api/agent/settings", methods=["GET"])
    def get_agent_settings():
        """GET /api/agent/settings - Get current agent autonomy settings."""
        settings = _cached("agent_settings", 30, get_settings)
        if not settings:
            return jsonify({"error": "Settings not initialized"}), 500
        resp = jsonify(settings)
        resp.headers['X-Cache-TTL'] = '30'
        return resp

    @app.route("/api/agent/settings", methods=["POST"])
    def update_agent_settings():
        """POST /api/agent/settings - Update agent autonomy settings.
        Body: {
            autonomy_level: 0-3,
            daily_budget: 500,
            per_card_max: 200,
            deal_threshold_percent: 15,
            psa10_only: true,
            raw_allowed: false,
            modern_only: true,
            ebay_allowed: true,
            tcgplayer_allowed: true,
            facebook_allowed: false,
            notification_discord: true,
            notification_telegram: false
        }
        """
        data = request.get_json() or {}

        # Validate autonomy_level if provided
        if "autonomy_level" in data:
            level = data["autonomy_level"]
            if not isinstance(level, int) or level < 0 or level > 3:
                return jsonify({"error": "autonomy_level must be 0-3"}), 400

        success = update_settings(data)
        if success:
            return jsonify({"success": True, "settings": get_settings()})
        return jsonify({"error": "Failed to update settings"}), 500

    @app.route("/api/agent/can-purchase", methods=["POST"])
    def check_can_purchase():
        """POST /api/agent/can-purchase - Check if a specific purchase would be auto-executed.
        Body: {price: 120.0, market_price: 150.0}
        """
        data = request.get_json() or {}
        price = data.get("price")
        market_price = data.get("market_price")

        if price is None or market_price is None:
            return jsonify({"error": "price and market_price are required"}), 400

        settings = get_settings()
        can_auto = can_auto_purchase(float(price), float(market_price))
        remaining = get_remaining_budget()

        return jsonify({
            "can_auto_purchase": can_auto,
            "price": price,
            "market_price": market_price,
            "remaining_budget": remaining,
            "settings": settings
        })

    @app.route("/api/agent/budget", methods=["GET"])
    def get_budget_status():
        """GET /api/agent/budget - Get daily budget status."""
        settings = _cached("agent_settings", 30, get_settings)
        remaining = get_remaining_budget()
        spent = settings["daily_budget"] - remaining if settings else 0

        resp = jsonify({
            "daily_budget": settings["daily_budget"] if settings else 0,
            "spent_today": spent,
            "remaining": remaining,
            "autonomy_level": settings["autonomy_level"] if settings else 0
        })
        resp.headers['X-Cache-TTL'] = '30'
        return resp

    # ===== Assistant Endpoint (Claude AI) =====

    @app.route("/api/assistant/chat", methods=["POST"])
    def assistant_chat():
        """POST /api/assistant/chat - Chat with Claude AI assistant.
        Body: {message: "...", history: [{role, content}, ...]}
        """
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "message is required"}), 400

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            # Demo mode: return helpful response without Claude
            return jsonify({
                "response": _demo_response(message),
                "tool_results": [],
                "model": "demo",
                "demo_mode": True,
            })

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            # Build tools for Claude
            tools = [
                {
                    "name": "search_cards",
                    "description": "Search for Pokemon TCG cards by name. Returns card names, sets, rarities, and prices.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Card name to search for"},
                            "limit": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "get_card_price",
                    "description": "Get detailed pricing for a specific card by ID, including market, low, mid, and high prices.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "card_id": {"type": "string", "description": "The card ID (e.g. 'sv8-123')"},
                        },
                        "required": ["card_id"],
                    },
                },
                {
                    "name": "get_set_info",
                    "description": "Get information about a Pokemon TCG set including total cards, release date, and value index.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "set_id": {"type": "string", "description": "Set ID or name"},
                        },
                        "required": ["set_id"],
                    },
                },
                {
                    "name": "grading_advice",
                    "description": "Get grading cost estimate and ROI analysis for a card.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "card_value": {"type": "number", "description": "Current raw card value in dollars"},
                            "estimated_grade": {"type": "number", "description": "Estimated PSA grade (1-10)"},
                        },
                        "required": ["card_value", "estimated_grade"],
                    },
                },
            ]

            # Build messages
            msgs = [{"role": "user" if m.get("role") == "user" else "assistant", "content": m.get("content", "")}
                    for m in history[-10:]]  # last 10 messages for context
            msgs.append({"role": "user", "content": message})

            system_prompt = (
                "You are PokeAgent, an expert Pokemon TCG market analyst and advisor. "
                "You help users with card pricing, investment advice, grading decisions, "
                "set analysis, and market trends. Use the available tools to look up real "
                "card data when users ask about specific cards or sets. Be concise, data-driven, "
                "and actionable. Format prices as dollars. Use bold for emphasis."
            )

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                tools=tools,
                messages=msgs,
            )

            # Process tool calls
            tool_results = []
            final_text = ""

            for block in response.content:
                if block.type == "text":
                    final_text += block.text
                elif block.type == "tool_use":
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({"tool": block.name, "input": block.input, "result": result})

            # If there were tool calls, make a follow-up request
            if tool_results and response.stop_reason == "tool_use":
                follow_up_msgs = msgs + [{"role": "assistant", "content": response.content}]
                tool_result_content = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = _execute_tool(block.name, block.input)
                        tool_result_content.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                follow_up_msgs.append({"role": "user", "content": tool_result_content})

                follow_up = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system_prompt,
                    tools=tools,
                    messages=follow_up_msgs,
                )

                final_text = ""
                for block in follow_up.content:
                    if block.type == "text":
                        final_text += block.text

            return jsonify({
                "response": final_text or "I couldn't generate a response. Please try again.",
                "tool_results": tool_results,
                "model": "claude-sonnet-4-20250514",
                "demo_mode": False,
            })

        except ImportError:
            return jsonify({
                "response": _demo_response(message),
                "tool_results": [],
                "model": "demo",
                "demo_mode": True,
            })
        except Exception as e:
            return jsonify({
                "response": f"I encountered an error processing your request. Please try again.\n\nError: {str(e)[:200]}",
                "tool_results": [],
                "model": "error",
                "demo_mode": True,
            }), 500

    def _execute_tool(name: str, inputs: dict):
        """Execute a tool call and return the result."""
        try:
            if name == "search_cards":
                results = search_cards(inputs["query"], limit=inputs.get("limit", 5))
                return {"cards": results[:5]}
            elif name == "get_card_price":
                card = get_card_by_id(inputs["card_id"])
                if card:
                    return {"card": card}
                return {"error": "Card not found"}
            elif name == "get_set_info":
                resolved = resolve_set_id(inputs["set_id"])
                if resolved:
                    s = get_set(resolved)
                    return {"set": s} if s else {"error": "Set not found"}
                return {"error": "Set not found"}
            elif name == "grading_advice":
                result = get_grading_cost_estimate(inputs["card_value"], inputs["estimated_grade"])
                return result
            return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)[:200]}

    def _demo_response(message: str) -> str:
        """Generate a helpful response without Claude API."""
        q = message.lower()
        if any(w in q for w in ["best set", "invest", "buy"]):
            return ("**Top sets to consider right now:**\n\n"
                    "1. **Prismatic Evolutions** — Eeveelution SARs driving massive demand\n"
                    "2. **Surging Sparks** — Strong chase cards with good pull rates\n"
                    "3. **Evolving Skies** — Sealed product continues climbing\n\n"
                    "*Running in demo mode. Set ANTHROPIC_API_KEY for full AI capabilities.*")
        if any(w in q for w in ["grade", "raw", "psa"]):
            return ("**Grading rules of thumb:**\n\n"
                    "- Grade cards worth **$50+ raw** in NM condition\n"
                    "- PSA 10 multipliers: typically 2-4x raw price\n"
                    "- Cards under $30 raw: sell raw after grading fees\n"
                    "- Use the **Flip Calculator** for exact ROI\n\n"
                    "*Running in demo mode. Set ANTHROPIC_API_KEY for full AI capabilities.*")
        if any(w in q for w in ["chase", "top card", "expensive"]):
            return ("**Current top chase cards:**\n\n"
                    "1. **Umbreon VMAX Alt Art** (Evolving Skies) — $350+\n"
                    "2. **Charizard ex SAR** (Obsidian Flames) — $195\n"
                    "3. **Pikachu ex SAR** (Prismatic Evolutions) — $180\n\n"
                    "*Running in demo mode. Set ANTHROPIC_API_KEY for full AI capabilities.*")
        if any(w in q for w in ["trend", "market", "news"]):
            return ("**Current market trends:**\n\n"
                    "- Modern sealed appreciating 10-20% monthly\n"
                    "- PSA turnaround improving → more submissions\n"
                    "- Japanese products gaining western market share\n"
                    "- Vintage Base Set: steady growth\n\n"
                    "*Running in demo mode. Set ANTHROPIC_API_KEY for full AI capabilities.*")
        return ("I can help with Pokemon TCG questions about:\n"
                "- **Card Pricing** — current values and trends\n"
                "- **Investing** — best sets and products\n"
                "- **Grading** — grade vs sell raw analysis\n"
                "- **Market Trends** — latest news\n\n"
                "*Running in demo mode. Set ANTHROPIC_API_KEY for full AI capabilities.*")

    # ===== Price History Endpoints =====

    @app.route("/api/cards/<card_id>/price-history", methods=["GET"])
    def card_price_history(card_id: str):
        """GET /api/cards/<card_id>/price-history?days=90 — Price history for charts."""
        try:
            days = int(request.args.get("days", 90))
        except (TypeError, ValueError):
            days = 90
        days = min(max(1, days), 730)

        history = _cached(
            f"card_price_history:{card_id}:{days}",
            60,
            lambda: get_card_price_history(card_id, days=days),
        )
        resp = jsonify({"card_id": card_id, "days": days, "data": history, "count": len(history)})
        resp.headers['X-Cache-TTL'] = '60'
        return resp

    @app.route("/api/cards/<card_id>/graded-prices-structured", methods=["GET"])
    def graded_prices_structured(card_id: str):
        """GET /api/cards/<card_id>/graded-prices-structured — Structured graded prices by grader and grade."""
        prices = _cached(
            f"graded_structured:{card_id}",
            120,
            lambda: get_graded_prices_structured(card_id),
        )
        resp = jsonify({"card_id": card_id, "data": prices})
        resp.headers['X-Cache-TTL'] = '120'
        return resp

    # ===== Sealed Products Endpoints =====

    @app.route("/api/sealed", methods=["GET"])
    def list_sealed_products():
        """GET /api/sealed?set_name=Prismatic+Evolutions&product_type=Elite+Trainer+Box — List sealed products."""
        set_name = request.args.get("set_name")
        product_type = request.args.get("product_type")
        products = _cached(
            f"sealed:{set_name}:{product_type}",
            300,
            lambda: get_sealed_products(set_name=set_name, product_type=product_type),
        )
        resp = jsonify({"data": products, "count": len(products)})
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    @app.route("/api/sealed/<int:product_id>", methods=["GET"])
    def get_sealed_product(product_id: int):
        """GET /api/sealed/<id> — Single sealed product details."""
        product = _cached(f"sealed_product:{product_id}", 300, lambda: get_sealed_product_by_id(product_id))
        if not product:
            return jsonify({"error": "Sealed product not found"}), 404
        resp = jsonify(product)
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    @app.route("/api/sealed/<int:product_id>/price-history", methods=["GET"])
    def sealed_product_price_history(product_id: int):
        """GET /api/sealed/<id>/price-history?days=90 — Sealed product price history for charts."""
        try:
            days = int(request.args.get("days", 90))
        except (TypeError, ValueError):
            days = 90
        days = min(max(1, days), 730)

        history = _cached(
            f"sealed_history:{product_id}:{days}",
            60,
            lambda: get_sealed_price_history(product_id, days=days),
        )
        resp = jsonify({"sealed_product_id": product_id, "days": days, "data": history, "count": len(history)})
        resp.headers['X-Cache-TTL'] = '60'
        return resp

    # ===== Trending Endpoint =====

    @app.route("/api/trending", methods=["GET"])
    def trending_cards():
        """GET /api/trending?limit=20 — Top cards by price with change metrics."""
        try:
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        limit = min(max(1, limit), 100)

        raw_cards = _cached(
            f"trending:{limit}",
            180,
            lambda: get_trending_cards(limit=limit),
        )
        # Map DB fields to frontend TrendingCard type
        cards = []
        for c in raw_cards:
            cards.append({
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "set_name": c.get("set_name", ""),
                "set": c.get("set_id", ""),
                "rarity": c.get("rarity", ""),
                "price": c.get("tcgplayer_market"),
                "change_7d": c.get("change_7d"),
                "change_30d": c.get("change_30d"),
                "image_url": c.get("image_url", ""),
                "small_image_url": c.get("small_image_url", ""),
                "tcgplayer_market": c.get("tcgplayer_market"),
            })
        resp = jsonify({"data": cards, "count": len(cards)})
        resp.headers['X-Cache-TTL'] = '180'
        return resp

    # ===== Cache Management Endpoints =====

    @app.route("/api/cache/stats", methods=["GET"])
    def cache_stats():
        """GET /api/cache/stats - Get server-side cache statistics."""
        now = time.time()
        keys_info = []
        for key, (data, ts) in _cache.items():
            keys_info.append({
                "key": key,
                "age_seconds": round(now - ts, 1),
                "cached_at": ts,
            })
        return jsonify({
            "size": len(_cache),
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "hit_rate": round(_cache_stats["hits"] / max(_cache_stats["hits"] + _cache_stats["misses"], 1) * 100, 1),
            "keys": keys_info,
        })

    @app.route("/api/cache", methods=["DELETE"])
    def clear_cache():
        """DELETE /api/cache - Clear all server-side cache entries."""
        count = len(_cache)
        _cache.clear()
        return jsonify({"success": True, "cleared": count})

    # ===== Price Sync Endpoint =====

    @app.route("/api/sync/prices", methods=["POST"])
    def trigger_price_sync():
        """POST /api/sync/prices — Trigger manual price sync (admin)."""
        try:
            from agents.price_sync import run_full_sync
            result = run_full_sync()
            # Clear cache after sync
            _cache.clear()
            return jsonify({"success": True, "result": result})
        except ImportError:
            return jsonify({"error": "Price sync module not available"}), 500
        except Exception as e:
            return jsonify({"error": str(e)[:200]}), 500

    # ===== Stats Endpoints =====

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """GET /api/stats - Get overall system statistics."""
        coll_stats = _cached("collection_stats", 60, get_collection_stats)
        a_stats = _cached("alert_stats", 60, get_alert_stats)
        resp = jsonify({
            "collections": coll_stats,
            "alerts": a_stats
        })
        resp.headers['X-Cache-TTL'] = '60'
        return resp

    # ===== Image Proxy with Disk Cache =====
    # Caches external images locally to avoid rate limiting and CORS issues
    _img_cache_dir = Path(__file__).parent.parent / ".image_cache"
    _img_cache_dir.mkdir(exist_ok=True)
    _img_fetch_lock = threading.Lock()

    # Allowed image domains (whitelist to prevent open proxy abuse)
    _ALLOWED_IMAGE_DOMAINS = {
        "m.media-amazon.com",
        "images.pokemontcg.io",
        "product-images.tcgplayer.com",
        "tcgplayer-cdn.tcgplayer.com",
        "tcg.pokemon.com",
        "assets.pokemon.com",
        "cdn.shopify.com",
    }

    @app.route("/api/image-proxy", methods=["GET"])
    def image_proxy():
        """
        GET /api/image-proxy?url=<encoded_url>
        Proxies and caches external images to avoid CORS/referrer issues and rate limits.
        Images are cached on disk for 7 days.
        """
        import urllib.request
        import urllib.parse
        import urllib.error

        url = request.args.get("url", "").strip()
        if not url:
            return jsonify({"error": "Missing 'url' parameter"}), 400

        # Validate domain whitelist
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.hostname or ""
        except Exception:
            return jsonify({"error": "Invalid URL"}), 400

        if domain not in _ALLOWED_IMAGE_DOMAINS:
            return jsonify({"error": f"Domain '{domain}' not in whitelist"}), 403

        # Generate cache key from URL hash
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:24]
        # Determine extension from URL
        ext = ".jpg"
        lower_path = (parsed.path or "").lower()
        if lower_path.endswith(".png"):
            ext = ".png"
        elif lower_path.endswith(".webp"):
            ext = ".webp"
        elif lower_path.endswith(".gif"):
            ext = ".gif"
        cache_file = _img_cache_dir / f"{url_hash}{ext}"

        # Check disk cache (7 day TTL)
        cache_ttl = 7 * 24 * 3600  # 7 days
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < cache_ttl:
                content_type = {
                    ".jpg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                }.get(ext, "image/jpeg")
                resp = send_file(str(cache_file), mimetype=content_type)
                resp.headers["Cache-Control"] = f"public, max-age={min(int(cache_ttl - age), 86400)}"
                resp.headers["X-Cache"] = "HIT"
                return resp

        # Fetch from origin (with lock to prevent thundering herd)
        with _img_fetch_lock:
            # Double-check after acquiring lock
            if cache_file.exists():
                age = time.time() - cache_file.stat().st_mtime
                if age < cache_ttl:
                    content_type = {
                        ".jpg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                        ".gif": "image/gif",
                    }.get(ext, "image/jpeg")
                    resp = send_file(str(cache_file), mimetype=content_type)
                    resp.headers["Cache-Control"] = "public, max-age=86400"
                    resp.headers["X-Cache"] = "HIT"
                    return resp

            try:
                import requests as http_requests
                r = http_requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": f"{parsed.scheme}://{parsed.hostname}/",
                    "Sec-Fetch-Dest": "image",
                    "Sec-Fetch-Mode": "no-cors",
                    "Sec-Fetch-Site": "cross-site",
                }, timeout=15, allow_redirects=True)
                r.raise_for_status()
                data = r.content
                if len(data) < 100:
                    return jsonify({"error": "Image too small / blocked"}), 502

                # Detect content type from response
                ct = r.headers.get("Content-Type", "image/jpeg")
                if "png" in ct:
                    ext = ".png"
                elif "webp" in ct:
                    ext = ".webp"
                elif "gif" in ct:
                    ext = ".gif"
                # Re-derive cache file with correct ext
                cache_file = _img_cache_dir / f"{url_hash}{ext}"

                cache_file.write_bytes(data)

                content_type = {
                    ".jpg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                }.get(ext, "image/jpeg")
                resp = Response(data, content_type=content_type)
                resp.headers["Cache-Control"] = "public, max-age=86400"
                resp.headers["X-Cache"] = "MISS"
                return resp
            except Exception as e:
                return jsonify({"error": str(e)}), 502

    @app.route("/api/image-cache/stats", methods=["GET"])
    def image_cache_stats():
        """GET /api/image-cache/stats — cache size and file count."""
        files = list(_img_cache_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        return jsonify({
            "cached_images": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(_img_cache_dir),
        })

    # ===== eBay Sold Prices =====

    @app.route("/api/cards/<card_id>/ebay-sold", methods=["GET"])
    def ebay_sold_prices(card_id: str):
        """GET /api/cards/<card_id>/ebay-sold — eBay last-sold prices for a card."""
        # Get card info first for search query
        card = _cached(f"card:{card_id}", 120, lambda: get_card_by_id(card_id))
        if not card:
            return jsonify({"error": "Card not found", "card_id": card_id}), 404

        card_name = card.get("name", "")
        set_name = card.get("set_name", "")
        card_number = card.get("number", "")
        try:
            limit = min(int(request.args.get("limit", 10)), 50)
        except (ValueError, TypeError):
            limit = 10

        result = _cached(
            f"ebay_sold:{card_id}:{limit}",
            300,  # 5-min cache
            lambda: search_sold_listings(card_name, set_name, card_number, limit),
        )
        resp = jsonify(result)
        resp.headers['X-Cache-TTL'] = '300'
        return resp

    # ── Stock Scanner (Real Retailer APIs) ──────────────────
    @app.route('/api/scan', methods=['POST'])
    def api_scan():
        """Scan retailers for Pokemon TCG products using real retailer APIs.

        POST body: {"query": "prismatic evolutions etb", "retailers": ["target","walmart"], "zip": "90210"}
        If retailers is omitted, scans all.
        """
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from agents.scanners.stock_checker import StockChecker

        data = request.get_json(silent=True) or {}
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"error": "query is required"}), 400

        zip_code = data.get('zip', '90210')
        retailers = data.get('retailers')  # None = all
        checker = StockChecker(zip_code=zip_code)

        if retailers:
            scan_data = checker.scan_multiple(retailers, query)
        else:
            scan_data = checker.scan_all(query, parallel=True)

        # Transform to frontend-expected format: results[] with retailer/products
        results = []
        by_retailer = scan_data.get('by_retailer', {})
        products_list = scan_data.get('products', [])

        retailer_names = {
            'target': 'Target', 'walmart': 'Walmart', 'bestbuy': 'Best Buy',
            'gamestop': 'GameStop', 'pokemoncenter': 'Pokemon Center', 'tcgplayer': 'TCGPlayer',
        }

        for ret_id, ret_info in by_retailer.items():
            ret_products = [p for p in products_list if p.get('retailer', '').lower().replace(' ', '') == ret_id]
            results.append({
                "retailer": retailer_names.get(ret_id, ret_id),
                "retailer_id": ret_id,
                "products": [
                    {
                        "name": p.get("name", ""),
                        "retailer": p.get("retailer", ""),
                        "retailer_id": ret_id,
                        "price": p.get("price"),
                        "in_stock": p.get("stock", False),
                        "url": p.get("url", ""),
                        "image_url": p.get("image_url", ""),
                    }
                    for p in ret_products
                ],
                "error": ret_info.get("error"),
            })

        return jsonify({
            "query": query,
            "results": results,
            "total_products": scan_data.get('total', 0),
            "in_stock_count": scan_data.get('in_stock_count', 0),
            "scan_time": scan_data.get('scan_time_seconds'),
        })

    @app.route('/api/scan/<retailer>', methods=['POST'])
    def api_scan_retailer(retailer):
        """Scan a single retailer using real APIs."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from agents.scanners.stock_checker import StockChecker

        data = request.get_json(silent=True) or {}
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"error": "query is required"}), 400

        zip_code = data.get('zip', '90210')
        checker = StockChecker(zip_code=zip_code)
        result = checker.scan_retailer(retailer, query)

        # Transform products to frontend format
        if 'products' in result:
            result['products'] = [
                {
                    "name": p.get("name", ""),
                    "retailer": p.get("retailer", ""),
                    "retailer_id": retailer,
                    "price": p.get("price"),
                    "in_stock": p.get("stock", False),
                    "url": p.get("url", ""),
                    "image_url": p.get("image_url", ""),
                }
                for p in result['products']
            ]

        return jsonify(result)

    return app


try:
    app = create_app()
except Exception:
    from flask import Flask as _Flask, jsonify as _jsonify
    app = _Flask(__name__)

    @app.route('/health')
    def _health():
        return _jsonify({'status': 'ok'})


if __name__ == "__main__":
    # Run from project root: python -m api.app  (or: flask --app api.app run)
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)
