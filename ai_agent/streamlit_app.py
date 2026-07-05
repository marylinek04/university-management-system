"""
Layer 1 - Web Interface (Streamlit).

A chat-based front end for the University Operations AI Agent that shows:

  - the conversation history (Short-Term Memory),
  - a live "Working Memory" / workflow-state panel
    (current_intent, intent_confidence, collected_information,
    missing_fields, pending_confirmation, latest_tool_result,
    workflow_state, iteration_count, state_history), and
  - a "Tool Activity" trace for the most recent turn (tool name, input,
    and structured result for every tool the orchestration layer called).

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
import uuid

import streamlit as st

from app import config
from app.db.connection import ensure_database
from app.llm.client import LLMConfigurationError
from app.memory import LongTermMemory
from app.workflow import new_agent_state, run_turn

st.set_page_config(page_title="University Operations AI Agent", page_icon="🎓", layout="wide")

ROLE_OPTIONS = ["Student", "Instructor", "Registrar Staff", "Finance Officer", "Guest"]


# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------
def _init_session() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Maryline Karam"
    if "user_role" not in st.session_state:
        st.session_state.user_role = "Student"
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = new_agent_state(
            session_id=st.session_state.session_id,
            user_name=st.session_state.user_name,
            user_role=st.session_state.user_role.lower(),
        )
    if "db_ready" not in st.session_state:
        try:
            ensure_database()
            st.session_state.db_ready = True
            st.session_state.db_error = None
        except Exception as exc:  # pragma: no cover - surfaced in UI
            st.session_state.db_ready = False
            st.session_state.db_error = str(exc)


def _reset_conversation() -> None:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.agent_state = new_agent_state(
        session_id=st.session_state.session_id,
        user_name=st.session_state.user_name,
        user_role=st.session_state.user_role.lower(),
    )


_init_session()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("University Operations AI Agent")
    st.caption("Educational Support Agent - decision support for Students, "
               "Instructors, Registrar Staff, and Finance Officers.")

    if not st.session_state.get("db_ready", False):
        st.error(f"Database not ready: {st.session_state.get('db_error')}")

    st.subheader("Your profile")
    new_name = st.text_input("Name / ID / email", value=st.session_state.user_name,
                              help="Used to look up your student/instructor record when you say "
                                   "'my GPA', 'my balance', etc.")
    new_role = st.selectbox("Role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(st.session_state.user_role))

    if new_name != st.session_state.user_name or new_role != st.session_state.user_role:
        st.session_state.user_name = new_name
        st.session_state.user_role = new_role
        st.session_state.agent_state["user_name"] = new_name
        st.session_state.agent_state["user_role"] = new_role.lower()

    if st.button("New conversation", use_container_width=True):
        _reset_conversation()
        st.rerun()

    st.divider()
    st.subheader("Layer 3 - LLM configuration")
    st.code(
        f"LLM_PROVIDER = {config.LLM_PROVIDER}\n"
        f"LLM_MODEL    = {config.LLM_MODEL}\n"
        f"TEMPERATURE  = {config.LLM_TEMPERATURE}",
        language="bash",
    )

    if config.ENABLE_LONG_TERM_MEMORY:
        st.divider()
        st.subheader("Long-term memory (preferences)")
        ltm = LongTermMemory(st.session_state.user_name)
        try:
            prefs = ltm.all_preferences()
        except Exception:
            prefs = {}
        if prefs:
            st.json(prefs)
        else:
            st.caption("No saved preferences yet.")

    st.divider()
    st.subheader("Working memory / workflow state")
    state = st.session_state.agent_state
    st.markdown(f"**Workflow state:** `{state.get('workflow_state', 'START')}`")
    st.markdown(f"**State history (last turn):** {' → '.join(state.get('state_history', [])) or '—'}")
    st.markdown(f"**Current intent:** `{state.get('current_intent')}`  "
                f"(confidence: {state.get('intent_confidence', 0.0):.2f})")
    st.markdown(f"**Iteration count:** {state.get('iteration_count', 0)} / {config.MAX_ITERATIONS}")
    if state.get("fallback_reason"):
        st.markdown(f"**Fallback reason:** `{state['fallback_reason']}`")

    with st.expander("collected_information"):
        st.json(state.get("collected_information", {}))
    with st.expander("missing_fields"):
        st.json(state.get("missing_fields", []))
    with st.expander("pending_confirmation"):
        st.json(state.get("pending_confirmation"))
    with st.expander("latest_tool_result"):
        st.json(state.get("latest_tool_result"))


# ---------------------------------------------------------------------------
# Main chat interface
# ---------------------------------------------------------------------------
st.title("🎓 University Operations AI Agent")
st.caption(
    "Ask about courses, policies, enrollment eligibility, GPA, transcripts, "
    "study plans, payroll, or section utilization. State-changing actions "
    "(like enrolling) always ask for your confirmation first."
)

# Conversation history
for msg in st.session_state.agent_state.get("messages", []):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_message = st.chat_input("Type your message...")

if user_message:
    with st.chat_message("user"):
        st.write(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                st.session_state.agent_state = run_turn(st.session_state.agent_state, user_message)
                reply = st.session_state.agent_state.get("final_response") or ""
            except LLMConfigurationError as exc:
                reply = (
                    f"⚠️ LLM configuration error: {exc}\n\n"
                    "Set the required environment variable(s) (see .env.example) and restart the app."
                )
            except Exception as exc:  # pragma: no cover - last-resort safety net
                reply = f"⚠️ Unexpected error while processing your request: {exc}"
        st.write(reply)

    st.rerun()


# ---------------------------------------------------------------------------
# Tool activity (most recent turn)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🔧 Tool activity (most recent turn)")

activity = st.session_state.agent_state.get("tool_activity", [])
if not activity:
    st.caption("No tools have been called yet.")
else:
    for i, call in enumerate(activity, start=1):
        with st.expander(f"{i}. {call['tool_name']}"):
            st.markdown("**Input**")
            st.json(call["tool_input"])
            st.markdown("**Result**")
            st.json(call["tool_result"] if isinstance(call["tool_result"], (dict, list)) else {"result": call["tool_result"]})
