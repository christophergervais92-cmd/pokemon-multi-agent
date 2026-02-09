#!/usr/bin/env python3
"""
Background task runner for stock monitoring.

This provides a Refract-like "tasks + task groups" execution model:
- Each task scans one retailer for one query on an interval.
- Only emits alerts on stock transitions (new in-stock items vs last run).

Notes:
- This runner does *not* implement automated checkout flows.
- Run it as a standalone process, or start it from the Flask server (single-worker).
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from tasks.task_db import list_enabled_tasks_with_groups, set_runner_heartbeat, update_task_run


def _parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _product_key(p: Dict[str, Any]) -> str:
    retailer = (p.get("retailer") or "").strip().lower()
    sku = (p.get("sku") or "").strip()
    url = (p.get("url") or "").strip()
    name = (p.get("name") or "").strip()
    ident = sku or url or name
    return f"{retailer}|{ident}"


def _load_last_in_stock_keys(raw_json: Optional[str]) -> Set[str]:
    if not raw_json:
        return set()
    try:
        data = json.loads(raw_json)
        if isinstance(data, list):
            return {str(x) for x in data}
    except Exception:
        return set()
    return set()


def _is_allowed_discord_webhook_url(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith("https://discord.com/api/webhooks/") or u.startswith("https://discordapp.com/api/webhooks/")


def _is_allowed_live_send_url(url: str) -> bool:
    """
    Only allow posting to the local Flask server to avoid SSRF.

    The runner may be deployed independently; we intentionally do not support
    arbitrary URLs here.
    """
    try:
        from urllib.parse import urlparse

        u = urlparse((url or "").strip())
        if u.scheme not in ("http", "https"):
            return False
        if u.hostname not in ("127.0.0.1", "localhost"):
            return False
        if u.path.rstrip("/") != "/live/send":
            return False
        return True
    except Exception:
        return False


def _send_live_alerts(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Post restock events into the app's SSE stream via /live/send.
    """
    url = os.environ.get("POKEAGENT_LIVE_SEND_URL", "http://127.0.0.1:5001/live/send")
    if not _is_allowed_live_send_url(url):
        return {"success": False, "skipped": True, "reason": "invalid_live_send_url"}

    try:
        import requests  # lazy import
    except Exception:
        return {"success": False, "skipped": True, "reason": "requests_not_available"}

    attempted = min(len(products), 10)
    sent = 0
    for i, p in enumerate(products[:attempted]):
        name = (p.get("name") or "Pokemon TCG Item").strip()
        payload = {
            "type": "alert",
            "id": int(time.time() * 1000) + i,
            "product_name": name,
            "retailer": (p.get("retailer") or "").strip(),
            "price": p.get("price"),
            "url": (p.get("url") or "").strip(),
            "stock": True,
            "message": "Restock detected",
        }
        try:
            r = requests.post(url, json=payload, timeout=3)
            if 200 <= r.status_code < 300:
                sent += 1
        except Exception:
            continue

    return {"success": sent > 0, "skipped": False, "attempted": attempted, "sent": sent}


