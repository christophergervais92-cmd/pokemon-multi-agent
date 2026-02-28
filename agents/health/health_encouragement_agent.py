#!/usr/bin/env python3
"""
Health Encouragement Agent

Scans the internet for supportive content for people on their
weight loss and health journey. Presents content in HN-style ranking.

This is NOT about making fun of anyone - it's about finding and
sharing encouraging stories, tips, and motivation.
"""

import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

# Local imports
from .content_sources import (
    HealthContent,
    aggregate_and_rank_content,
    get_cached_content,
    save_content_to_json,
    load_content_from_json,
    fetch_reddit_posts,
    get_motivational_quotes,
    REDDIT_SUBREDDITS,
)

# Try to import Flask for API server
try:
    from flask import Flask, jsonify, render_template_string, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "refresh_interval": 900,  # 15 minutes
    "max_items": 50,
    "include_reddit": True,
    "include_rss": True,
    "include_quotes": True,
    "categories": ["success_story", "motivation", "tip", "community", "news"],
    "api_port": 5050,
}


class HealthEncouragementAgent:
    """
    Agent that aggregates and serves health encouragement content.
    
    Features:
    - Scans Reddit communities for success stories and support
    - Fetches health news from RSS feeds
    - Ranks content using HN-style algorithm
    - Serves content via API for HN-style frontend
    """
    
    def __init__(self, config: Dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.content: List[HealthContent] = []
        self.last_refresh: Optional[datetime] = None
        self.app = None
        
    def refresh_content(self, force: bool = False) -> List[HealthContent]:
        """
        Refresh content from all sources.
        
        Args:
            force: Force refresh even if cache is valid
        
        Returns:
            List of ranked HealthContent
        """
        # Check if refresh is needed
        if not force and self.last_refresh:
            elapsed = (datetime.now() - self.last_refresh).total_seconds()
            if elapsed < self.config["refresh_interval"]:
                return self.content
        
        print(f"[{datetime.now().isoformat()}] Refreshing health content...")
        
        self.content = aggregate_and_rank_content(
            include_reddit=self.config["include_reddit"],
            include_rss=self.config["include_rss"],
            include_quotes=self.config["include_quotes"],
            max_items=self.config["max_items"],
        )
        
        self.last_refresh = datetime.now()
        print(f"[{datetime.now().isoformat()}] Loaded {len(self.content)} items")
        
        return self.content
    
    def get_content(
        self,
        category: str = None,
        source: str = None,
        limit: int = 30,
        offset: int = 0,
    ) -> List[HealthContent]:
        """
        Get filtered content.
        
        Args:
            category: Filter by category
            source: Filter by source
            limit: Max items to return
            offset: Pagination offset
        
        Returns:
            Filtered list of HealthContent
        """
        # Ensure content is loaded
        if not self.content:
            self.refresh_content()
        
        filtered = self.content
        
        # Apply filters
        if category:
            filtered = [c for c in filtered if c.category == category]
        
        if source:
            filtered = [c for c in filtered if source.lower() in c.source.lower()]
        
        # Paginate
        return filtered[offset:offset + limit]
    
    def get_content_by_id(self, content_id: str) -> Optional[HealthContent]:
        """Get a specific content item by ID."""
        for item in self.content:
            if item.id == content_id:
                return item
        return None
    
    def get_categories(self) -> List[Dict]:
        """Get list of available categories with counts."""
        category_counts = {}
        for item in self.content:
            cat = item.category
            if cat not in category_counts:
                category_counts[cat] = {"name": cat, "count": 0}
            category_counts[cat]["count"] += 1
        
        return list(category_counts.values())
    
    def get_sources(self) -> List[Dict]:
        """Get list of available sources with counts."""
        source_counts = {}
        for item in self.content:
            src = item.source
            if src not in source_counts:
                source_counts[src] = {"name": src, "count": 0}
            source_counts[src]["count"] += 1
        
        return sorted(source_counts.values(), key=lambda x: x["count"], reverse=True)
    
    def to_json(self) -> str:
        """Export content as JSON."""
        return json.dumps([c.to_dict() for c in self.content], indent=2, default=str)
    
    def save(self, filepath: str):
        """Save content to file."""
        save_content_to_json(self.content, filepath)
    
    def load(self, filepath: str):
        """Load content from file."""
        self.content = load_content_from_json(filepath)
        self.last_refresh = datetime.now()


# =============================================================================
# API SERVER
# =============================================================================

def create_api_server(agent: HealthEncouragementAgent) -> Optional[Any]:
    """
    Create Flask API server for the agent.
    
    Endpoints:
    - GET /api/content - Get ranked content
    - GET /api/content/<id> - Get specific item
    - GET /api/categories - Get categories
    - GET /api/sources - Get sources
    - POST /api/refresh - Force refresh
    """
    if not FLASK_AVAILABLE:
        print("Flask not available. Install: pip install flask flask-cors")
        return None
    
    app = Flask(__name__)
    CORS(app)
    
    @app.route("/api/content")
    def get_content():
        category = request.args.get("category")
        source = request.args.get("source")
        limit = int(request.args.get("limit", 30))
        offset = int(request.args.get("offset", 0))
        
        content = agent.get_content(
            category=category,
            source=source,
            limit=limit,
            offset=offset,
        )
        
        return jsonify({
            "success": True,
            "count": len(content),
            "total": len(agent.content),
            "items": [c.to_dict() for c in content],
        })
    
    @app.route("/api/content/<content_id>")
    def get_content_item(content_id):
        item = agent.get_content_by_id(content_id)
        if item:
            return jsonify({"success": True, "item": item.to_dict()})
        return jsonify({"success": False, "error": "Not found"}), 404
    
    @app.route("/api/categories")
    def get_categories():
        return jsonify({
            "success": True,
            "categories": agent.get_categories(),
        })
    
    @app.route("/api/sources")
    def get_sources():
        return jsonify({
            "success": True,
            "sources": agent.get_sources(),
        })
    
    @app.route("/api/refresh", methods=["POST"])
    def refresh():
        agent.refresh_content(force=True)
        return jsonify({
            "success": True,
            "count": len(agent.content),
            "refreshed_at": agent.last_refresh.isoformat(),
        })
    
    @app.route("/api/stats")
    def get_stats():
        return jsonify({
            "success": True,
            "total_items": len(agent.content),
            "last_refresh": agent.last_refresh.isoformat() if agent.last_refresh else None,
            "categories": agent.get_categories(),
            "top_sources": agent.get_sources()[:10],
        })
    
    @app.route("/")
    def index():
        """Redirect to the main dashboard."""
        return """
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=/health_dashboard.html" />
        </head>
        <body>
            <p>Redirecting to <a href="/health_dashboard.html">Health Encouragement Dashboard</a>...</p>
        </body>
        </html>
        """
    
    return app


def run_server(agent: HealthEncouragementAgent, port: int = 5050, debug: bool = False):
    """Run the API server."""
    app = create_api_server(agent)
    if app:
        print(f"Starting Health Encouragement API on port {port}...")
        print(f"Dashboard: http://localhost:{port}/")
        print(f"API: http://localhost:{port}/api/content")
        app.run(host="0.0.0.0", port=port, debug=debug)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Health Encouragement Agent - Supportive content aggregator"
    )
    
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run API server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="API server port (default: 5050)"
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch content and print to stdout"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save content to JSON file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Max items to fetch"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["success_story", "motivation", "tip", "community", "news"],
        help="Filter by category"
    )
    parser.add_argument(
        "--no-reddit",
        action="store_true",
        help="Disable Reddit fetching"
    )
    parser.add_argument(
        "--no-rss",
        action="store_true",
        help="Disable RSS fetching"
    )
    
    args = parser.parse_args()
    
    # Create agent
    config = {
        "include_reddit": not args.no_reddit,
        "include_rss": not args.no_rss,
        "max_items": args.limit,
    }
    
    agent = HealthEncouragementAgent(config)
    
    if args.server:
        # Run API server
        agent.refresh_content()
        run_server(agent, port=args.port)
    
    elif args.fetch or args.output:
        # Fetch and output content
        agent.refresh_content()
        
        content = agent.get_content(category=args.category, limit=args.limit)
        
        if args.output:
            agent.save(args.output)
            print(f"Saved {len(content)} items to {args.output}")
        else:
            # Print HN-style output
            print("\n" + "=" * 70)
            print("  HEALTH ENCOURAGEMENT - Supporting Your Journey")
            print("=" * 70)
            
            for i, item in enumerate(content, 1):
                print(f"\n{i}. {item.title[:65]}")
                print(f"   {item.score} points | {item.source} | {item.comments} comments")
                if item.summary and item.category != "motivation":
                    summary = item.summary[:80].replace("\n", " ")
                    print(f"   {summary}...")
            
            print("\n" + "-" * 70)
            print(f"  Total: {len(content)} encouraging posts")
            print("-" * 70)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
