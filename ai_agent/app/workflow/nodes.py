"""
Node functions for each explicit workflow state.

Every node:
  - sets ``state["workflow_state"]`` to the state it represents,
  - appends that state name to ``state["state_history"]`` (for the
    Streamlit "workflow state" panel),
  - updates the relevant Working Memory fields, and
  - writes to the agent_logs table via ``AgentLogger`` where the project
    spec requires logging (intent, tool calls, validation failures,
    fallbacks, errors).

No node ever fabricates data: every fact in a response comes from a tool
result (grounded in the SQLite database / policies.json) or from the
policy-defined fallback message.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import MAX_ITERATIONS
from ..logging_system import AgentLogger
from ..tools import (
    analyze_enrollment_eligibility,
    analyze_section_utilization,
    create_enrollment_request,
    generate_institution_report,
    generate_payroll_report,
    generate_study_plan,
    generate_student_report,
    get_university_information,
    predict_future_gpa,
)
from .router import classify_intent
from .state import AgentState, INTENT_REQUIRED_FIELDS

FALLBACK_MESSAGE = (
    "I cannot perform that action because it is outside my supported university "
    "operations domain, and I won't guess an answer. If you'd like, I can forward "
    "your request to university staff - just say 'talk to a human' and I'll create "
    "a handoff ticket for you."
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _logger(state: AgentState) -> AgentLogger:
    return AgentLogger(
        session_id=state.get("session_id", ""),
        user_role=state.get("user_role", ""),
        user_name=state.get("user_name", ""),
    )


def _push_state(state: AgentState, name: str) -> None:
    state["workflow_state"] = name
    state.setdefault("state_history", []).append(name)


def _record_tool_call(state: AgentState, tool_name: str, tool_input: dict, tool_result: Any) -> None:
    state.setdefault("tool_activity", []).append(
        {"tool_name": tool_name, "tool_input": tool_input, "tool_result": tool_result}
    )
    _logger(state).log_tool_call(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_result,
        workflow_state=state["workflow_state"],
        intent=state.get("current_intent"),
    )


def _invoke_tool(state: AgentState, tool, tool_input: dict) -> dict:
    try:
        result = tool.invoke(tool_input)
    except Exception as exc:  # tool input validation / runtime error
        result = {"found": False, "message": f"Internal error while running {tool.name}: {exc}"}
        _logger(state).log_error(
            error=str(exc), workflow_state=state["workflow_state"], tool_name=tool.name, intent=state.get("current_intent")
        )
    _record_tool_call(state, tool.name, tool_input, result)
    return result


def _phrase_from_result(result: Any) -> str:
    """Deterministic, grounded phrasing - never adds facts not present in ``result``."""
    if isinstance(result, dict):
        if result.get("formatted_text"):
            return str(result["formatted_text"])
        data = result.get("data")
        if isinstance(data, dict) and data.get("formatted_text"):
            return str(data["formatted_text"])
        if result.get("message"):
            return str(result["message"])
        if result.get("found") is False:
            return "I couldn't find that information."
    return json.dumps(result, default=str)


_FIELD_PROMPTS = {
    "student_identifier": "the student's ID, full name, or email",
    "course_code": "the course code (e.g. 'CE410')",
    "instructor_identifier": "the instructor's ID, full name, or email",
    "query_type": "what kind of information you'd like (course, policy, instructor, program, department, section, or semester)",
}


def _missing_field_prompt(intent: str, field: str) -> str:
    if field == "report_type":
        if intent == "student_report":
            return "which report you'd like (transcript summary, GPA summary, academic standing, or recommendations)"
        if intent == "institution_report":
            return "which report you'd like (tuition summary, payroll summary, or enrollment overview)"
        return "the type of report you'd like"
    return _FIELD_PROMPTS.get(field, field)


# ---------------------------------------------------------------------------
# Node: INTENT_CLASSIFICATION
# ---------------------------------------------------------------------------
def node_intent_classification(state: AgentState) -> AgentState:
    _push_state(state, "INTENT_CLASSIFICATION")
    state["iteration_count"] = state.get("iteration_count", 0) + 1

    intent, confidence, entities = classify_intent(state)
    state["current_intent"] = intent
    state["intent_confidence"] = confidence

    collected = dict(state.get("collected_information", {}))
    for key, value in entities.items():
        if value not in (None, "", [], {}):
            collected[key] = value
    state["collected_information"] = collected

    _logger(state).log_intent(intent=intent, workflow_state=state["workflow_state"])
    return state


# ---------------------------------------------------------------------------
# Node: INFORMATION_GATHERING
# ---------------------------------------------------------------------------
_STUDENT_INTENTS = {"eligibility_check", "enrollment_request", "student_report", "gpa_prediction", "study_plan"}


def node_information_gathering(state: AgentState) -> AgentState:
    _push_state(state, "INFORMATION_GATHERING")

    collected = dict(state.get("collected_information", {}))
    intent = state.get("current_intent")
    role = (state.get("user_role") or "").lower()
    user_name = state.get("user_name")

    # If the requester is the student/instructor themselves and didn't name
    # someone else, default the identifier to their own account.
    if intent in _STUDENT_INTENTS and not collected.get("student_identifier") and role == "student" and user_name:
        collected["student_identifier"] = user_name

    if intent == "payroll_report" and not collected.get("instructor_identifier") and role == "instructor" and user_name:
        collected["instructor_identifier"] = user_name

    state["collected_information"] = collected
    return state


# ---------------------------------------------------------------------------
# Node: VALIDATION
# ---------------------------------------------------------------------------
def node_validation(state: AgentState) -> AgentState:
    _push_state(state, "VALIDATION")

    intent = state.get("current_intent") or "unsupported"
    required = INTENT_REQUIRED_FIELDS.get(intent, [])
    collected = state.get("collected_information", {})

    missing = [f for f in required if not collected.get(f)]
    state["missing_fields"] = missing

    if missing:
        _logger(state).log_validation_failure(
            tool_name=intent,
            reason=f"Missing required field(s): {', '.join(missing)}",
            workflow_state=state["workflow_state"],
            intent=intent,
        )
        asks = [_missing_field_prompt(intent, f) for f in missing]
        if len(asks) == 1:
            state["final_response"] = f"Could you please tell me {asks[0]}?"
        else:
            state["final_response"] = "Could you please tell me " + ", and ".join(asks) + "?"

    return state


# ---------------------------------------------------------------------------
# Node: ANALYSIS
# ---------------------------------------------------------------------------
def node_analysis(state: AgentState) -> AgentState:
    _push_state(state, "ANALYSIS")

    collected = state.get("collected_information", {})
    tool_input = {
        "student_identifier": collected.get("student_identifier"),
        "course_code": collected.get("course_code"),
        "semester_name": collected.get("semester_name"),
    }
    result = _invoke_tool(state, analyze_enrollment_eligibility, tool_input)
    state["latest_tool_result"] = result
    return state


# ---------------------------------------------------------------------------
# Node: CONFIRMATION_REQUIRED
# ---------------------------------------------------------------------------
def node_confirmation_required(state: AgentState) -> AgentState:
    _push_state(state, "CONFIRMATION_REQUIRED")

    collected = state.get("collected_information", {})
    tool_input = {
        "student_identifier": collected.get("student_identifier"),
        "course_code": collected.get("course_code"),
        "semester_name": collected.get("semester_name"),
        "confirm": False,
    }
    result = _invoke_tool(state, create_enrollment_request, tool_input)
    state["latest_tool_result"] = result

    state["pending_confirmation"] = {
        "student_identifier": collected.get("student_identifier"),
        "course_code": collected.get("course_code"),
        "semester_name": collected.get("semester_name"),
        "request_id": result.get("request_id"),
        "eligible": result.get("eligible"),
    }

    message = result.get("message", "")
    if result.get("eligible"):
        state["final_response"] = f"{message} Reply 'yes' to confirm or 'no' to cancel."
    else:
        # Not eligible - nothing useful to confirm, but keep pending_confirmation
        # so a 'yes'/'no' reply is still routed sensibly instead of falling back.
        state["final_response"] = f"{message} If you'd like, reply 'no' to cancel this request."

    return state


# ---------------------------------------------------------------------------
# Node: ACTION_EXECUTION
# ---------------------------------------------------------------------------
def node_action_execution(state: AgentState) -> AgentState:
    _push_state(state, "ACTION_EXECUTION")

    pending = state.get("pending_confirmation") or {}
    intent = state.get("current_intent")

    if intent == "confirm_no":
        result = {
            "status": "cancelled",
            "message": "Okay, the enrollment request has been cancelled. No changes were made.",
        }
        _record_tool_call(state, "create_enrollment_request", {"confirm": False, "cancelled_by_user": True}, result)
    else:
        tool_input = {
            "student_identifier": pending.get("student_identifier"),
            "course_code": pending.get("course_code"),
            "semester_name": pending.get("semester_name"),
            "confirm": True,
        }
        result = _invoke_tool(state, create_enrollment_request, tool_input)

    state["latest_tool_result"] = result
    state["pending_confirmation"] = None
    return state


# ---------------------------------------------------------------------------
# Node: REPORT_GENERATION
# ---------------------------------------------------------------------------
def node_report_generation(state: AgentState) -> AgentState:
    _push_state(state, "REPORT_GENERATION")

    intent = state.get("current_intent")
    collected = state.get("collected_information", {})

    if intent == "human_handoff":
        # Simulated human-handoff path (project spec, Section 7): create a
        # traceable ticket in agent_logs and tell the user what happens next.
        # Deterministic - no LLM or external system involved.
        from datetime import datetime, timezone

        ticket_ref = "HANDOFF-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        last_user_msgs = [m["content"] for m in state.get("messages", []) if m["role"] == "user"][-3:]
        result = {
            "status": "handoff_created",
            "ticket_ref": ticket_ref,
            "message": (
                f"I've created handoff ticket {ticket_ref} and forwarded your request to "
                "university staff (simulated). A staff member would review the conversation "
                "and follow up with you. Is there anything else I can help with in the meantime?"
            ),
        }
        _record_tool_call(
            state,
            "create_handoff_ticket",
            {"ticket_ref": ticket_ref, "recent_user_messages": last_user_msgs},
            result,
        )
        state["latest_tool_result"] = result
        state["final_response"] = result["message"]
        return state

    if intent == "information_query":
        tool_input = {
            "query_type": collected.get("query_type"),
            "identifier": (
                collected.get("identifier")
                or collected.get("course_code")
                or collected.get("instructor_identifier")
                or collected.get("student_identifier")
            ),
            "semester_name": collected.get("semester_name"),
        }
        result = _invoke_tool(state, get_university_information, tool_input)
        state["latest_tool_result"] = result
        state["final_response"] = _phrase_from_result(result)
        return state

    if intent == "eligibility_check":
        result = state.get("latest_tool_result") or {}
        eligible = result.get("eligible")
        reasons = result.get("reasons", [])
        details = result.get("details", {})
        student_name = (details.get("student") or {}).get("name", "The student")
        course_code = (details.get("course") or {}).get("course_code", collected.get("course_code", ""))
        if eligible:
            state["final_response"] = f"{student_name} is eligible to enroll in {course_code}."
        else:
            state["final_response"] = (
                f"{student_name} is NOT eligible to enroll in {course_code}: " + "; ".join(reasons)
            )
        return state

    if intent in ("enrollment_request", "confirm_yes", "confirm_no"):
        result = state.get("latest_tool_result") or {}
        state["final_response"] = _phrase_from_result(result)
        return state

    if intent == "student_report":
        tool_input = {
            "student_identifier": collected.get("student_identifier"),
            "report_type": collected.get("report_type"),
        }
        result = _invoke_tool(state, generate_student_report, tool_input)

    elif intent == "gpa_prediction":
        tool_input = {
            "student_identifier": collected.get("student_identifier"),
            "planned_courses": collected.get("planned_courses") or [],
        }
        result = _invoke_tool(state, predict_future_gpa, tool_input)

    elif intent == "study_plan":
        tool_input: dict = {"student_identifier": collected.get("student_identifier")}
        if collected.get("max_credits_per_semester"):
            tool_input["max_credits_per_semester"] = collected["max_credits_per_semester"]
        result = _invoke_tool(state, generate_study_plan, tool_input)

    elif intent == "payroll_report":
        tool_input = {
            "instructor_identifier": collected.get("instructor_identifier"),
            "period_start": collected.get("period_start"),
            "period_end": collected.get("period_end"),
        }
        result = _invoke_tool(state, generate_payroll_report, tool_input)

    elif intent == "section_utilization":
        tool_input = {"semester_name": collected.get("semester_name")}
        result = _invoke_tool(state, analyze_section_utilization, tool_input)

    elif intent == "institution_report":
        tool_input = {
            "report_type": collected.get("report_type"),
            "semester_name": collected.get("semester_name"),
            "period_start": collected.get("period_start"),
            "period_end": collected.get("period_end"),
        }
        result = _invoke_tool(state, generate_institution_report, tool_input)

    else:
        result = {"found": False, "message": FALLBACK_MESSAGE}

    state["latest_tool_result"] = result
    state["final_response"] = _phrase_from_result(result)
    return state


# ---------------------------------------------------------------------------
# Node: fallback (safety / stopping condition)
# ---------------------------------------------------------------------------
def node_fallback(state: AgentState) -> AgentState:
    intent = state.get("current_intent")

    if state.get("iteration_count", 0) > MAX_ITERATIONS:
        reason = "max_iterations_exceeded"
        message = (
            "I've reached the maximum number of steps I can take for this request. "
            "Could you rephrase or simplify it?"
        )
    elif intent in ("confirm_yes", "confirm_no") and not state.get("pending_confirmation"):
        reason = "no_pending_confirmation"
        message = "There's nothing pending that needs confirmation right now. How can I help?"
    else:
        reason = "unsupported_or_low_confidence"
        message = FALLBACK_MESSAGE

    state["fallback_reason"] = reason
    state["final_response"] = message
    _logger(state).log_fallback(reason=reason, workflow_state=state.get("workflow_state", "INTENT_CLASSIFICATION"), intent=intent)
    return state


# ---------------------------------------------------------------------------
# Node: END (finalize)
# ---------------------------------------------------------------------------
def node_finalize(state: AgentState) -> AgentState:
    _push_state(state, "END")

    if state.get("final_response") is None:
        state["final_response"] = FALLBACK_MESSAGE

    state["messages"] = list(state.get("messages", [])) + [
        {"role": "assistant", "content": state["final_response"]}
    ]
    return state
