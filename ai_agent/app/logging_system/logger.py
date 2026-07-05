"""
Observability layer.

Every intent classification, tool call, validation failure, and fallback
event is written to the ``agent_logs`` table (app/db/schema.sql) so that:

  - the Streamlit UI can render a live "tool activity" / trace panel, and
  - the evaluation suite (ai_agent/tests) can compute metrics such as
    tool-selection accuracy and fallback accuracy from real traces.

Logging never raises: a logging failure must not break the conversation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..db.connection import get_connection

_py_logger = logging.getLogger("university_agent")


class AgentLogger:
    def __init__(self, session_id: str, user_role: str = "", user_name: str = ""):
        self.session_id = session_id
        self.user_role = user_role
        self.user_name = user_name

    def _write(
        self,
        *,
        intent: str | None = None,
        workflow_state: str | None = None,
        tool_name: str | None = None,
        tool_input: Any = None,
        tool_result: Any = None,
        validation_failure: str | None = None,
        fallback: bool = False,
        error: str | None = None,
    ) -> None:
        record = {
            "session_id": self.session_id,
            "user_role": self.user_role,
            "user_name": self.user_name,
            "intent": intent,
            "workflow_state": workflow_state,
            "tool_name": tool_name,
            "tool_input": json.dumps(tool_input, default=str) if tool_input is not None else None,
            "tool_result": json.dumps(tool_result, default=str) if tool_result is not None else None,
            "validation_failure": validation_failure,
            "fallback": int(bool(fallback)),
            "error": error,
        }
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_logs
                        (session_id, user_role, user_name, intent, workflow_state,
                         tool_name, tool_input, tool_result, validation_failure, fallback, error)
                    VALUES (:session_id, :user_role, :user_name, :intent, :workflow_state,
                            :tool_name, :tool_input, :tool_result, :validation_failure, :fallback, :error)
                    """,
                    record,
                )
        except Exception:  # pragma: no cover - logging must never break the agent
            _py_logger.exception("Failed to write agent log record: %s", record)

    # ------------------------------------------------------------------
    # Convenience methods used throughout the workflow
    # ------------------------------------------------------------------
    def log_intent(self, intent: str, workflow_state: str) -> None:
        self._write(intent=intent, workflow_state=workflow_state)

    def log_tool_call(
        self, tool_name: str, tool_input: Any, tool_result: Any, workflow_state: str, intent: str | None = None
    ) -> None:
        self._write(
            intent=intent,
            workflow_state=workflow_state,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_result=tool_result,
        )

    def log_validation_failure(self, tool_name: str, reason: str, workflow_state: str, intent: str | None = None) -> None:
        self._write(
            intent=intent,
            workflow_state=workflow_state,
            tool_name=tool_name,
            validation_failure=reason,
        )

    def log_fallback(self, reason: str, workflow_state: str, intent: str | None = None) -> None:
        self._write(intent=intent, workflow_state=workflow_state, fallback=True, error=reason)

    def log_error(self, error: str, workflow_state: str, tool_name: str | None = None, intent: str | None = None) -> None:
        self._write(intent=intent, workflow_state=workflow_state, tool_name=tool_name, error=error)


def get_recent_logs(session_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch recent log rows (most recent first) for the UI trace panel / eval suite."""
    with get_connection() as conn:
        if session_id:
            rows = conn.execute(
                "SELECT * FROM agent_logs WHERE session_id = ? ORDER BY log_id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agent_logs ORDER BY log_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]
