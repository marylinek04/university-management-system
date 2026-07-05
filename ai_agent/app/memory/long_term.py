"""
Long-term memory (bonus): per-user preferences that persist across sessions.

Backed by the ``user_preferences`` table in the SQLite database
(app/db/schema.sql). Examples of what gets stored:

  - favorite_courses: ["CE410", "EE320"]
  - last_report_type: "transcript_summary"
  - preferred_semester: "Spring 2026"

Keys/values are stored as plain strings (JSON-encoded for non-strings) so
the schema stays generic.
"""

from __future__ import annotations

import json
from typing import Any

from ..db.connection import get_connection


class LongTermMemory:
    def __init__(self, user_name: str):
        self.user_name = user_name

    def set_preference(self, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_name, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(user_name, preference_key)
                DO UPDATE SET preference_value = excluded.preference_value,
                               updated_at = datetime('now')
                """,
                (self.user_name, key, encoded),
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT preference_value FROM user_preferences WHERE user_name = ? AND preference_key = ?",
                (self.user_name, key),
            ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["preference_value"])
        except (TypeError, ValueError):
            return row["preference_value"]

    def all_preferences(self) -> dict[str, Any]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT preference_key, preference_value FROM user_preferences WHERE user_name = ?",
                (self.user_name,),
            ).fetchall()
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[row["preference_key"]] = json.loads(row["preference_value"])
            except (TypeError, ValueError):
                result[row["preference_key"]] = row["preference_value"]
        return result
