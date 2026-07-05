"""
Layer 2 - Orchestration (LangGraph).

Exposes the compiled workflow graph plus the AgentState type and the
explicit workflow states used by the state machine:

    START -> INTENT_CLASSIFICATION -> INFORMATION_GATHERING -> VALIDATION
          -> ANALYSIS -> CONFIRMATION_REQUIRED -> ACTION_EXECUTION
          -> REPORT_GENERATION -> END

Not every turn visits every state - routing depends on the classified
intent (see app.workflow.router and app.workflow.graph for the conditional
edges), but every state the turn *does* pass through is recorded in
``AgentState["workflow_state"]`` and ``AgentState["state_history"]`` so the
Streamlit UI can display it.
"""

from __future__ import annotations

from .state import AgentState, WORKFLOW_STATES, new_agent_state
from .graph import build_graph, run_turn

__all__ = [
    "AgentState",
    "WORKFLOW_STATES",
    "new_agent_state",
    "build_graph",
    "run_turn",
]
