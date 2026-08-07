"""Persistência local (SQLite via aiosqlite): preferências e histórico."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import aiosqlite

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS searches (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    uf        TEXT NOT NULL,
    city      TEXT NOT NULL,
    lat       REAL NOT NULL,
    lng       REAL NOT NULL,
    crop_slug TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def get_setting(key: str, default: Any = None) -> Any:
    """Lê uma preferência do usuário (bloqueante, para uso em sync paths)."""
    conn = _connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])
    finally:
        conn.close()


def set_setting(key: str, value: Any) -> None:
    """Grava uma preferência do usuário."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


async def aset_setting(key: str, value: Any) -> None:
    """Versão assíncrona de set_setting."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        await db.commit()


async def record_search(
    uf: str, city: str, lat: float, lng: float, crop_slug: str | None = None
) -> None:
    """Registra uma consulta no histórico local."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS searches (id INTEGER PRIMARY KEY AUTOINCREMENT, uf TEXT NOT NULL, city TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, crop_slug TEXT, created_at TEXT DEFAULT (datetime('now')))")
        await db.execute(
            "INSERT INTO searches (uf, city, lat, lng, crop_slug) VALUES (?, ?, ?, ?, ?)",
            (uf, city, lat, lng, crop_slug),
        )
        await db.commit()


async def recent_searches(limit: int = 10) -> list[dict[str, Any]]:
    """Últimas consultas do usuário."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS searches (id INTEGER PRIMARY KEY AUTOINCREMENT, uf TEXT NOT NULL, city TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, crop_slug TEXT, created_at TEXT DEFAULT (datetime('now')))")
        cursor = await db.execute(
            "SELECT uf, city, lat, lng, crop_slug, created_at FROM searches "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "uf": r[0],
                "city": r[1],
                "lat": r[2],
                "lng": r[3],
                "crop_slug": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
