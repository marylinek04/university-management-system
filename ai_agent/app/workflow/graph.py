"""
Builds and runs the LangGraph orchestration graph (Layer 2).

Graph topology
--------------
::

    START -> intent_classification
        --(fallback)-->        fallback        -> finalize -> END
        --(information_gathering)--> information_gathering -> validation
        --(action_execution)-->      action_execution       -> report_generation

    validation
        --(finalize)-->        finalize -> END         (missing required fields,
                                                          or a student-role user
                                                          requesting another
                                                          student's data - denied)
        --(analysis)-->        analysis
        --(report_generation)--> report_generation

    analysis
        --(confirmation_required)--> confirmation_required -> finalize -> END
        --(report_generation)-->     report_generation -> finalize -> END

    report_generation -> finalize -> END

This mirrors the required explicit state machine
(START -> INTENT_CLASSIFICATION -> INFORMATION_GATHERING -> VALIDATION ->
ANALYSIS -> CONFIRMATION_REQUIRED -> ACTION_EXECUTION -> REPORT_GENERATION ->
END) while allowing intents that don't need every stage (e.g. a plain
information lookup, or a "yes/no" reply to a pending confirmation) to skip
directly to the relevant stage. ``state["state_history"]`` records exactly
which states a given turn passed through.

Stopping conditions / safety
-----------------------------
- ``MAX_ITERATIONS`` (app.config) caps how many times
  ``intent_classification`` can run for a single turn before the graph is
  forced to ``fallback``.
- Any request classified as ``unsupported`` or below
  ``INTENT_CONFIDENCE_THRESHOLD`` is routed to ``fallback``, which returns
  the policy-defined refusal message and never calls a tool.
- ``create_enrollment_request`` is only ever invoked with ``confirm=True``
  from ``action_execution``, which is only reachable via a ``confirm_yes``
  intent against an existing ``pending_confirmation`` - i.e. only after the
  user has explicitly confirmed.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import nodes
from .router import route_after_analysis, route_after_intent, route_after_validation
from .state import AgentState, new_agent_state, start_turn

__all__ = ["build_graph", "run_turn", "new_agent_state"]


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("intent_classification", nodes.node_intent_classification)
    graph.add_node("information_gathering", nodes.node_information_gathering)
    graph.add_node("validation", nodes.node_validation)
    graph.add_node("analysis", nodes.node_analysis)
    graph.add_node("confirmation_required", nodes.node_confirmation_required)
    graph.add_node("action_execution", nodes.node_action_execution)
    graph.add_node("report_generation", nodes.node_report_generation)
    graph.add_node("fallback", nodes.node_fallback)
    graph.add_node("finalize", nodes.node_finalize)

    graph.add_edge(START, "intent_classification")

    graph.add_conditional_edges(
        "intent_classification",
        route_after_intent,
        {
            "fallback": "fallback",
            "information_gathering": "information_gathering",
            "action_execution": "action_execution",
        },
    )

    graph.add_edge("information_gathering", "validation")

    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "finalize": "finalize",
            "analysis": "analysis",
            "report_generation": "report_generation",
        },
    )

    graph.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {
            "confirmation_required": "confirmation_required",
            "report_generation": "report_generation",
        },
    )

    graph.add_edge("confirmation_required", "finalize")
    graph.add_edge("action_execution", "report_generation")
    graph.add_edge("report_generation", "finalize")
    graph.add_edge("fallback", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_turn(state: AgentState, user_message: str) -> AgentState:
    """Run one full turn of the workflow against ``state`` and return the
    updated state (including ``final_response`` and the appended assistant
    message)."""
    state = start_turn(state, user_message)
    graph = get_graph()
    result = graph.invoke(state)
    return result
