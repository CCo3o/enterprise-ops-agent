"""SQLite-backed conversation and trace storage."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "agent.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    connection.execute("CREATE TABLE IF NOT EXISTS traces (trace_id TEXT PRIMARY KEY, session_id TEXT, latency_ms INTEGER, tools TEXT, model_mode TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    return connection


def add_message(session_id: str, role: str, content: str) -> None:
    with _connect() as connection:
        connection.execute("INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))


def get_history(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    with _connect() as connection:
        rows = connection.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def add_trace(trace_id: str, session_id: str, latency_ms: int, tools: list[str], model_mode: str) -> None:
    with _connect() as connection:
        connection.execute("INSERT INTO traces(trace_id, session_id, latency_ms, tools, model_mode) VALUES (?, ?, ?, ?, ?)", (trace_id, session_id, latency_ms, json.dumps(tools), model_mode))


def recent_traces(limit: int = 20) -> list[dict]:
    with _connect() as connection:
        rows = connection.execute("SELECT trace_id, session_id, latency_ms, tools, model_mode, created_at FROM traces ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"trace_id": row[0], "session_id": row[1], "latency_ms": row[2], "tools": json.loads(row[3]), "model_mode": row[4], "created_at": row[5]} for row in rows]
