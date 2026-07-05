"""Shared SQLite connection helper for the University Operations AI Agent."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .init_db import DB_PATH, build_database


def ensure_database() -> Path:
    """Make sure the database file exists (build it with seed data if missing)."""
    if not DB_PATH.exists():
        build_database()
    return DB_PATH


@contextmanager
def get_connection():
    """Yield a sqlite3 connection with row access by column name and FK enforcement on."""
    ensure_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
