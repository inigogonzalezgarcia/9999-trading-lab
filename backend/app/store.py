"""SQLite persistence for research runs so results survive restarts and can be compared.

The full JSON result is stored zlib-compressed; a compact summary row powers listings. The
database path comes from ``FXLAB_DB`` (default ``data/fxlab.sqlite3``, git-ignored).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "fxlab.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT,
    symbol TEXT,
    dataset_name TEXT,
    dataset_hash TEXT,
    strategy_version TEXT,
    config_hash TEXT,
    software_revision TEXT,
    summary_json TEXT NOT NULL,
    result_blob BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_created_at ON runs(created_at DESC);
"""


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def dumps(payload: Any) -> str:
    return json.dumps(payload, default=_json_default, allow_nan=True)


class RunStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("FXLAB_DB") or DEFAULT_DB)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)

    def save(self, kind: str, result: dict[str, Any], summary: dict[str, Any], symbol: str | None = None,
             dataset_name: str | None = None, label: str | None = None) -> str:
        run_id = str(uuid4())
        repro = result.get("reproducibility", {})
        row = (run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"), kind, label, symbol, dataset_name,
               result.get("dataset_version") or repro.get("dataset_hash"), repro.get("strategy_version"), repro.get("config_hash"),
               repro.get("software_revision"), dumps(summary), zlib.compress(dumps(result).encode("utf-8"), 6))
        with self._lock:
            self._conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
            self._conn.commit()
        return run_id

    def list(self, limit: int = 100, kind: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT id, created_at, kind, label, symbol, dataset_name, dataset_hash, strategy_version, config_hash, software_revision, summary_json, length(result_blob) AS size FROM runs"
        params: tuple[Any, ...] = ()
        if kind:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY created_at DESC LIMIT ?"
        with self._lock:
            rows = self._conn.execute(query, params + (limit,)).fetchall()
        return [{**{k: row[k] for k in row.keys() if k != "summary_json"}, "summary": json.loads(row["summary_json"])} for row in rows]

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT result_blob FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return json.loads(zlib.decompress(row["result_blob"]).decode("utf-8"))

    def meta(self, run_id: str) -> dict[str, Any] | None:
        rows = [row for row in self.list(limit=100000) if row["id"] == run_id]
        return rows[0] if rows else None

    def delete(self, run_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            self._conn.commit()
        return cursor.rowcount > 0

    def relabel(self, run_id: str, label: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("UPDATE runs SET label = ? WHERE id = ?", (label, run_id))
            self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
