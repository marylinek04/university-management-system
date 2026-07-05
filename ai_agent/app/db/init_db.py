"""
Builds (or rebuilds) the SQLite database used by the University Operations
AI Agent from schema.sql + seed_data.sql.

Usage:
    python -m app.db.init_db            # build app/db/university.db
    python -m app.db.init_db --force     # drop & rebuild even if it exists
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .. import config

DB_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_PATH = DB_DIR / "seed_data.sql"

# Honor DATABASE_PATH (app.config, env-var configurable) so the database can
# live on a mounted Docker volume; defaults to app/db/university.db.
DB_PATH = config.DATABASE_PATH


def build_database(db_path: Path = DB_PATH, force: bool = False, seed: bool = True) -> Path:
    """Create the SQLite database file and apply schema (+ optional seed data)."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if force and db_path.exists():
        db_path.unlink()

    is_new = not db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        if seed and is_new:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))

        conn.commit()
    finally:
        conn.close()

    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the University Operations AI Agent SQLite DB")
    parser.add_argument("--force", action="store_true", help="Drop and recreate the database file")
    parser.add_argument("--no-seed", action="store_true", help="Skip loading sample data")
    args = parser.parse_args()

    path = build_database(force=args.force, seed=not args.no_seed)
    print(f"Database ready at: {path}")


if __name__ == "__main__":
    main()
