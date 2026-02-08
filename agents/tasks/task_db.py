#!/usr/bin/env python3
"""
Task storage for the stock monitor task runner.

This is intentionally lightweight:
- SQLite (repo-root `pokemon_tasks.db`, gitignored by `*.db`)
- Task groups define default interval + zip
- Tasks define retailer + query and optional overrides
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "pokemon_tasks.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS task_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                default_interval_seconds INTEGER NOT NULL DEFAULT 60,
                default_zip_code TEXT NOT NULL DEFAULT '90210',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                retailer TEXT NOT NULL,
                query TEXT NOT NULL,
                zip_code TEXT,
                interval_seconds INTEGER,
                last_run_at TEXT,
                last_status TEXT,
                last_error TEXT,
                last_in_stock_keys_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES task_groups(id)
            )
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_group_id ON tasks(group_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks(enabled)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_groups_enabled ON task_groups(enabled)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_last_run_at ON tasks(last_run_at)")

        conn.commit()


@dataclass(frozen=True)
class TaskGroup:
    id: int
    name: str
    enabled: bool
    default_interval_seconds: int
    default_zip_code: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: int
    group_id: int
    name: str
    enabled: bool
    retailer: str
    query: str
    zip_code: Optional[str]
    interval_seconds: Optional[int]
    last_run_at: Optional[str]
    last_status: Optional[str]
    last_error: Optional[str]
    last_in_stock_keys_json: Optional[str]
    created_at: str
    updated_at: str

    def last_in_stock_keys(self) -> List[str]:
        if not self.last_in_stock_keys_json:
            return []
        try:
            keys = json.loads(self.last_in_stock_keys_json)
            if isinstance(keys, list):
                return [str(k) for k in keys]
        except Exception:
            return []
        return []


def _row_to_group(row: sqlite3.Row) -> TaskGroup:
    return TaskGroup(
        id=int(row["id"]),
        name=str(row["name"]),
        enabled=bool(row["enabled"]),
        default_interval_seconds=int(row["default_interval_seconds"]),
        default_zip_code=str(row["default_zip_code"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=int(row["id"]),
        group_id=int(row["group_id"]),
        name=str(row["name"]),
        enabled=bool(row["enabled"]),
        retailer=str(row["retailer"]),
        query=str(row["query"]),
        zip_code=(str(row["zip_code"]) if row["zip_code"] is not None else None),
        interval_seconds=(int(row["interval_seconds"]) if row["interval_seconds"] is not None else None),
        last_run_at=(str(row["last_run_at"]) if row["last_run_at"] is not None else None),
        last_status=(str(row["last_status"]) if row["last_status"] is not None else None),
        last_error=(str(row["last_error"]) if row["last_error"] is not None else None),
        last_in_stock_keys_json=(str(row["last_in_stock_keys_json"]) if row["last_in_stock_keys_json"] is not None else None),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def create_task_group(
    name: str,
    default_interval_seconds: int = 60,
    default_zip_code: str = "90210",
    enabled: bool = True,
) -> int:
    now = _utc_now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO task_groups (name, enabled, default_interval_seconds, default_zip_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, 1 if enabled else 0, int(default_interval_seconds), str(default_zip_code), now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_task_groups() -> List[TaskGroup]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM task_groups ORDER BY id ASC")
        rows = cur.fetchall()
        return [_row_to_group(r) for r in rows]


def get_task_group(group_id: int) -> Optional[TaskGroup]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM task_groups WHERE id = ? LIMIT 1", (int(group_id),))
        row = cur.fetchone()
        return _row_to_group(row) if row else None


def set_task_group_enabled(group_id: int, enabled: bool) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE task_groups SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, _utc_now_iso(), int(group_id)),
        )
        conn.commit()


def create_task(
    group_id: int,
    name: str,
    retailer: str,
    query: str,
    zip_code: Optional[str] = None,
    interval_seconds: Optional[int] = None,
    enabled: bool = True,
) -> int:
    now = _utc_now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (
              group_id, name, enabled, retailer, query, zip_code, interval_seconds,
              last_run_at, last_status, last_error, last_in_stock_keys_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                int(group_id),
                name,
                1 if enabled else 0,
                retailer,
                query,
                zip_code,
                int(interval_seconds) if interval_seconds is not None else None,
                now,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_tasks(group_id: Optional[int] = None) -> List[Task]:
    with get_connection() as conn:
        cur = conn.cursor()
        if group_id is None:
            cur.execute("SELECT * FROM tasks ORDER BY id ASC")
        else:
            cur.execute("SELECT * FROM tasks WHERE group_id = ? ORDER BY id ASC", (int(group_id),))
        rows = cur.fetchall()
        return [_row_to_task(r) for r in rows]


def get_task(task_id: int) -> Optional[Task]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ? LIMIT 1", (int(task_id),))
        row = cur.fetchone()
        return _row_to_task(row) if row else None


def set_task_enabled(task_id: int, enabled: bool) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE tasks SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, _utc_now_iso(), int(task_id)),
        )
        conn.commit()


def update_task_run(
    task_id: int,
    *,
    last_run_at: Optional[str] = None,
    last_status: Optional[str] = None,
    last_error: Optional[str] = None,
    last_in_stock_keys: Optional[Iterable[str]] = None,
) -> None:
    updates: List[Tuple[str, Any]] = []
    if last_run_at is not None:
        updates.append(("last_run_at", last_run_at))
    if last_status is not None:
        updates.append(("last_status", last_status))
    if last_error is not None:
        updates.append(("last_error", last_error))
    if last_in_stock_keys is not None:
        updates.append(("last_in_stock_keys_json", json.dumps(list(last_in_stock_keys))))

    if not updates:
        return

    updates.append(("updated_at", _utc_now_iso()))

    set_expr = ", ".join([f"{col} = ?" for col, _ in updates])
    values = [val for _, val in updates] + [int(task_id)]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE tasks SET {set_expr} WHERE id = ?", values)
        conn.commit()


def list_enabled_tasks_with_groups() -> List[Dict[str, Any]]:
    """
    Return enabled tasks joined with group settings.
    The runner uses this to calculate effective interval/zip and to ignore disabled groups.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              t.*,
              g.enabled AS group_enabled,
              g.default_interval_seconds AS group_default_interval_seconds,
              g.default_zip_code AS group_default_zip_code,
              g.name AS group_name
            FROM tasks t
            JOIN task_groups g ON g.id = t.group_id
            WHERE t.enabled = 1
            ORDER BY t.id ASC
            """
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            # Normalize a couple fields.
            d["enabled"] = bool(d.get("enabled"))
            d["group_enabled"] = bool(d.get("group_enabled"))
            out.append(d)
        return out


# Ensure schema exists on import.
init_db()

