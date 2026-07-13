"""
Shared state for the LangGraph orchestration layer.

``AgentState`` is the single object threaded through every node in the
graph. It embeds the Working Memory fields required by the project spec
(``current_intent``, ``intent_confidence``, ``collected_information``,
``missing_fields``, ``pending_confirmation``, ``latest_tool_result``,
``workflow_state``, ``iteration_count``) directly as top-level keys so they
are visible in LangGraph's state and can be rendered by the Streamlit UI.

It also carries the Short-Term Memory essentials (conversation messages,
user name/role, session id) and a few bookkeeping fields used to produce
the final response and tool-activity log for a turn.
"""

from __future__ import annotations

from typing import Any, List, Optional, TypedDict

# The explicit workflow states required by the project spec.
WORKFLOW_STATES = [
    "START",
    "INTENT_CLASSIFICATION",
    "INFORMATION_GATHERING",
    "VALIDATION",
    "ANALYSIS",
    "CONFIRMATION_REQUIRED",
    "ACTION_EXECUTION",
    "REPORT_GENERATION",
    "END",
]

# Recognized intents. "confirm_yes" / "confirm_no" are only produced when a
# pending_confirmation already exists from a previous turn.
INTENTS = [
    "information_query",
    "eligibility_check",
    "enrollment_request",
    "student_report",
    "gpa_prediction",
    "study_plan",
    "payroll_report",
    "section_utilization",
    "institution_report",
    "human_handoff",
    "confirm_yes",
    "confirm_no",
    "unsupported",
]

# Fields that must be present in collected_information before a given
# intent may proceed past VALIDATION.
INTENT_REQUIRED_FIELDS: dict[str, list[str]] = {
    "information_query": ["query_type"],
    "eligibility_check": ["student_identifier", "course_code"],
    "enrollment_request": ["student_identifier", "course_code"],
    "student_report": ["student_identifier", "report_type"],
    "gpa_prediction": ["student_identifier"],
    "study_plan": ["student_identifier"],
    "payroll_report": ["instructor_identifier"],
    "section_utilization": [],
    "institution_report": ["report_type"],
    "human_handoff": [],
    "confirm_yes": [],
    "confirm_no": [],
    "unsupported": [],
}


class ToolActivity(TypedDict):
    tool_name: str
    tool_input: dict
    tool_result: Any


class AgentState(TypedDict, total=False):
    # ---- Short-Term Memory ----------------------------------------
    session_id: str
    user_name: str
    user_role: str
    messages: List[dict]            # [{"role": "user"/"assistant", "content": str}, ...]

    # ---- Working Memory (required keys, mirrored verbatim) ---------
    current_intent: Optional[str]
    intent_confidence: float
    collected_information: dict
    missing_fields: List[str]
    pending_confirmation: Optional[dict]
    latest_tool_result: Optional[dict]
    workflow_state: str
    iteration_count: int

    # ---- Per-turn bookkeeping ---------------------------------------
    state_history: List[str]        # ordered list of workflow states visited this turn
    tool_activity: List[ToolActivity]
    final_response: Optional[str]
    fallback_reason: Optional[str]


def new_agent_state(session_id: str, user_name: str = "", user_role: str = "") -> AgentState:
    """Create a fresh AgentState for a new conversation/session."""
    return AgentState(
        session_id=session_id,
        user_name=user_name,
        user_role=user_role,
        messages=[],
        current_intent=None,
        intent_confidence=0.0,
        collected_information={},
        missing_fields=[],
        pending_confirmation=None,
        latest_tool_result=None,
        workflow_state="START",
        iteration_count=0,
        state_history=[],
        tool_activity=[],
        final_response=None,
        fallback_reason=None,
    )


def start_turn(state: AgentState, user_message: str) -> AgentState:
    """Reset per-turn bookkeeping and append the new user message."""
    state["messages"] = list(state.get("messages", [])) + [{"role": "user", "content": user_message}]
    state["workflow_state"] = "START"
    state["state_history"] = ["START"]
    state["tool_activity"] = []
    state["final_response"] = None
    state["fallback_reason"] = None
    # collected_information / pending_confirmation / latest_tool_result persist
    # across turns intentionally (working memory continuity).
    return state
