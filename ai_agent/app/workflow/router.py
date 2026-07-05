"""
Intent classification and conditional-edge routing functions for the
LangGraph orchestration layer.

``classify_intent`` is the only function here that calls the LLM (Layer 3).
Everything else is pure, deterministic routing logic over ``AgentState`` so
that the explicit state machine (workflow transitions, stopping conditions,
fallback routing) is easy to reason about and test independently of the LLM.
"""

from __future__ import annotations

import json
import re

from ..config import INTENT_CONFIDENCE_THRESHOLD, MAX_ITERATIONS
from ..llm import get_chat_model
from .prompts import build_intent_classification_messages
from .state import AgentState, INTENTS

_YES_RE = re.compile(r"^\s*(yes|yeah|yep|yup|sure|confirm|confirmed|ok|okay|proceed|do it|go ahead)\b", re.I)
_NO_RE = re.compile(r"^\s*(no|nope|cancel|don'?t|do not|stop|never\s*mind|nevermind)\b", re.I)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}


def classify_intent(state: AgentState) -> tuple[str, float, dict]:
    """Classify the latest user message into (intent, confidence, entities).

    Short-circuits to ``confirm_yes`` / ``confirm_no`` (confidence 1.0,
    no entities) when a ``pending_confirmation`` exists and the latest
    message is a clear yes/no reply - this avoids an unnecessary LLM call
    for the most safety-critical turn in the conversation.
    """
    messages = state.get("messages", [])
    latest = messages[-1]["content"] if messages else ""

    if state.get("pending_confirmation"):
        if _YES_RE.match(latest):
            return "confirm_yes", 1.0, {}
        if _NO_RE.match(latest):
            return "confirm_no", 1.0, {}

    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-8:]) or "(none)"

    try:
        llm = get_chat_model()
        response = llm.invoke(
            build_intent_classification_messages(history_text, state.get("collected_information", {}), latest)
        )
        content = response.content if hasattr(response, "content") else str(response)
        data = _extract_json(content)
    except Exception:
        data = {}

    intent = data.get("intent")
    if intent not in INTENTS:
        intent = "unsupported"

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    entities = data.get("entities")
    if not isinstance(entities, dict):
        entities = {}

    return intent, confidence, entities


# ---------------------------------------------------------------------------
# Conditional-edge routing functions
# ---------------------------------------------------------------------------
def route_after_intent(state: AgentState) -> str:
    """INTENT_CLASSIFICATION -> {fallback, information_gathering, action_execution}."""
    if state.get("iteration_count", 0) > MAX_ITERATIONS:
        return "fallback"

    intent = state.get("current_intent")
    confidence = state.get("intent_confidence", 0.0)

    if intent in ("confirm_yes", "confirm_no"):
        if state.get("pending_confirmation"):
            return "action_execution"
        return "fallback"

    if intent == "unsupported" or confidence < INTENT_CONFIDENCE_THRESHOLD:
        return "fallback"

    return "information_gathering"


def route_after_validation(state: AgentState) -> str:
    """VALIDATION -> {finalize, analysis, report_generation}."""
    if state.get("missing_fields"):
        return "finalize"

    intent = state.get("current_intent")
    if intent in ("eligibility_check", "enrollment_request"):
        return "analysis"

    return "report_generation"


def route_after_analysis(state: AgentState) -> str:
    """ANALYSIS -> {confirmation_required, report_generation}."""
    if state.get("current_intent") == "enrollment_request":
        return "confirmation_required"
    return "report_generation"
