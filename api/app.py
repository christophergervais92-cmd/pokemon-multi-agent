"""
Flask API for Pokemon TCG Set Database UI.
Run from project root: flask --app api.app run  (or python -m api.app)
"""
from flask import Flask, jsonify, request

from market.prices import (
    get_sets,
    get_set,
    get_pull_rates,
    get_chase_cards,
    get_graded_prices,
    resolve_set_id,
)
from search.cards import search_cards, search_by_card_number, get_card_by_id, get_related_cards
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


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/api/sets", methods=["GET"])
    def list_sets():
        """GET /api/sets?series=Scarlet%20%26%20Violet — list sets (for SELECT SET dropdown)."""
        series = request.args.get("series")
        if series and series.strip().lower() in ("all", "all series", ""):
            series = None
        sets_list = get_sets(series_filter=series)
        return jsonify({"data": sets_list})

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
        s = get_set(resolved)
        if s is None:
            return jsonify({"error": "Set not found", "identifier": set_id}), 404
        return jsonify(s)

    @app.route("/api/sets/<set_id>/pull-rates", methods=["GET"])
    def pull_rates(set_id: str):
        """GET /api/sets/<set_id>/pull-rates — pull rates per pack. set_id can be id, name, or slug."""
        resolved, err = _resolve_set(set_id)
        if err is not None:
            return err
        rates = get_pull_rates(resolved)
        return jsonify({"data": rates, "set_id": resolved})

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
        cards_list = get_chase_cards(set_id=resolved, rarity_filter=rarity, limit=limit)
        return jsonify({"data": cards_list, "set_id": resolved})

    @app.route("/api/cards/<card_id>/graded-prices", methods=["GET"])
    def graded_prices(card_id: str):
        """GET /api/cards/<card_id>/graded-prices — PSA, CGC, Beckett (BGS) graded prices."""
        prices = get_graded_prices(card_id)
        return jsonify(prices)

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
        
        results = search_cards(query, set_id=set_id, rarity=rarity, limit=limit)
        return jsonify({"data": results, "query": query, "count": len(results)})
    
    @app.route("/api/cards/<card_id>", methods=["GET"])
    def get_card_details(card_id: str):
        """GET /api/cards/<card_id> - Get detailed card info with related cards."""
        card = get_card_by_id(card_id)
        if not card:
            return jsonify({"error": "Card not found", "card_id": card_id}), 404
        
        related = get_related_cards(card_id, limit=8)
        return jsonify({"card": card, "related": related})
    
    # ===== Collection Endpoints =====
    
    @app.route("/api/collection/<user_id>", methods=["GET"])
    def get_user_collection(user_id: str):
        """GET /api/collection/<user_id>?set=sv8 - Get user's collection."""
        set_id = request.args.get("set")
        items = get_collection(user_id, set_id=set_id)
        summary = get_portfolio_summary(user_id)
        return jsonify({
            "user_id": user_id,
            "items": items,
            "summary": summary,
            "count": len(items)
        })
    
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
        days = int(request.args.get("days", 30))
        summary = get_portfolio_summary(user_id)
        history = get_portfolio_history(user_id, days=days)
        return jsonify({
            "user_id": user_id,
            "summary": summary,
            "history": history
        })
    
    @app.route("/api/collection/stats", methods=["GET"])
    def collection_stats():
        """GET /api/collection/stats - Get global collection statistics."""
        stats = get_collection_stats()
        return jsonify(stats)
    
    # ===== Alert Endpoints =====
    
    @app.route("/api/alerts/<user_id>", methods=["GET"])
    def get_alerts(user_id: str):
        """GET /api/alerts/<user_id> - Get user's price alerts."""
        alerts = get_user_alerts(user_id)
        return jsonify({
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
        stats = get_alert_stats()
        return jsonify(stats)
    
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
        settings = get_settings()
        if not settings:
            return jsonify({"error": "Settings not initialized"}), 500
        return jsonify(settings)

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
        settings = get_settings()
        remaining = get_remaining_budget()
        spent = settings["daily_budget"] - remaining if settings else 0

        return jsonify({
            "daily_budget": settings["daily_budget"] if settings else 0,
            "spent_today": spent,
            "remaining": remaining,
            "autonomy_level": settings["autonomy_level"] if settings else 0
        })

    # ===== Stats Endpoints =====

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """GET /api/stats - Get overall system statistics."""
        collection_stats = get_collection_stats()
        alert_stats = get_alert_stats()
        return jsonify({
            "collections": collection_stats,
            "alerts": alert_stats
        })

    return app


app = create_app()


if __name__ == "__main__":
    # Run from project root: python -m api.app  (or: flask --app api.app run)
    app.run(host="0.0.0.0", port=5000, debug=True)
