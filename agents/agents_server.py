#!/usr/bin/env python3
"""
Pokemon Multi-Agent HTTP Server

Exposes all agents as HTTP endpoints for n8n integration.
Each retailer scanner and the processing agents have their own endpoint.
Includes Server-Sent Events (SSE) for real-time live notifications.
"""
import json
import os
import subprocess
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, Response, stream_with_context

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

# =============================================================================
# CORS SUPPORT - Restricted to allowed origins
# =============================================================================

# Allowed origins for CORS - add your domains here
ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5000',
    'http://localhost:5001',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5000',
    'http://127.0.0.1:5001',
    'https://pokemon-multi-agent.vercel.app',
    'https://poke-agent.vercel.app',
    'https://pokemon-multi-agent.onrender.com',
]

def get_cors_origin():
    """Get the appropriate CORS origin based on request."""
    origin = request.headers.get('Origin', '')
    
    # Allow file:// protocol for local development
    if origin.startswith('file://'):
        return '*'
    
    # Check if origin is in allowed list
    if origin in ALLOWED_ORIGINS:
        return origin
    
    # Allow any vercel.app subdomain for preview deployments
    if origin.endswith('.vercel.app'):
        return origin
    
    # Default: return first allowed origin (restrictive)
    return ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else ''

@app.after_request
def add_cors_headers(response):
    """Add CORS headers and optimization headers to all responses."""
    # CORS headers - use specific origin instead of wildcard
    cors_origin = get_cors_origin()
    response.headers['Access-Control-Allow-Origin'] = cors_origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '3600'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Performance optimizations
    # Cache static/scanner endpoints for 30 seconds
    if request.endpoint and any(x in request.endpoint for x in ['scanner', 'drops', 'live/status']):
        response.cache_control.max_age = 30
        response.cache_control.public = True
    
    # Cache static data longer (sets, card info)
    if request.endpoint and any(x in request.endpoint for x in ['sets', 'cards/info']):
        response.cache_control.max_age = 300  # 5 minutes
        response.cache_control.public = True
    
    # Enable compression hint (server should compress)
    if response.content_length and response.content_length > 1024:  # >1KB
        response.headers['Vary'] = 'Accept-Encoding'
    
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle preflight OPTIONS requests."""
    return '', 204

# =============================================================================
# LIVE NOTIFICATIONS SYSTEM (SSE)
# =============================================================================

# Store connected clients and their message queues
live_clients = []
alert_history = []
scan_results_cache = {}
background_scanner_running = False
background_scanner_interval = 60  # seconds

def send_to_all_clients(event_type: str, data: dict):
    """Send an event to all connected SSE clients."""
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Store in history
    if event_type == "alert":
        alert_history.insert(0, message)
        if len(alert_history) > 100:
            alert_history.pop()
    
    # Send to all clients
    dead_clients = []
    for client_queue in live_clients:
        try:
            client_queue.put_nowait(message)
        except:
            dead_clients.append(client_queue)
    
    # Remove dead clients
    for dead in dead_clients:
        if dead in live_clients:
            live_clients.remove(dead)


def format_sse(data: dict, event: str = None) -> str:
    """Format data as SSE message."""
    msg = ""
    if event:
        msg += f"event: {event}\n"
    msg += f"data: {json.dumps(data)}\n\n"
    return msg


@app.route('/live/stream')
def live_stream():
    """
    Server-Sent Events endpoint for real-time notifications.
    
    Connect with JavaScript:
    const events = new EventSource('http://127.0.0.1:5001/live/stream');
    events.onmessage = (e) => console.log(JSON.parse(e.data));
    events.addEventListener('alert', (e) => handleAlert(JSON.parse(e.data)));
    """
    def generate():
        # Create a queue for this client
        client_queue = queue.Queue()
        live_clients.append(client_queue)
        
        try:
            # Send initial connection message
            yield format_sse({
                "message": "Connected to LO TCG Live Alerts",
                "clients": len(live_clients),
            }, "connected")
            
            # Send recent alerts
            for alert in alert_history[:10]:
                yield format_sse(alert["data"], alert["type"])
            
            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for message with timeout (for keepalive)
                    message = client_queue.get(timeout=30)
                    yield format_sse(message["data"], message["type"])
                except queue.Empty:
                    # Send keepalive ping
                    yield format_sse({"ping": True}, "ping")
        finally:
            # Remove client on disconnect
            if client_queue in live_clients:
                live_clients.remove(client_queue)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/live/status')
def live_status():
    """Get live notification system status."""
    return jsonify({
        "success": True,
        "connected_clients": len(live_clients),
        "recent_alerts": len(alert_history),
        "background_scanner": background_scanner_running,
        "scan_interval": background_scanner_interval,
    })


@app.route('/live/test')
def live_test():
    """Send a test notification to all clients."""
    send_to_all_clients("alert", {
        "id": int(time.time() * 1000),
        "type": "test",
        "product_name": "Test Alert - Pokemon ETB",
        "retailer": "Test Store",
        "price": 49.99,
        "market_price": 69.99,
        "delta_pct": 0.29,
        "url": "https://example.com",
        "message": "This is a test alert!",
    })
    return jsonify({"success": True, "message": "Test alert sent to all clients"})


@app.route('/live/send', methods=['POST'])
def live_send():
    """Manually send an alert to all clients."""
    data = request.get_json(force=True) or {}
    event_type = data.get("type", "alert")
    send_to_all_clients(event_type, data)
    return jsonify({"success": True, "sent_to": len(live_clients)})


# Background scanner thread
def background_scanner():
    """Background thread that scans and sends live alerts."""
    global background_scanner_running, scan_results_cache
    
    while background_scanner_running:
        try:
            # Notify clients scan is starting
            send_to_all_clients("scan_start", {
                "message": "Background scan starting...",
            })
            
            # Run unified scanner
            from scanners.stock_checker import StockChecker
            checker = StockChecker()
            results = checker.scan_all("pokemon trading cards")
            
            products = results.get("products", [])
            
            # Check for deals (15%+ below market)
            deals = []
            for p in products:
                if not isinstance(p, dict):
                    continue
                price = p.get("price", 0)
                market = p.get("market_price", 0)
                if price and market and price < market * 0.85:
                    deals.append({
                        "id": int(time.time() * 1000) + hash(p.get("name", "")),
                        "product_name": p.get("name", "Unknown"),
                        "retailer": p.get("retailer", "Unknown"),
                        "price": price,
                        "market_price": market,
                        "delta_pct": (market - price) / market,
                        "url": p.get("url", ""),
                        "stock": p.get("stock", True),
                    })
            
            # Cache results
            scan_results_cache = {
                "products": products,
                "deals": deals,
                "scanned_at": datetime.now().isoformat(),
            }
            
            # Send scan complete event
            send_to_all_clients("scan_complete", {
                "products_found": len(products),
                "deals_found": len(deals),
                "scanned_at": datetime.now().isoformat(),
            })
            
            # Send individual deal alerts
            for deal in deals:
                send_to_all_clients("alert", deal)
            
        except Exception as e:
            send_to_all_clients("error", {
                "message": f"Scan error: {str(e)}",
            })
        
        # Wait for next scan
        time.sleep(background_scanner_interval)


@app.route('/live/scanner/start', methods=['POST'])
def start_background_scanner():
    """Start the background scanner."""
    global background_scanner_running, background_scanner_interval
    
    data = request.get_json(force=True) or {}
    interval = data.get("interval", 60)
    background_scanner_interval = max(30, min(300, interval))  # 30s to 5min
    
    if not background_scanner_running:
        background_scanner_running = True
        thread = threading.Thread(target=background_scanner, daemon=True)
        thread.start()
        
        send_to_all_clients("scanner_status", {
            "running": True,
            "interval": background_scanner_interval,
        })
        
        return jsonify({
            "success": True,
            "message": "Background scanner started",
            "interval": background_scanner_interval,
        })
    else:
        return jsonify({
            "success": True,
            "message": "Scanner already running",
            "interval": background_scanner_interval,
        })


@app.route('/live/scanner/stop', methods=['POST'])
def stop_background_scanner():
    """Stop the background scanner."""
    global background_scanner_running
    
    background_scanner_running = False
    
    send_to_all_clients("scanner_status", {
        "running": False,
    })
    
    return jsonify({
        "success": True,
        "message": "Background scanner stopped",
    })


@app.route('/live/history')
def alert_history_endpoint():
    """Get recent alert history."""
    limit = request.args.get("limit", 50, type=int)
    return jsonify({
        "success": True,
        "alerts": alert_history[:limit],
        "total": len(alert_history),
    })


def run_cmd(cmd, stdin_json=None):
    """Run a Python agent as a subprocess and return its JSON output."""
    input_bytes = None
    if stdin_json is not None:
        input_bytes = json.dumps(stdin_json).encode("utf-8")

    result = subprocess.run(
        cmd,
        input=input_bytes,
        capture_output=True,
        check=False,
    )

    stdout = (result.stdout or b"").decode("utf-8", errors="ignore").strip()
    if result.returncode != 0:
        return {
            "success": False,
            "error": "command_failed",
            "details": {
                "cmd": " ".join(cmd),
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": (result.stderr or b"").decode("utf-8", errors="ignore"),
            },
        }

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "invalid_json",
            "details": {"message": str(e), "raw": stdout},
        }


# =============================================================================
# RETAILER SCANNER ENDPOINTS (Using Unified Stock Checker)
# =============================================================================

@app.post("/scanner/target")
@app.get("/scanner/target")
def scan_target():
    """
    Scan Target for Pokemon products using Redsky API.
    
    This API is working as of 2026 - returns real stock data.
    """
    try:
        from scanners.stock_checker import scan_target as _scan_target
        query = request.args.get("q", "pokemon trading cards")
        zip_code = request.args.get("zip", "90210")
        products = _scan_target(query, zip_code)
        return jsonify({
            "success": True,
            "retailer": "Target",
            "total_found": len(products),
            "in_stock_count": len([p for p in products if p.stock]),
            "products": [p.to_dict() for p in products],
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/scanner/bestbuy")
@app.get("/scanner/bestbuy")
def scan_bestbuy():
    """Scan Best Buy for Pokemon products."""
    try:
        from scanners.stock_checker import scan_bestbuy as _scan_bestbuy
        query = request.args.get("q", "pokemon trading cards")
        products = _scan_bestbuy(query)
        return jsonify({
            "success": True,
            "retailer": "Best Buy",
            "total_found": len(products),
            "in_stock_count": len([p for p in products if p.stock]),
            "products": [p.to_dict() for p in products],
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/scanner/gamestop")
@app.get("/scanner/gamestop")
def scan_gamestop():
    """Scan GameStop for Pokemon products."""
    try:
        from scanners.stock_checker import scan_gamestop as _scan_gamestop
        query = request.args.get("q", "pokemon cards")
        products = _scan_gamestop(query)
        return jsonify({
            "success": True,
            "retailer": "GameStop",
            "total_found": len(products),
            "in_stock_count": len([p for p in products if p.stock]),
            "products": [p.to_dict() for p in products],
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/scanner/pokemoncenter")
@app.get("/scanner/pokemoncenter")
def scan_pokemoncenter():
    """
    Scan Pokemon Center (official store) for Pokemon TCG products.
    
    Has exclusives like ETBs and promo cards.
    """
    try:
        from scanners.stock_checker import scan_pokemoncenter as _scan_pokemoncenter
        query = request.args.get("q", "trading cards")
        products = _scan_pokemoncenter(query)
        return jsonify({
            "success": True,
            "retailer": "Pokemon Center",
            "total_found": len(products),
            "in_stock_count": len([p for p in products if p.stock]),
            "products": [p.to_dict() for p in products],
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/scanner/all")
@app.get("/scanner/all")
def scan_all_retailers():
    """
    Scan ALL retailers and merge results.
    Uses the unified stock checker for best results.
    
    Query params:
    - q: Search query (default: "pokemon trading cards")
    - zip: ZIP code for local inventory (default: "90210")
    """
    try:
        from scanners.stock_checker import scan_all
        
        # Get query params
        payload = request.get_json(force=True) if request.is_json else {}
        query = payload.get("query") or request.args.get("q", "pokemon trading cards")
        zip_code = payload.get("zip_code") or request.args.get("zip", "90210")
        
        result = scan_all(query, zip_code)
        return jsonify(result)
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})


@app.post("/scanner/unified")
@app.get("/scanner/unified")
def unified_stock_check():
    """
    Unified stock checker - uses multiple methods to get real stock data.
    
    Methods used:
    - Target Redsky API (official internal API - WORKING)
    - Best Buy (API or scrape)
    - Pokemon Center (scrape)
    - GameStop (scrape)
    - TCGPlayer/Pokemon TCG API (for cards)
    
    Query params:
    - q: Search query (default: "pokemon trading cards")
    - zip: ZIP code (default: "90210")
    - retailer: Specific retailer to check (optional)
    """
    try:
        from scanners.stock_checker import StockChecker
        
        # Get params
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            query = payload.get("query", "pokemon trading cards")
            zip_code = payload.get("zip_code", "90210")
            retailer = payload.get("retailer")
        else:
            query = request.args.get("q", "pokemon trading cards")
            zip_code = request.args.get("zip", "90210")
            retailer = request.args.get("retailer")
        
        checker = StockChecker(zip_code=zip_code)
        
        if retailer:
            result = checker.scan_retailer(retailer, query)
        else:
            result = checker.scan_all(query)
        
        return jsonify(result)
        
    except ImportError as e:
        import traceback
        error_msg = f"Import error: {e}"
        print(f"Stock checker import error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"error": error_msg, "type": "import_error"}), 500
    except AttributeError as e:
        import traceback
        error_msg = f"Method error: {e}"
        print(f"Stock checker attribute error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"error": error_msg, "type": "attribute_error"}), 500
    except NameError as e:
        import traceback
        error_msg = f"Name error: {e}"
        print(f"Stock checker name error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"error": error_msg, "type": "name_error"}), 500
    except Exception as e:
        import traceback
        error_msg = f"Stock checker error: {str(e)}"
        print(f"Stock checker exception: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"error": error_msg, "type": "exception"}), 500


@app.post("/scanner/local")
def scan_local():
    """
    Scan for products near a specific ZIP code.
    
    Input: { "zip_code": "90210", "search": "pokemon 151", "radius": 25 }
    Returns: Local inventory results from all retailers.
    """
    try:
        from stealth.local_inventory import LocalInventoryScanner
        
        payload = request.get_json(force=True) or {}
        zip_code = payload.get("zip_code", "90210")
        search = payload.get("search", "pokemon")
        radius = payload.get("radius", 25)
        
        scanner = LocalInventoryScanner(
            zip_code=zip_code,
            radius_miles=radius,
        )
        
        results = scanner.scan_all_retailers(search)
        return jsonify(results)
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/scanner/tcgplayer")
@app.post("/scanner/tcgplayer")
def tcgplayer_search():
    """
    Search for card availability and prices via Pokemon TCG API.
    
    Returns card data with TCGPlayer prices.
    
    Query params (GET) or JSON body (POST):
    - q: Card name to search
    - set: Set name (optional)
    """
    try:
        from scanners.stock_checker import scan_cards
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "charizard")
            set_name = payload.get("set_name") or payload.get("set", "")
        else:
            card_name = request.args.get("q", "charizard")
            set_name = request.args.get("set", "")
        
        products = scan_cards(card_name, set_name)
        
        return jsonify({
            "success": True,
            "query": card_name,
            "set": set_name,
            "total_results": len(products),
            "products": [p.to_dict() for p in products],
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/scanner/cards")
@app.post("/scanner/cards")
def search_cards():
    """
    Search for Pokemon cards using the Pokemon TCG API.
    
    Returns card data with TCGPlayer prices.
    
    Query params (GET) or JSON body (POST):
    - q: Card name to search
    - set: Set name (optional)
    """
    try:
        from scanners.stock_checker import scan_cards
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "")
            set_name = payload.get("set_name") or payload.get("set", "")
        else:
            card_name = request.args.get("q", "")
            set_name = request.args.get("set", "")
        
        products = scan_cards(card_name, set_name)
        
        return jsonify({
            "success": True,
            "query": card_name,
            "set": set_name,
            "total_results": len(products),
            "cards": [p.to_dict() for p in products],
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/scanner/stealth-config")
def stealth_config():
    """Get current stealth scanning configuration."""
    try:
        from stealth.anti_detect import get_scan_config
        return jsonify(get_scan_config())
    except ImportError:
        return jsonify({
            "error": "Stealth module not found",
            "hint": "Ensure stealth/anti_detect.py exists"
        })


@app.get("/scanner/captcha-stats")
def captcha_stats():
    """Get CAPTCHA detection statistics."""
    try:
        from stealth.captcha_handler import get_captcha_stats
        return jsonify(get_captcha_stats())
    except ImportError:
        return jsonify({
            "error": "CAPTCHA handler not found",
            "hint": "Ensure stealth/captcha_handler.py exists"
        })


@app.get("/security/config")
def security_config():
    """Get security configuration (non-sensitive)."""
    try:
        from stealth.security import get_secure_config
        return jsonify(get_secure_config())
    except ImportError:
        return jsonify({
            "input_sanitization": True,
            "rate_limiting": True,
            "api_key_required": False,
        })


# =============================================================================
# PROCESSING AGENT ENDPOINTS
# =============================================================================

@app.post("/agent/retail")
def retail_agent():
    """Legacy retail agent - kept for compatibility."""
    body = request.get_json(force=True) or {}
    set_name = body.get("set_name", "Paldean Fates")
    script = str((BASE_DIR / "retail_agent.py").resolve())
    out = run_cmd(["python3", script, "--set-name", set_name])
    return jsonify(out)


@app.post("/agent/price")
def price_agent():
    """Price analysis agent - adds market pricing to products."""
    payload = request.get_json(force=True) or {}
    script = str((BASE_DIR / "price_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


@app.post("/agent/grading")
def grading_agent():
    """Grading agent - evaluates products for ROI and generates buy signals."""
    payload = request.get_json(force=True) or {}
    script = str((BASE_DIR / "grading_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


@app.post("/agent/buy")
def buy_agent():
    """Legacy buy agent - simulates purchases."""
    payload = request.get_json(force=True) or {}
    script = str((BASE_DIR / "buy_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


@app.post("/agent/autobuy")
def autobuy_agent():
    """
    Auto-buy agent - handles real/simulated purchases.
    Respects price limits and daily spend caps.
    """
    payload = request.get_json(force=True) or {}
    script = str((BASE_DIR / "buyers" / "auto_buyer.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


# =============================================================================
# VISUAL GRADING AGENT ENDPOINTS
# =============================================================================

@app.post("/grader/analyze")
def visual_grading():
    """
    AI-powered visual card grading agent.
    
    Accepts:
    - image_base64: Base64-encoded card image
    - image_url: URL to card image
    - raw_value: Estimated ungraded card value (for ROI calculation)
    - card_name: Optional card name
    
    Returns predicted PSA, CGC, and Beckett grades with value analysis.
    """
    payload = request.get_json(force=True) or {}
    script = str((BASE_DIR / "graders" / "visual_grading_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


@app.get("/grader/standards")
def grading_standards():
    """
    Get grading standards reference for PSA, CGC, and Beckett.
    Useful for understanding what each grade means.
    """
    script = str((BASE_DIR / "graders" / "visual_grading_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json={})  # No image = returns standards
    return jsonify(out)


@app.post("/grader/batch")
def batch_grading():
    """
    Grade multiple cards at once.
    
    Accepts:
    - cards: Array of {image_url, image_base64, raw_value, card_name}
    
    Returns array of grading results.
    """
    payload = request.get_json(force=True) or {}
    cards = payload.get("cards", [])
    
    results = []
    script = str((BASE_DIR / "graders" / "visual_grading_agent.py").resolve())
    
    for i, card in enumerate(cards):
        card_result = run_cmd(["python3", script], stdin_json=card)
        card_result["index"] = i
        results.append(card_result)
    
    return jsonify({
        "success": True,
        "total_cards": len(cards),
        "results": results,
    })


# =============================================================================
# MARKET ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/market/analysis")
@app.post("/market/analysis")
def market_analysis():
    """
    Get full market analysis across sealed, raw, and slabs.
    
    Returns:
    - Overall market sentiment
    - Top gainers and losers by category
    - Price movement statistics
    """
    payload = request.get_json(force=True) if request.method == "POST" else {}
    script = str((BASE_DIR / "market" / "market_analysis_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json=payload)
    return jsonify(out)


@app.get("/market/sealed")
def market_sealed():
    """Get market data for sealed Pokemon products (ETBs, Booster Boxes)."""
    script = str((BASE_DIR / "market" / "market_analysis_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json={"category": "sealed"})
    return jsonify(out)


@app.get("/market/raw")
def market_raw():
    """Get market data for raw (ungraded) cards."""
    script = str((BASE_DIR / "market" / "market_analysis_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json={"category": "raw"})
    return jsonify(out)


@app.get("/market/slabs")
def market_slabs():
    """Get market data for graded cards (PSA, CGC, BGS slabs)."""
    script = str((BASE_DIR / "market" / "market_analysis_agent.py").resolve())
    out = run_cmd(["python3", script], stdin_json={"category": "slabs"})
    return jsonify(out)


# =============================================================================
# GRADED CARD PRICES ENDPOINTS
# =============================================================================

@app.get("/prices/card/<card_name>")
@app.post("/prices/card")
def get_graded_prices(card_name: str = None):
    """
    Get real-time prices for a card including raw and all graded prices.
    
    Returns:
    - Raw (ungraded) price from TCGPlayer
    - PSA 10, 9, 8, 7 prices
    - CGC 10, 9.5, 9 prices
    - BGS 10, 9.5, 9 prices
    
    GET /prices/card/Charizard%20VMAX
    or
    POST with {"card_name": "Charizard VMAX", "set": "Champion's Path", "include_ebay": false}
    """
    try:
        from market.graded_prices import get_card_prices
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "")
            set_name = payload.get("set_name") or payload.get("set", "")
            include_ebay = payload.get("include_ebay", False)
        else:
            set_name = request.args.get("set", "")
            include_ebay = request.args.get("ebay", "false").lower() == "true"
        
        if not card_name:
            return jsonify({"error": "card_name required"})
        
        prices = get_card_prices(card_name, set_name, include_ebay=include_ebay)
        
        return jsonify({
            "success": True,
            **prices,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/prices/psa/<card_name>")
@app.post("/prices/psa")
def get_psa_prices(card_name: str = None):
    """
    Get PSA graded prices only.
    
    Returns raw price + PSA 10, 9, 8, 7 prices.
    """
    try:
        from market.graded_prices import get_psa_prices as _get_psa_prices
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "")
            set_name = payload.get("set_name") or payload.get("set", "")
        else:
            set_name = request.args.get("set", "")
        
        if not card_name:
            return jsonify({"error": "card_name required"})
        
        prices = _get_psa_prices(card_name, set_name)
        
        return jsonify({
            "success": True,
            **prices,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/prices/cgc/<card_name>")
@app.post("/prices/cgc")
def get_cgc_prices(card_name: str = None):
    """
    Get CGC graded prices only.
    
    Returns raw price + CGC 10, 9.5, 9 prices.
    """
    try:
        from market.graded_prices import get_cgc_prices as _get_cgc_prices
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "")
            set_name = payload.get("set_name") or payload.get("set", "")
        else:
            set_name = request.args.get("set", "")
        
        if not card_name:
            return jsonify({"error": "card_name required"})
        
        prices = _get_cgc_prices(card_name, set_name)
        
        return jsonify({
            "success": True,
            **prices,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/prices/bgs/<card_name>")
@app.post("/prices/bgs")
def get_bgs_prices(card_name: str = None):
    """
    Get BGS/Beckett graded prices only.
    
    Returns raw price + BGS 10 Black Label, 10, 9.5, 9 prices.
    """
    try:
        from market.graded_prices import get_bgs_prices as _get_bgs_prices
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("q", "")
            set_name = payload.get("set_name") or payload.get("set", "")
        else:
            set_name = request.args.get("set", "")
        
        if not card_name:
            return jsonify({"error": "card_name required"})
        
        prices = _get_bgs_prices(card_name, set_name)
        
        return jsonify({
            "success": True,
            **prices,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/prices/batch")
def get_batch_prices():
    """
    Get prices for multiple cards at once.
    
    Input: {"cards": [{"name": "Charizard VMAX", "set": "..."}, ...]}
    """
    try:
        from market.graded_prices import get_card_prices
        
        payload = request.get_json(force=True) or {}
        cards = payload.get("cards", [])
        include_ebay = payload.get("include_ebay", False)
        
        results = []
        for card in cards:
            card_name = card.get("name", "")
            set_name = card.get("set", "")
            
            if card_name:
                prices = get_card_prices(card_name, set_name, include_ebay=include_ebay)
                results.append(prices)
        
        return jsonify({
            "success": True,
            "total_cards": len(results),
            "prices": results,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# FLIP CALCULATOR ENDPOINTS
# =============================================================================

@app.get("/flip/<card_name>")
@app.post("/flip")
def flip_calculator(card_name: str = None):
    """
    Flip Calculator - Calculate if grading a card is profitable.
    
    GET /flip/Charizard%20VMAX
    or
    POST with:
    {
        "card_name": "Charizard VMAX",
        "set_name": "Champion's Path",
        "raw_price": 80,  // Optional, fetches if not provided
        "company": "PSA",  // PSA, CGC, or BGS
        "tier": "economy",  // economy, regular, express, etc.
        "condition": "mint"  // mint, near_mint, lightly_played, played
    }
    
    Returns complete ROI analysis for each grade scenario.
    """
    try:
        from market.flip_calculator import calculate_flip, format_flip_discord
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name") or payload.get("card", "")
            set_name = payload.get("set_name") or payload.get("set", "")
            raw_price = payload.get("raw_price") or payload.get("price")
            company = payload.get("company") or payload.get("grading_company", "PSA")
            tier = payload.get("tier") or payload.get("grading_tier", "economy")
            condition = payload.get("condition", "mint")
        else:
            set_name = request.args.get("set", "")
            raw_price = request.args.get("price")
            if raw_price:
                raw_price = float(raw_price)
            company = request.args.get("company", "PSA")
            tier = request.args.get("tier", "economy")
            condition = request.args.get("condition", "mint")
        
        if not card_name:
            return jsonify({"error": "card_name required"})
        
        result = calculate_flip(
            card_name=card_name,
            set_name=set_name,
            raw_price=raw_price,
            company=company,
            tier=tier,
            condition=condition,
        )
        
        # Add formatted Discord message
        result["discord_message"] = format_flip_discord(result)
        
        return jsonify({
            "success": True,
            **result,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/flip/costs")
def grading_costs():
    """
    Get all grading company costs and tiers.
    
    Returns PSA, CGC, and BGS pricing for all service levels.
    """
    try:
        from market.flip_calculator import get_grading_costs
        
        costs = get_grading_costs()
        
        return jsonify({
            "success": True,
            "grading_costs": costs,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})


@app.post("/flip/batch")
def flip_batch():
    """
    Calculate flip profitability for multiple cards.
    
    Input: {"cards": [{"name": "...", "raw_price": 50}, ...]}
    """
    try:
        from market.flip_calculator import calculate_flip
        
        payload = request.get_json(force=True) or {}
        cards = payload.get("cards", [])
        company = payload.get("company", "PSA")
        tier = payload.get("tier", "economy")
        condition = payload.get("condition", "mint")
        
        results = []
        for card in cards:
            card_name = card.get("name") or card.get("card_name", "")
            if card_name:
                result = calculate_flip(
                    card_name=card_name,
                    set_name=card.get("set", ""),
                    raw_price=card.get("raw_price") or card.get("price"),
                    company=company,
                    tier=tier,
                    condition=condition,
                )
                results.append(result)
        
        return jsonify({
            "success": True,
            "total_cards": len(results),
            "results": results,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# STOCK MAP ENDPOINTS
# =============================================================================

@app.get("/stockmap/<zip_code>")
@app.post("/stockmap")
def stock_map(zip_code: str = None):
    """
    Local Stock Map - Find Pokemon TCG stock near you.
    
    GET /stockmap/90210?q=pokemon%20etb&radius=25
    or
    POST with:
    {
        "zip_code": "90210",
        "radius": 25,
        "query": "pokemon elite trainer box"
    }
    
    Returns visual map of nearby stores with stock status.
    """
    try:
        from market.stock_map import get_stock_map, format_stock_map_discord
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            zip_code = payload.get("zip_code") or payload.get("zip", "90210")
            radius = int(payload.get("radius", 25))
            query = payload.get("query") or payload.get("q", "pokemon elite trainer box")
        else:
            radius = int(request.args.get("radius", 25))
            query = request.args.get("q", "pokemon elite trainer box")
        
        if not zip_code:
            zip_code = "90210"
        
        result = get_stock_map(zip_code, radius, query)
        
        # Add formatted Discord message
        result["discord_message"] = format_stock_map_discord(result)
        
        return jsonify({
            "success": True,
            **result,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/stockmap/<zip_code>/compact")
def stock_map_compact(zip_code: str):
    """
    Compact stock map - quick overview format.
    """
    try:
        from market.stock_map import get_stock_map, format_stock_map_compact
        
        query = request.args.get("q", "pokemon")
        radius = int(request.args.get("radius", 25))
        
        result = get_stock_map(zip_code, radius, query)
        
        return jsonify({
            "success": True,
            "zip_code": zip_code,
            "stores_with_stock": result["stores_with_stock"],
            "total_stores": result["total_stores"],
            "summary": result["summary"],
            "compact_message": format_stock_map_compact(result),
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# FULL PIPELINE ENDPOINT
# =============================================================================

@app.post("/pipeline/full")
def full_pipeline():
    """
    Run the FULL multi-agent pipeline:
    1. Scan all retailers
    2. Analyze prices
    3. Grade/evaluate products
    4. Auto-buy qualifying items
    
    Returns complete results with purchases and alerts.
    """
    body = request.get_json(force=True) or {}
    set_name = body.get("set_name", "Pokemon TCG")
    
    # Step 1: Scan all retailers
    scan_result = scan_all_retailers().get_json()
    
    # Add set_name to the data for downstream agents
    scan_result["set_name"] = set_name
    
    # Step 2: Price analysis
    price_script = str((BASE_DIR / "price_agent.py").resolve())
    price_result = run_cmd(["python3", price_script], stdin_json=scan_result)
    
    # Step 3: Grading/evaluation
    grading_script = str((BASE_DIR / "grading_agent.py").resolve())
    grading_result = run_cmd(["python3", grading_script], stdin_json=price_result)
    
    # Step 4: Auto-buy
    autobuy_script = str((BASE_DIR / "buyers" / "auto_buyer.py").resolve())
    final_result = run_cmd(["python3", autobuy_script], stdin_json=grading_result)
    
    return jsonify(final_result)


# =============================================================================
# MULTI-USER ENDPOINTS
# =============================================================================

@app.post("/users/notify")
def notify_users():
    """
    Send deal notifications to users based on their watchlists.
    
    Input: { "products": [...] } - products with deals
    Returns: notification results
    """
    try:
        from discord_bot.notifier import notify_users_sync
        payload = request.get_json(force=True) or {}
        products = payload.get("products", [])
        result = notify_users_sync(products)
        return jsonify({"success": True, **result})
    except ImportError:
        return jsonify({"error": "discord_bot module not found", "hint": "pip install discord.py aiohttp"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/users/autobuy")
def multi_user_autobuy():
    """
    Execute auto-buy for all eligible users based on their:
    - Watchlist matches
    - Payment info
    - Spending limits
    
    Input: { "products": [...] } - available products
    Returns: purchase results per user
    """
    try:
        from discord_bot.user_db import (
            get_all_users_with_autobuy, get_users_watching,
            get_payment_info, log_purchase, get_user
        )
        from buyers.auto_buyer import attempt_purchase
        
        payload = request.get_json(force=True) or {}
        products = payload.get("products", [])
        
        results = {
            "total_users_checked": 0,
            "purchases_attempted": 0,
            "purchases_successful": 0,
            "purchases": [],
        }
        
        # Get users with auto-buy enabled
        autobuy_users = get_all_users_with_autobuy()
        results["total_users_checked"] = len(autobuy_users)
        
        for product in products:
            product_name = product.get("name", "")
            retailer = product.get("retailer", "")
            price = product.get("price", 0)
            
            # Find users watching this product
            watchers = get_users_watching(product_name)
            
            for watcher in watchers:
                discord_id = watcher.get("discord_id")
                
                # Check if user has auto-buy enabled for this item
                if not watcher.get("autobuy_on_deal"):
                    continue
                
                # Check user limits
                user = get_user(discord_id)
                if not user or not user.get("autobuy_enabled"):
                    continue
                
                if price > user.get("max_price_limit", 100):
                    continue  # Over their price limit
                
                daily_remaining = user.get("daily_spend_limit", 500) - user.get("daily_spent", 0)
                if price > daily_remaining:
                    continue  # Would exceed daily limit
                
                # Get payment info
                payment = get_payment_info(discord_id, retailer)
                if not payment or not payment.get("password"):
                    continue  # No payment set up
                
                # Attempt purchase
                results["purchases_attempted"] += 1
                
                purchase_result = attempt_purchase(
                    product=product,
                    credentials={
                        "email": payment.get("email"),
                        "password": payment.get("password"),
                    },
                    shipping={
                        "name": payment.get("shipping_name"),
                        "address": payment.get("shipping_address"),
                        "city": payment.get("shipping_city"),
                        "state": payment.get("shipping_state"),
                        "zip": payment.get("shipping_zip"),
                    }
                )
                
                # Log the purchase
                status = "success" if purchase_result.get("success") else "failed"
                log_purchase(
                    discord_id=discord_id,
                    product_name=product_name,
                    retailer=retailer,
                    price=price,
                    purchase_id=purchase_result.get("purchase_id", "N/A"),
                    status=status
                )
                
                if purchase_result.get("success"):
                    results["purchases_successful"] += 1
                
                results["purchases"].append({
                    "user_id": discord_id,
                    "product": product_name,
                    "retailer": retailer,
                    "price": price,
                    "result": purchase_result,
                })
        
        return jsonify(results)
    
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}", "hint": "pip install discord.py cryptography"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/users/stats")
def user_stats():
    """Get statistics about registered users."""
    try:
        from discord_bot.user_db import get_all_users_with_autobuy
        import sqlite3
        from pathlib import Path
        
        db_path = Path(__file__).parent / "pokemon_users.db"
        if not db_path.exists():
            return jsonify({
                "total_users": 0,
                "autobuy_enabled": 0,
                "watchlist_items": 0,
                "total_purchases": 0,
            })
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE autobuy_enabled = 1")
        autobuy_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM watchlists")
        watchlist_items = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM purchase_history")
        total_purchases = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(price) FROM purchase_history WHERE status = 'success'")
        total_spent = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            "total_users": total_users,
            "autobuy_enabled": autobuy_users,
            "watchlist_items": watchlist_items,
            "total_purchases": total_purchases,
            "total_spent": round(total_spent, 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# PHOTO CARD SCANNER ENDPOINTS
# =============================================================================

@app.post("/vision/scan")
def scan_card_photo():
    """
    AI-powered card identification from photo.
    
    Accepts:
    - image_url: URL to card image
    - image_base64: Base64-encoded card image
    
    Returns:
    - Card identification (name, set, number)
    - Condition assessment (centering, corners, edges, surface)
    - Estimated PSA grade
    - Market pricing (raw and graded)
    - Grading recommendation
    """
    try:
        from vision.card_scanner import CardScanner
        
        payload = request.get_json(force=True) or {}
        scanner = CardScanner()
        
        result = scanner.scan_card(
            image_url=payload.get("image_url"),
            image_base64=payload.get("image_base64"),
            image_path=payload.get("image_path"),
        )
        
        return jsonify(result)
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/vision/batch")
def batch_scan_cards():
    """
    Scan multiple card photos at once.
    
    Accepts:
    - cards: Array of {image_url or image_base64}
    
    Returns array of scan results.
    """
    try:
        from vision.card_scanner import CardScanner
        
        payload = request.get_json(force=True) or {}
        cards = payload.get("cards", [])
        
        scanner = CardScanner()
        results = scanner.batch_scan(cards)
        
        return jsonify({
            "success": True,
            "total_cards": len(cards),
            "results": results,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# PRICE TREND ENDPOINTS
# =============================================================================

@app.get("/trends/card/<card_name>")
@app.post("/trends/card")
def get_card_trend(card_name=None):
    """
    Get 7-day price trend with sparkline for a card.
    
    GET /trends/card/Charizard%20VMAX
    or
    POST with {"card_name": "Charizard VMAX", "set": "Champion's Path", "days": 7}
    
    Returns:
    - Current price and change %
    - ASCII sparkline graph
    - Trend emoji indicator
    - High/low/average
    """
    try:
        from market.price_trends import PriceTrendAnalyzer
        
        analyzer = PriceTrendAnalyzer()
        
        if request.method == "POST":
            payload = request.get_json(force=True) or {}
            card_name = payload.get("card_name", "")
            set_name = payload.get("set")
            days = payload.get("days", 7)
        else:
            set_name = request.args.get("set")
            days = int(request.args.get("days", 7))
        
        trend = analyzer.get_trend(card_name, set_name, days)
        return jsonify(trend)
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/trends/movers")
def get_top_movers():
    """
    Get top gaining and losing cards.
    
    Returns:
    - gainers: Top 5 cards by % gain
    - losers: Top 5 cards by % loss
    """
    try:
        from market.price_trends import get_top_movers
        
        limit = int(request.args.get("limit", 5))
        movers = get_top_movers(limit)
        
        return jsonify(movers)
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/trends/bulk")
def get_bulk_trends():
    """
    Get trends for multiple cards at once.
    
    Input: {"cards": [{"name": "...", "set": "..."}, ...]}
    Returns array of trend data.
    """
    try:
        from market.price_trends import PriceTrendAnalyzer
        
        payload = request.get_json(force=True) or {}
        cards = payload.get("cards", [])
        days = payload.get("days", 7)
        
        analyzer = PriceTrendAnalyzer()
        trends = analyzer.get_bulk_trends(cards, days)
        
        return jsonify({
            "success": True,
            "period_days": days,
            "total_cards": len(cards),
            "trends": trends,
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# MULTI-CHANNEL NOTIFICATION ENDPOINTS
# =============================================================================

@app.get("/notifications/channels")
def notification_channels():
    """
    Get available notification channels.
    
    Returns which channels are configured (SMS, Push, Email, etc.)
    """
    try:
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        return jsonify({
            "success": True,
            "channels": manager.get_available_channels(),
        })
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/notifications/send")
def send_notification():
    """
    Send a notification to a user via all their enabled channels.
    
    Input:
    {
        "discord_id": "123456789",
        "title": "🔥 RESTOCK!",
        "message": "Product is back in stock!",
        "priority": "critical",  // critical, high, normal, low
        "url": "https://...",
        "product": {...}
    }
    """
    try:
        from notifications.multi_channel import NotificationManager
        
        payload = request.get_json(force=True) or {}
        
        manager = NotificationManager()
        result = manager.send_alert(
            discord_id=payload.get("discord_id"),
            title=payload.get("title", "LO TCG Alert"),
            message=payload.get("message", ""),
            priority=payload.get("priority", "normal"),
            url=payload.get("url"),
            product_data=payload.get("product"),
        )
        
        return jsonify({"success": True, **result})
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/notifications/restock")
def send_restock_notification():
    """
    Send restock alerts to all users watching a product.
    
    Input:
    {
        "product": {...},
        "user_ids": ["123", "456"]  // Optional, defaults to all watchers
    }
    """
    try:
        from notifications.multi_channel import NotificationManager
        
        payload = request.get_json(force=True) or {}
        
        manager = NotificationManager()
        result = manager.send_restock_alert(
            product=payload.get("product", {}),
            user_ids=payload.get("user_ids"),
        )
        
        return jsonify({"success": True, **result})
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/notifications/price-drop")
def send_price_drop_notification():
    """
    Send price drop alerts to users.
    
    Input:
    {
        "product": {...},
        "old_price": 49.99,
        "new_price": 29.99,
        "user_ids": ["123", "456"]
    }
    """
    try:
        from notifications.multi_channel import NotificationManager
        
        payload = request.get_json(force=True) or {}
        
        manager = NotificationManager()
        result = manager.send_price_drop_alert(
            product=payload.get("product", {}),
            old_price=float(payload.get("old_price", 0)),
            new_price=float(payload.get("new_price", 0)),
            user_ids=payload.get("user_ids", []),
        )
        
        return jsonify({"success": True, **result})
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.post("/notifications/settings")
def update_notification_settings():
    """
    Update a user's notification preferences.
    
    Input:
    {
        "discord_id": "123456789",
        "phone_number": "+1234567890",
        "email": "user@example.com",
        "sms_enabled": true,
        "push_enabled": true,
        "sms_min_priority": "critical",
        ...
    }
    """
    try:
        from notifications.multi_channel import NotificationManager
        
        payload = request.get_json(force=True) or {}
        discord_id = payload.pop("discord_id", None)
        
        if not discord_id:
            return jsonify({"error": "discord_id required"})
        
        manager = NotificationManager()
        manager.update_user_prefs(discord_id, **payload)
        
        return jsonify({"success": True, "message": "Settings updated"})
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.get("/notifications/settings/<discord_id>")
def get_notification_settings(discord_id):
    """Get a user's notification preferences."""
    try:
        from notifications.multi_channel import NotificationManager
        
        manager = NotificationManager()
        prefs = manager.get_user_prefs(discord_id)
        
        if prefs:
            # Remove sensitive fields
            safe_prefs = {k: v for k, v in prefs.items() 
                        if k not in ("phone_number", "pushover_user_key")}
            return jsonify({"success": True, "preferences": safe_prefs})
        else:
            return jsonify({"success": True, "preferences": None, "message": "No preferences set"})
        
    except ImportError as e:
        return jsonify({"error": f"Import error: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "pokemon-multi-agent"})


@app.get("/agents")
def list_agents():
    """List all available agent endpoints."""
    return jsonify({
        "scanners": [
            {"name": "🔥 Unified Stock Checker", "endpoint": "/scanner/unified", "method": "GET/POST",
             "description": "BEST - Scans Target, Best Buy, GameStop, Pokemon Center, TCGPlayer"},
            {"name": "📦 All Retailers", "endpoint": "/scanner/all", "method": "GET/POST",
             "description": "Scan all sources for Pokemon products"},
            {"name": "🎴 Card Search", "endpoint": "/scanner/cards", "method": "GET/POST",
             "description": "Search Pokemon cards with TCGPlayer prices"},
            {"name": "🎯 Target", "endpoint": "/scanner/target", "method": "GET/POST",
             "description": "Target.com via Redsky API (WORKING)"},
            {"name": "🛒 Best Buy", "endpoint": "/scanner/bestbuy", "method": "GET/POST",
             "description": "BestBuy.com search"},
            {"name": "🎮 GameStop", "endpoint": "/scanner/gamestop", "method": "GET/POST",
             "description": "GameStop.com search"},
            {"name": "⭐ Pokemon Center", "endpoint": "/scanner/pokemoncenter", "method": "GET/POST",
             "description": "Official Pokemon store - has exclusives!"},
            {"name": "📍 Local Inventory (ZIP)", "endpoint": "/scanner/local", "method": "POST",
             "description": "Scan nearby stores by ZIP code"},
        ],
        "agents": [
            {"name": "Price Agent", "endpoint": "/agent/price", "method": "POST"},
            {"name": "Grading Agent", "endpoint": "/agent/grading", "method": "POST"},
            {"name": "Auto-Buy Agent", "endpoint": "/agent/autobuy", "method": "POST"},
        ],
        "vision": [
            {"name": "📸 Card Photo Scanner", "endpoint": "/vision/scan", "method": "POST",
             "description": "AI identifies card from photo, returns pricing & grade estimate"},
            {"name": "📸 Batch Photo Scan", "endpoint": "/vision/batch", "method": "POST",
             "description": "Scan multiple card photos at once"},
        ],
        "graders": [
            {"name": "Visual Grading (AI)", "endpoint": "/grader/analyze", "method": "POST", 
             "description": "Submit card image for AI grading prediction"},
            {"name": "Grading Standards", "endpoint": "/grader/standards", "method": "GET",
             "description": "Get PSA/CGC/Beckett grading criteria reference"},
            {"name": "Batch Grading", "endpoint": "/grader/batch", "method": "POST",
             "description": "Grade multiple cards at once"},
        ],
        "trends": [
            {"name": "📈 Card Price Trend", "endpoint": "/trends/card", "method": "POST",
             "description": "7-day price sparkline for a specific card"},
            {"name": "📊 Top Movers", "endpoint": "/trends/movers", "method": "GET",
             "description": "Top gaining and losing cards"},
            {"name": "📈 Bulk Trends", "endpoint": "/trends/bulk", "method": "POST",
             "description": "Get trends for multiple cards at once"},
        ],
        "market": [
            {"name": "Full Market Analysis", "endpoint": "/market/analysis", "method": "GET",
             "description": "Complete market sentiment, gainers/losers across all categories"},
            {"name": "Sealed Market", "endpoint": "/market/sealed", "method": "GET",
             "description": "Market data for sealed products (ETBs, Booster Boxes)"},
            {"name": "Raw Cards Market", "endpoint": "/market/raw", "method": "GET",
             "description": "Market data for raw (ungraded) cards"},
            {"name": "Slabs Market", "endpoint": "/market/slabs", "method": "GET",
             "description": "Market data for graded cards (PSA, CGC, BGS)"},
        ],
        "prices": [
            {"name": "💰 Card Prices (All Grades)", "endpoint": "/prices/card/<name>", "method": "GET/POST",
             "description": "Raw + PSA + CGC + BGS prices for any card"},
            {"name": "🏆 PSA Prices", "endpoint": "/prices/psa/<name>", "method": "GET/POST",
             "description": "PSA 10, 9, 8, 7 graded prices"},
            {"name": "🥇 CGC Prices", "endpoint": "/prices/cgc/<name>", "method": "GET/POST",
             "description": "CGC 10, 9.5, 9 graded prices"},
            {"name": "⭐ BGS Prices", "endpoint": "/prices/bgs/<name>", "method": "GET/POST",
             "description": "Beckett 10, 9.5, 9 graded prices"},
            {"name": "📊 Batch Prices", "endpoint": "/prices/batch", "method": "POST",
             "description": "Get prices for multiple cards at once"},
        ],
        "flip_calculator": [
            {"name": "🔄 Flip Calculator", "endpoint": "/flip/<card>", "method": "GET/POST",
             "description": "Calculate if grading a card is profitable - ROI analysis"},
            {"name": "💵 Grading Costs", "endpoint": "/flip/costs", "method": "GET",
             "description": "Get PSA, CGC, BGS pricing for all service levels"},
            {"name": "🔄 Batch Flip", "endpoint": "/flip/batch", "method": "POST",
             "description": "Calculate flip profitability for multiple cards"},
        ],
        "stock_map": [
            {"name": "🗺️ Local Stock Map", "endpoint": "/stockmap/<zip>", "method": "GET/POST",
             "description": "Find Pokemon TCG stock at nearby stores"},
            {"name": "🗺️ Compact Stock Map", "endpoint": "/stockmap/<zip>/compact", "method": "GET",
             "description": "Quick overview of stock by retailer"},
        ],
        "notifications": [
            {"name": "📱 Available Channels", "endpoint": "/notifications/channels", "method": "GET",
             "description": "Check which notification channels are configured (SMS, Push, Email)"},
            {"name": "📱 Send Alert", "endpoint": "/notifications/send", "method": "POST",
             "description": "Send multi-channel alert to a user"},
            {"name": "📱 Restock Alert", "endpoint": "/notifications/restock", "method": "POST",
             "description": "Send restock alerts to product watchers"},
            {"name": "📱 Price Drop Alert", "endpoint": "/notifications/price-drop", "method": "POST",
             "description": "Send price drop alerts"},
            {"name": "📱 User Settings", "endpoint": "/notifications/settings", "method": "POST",
             "description": "Update user notification preferences"},
        ],
        "pipelines": [
            {"name": "Full Pipeline", "endpoint": "/pipeline/full", "method": "POST"},
        ],
        "multiuser": [
            {"name": "Notify Users", "endpoint": "/users/notify", "method": "POST",
             "description": "Send deal alerts to users based on watchlists"},
            {"name": "Multi-User Auto-Buy", "endpoint": "/users/autobuy", "method": "POST",
             "description": "Execute auto-buy for all eligible users"},
            {"name": "User Stats", "endpoint": "/users/stats", "method": "GET",
             "description": "Get statistics about registered users"},
        ],
    })


# =============================================================================
# AUTHENTICATION SYSTEM (Discord OAuth)
# =============================================================================

try:
    from auth import (
        get_discord_auth_url,
        exchange_code_for_token,
        get_discord_user,
        verify_oauth_state,
        get_or_create_user,
        create_session,
        validate_session,
        invalidate_session,
        save_user_data,
        get_user_data,
        get_all_user_data,
        delete_user_data,
        check_rate_limit,
        sanitize_input,
        log_audit,
        require_auth,
        optional_auth,
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Auth module not loaded: {e}")
    AUTH_AVAILABLE = False


@app.route('/auth/discord', methods=['GET'])
def auth_discord_start():
    """Start Discord OAuth flow. Returns URL to redirect user to."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    ip = request.remote_addr or ''
    if not check_rate_limit(ip, 'auth_start', max_requests=10, window_seconds=60):
        return jsonify({'error': 'Rate limited. Try again later.'}), 429
    
    result = get_discord_auth_url()
    if 'error' in result:
        return jsonify(result), 503
    
    return jsonify(result)


@app.route('/auth/discord/callback', methods=['GET', 'POST'])
def auth_discord_callback():
    """
    Discord OAuth callback. Exchange code for token and create session.
    
    Query params:
    - code: Authorization code from Discord
    - state: CSRF state token
    
    Returns: Session token on success
    """
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    ip = request.remote_addr or ''
    if not check_rate_limit(ip, 'auth_callback', max_requests=5, window_seconds=60):
        log_audit(None, 'AUTH_RATE_LIMITED', f'IP: {ip}')
        return jsonify({'error': 'Rate limited. Try again later.'}), 429
    
    # Get parameters
    code = request.args.get('code') or request.form.get('code') or ''
    state = request.args.get('state') or request.form.get('state') or ''
    
    if not code or not state:
        return jsonify({'error': 'Missing code or state parameter'}), 400
    
    # Verify CSRF state
    if not verify_oauth_state(state):
        log_audit(None, 'AUTH_INVALID_STATE', f'IP: {ip}')
        return jsonify({'error': 'Invalid or expired state. Please try again.'}), 400
    
    # Exchange code for token
    token_data = exchange_code_for_token(code)
    if not token_data or 'access_token' not in token_data:
        log_audit(None, 'AUTH_TOKEN_EXCHANGE_FAILED', f'IP: {ip}')
        return jsonify({'error': 'Failed to authenticate with Discord'}), 400
    
    # Get user info
    discord_user = get_discord_user(token_data['access_token'])
    if not discord_user or 'id' not in discord_user:
        log_audit(None, 'AUTH_USER_FETCH_FAILED', f'IP: {ip}')
        return jsonify({'error': 'Failed to get user info from Discord'}), 400
    
    # Create/update user and create session
    user_id = get_or_create_user(discord_user)
    if not user_id:
        return jsonify({'error': 'Failed to create user'}), 500
    
    user_agent = request.headers.get('User-Agent', '')[:500]
    session_token = create_session(user_id, ip, user_agent)
    
    log_audit(user_id, 'LOGIN_SUCCESS', f'Discord: {discord_user.get("username")}')
    
    return jsonify({
        'success': True,
        'session_token': session_token,
        'user': {
            'id': user_id,
            'discord_id': discord_user.get('id'),
            'username': discord_user.get('username'),
            'avatar': discord_user.get('avatar'),
        }
    })


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Logout and invalidate session."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = request.json.get('session_token', '') if request.is_json else ''
    
    if token:
        user = validate_session(token)
        if user:
            log_audit(user['user_id'], 'LOGOUT')
        invalidate_session(token)
    
    return jsonify({'success': True})


@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Get current user info."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = validate_session(token)
    if not user:
        return jsonify({'error': 'Invalid or expired session'}), 401
    
    return jsonify({
        'user_id': user['user_id'],
        'discord_id': user['discord_id'],
        'username': user['username'],
        'avatar': user['avatar'],
    })


@app.route('/auth/data', methods=['GET'])
def auth_get_data():
    """Get all user data (portfolio, settings, etc.)."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = validate_session(token)
    if not user:
        return jsonify({'error': 'Invalid or expired session'}), 401
    
    data = get_all_user_data(user['user_id'])
    return jsonify({
        'success': True,
        'data': data
    })


@app.route('/auth/data/<data_type>', methods=['GET', 'PUT'])
def auth_data_type(data_type):
    """Get or update specific user data type (portfolio, settings, watchlist, autobuy_rules)."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    if data_type not in ['portfolio', 'settings', 'watchlist', 'autobuy_rules']:
        return jsonify({'error': 'Invalid data type'}), 400
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = validate_session(token)
    if not user:
        return jsonify({'error': 'Invalid or expired session'}), 401
    
    ip = request.remote_addr or ''
    
    if request.method == 'GET':
        data = get_user_data(user['user_id'], data_type)
        return jsonify({'success': True, data_type: data})
    
    else:  # PUT
        if not check_rate_limit(ip, f'save_{data_type}', max_requests=30, window_seconds=60):
            return jsonify({'error': 'Rate limited'}), 429
        
        try:
            new_data = request.json.get(data_type) if request.is_json else None
            if new_data is None:
                return jsonify({'error': f'Missing {data_type} in request body'}), 400
            
            save_user_data(user['user_id'], data_type, new_data)
            log_audit(user['user_id'], f'DATA_UPDATED_{data_type.upper()}')
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


@app.route('/auth/delete', methods=['DELETE'])
def auth_delete_data():
    """Delete all user data (GDPR compliance)."""
    if not AUTH_AVAILABLE:
        return jsonify({'error': 'Authentication not configured'}), 503
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = validate_session(token)
    if not user:
        return jsonify({'error': 'Invalid or expired session'}), 401
    
    # Require confirmation
    confirm = request.json.get('confirm', False) if request.is_json else False
    if not confirm:
        return jsonify({'error': 'Must confirm deletion by setting confirm: true'}), 400
    
    delete_user_data(user['user_id'])
    return jsonify({'success': True, 'message': 'All user data has been deleted'})


# =============================================================================
# STRIPE & PAYPAL PAYMENT ENDPOINTS
# =============================================================================

# In production, set these environment variables
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' or 'live'

@app.route('/payments/stripe/create-setup-intent', methods=['POST'])
def stripe_create_setup_intent():
    """
    Create a Stripe SetupIntent for saving card details securely.
    
    The SetupIntent allows you to collect card details without charging,
    storing a PaymentMethod for future use.
    
    Returns:
    - client_secret: Use with Stripe.js on frontend
    """
    if not STRIPE_SECRET_KEY:
        return jsonify({
            'error': 'Stripe not configured',
            'demo_mode': True,
            'message': 'Set STRIPE_SECRET_KEY for live payments'
        }), 503
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get user from session (optional - can work without auth)
        customer_id = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer ') and AUTH_AVAILABLE:
            token = auth_header[7:]
            user = validate_session(token)
            if user:
                # Check if user has a Stripe customer ID stored
                user_data = get_all_user_data(user['user_id']) or {}
                if user_data.get('stripe_customer_id'):
                    customer_id = user_data['stripe_customer_id']
        
        # Create SetupIntent
        intent_params = {
            'usage': 'off_session',  # Allow charging later
            'automatic_payment_methods': {
                'enabled': True,
            },
        }
        if customer_id:
            intent_params['customer'] = customer_id
            
        setup_intent = stripe.SetupIntent.create(**intent_params)
        
        return jsonify({
            'client_secret': setup_intent.client_secret,
            'setup_intent_id': setup_intent.id
        })
        
    except ImportError:
        return jsonify({
            'error': 'Stripe library not installed',
            'message': 'pip install stripe'
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/payments/stripe/confirm-setup', methods=['POST'])
def stripe_confirm_setup():
    """
    Confirm that a SetupIntent was successful and save payment method info.
    
    Body:
    - setup_intent_id: The SetupIntent ID
    - payment_method_id: The PaymentMethod ID
    """
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        data = request.get_json() or {}
        pm_id = data.get('payment_method_id')
        
        if not pm_id:
            return jsonify({'error': 'payment_method_id required'}), 400
        
        # Retrieve PaymentMethod to get card details
        pm = stripe.PaymentMethod.retrieve(pm_id)
        
        card_info = {
            'payment_method_id': pm.id,
            'brand': pm.card.brand if pm.card else 'card',
            'last4': pm.card.last4 if pm.card else '****',
            'exp_month': pm.card.exp_month if pm.card else None,
            'exp_year': pm.card.exp_year if pm.card else None,
        }
        
        # If user is authenticated, save to their profile
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer ') and AUTH_AVAILABLE:
            token = auth_header[7:]
            user = validate_session(token)
            if user:
                stripe_payment = {
                    'provider': 'stripe',
                    'last4': card_info['last4'],
                    'brand': card_info['brand'],
                    'expMonth': card_info['exp_month'],
                    'expYear': card_info['exp_year'],
                    'connectedAt': datetime.now().isoformat()
                }
                save_user_data(user['user_id'], 'stripe_payment', stripe_payment)
        
        return jsonify({
            'success': True,
            'card': card_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/payments/paypal/create-order', methods=['POST'])
def paypal_create_order():
    """
    Create a PayPal order for saving payment method.
    
    In production, use PayPal's Vault flow for saving payment methods.
    """
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return jsonify({
            'error': 'PayPal not configured',
            'demo_mode': True,
            'message': 'Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET'
        }), 503
    
    try:
        import requests as req
        
        # Get access token
        base_url = 'https://api-m.sandbox.paypal.com' if PAYPAL_MODE == 'sandbox' else 'https://api-m.paypal.com'
        
        auth_response = req.post(
            f'{base_url}/v1/oauth2/token',
            data={'grant_type': 'client_credentials'},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
        )
        
        if auth_response.status_code != 200:
            return jsonify({'error': 'Failed to authenticate with PayPal'}), 500
            
        access_token = auth_response.json()['access_token']
        
        # Create vault setup token (for saving payment method without charging)
        setup_response = req.post(
            f'{base_url}/v3/vault/setup-tokens',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={
                'payment_source': {
                    'paypal': {
                        'experience_context': {
                            'return_url': request.host_url + 'payments/paypal/callback',
                            'cancel_url': request.host_url + 'payments/paypal/cancel'
                        }
                    }
                }
            }
        )
        
        if setup_response.status_code in [200, 201]:
            data = setup_response.json()
            return jsonify({
                'id': data.get('id'),
                'links': data.get('links', [])
            })
        else:
            return jsonify({'error': 'Failed to create PayPal setup'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/payments/paypal/confirm', methods=['POST'])
def paypal_confirm():
    """
    Confirm PayPal connection and save payment method.
    
    Body:
    - email: PayPal email (from OAuth)
    - payer_id: PayPal Payer ID (optional)
    """
    data = request.get_json() or {}
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'email required'}), 400
    
    paypal_info = {
        'provider': 'paypal',
        'email': email,
        'payer_id': data.get('payer_id'),
        'connectedAt': datetime.now().isoformat()
    }
    
    # If user is authenticated, save to their profile
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and AUTH_AVAILABLE:
        token = auth_header[7:]
        user = validate_session(token)
        if user:
            save_user_data(user['user_id'], 'paypal_payment', paypal_info)
    
    return jsonify({
        'success': True,
        'paypal': {
            'email': email,
            'provider': 'paypal'
        }
    })


@app.route('/payments/status', methods=['GET'])
def payment_status():
    """
    Get payment method status for current user.
    """
    result = {
        'stripe_configured': bool(STRIPE_SECRET_KEY),
        'paypal_configured': bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET),
        'stripe_connected': False,
        'paypal_connected': False
    }
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and AUTH_AVAILABLE:
        token = auth_header[7:]
        user = validate_session(token)
        if user:
            data = get_all_user_data(user['user_id']) or {}
            stripe_payment = data.get('stripe_payment')
            paypal_payment = data.get('paypal_payment')
            result['stripe_connected'] = bool(stripe_payment)
            result['paypal_connected'] = bool(paypal_payment)
            if stripe_payment:
                result['stripe_last4'] = stripe_payment.get('last4')
                result['stripe_brand'] = stripe_payment.get('brand')
            if paypal_payment:
                result['paypal_email'] = paypal_payment.get('email')
    
    return jsonify(result)


# =============================================================================
# LIVE DROP INTEL - Reddit & PokeBeach Integration
# =============================================================================

import re
import xml.etree.ElementTree as ET

# Reddit API (no auth needed for public subreddits)
REDDIT_USER_AGENT = 'PokeAgent/1.0 (Pokemon TCG Drop Tracker)'

@app.route('/drops/reddit', methods=['GET'])
def get_reddit_drops():
    """
    Fetch drop intel from Reddit.
    Scrapes r/PokemonTCG and r/PokeInvesting for restock/drop posts.
    """
    try:
        import requests as req
        
        subreddits = ['PokemonTCG', 'PokeInvesting', 'pokemoncardcollectors']
        keywords = ['restock', 'drop', 'in stock', 'available', 'found', 'wave', 'release', 'preorder', 'pre-order']
        
        all_posts = []
        
        for subreddit in subreddits:
            try:
                url = f'https://www.reddit.com/r/{subreddit}/new.json?limit=50'
                headers = {'User-Agent': REDDIT_USER_AGENT}
                
                resp = req.get(url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        p = post.get('data', {})
                        title = p.get('title', '').lower()
                        
                        # Filter for relevant posts
                        if any(kw in title for kw in keywords):
                            # Extract retailer mentions
                            retailers = []
                            retailer_keywords = {
                                'target': 'Target',
                                'walmart': 'Walmart', 
                                'bestbuy': 'Best Buy',
                                'best buy': 'Best Buy',
                                'gamestop': 'GameStop',
                                'pokemon center': 'Pokemon Center',
                                'costco': 'Costco',
                                'amazon': 'Amazon',
                                'barnes': 'Barnes & Noble'
                            }
                            for kw, name in retailer_keywords.items():
                                if kw in title:
                                    retailers.append(name)
                            
                            # Extract product types
                            products = []
                            product_keywords = ['etb', 'booster', 'box', 'bundle', 'tin', 'blister', 'collection']
                            for pk in product_keywords:
                                if pk in title:
                                    products.append(pk.upper() if pk == 'etb' else pk.title())
                            
                            all_posts.append({
                                'title': p.get('title', ''),
                                'subreddit': subreddit,
                                'url': f"https://reddit.com{p.get('permalink', '')}",
                                'score': p.get('score', 0),
                                'comments': p.get('num_comments', 0),
                                'created': p.get('created_utc', 0),
                                'author': p.get('author', ''),
                                'retailers': retailers,
                                'products': products,
                                'flair': p.get('link_flair_text', ''),
                                'source': f'r/{subreddit}'
                            })
            except Exception as e:
                print(f"Error fetching r/{subreddit}: {e}")
                continue
        
        # Sort by score (most upvoted = most reliable)
        all_posts.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'success': True,
            'posts': all_posts[:30],  # Top 30 posts
            'count': len(all_posts),
            'subreddits': subreddits
        })
        
    except ImportError:
        return jsonify({'error': 'requests library not available'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/drops/pokebeach', methods=['GET'])
def get_pokebeach_news():
    """
    Fetch news from PokeBeach RSS feed.
    Great source for official Pokemon TCG announcements.
    """
    try:
        import requests as req
        
        # PokeBeach RSS feed
        rss_url = 'https://www.pokebeach.com/feed'
        headers = {'User-Agent': REDDIT_USER_AGENT}
        
        resp = req.get(rss_url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch PokeBeach RSS'}), 503
        
        # Parse RSS XML
        root = ET.fromstring(resp.content)
        
        news_items = []
        keywords = ['tcg', 'card', 'set', 'release', 'product', 'collection', 'expansion', 'promo', 'reprint']
        
        for item in root.findall('.//item'):
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            description = item.find('description')
            
            title_text = title.text if title is not None else ''
            
            # Filter for TCG-related news
            if any(kw in title_text.lower() for kw in keywords):
                # Try to extract set name
                set_patterns = [
                    r'(Prismatic Evolutions?)',
                    r'(Surging Sparks?)',
                    r'(Stellar Crown)',
                    r'(Shrouded Fable)',
                    r'(Twilight Masquerade)',
                    r'(Journey Together)',
                    r'(Destined Rivals)',
                    r'(Scarlet & Violet)',
                    r'(Paldea Evolved)',
                    r'(Obsidian Flames)',
                    r'(151)',
                    r'(Paradox Rift)',
                    r'(Temporal Forces)',
                ]
                
                set_name = None
                for pattern in set_patterns:
                    match = re.search(pattern, title_text, re.IGNORECASE)
                    if match:
                        set_name = match.group(1)
                        break
                
                news_items.append({
                    'title': title_text,
                    'url': link.text if link is not None else '',
                    'date': pub_date.text if pub_date is not None else '',
                    'description': (description.text[:200] + '...') if description is not None and description.text else '',
                    'set': set_name,
                    'source': 'PokeBeach'
                })
        
        return jsonify({
            'success': True,
            'news': news_items[:20],  # Latest 20 articles
            'count': len(news_items)
        })
        
    except ImportError:
        return jsonify({'error': 'requests library not available'}), 503
    except ET.ParseError as e:
        return jsonify({'error': f'Failed to parse RSS: {e}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/drops/twitter', methods=['GET'])
def get_twitter_drops():
    """
    Fetch drop intel from X (Twitter) via Nitter instances.
    Searches Pokemon TCG related hashtags and accounts.
    """
    try:
        import requests as req
        from bs4 import BeautifulSoup
        
        # Nitter instances (public Twitter mirrors)
        nitter_instances = [
            'https://nitter.net',
            'https://nitter.privacydev.net',
            'https://nitter.poast.org'
        ]
        
        # Search terms for Pokemon TCG drops
        search_queries = [
            'pokemon tcg restock',
            'pokemon cards target',
            'pokemon cards walmart',
            '#PokemonTCG restock',
            '#PokemonRestock'
        ]
        
        # Key accounts to check
        accounts = [
            'PokeGuardian',
            'PokemonTCGDrops', 
            'poikimon',
            'CardCollectorNT'
        ]
        
        all_tweets = []
        
        # Try each Nitter instance until one works
        working_instance = None
        for instance in nitter_instances:
            try:
                test_resp = req.get(f'{instance}/search?q=pokemon', headers={'User-Agent': REDDIT_USER_AGENT}, timeout=5)
                if test_resp.status_code == 200:
                    working_instance = instance
                    break
            except:
                continue
        
        if not working_instance:
            # Fallback: Return curated list of Pokemon TCG Twitter accounts
            return jsonify({
                'success': True,
                'source': 'X (Twitter)',
                'posts': [
                    {
                        'title': 'Follow @PokeGuardian for Pokemon TCG news and restocks',
                        'url': 'https://twitter.com/PokeGuardian',
                        'source': '@PokeGuardian',
                        'platform': 'twitter',
                        'type': 'account'
                    },
                    {
                        'title': 'Follow @poikimon for Target/Walmart restock alerts',
                        'url': 'https://twitter.com/poikimon',
                        'source': '@poikimon',
                        'platform': 'twitter',
                        'type': 'account'
                    },
                    {
                        'title': 'Search #PokemonRestock on X for live updates',
                        'url': 'https://twitter.com/search?q=%23PokemonRestock',
                        'source': '#PokemonRestock',
                        'platform': 'twitter',
                        'type': 'hashtag'
                    }
                ],
                'note': 'Live Twitter search unavailable - showing recommended accounts'
            })
        
        # Search for Pokemon TCG restocks
        for query in search_queries[:2]:  # Limit to avoid rate limits
            try:
                search_url = f'{working_instance}/search?q={query.replace(" ", "+")}&f=tweets'
                resp = req.get(search_url, headers={'User-Agent': REDDIT_USER_AGENT}, timeout=10)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    tweets = soup.select('.timeline-item')[:5]
                    
                    for tweet in tweets:
                        content = tweet.select_one('.tweet-content')
                        username = tweet.select_one('.username')
                        
                        if content:
                            text = content.get_text(strip=True)[:200]
                            user = username.get_text(strip=True) if username else 'Unknown'
                            
                            # Extract retailers mentioned
                            retailers = []
                            for r in ['Target', 'Walmart', 'Best Buy', 'GameStop', 'Amazon', 'Costco']:
                                if r.lower() in text.lower():
                                    retailers.append(r)
                            
                            all_tweets.append({
                                'title': text,
                                'url': f'https://twitter.com{tweet.select_one("a.tweet-link")["href"] if tweet.select_one("a.tweet-link") else ""}',
                                'source': f'@{user}',
                                'platform': 'twitter',
                                'retailers': retailers,
                                'score': len(retailers) * 10 + 5
                            })
            except Exception as e:
                print(f'Twitter search error: {e}')
                continue
        
        return jsonify({
            'success': True,
            'source': 'X (Twitter)',
            'posts': all_tweets[:15],
            'total': len(all_tweets)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'posts': []}), 500


@app.route('/drops/instagram', methods=['GET'])
def get_instagram_drops():
    """
    Fetch drop intel from Instagram.
    Returns curated list of Pokemon TCG influencers since Instagram API requires auth.
    """
    try:
        # Instagram requires authentication for API access
        # Return curated list of Pokemon TCG Instagram accounts to follow
        
        influencers = [
            {
                'title': 'Pokemon TCG official restocks and news',
                'url': 'https://www.instagram.com/pokemontcg/',
                'source': '@pokemontcg',
                'platform': 'instagram',
                'followers': '1.2M',
                'type': 'official'
            },
            {
                'title': 'Pokemon restock alerts and card pulls',
                'url': 'https://www.instagram.com/pokemonrestock/',
                'source': '@pokemonrestock',
                'platform': 'instagram',
                'type': 'community'
            },
            {
                'title': 'Card collection tips and market analysis',
                'url': 'https://www.instagram.com/pokerev/',
                'source': '@pokerev',
                'platform': 'instagram',
                'followers': '500K+',
                'type': 'influencer'
            },
            {
                'title': 'Pokemon card investments and pricing',
                'url': 'https://www.instagram.com/pokemon.investments/',
                'source': '@pokemon.investments',
                'platform': 'instagram',
                'type': 'community'
            },
            {
                'title': 'Daily Pokemon card content and restocks',
                'url': 'https://www.instagram.com/explore/tags/pokemontcgrestock/',
                'source': '#pokemontcgrestock',
                'platform': 'instagram',
                'type': 'hashtag'
            }
        ]
        
        return jsonify({
            'success': True,
            'source': 'Instagram',
            'posts': influencers,
            'total': len(influencers),
            'note': 'Instagram API requires authentication - showing recommended accounts to follow'
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'posts': []}), 500


@app.route('/drops/tiktok', methods=['GET'])
def get_tiktok_drops():
    """
    Fetch drop intel from TikTok.
    Returns curated list since TikTok API requires auth.
    """
    try:
        # TikTok requires authentication for API access
        # Return curated list of Pokemon TCG TikTok accounts
        
        creators = [
            {
                'title': 'Pokemon TCG pack openings and news',
                'url': 'https://www.tiktok.com/@pokemon',
                'source': '@pokemon',
                'platform': 'tiktok',
                'type': 'official'
            },
            {
                'title': 'Daily restock alerts and hunting tips',
                'url': 'https://www.tiktok.com/@pokemontcgcommunity',
                'source': '@pokemontcgcommunity',
                'platform': 'tiktok',
                'type': 'community'
            },
            {
                'title': 'Card pulls and collection tips',
                'url': 'https://www.tiktok.com/@pokemoncards',
                'source': '@pokemoncards',
                'platform': 'tiktok',
                'type': 'community'
            },
            {
                'title': 'Search #PokemonRestock for live videos',
                'url': 'https://www.tiktok.com/tag/pokemonrestock',
                'source': '#pokemonrestock',
                'platform': 'tiktok',
                'type': 'hashtag'
            },
            {
                'title': 'Search #PokemonTCG for trending content',
                'url': 'https://www.tiktok.com/tag/pokemontcg',
                'source': '#pokemontcg',
                'platform': 'tiktok',
                'type': 'hashtag'
            }
        ]
        
        return jsonify({
            'success': True,
            'source': 'TikTok',
            'posts': creators,
            'total': len(creators),
            'note': 'TikTok API requires authentication - showing recommended accounts to follow'
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'posts': []}), 500


@app.route('/drops/rumors', methods=['GET'])
def get_rumors():
    """
    Fetch rumors and speculation from all sources.
    Filters posts for unconfirmed/rumor keywords.
    """
    try:
        import requests as req
        
        rumor_keywords = [
            'rumor', 'rumored', 'rumours', 'rumoured',
            'speculation', 'speculated', 'speculating',
            'leak', 'leaked', 'leaking',
            'unconfirmed', 'unverified',
            'might', 'possibly', 'could be', 'may',
            'hearing', 'source says', 'allegedly', 'reportedly',
            'insider', 'insider info', 'according to sources'
        ]
        
        all_rumors = []
        base_url = f'http://127.0.0.1:{os.environ.get("PORT", 5001)}'
        
        # Fetch Reddit posts and filter for rumors
        try:
            reddit_resp = req.get(f'{base_url}/drops/reddit', timeout=10)
            if reddit_resp.status_code == 200:
                reddit_data = reddit_resp.json()
                posts = reddit_data.get('posts', [])
                
                for post in posts:
                    title_lower = (post.get('title', '') or '').lower()
                    if any(keyword in title_lower for keyword in rumor_keywords):
                        all_rumors.append({
                            'title': post.get('title', ''),
                            'url': post.get('url', ''),
                            'source': post.get('source', 'Reddit'),
                            'date': post.get('created', 0),
                            'type': 'reddit',
                            'score': post.get('score', 0)
                        })
        except:
            pass
        
        # Fetch Twitter posts and filter for rumors
        try:
            twitter_resp = req.get(f'{base_url}/drops/twitter', timeout=10)
            if twitter_resp.status_code == 200:
                twitter_data = twitter_resp.json()
                posts = twitter_data.get('posts', [])
                
                for post in posts:
                    title_lower = (post.get('title', '') or '').lower()
                    if any(keyword in title_lower for keyword in rumor_keywords):
                        all_rumors.append({
                            'title': post.get('title', ''),
                            'url': post.get('url', ''),
                            'source': post.get('source', 'Twitter'),
                            'date': int(time.time()),
                            'type': 'twitter',
                            'score': post.get('score', 0)
                        })
        except:
            pass
        
        # Sort by score (most engagement first)
        all_rumors.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'source': 'Rumors & Speculation',
            'rumors': all_rumors[:20],  # Limit to top 20
            'total': len(all_rumors)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'rumors': []}), 500


@app.route('/drops/all', methods=['GET'])
def get_all_drop_intel():
    """
    Aggregate drop intel from all sources.
    Combines Reddit + PokeBeach + Twitter + Instagram + TikTok into a unified feed.
    """
    try:
        import requests as req
        
        base_url = f'http://127.0.0.1:{os.environ.get("PORT", 5001)}'
        
        intel = {
            'reddit': [],
            'pokebeach': [],
            'twitter': [],
            'instagram': [],
            'tiktok': [],
            'combined': []
        }
        
        # Fetch Reddit
        try:
            reddit_resp = req.get(f'{base_url}/drops/reddit', timeout=15)
            if reddit_resp.status_code == 200:
                reddit_data = reddit_resp.json()
                intel['reddit'] = reddit_data.get('posts', [])
        except:
            pass
        
        # Fetch PokeBeach
        try:
            pb_resp = req.get(f'{base_url}/drops/pokebeach', timeout=15)
            if pb_resp.status_code == 200:
                pb_data = pb_resp.json()
                intel['pokebeach'] = pb_data.get('news', [])
        except:
            pass
        
        # Fetch Twitter
        try:
            twitter_resp = req.get(f'{base_url}/drops/twitter', timeout=15)
            if twitter_resp.status_code == 200:
                twitter_data = twitter_resp.json()
                intel['twitter'] = twitter_data.get('posts', [])
        except:
            pass
        
        # Fetch Instagram
        try:
            ig_resp = req.get(f'{base_url}/drops/instagram', timeout=15)
            if ig_resp.status_code == 200:
                ig_data = ig_resp.json()
                intel['instagram'] = ig_data.get('posts', [])
        except:
            pass
        
        # Fetch TikTok
        try:
            tt_resp = req.get(f'{base_url}/drops/tiktok', timeout=15)
            if tt_resp.status_code == 200:
                tt_data = tt_resp.json()
                intel['tiktok'] = tt_data.get('posts', [])
        except:
            pass
        
        # Combine and sort by date
        for post in intel['reddit']:
            intel['combined'].append({
                'type': 'reddit',
                'title': post.get('title'),
                'url': post.get('url'),
                'source': post.get('source'),
                'score': post.get('score', 0),
                'timestamp': post.get('created', 0),
                'retailers': post.get('retailers', []),
                'products': post.get('products', [])
            })
        
        for news in intel['pokebeach']:
            intel['combined'].append({
                'type': 'news',
                'title': news.get('title'),
                'url': news.get('url'),
                'source': 'PokeBeach',
                'score': 100,  # News gets high score
                'date': news.get('date'),
                'set': news.get('set')
            })
        
        for tweet in intel['twitter']:
            intel['combined'].append({
                'type': 'twitter',
                'title': tweet.get('title'),
                'url': tweet.get('url'),
                'source': tweet.get('source'),
                'platform': 'twitter',
                'score': tweet.get('score', 50),
                'retailers': tweet.get('retailers', [])
            })
        
        for post in intel['instagram']:
            intel['combined'].append({
                'type': 'instagram',
                'title': post.get('title'),
                'url': post.get('url'),
                'source': post.get('source'),
                'platform': 'instagram',
                'score': 30
            })
        
        for post in intel['tiktok']:
            intel['combined'].append({
                'type': 'tiktok',
                'title': post.get('title'),
                'url': post.get('url'),
                'source': post.get('source'),
                'platform': 'tiktok',
                'score': 25
            })
        
        # Sort combined by score/relevance
        intel['combined'].sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'intel': intel,
            'total': len(intel['combined']),
            'sources': ['Reddit', 'PokeBeach', 'X (Twitter)', 'Instagram', 'TikTok']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    print("🎴 LO TCG Multi-Agent Server Starting...")
    print("📡 Endpoints available at http://127.0.0.1:5001")
    print("⚡ Stealth mode: User-agent rotation, jitter, anti-detection enabled")
    print("")
    print("📦 SCANNERS (4 retailers + TCGPlayer):")
    print("   - /scanner/target (Redsky API - WORKING)")
    print("   - /scanner/bestbuy, /scanner/gamestop, /scanner/pokemoncenter")
    print("   - /scanner/all (scans ALL retailers)")
    print("   - /scanner/unified (BEST - multi-method scanning)")
    print("   - /scanner/local (ZIP code based - scans nearby stores!)")
    print("")
    print("📸 PHOTO CARD SCANNER (NEW!):")
    print("   - /vision/scan (AI identifies card from photo → name, set, price, grade)")
    print("   - /vision/batch (scan multiple cards at once)")
    print("")
    print("📈 PRICE TRENDS & SPARKLINES (NEW!):")
    print("   - /trends/card (7-day price trend with sparkline graph)")
    print("   - /trends/movers (top gaining & losing cards)")
    print("   - /trends/bulk (trends for multiple cards)")
    print("")
    print("📱 MULTI-CHANNEL NOTIFICATIONS (NEW!):")
    print("   - /notifications/channels (check configured channels)")
    print("   - /notifications/send (SMS + Push + Email + Discord)")
    print("   - /notifications/restock (restock alerts to watchers)")
    print("   - /notifications/price-drop (price drop alerts)")
    print("   - /notifications/settings (user preferences)")
    print("")
    print("🤖 AGENTS:")
    print("   - /agent/price (market price analysis)")
    print("   - /agent/grading (ROI evaluation)")
    print("   - /agent/autobuy (auto-purchase)")
    print("")
    print("🔍 AI VISUAL GRADING:")
    print("   - /grader/analyze (submit card image for AI grading)")
    print("   - /grader/standards (PSA/CGC/Beckett criteria reference)")
    print("")
    print("📊 MARKET ANALYSIS:")
    print("   - /market/analysis (full market sentiment & gainers/losers)")
    print("")
    print("🚀 PIPELINES:")
    print("   - /pipeline/full (runs entire scan→price→grade→buy pipeline)")
    print("")
    print("👥 MULTI-USER:")
    print("   - /users/notify, /users/autobuy, /users/stats")
    print("")
    app.run(host="127.0.0.1", port=5001, debug=True)