def _send_discord_webhook(webhook_url: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Send a restock alert to a Discord webhook.

    We intentionally only support Discord webhooks here to avoid SSRF.
    """
    if not _is_allowed_discord_webhook_url(webhook_url):
        return {"success": False, "skipped": False, "error": "invalid_webhook_url"}

    try:
        import requests  # lazy import
    except Exception:
        return {"success": False, "skipped": False, "error": "requests_not_available"}

    # Discord limits: keep this small.
    max_items = 6
    items = products[:max_items]

    embeds: List[Dict[str, Any]] = []
    for p in items:
        name = (p.get("name") or "Pokemon TCG Item").strip()
        retailer = (p.get("retailer") or "").strip()
        price = p.get("price")
        url = (p.get("url") or "").strip()
        img = (p.get("image_url") or "").strip()
        status = (p.get("stock_status") or "").strip()

        desc_parts = []
        if retailer:
            desc_parts.append(retailer)
        if isinstance(price, (int, float)) and price:
            desc_parts.append(f"${price:,.2f}")
        if status:
            desc_parts.append(status)

        embed: Dict[str, Any] = {
            "title": name[:256],
            "url": url or None,
            "description": " | ".join(desc_parts)[:4096] if desc_parts else None,
            "color": 0x57F287,  # Discord green
        }
        if img:
            embed["thumbnail"] = {"url": img}
        embeds.append({k: v for k, v in embed.items() if v is not None})

    payload = {
        "content": f"Restock detected: {len(products)} item(s) in stock",
        "embeds": embeds,
    }

    r = requests.post(webhook_url, json=payload, timeout=10)
    if 200 <= r.status_code < 300:
        return {"success": True, "skipped": False, "status_code": r.status_code}
    return {"success": False, "skipped": False, "status_code": r.status_code, "error": r.text[:200]}


def _notify_in_stock(products: List[Dict[str, Any]], *, webhook_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Prefer the existing Discord notifier if installed/configured.
    Falls back to a no-op if Discord deps aren't present.
    """
    if webhook_url:
        return _send_discord_webhook(webhook_url, products)

    try:
        from discord_bot.notifier import notify_users_sync  # type: ignore
    except Exception:
        return {"success": False, "skipped": True, "reason": "discord_bot notifier not available"}

    try:
        return {"success": True, "result": notify_users_sync(products)}
    except Exception as e:
        return {"success": False, "skipped": False, "error": str(e)}


@dataclass
class RunnerConfig:
    max_workers: int = 4
    loop_sleep_seconds: float = 1.0
    scan_parallel: bool = False  # avoid compounding blocks by default


class TaskRunner:
    def __init__(self, config: Optional[RunnerConfig] = None):
        self.config = config or RunnerConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._in_progress: Set[int] = set()
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="task-runner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _is_due(self, task_row: Dict[str, Any], now: datetime) -> Tuple[bool, int, str]:
        # Skip disabled groups.
        if not task_row.get("group_enabled", False):
            return False, 0, "group disabled"

        interval = task_row.get("interval_seconds")
        if interval is None:
            interval = task_row.get("group_default_interval_seconds", 60)
        try:
            interval = int(interval)
        except Exception:
            interval = 60

        last_run = _parse_iso(task_row.get("last_run_at"))
        if not last_run:
            return True, interval, "never ran"

        # If stored without tzinfo, treat as UTC.
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)

        due = (now - last_run).total_seconds() >= interval
        return due, interval, "interval"

    def _run_one(self, task_row: Dict[str, Any]) -> Dict[str, Any]:
        task_id = int(task_row["id"])
        retailer = str(task_row.get("retailer") or "")
        query = str(task_row.get("query") or "")

        zip_code = task_row.get("zip_code") or task_row.get("group_default_zip_code") or "90210"
        zip_code = str(zip_code)

        now = _utc_now()
        update_task_run(task_id, last_run_at=now.isoformat(), last_status="running", last_error=None)

        try:
            from scanners.stock_checker import scan_retailer  # type: ignore
        except Exception as e:
            update_task_run(task_id, last_status="error", last_error=f"import scan_retailer failed: {e}")
            return {"task_id": task_id, "success": False, "error": f"import scan_retailer failed: {e}"}

        try:
            result = scan_retailer(retailer, query, zip_code)
        except Exception as e:
            update_task_run(task_id, last_status="error", last_error=str(e))
            return {"task_id": task_id, "success": False, "error": str(e)}

        products = result.get("products") or []
        in_stock = [p for p in products if p.get("stock")]

        prev_keys = _load_last_in_stock_keys(task_row.get("last_in_stock_keys_json"))
        cur_keys = {_product_key(p) for p in in_stock}
        new_keys = cur_keys - prev_keys

        notify = {"success": True, "skipped": True, "reason": "no new in-stock items"}
        live_send = {"success": True, "skipped": True, "reason": "no new in-stock items"}
        if new_keys:
            # Only alert on new in-stock keys to avoid spam.
            new_products = [p for p in in_stock if _product_key(p) in new_keys]
            notify = _notify_in_stock(new_products, webhook_url=task_row.get("group_notify_webhook_url"))
            live_send = _send_live_alerts(new_products)

        update_task_run(
            task_id,
            last_status="ok" if result.get("success", True) else "error",
            last_error=None if result.get("success", True) else (result.get("error") or "scan failed"),
            last_in_stock_keys=sorted(cur_keys),
        )

        return {
            "task_id": task_id,
            "success": bool(result.get("success", True)),
            "retailer": retailer,
            "query": query,
            "zip_code": zip_code,
            "total_products": len(products),
            "in_stock_count": len(in_stock),
            "new_in_stock_count": len(new_keys),
            "notify": notify,
            "live_send": live_send,
        }

    def _loop(self) -> None:
        last_heartbeat = 0.0
        while self._running:
            now = _utc_now()
            # Heartbeat for worker-style runners (used by UI to show "live").
            if time.time() - last_heartbeat > 10:
                try:
                    set_runner_heartbeat(now.isoformat())
                except Exception:
                    pass
                last_heartbeat = time.time()

            # Compute due tasks.
            task_rows = list_enabled_tasks_with_groups()
            due: List[Dict[str, Any]] = []
            for t in task_rows:
                task_id = int(t["id"])
                with self._lock:
                    if task_id in self._in_progress:
                        continue
                is_due, _, _ = self._is_due(t, now)
                if is_due:
                    due.append(t)

            if not due:
                time.sleep(self.config.loop_sleep_seconds)
                continue

            # Run due tasks concurrently (bounded).
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
                futures = []
                for t in due:
                    task_id = int(t["id"])
                    with self._lock:
                        self._in_progress.add(task_id)
                    futures.append(pool.submit(self._run_one, t))

                for fut in as_completed(futures):
                    try:
                        _ = fut.result()
                    except Exception:
                        # Errors are recorded per-task; avoid killing the loop.
                        pass

            with self._lock:
                for t in due:
                    self._in_progress.discard(int(t["id"]))

            time.sleep(self.config.loop_sleep_seconds)


_runner: Optional[TaskRunner] = None


def get_task_runner() -> TaskRunner:
    global _runner
    if _runner is None:
        _runner = TaskRunner()
    return _runner
