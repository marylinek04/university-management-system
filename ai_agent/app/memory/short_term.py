"""
Short-term memory: the active conversation.

Requirement: "Store conversation messages, user name, recent interactions.
Must survive within active session."

This is intentionally a thin, framework-agnostic wrapper. In the LangGraph
graph, the message list lives in ``AgentState["messages"]`` (using
LangGraph's ``add_messages`` reducer); this class is what the Streamlit UI
and workflow entry point use to seed/read that state per session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShortTermMemory:
    session_id: str
    user_name: str
    user_role: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    # Rolling log of recent tool interactions, most recent last.
    recent_interactions: list[dict[str, Any]] = field(default_factory=list)
    max_recent_interactions: int = 10

    def add_message(self, role: str, content: str) -> None:
        """Append a chat message (role: 'user' | 'assistant' | 'system')."""
        self.messages.append({"role": role, "content": content})

    def add_interaction(self, tool_name: str, tool_input: dict, tool_result: Any) -> None:
        """Record a tool call so the UI / report tools can reference recent activity."""
        self.recent_interactions.append(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_result": tool_result,
            }
        )
        # keep only the most recent N
        if len(self.recent_interactions) > self.max_recent_interactions:
            self.recent_interactions = self.recent_interactions[-self.max_recent_interactions :]

    def history_as_text(self, limit: int = 20) -> str:
        """Plain-text rendering of the last `limit` messages (for prompts/debugging)."""
        lines = []
        for msg in self.messages[-limit:]:
            lines.append(f"{msg['role'].upper()}: {msg['content']}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_name": self.user_name,
            "user_role": self.user_role,
            "messages": self.messages,
            "recent_interactions": self.recent_interactions,
        }
