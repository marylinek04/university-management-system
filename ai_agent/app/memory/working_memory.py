"""
Working memory: the explicit, structured task state for the *current*
request/turn.

Requirement: "Must explicitly represent: current_intent, collected_information,
missing_fields, pending_confirmation, latest_tool_result, workflow_state.
This must be visible in LangGraph state."

``WorkingMemory`` is a TypedDict so it can be embedded directly inside the
LangGraph ``AgentState`` (see app/workflow/state.py) and rendered as-is by
the Streamlit "workflow state" panel.
"""

from __future__ import annotations

from typing import Any, TypedDict


class WorkingMemory(TypedDict):
    # The intent the router classified for the current user message
    # (e.g. "check_enrollment_eligibility", "get_information", "unsupported").
    current_intent: str | None

    # Confidence score (0-1) attached to current_intent by the router.
    intent_confidence: float

    # Slots/parameters gathered so far for the current intent
    # (e.g. {"course_code": "CE410", "semester_name": "Spring 2026"}).
    collected_information: dict[str, Any]

    # Required slots for the current intent that are still missing.
    missing_fields: list[str]

    # Set when a state-changing tool is staged and waiting for the user
    # to explicitly say "yes" / "confirm".
    pending_confirmation: dict[str, Any] | None

    # The most recent structured tool output (any tool).
    latest_tool_result: dict[str, Any] | None

    # Explicit workflow state, one of the values in app/workflow/state.py::WorkflowState
    workflow_state: str

    # Number of agent-loop iterations used for the current user turn
    # (compared against config.MAX_ITERATIONS).
    iteration_count: int


def new_working_memory() -> WorkingMemory:
    """Return a freshly-reset working memory dict for a new turn."""
    return WorkingMemory(
        current_intent=None,
        intent_confidence=0.0,
        collected_information={},
        missing_fields=[],
        pending_confirmation=None,
        latest_tool_result=None,
        workflow_state="START",
        iteration_count=0,
    )
