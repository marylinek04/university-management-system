"""
Evaluation runner for the University Operations AI Agent.

Runs every conversation in ``test_cases.json`` against a fresh, isolated
copy of the seeded database (a temp file - the real project database is
never touched), then reports the four required metrics:

    1. Task completion rate     - fraction of (non-lenient) test cases where
                                    every assertion in every turn passed.
    2. Tool selection accuracy   - fraction of turns where the set of tools
                                    actually called matches the expected set.
    3. Fallback accuracy         - fraction of turns where the agent
                                    correctly did/did not produce the
                                    domain-refusal fallback.
    4. Unsafe action count       - number of times a state-changing tool
                                    (create_enrollment_request with
                                    confirm=True) ran WITHOUT a
                                    pending_confirmation having been set in
                                    a previous turn (i.e. without going
                                    through CONFIRMATION_REQUIRED first).

Usage (from the ai_agent/ directory):

    python -m tests.eval.run_eval

A full JSON report (metrics + per-turn detail) is written next to this file
as ``eval_report.json``.

NOTE on LLM configuration: intent classification (Layer 3) requires a
reachable LLM provider (see app/config.py / .env). The default provider is
"ollama" (no API key needed) - it just needs an Ollama server reachable at
OLLAMA_BASE_URL (e.g. ``docker compose up ollama ollama-pull``, or a local
``ollama serve`` with the model pulled). If the configured provider is
unreachable/misconfigured, the eval ABORTS: without a live LLM every turn is
routed to the fallback node and the report is meaningless. Override with
``--allow-no-llm`` only to debug the runner itself - never commit or submit
a report produced that way.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# DATABASE_PATH MUST be set before any `app` module is imported: app.config
# reads it from the environment at import time, and app.db.init_db /
# app.db.connection freeze it into a module-level constant (DB_PATH). Setting
# it here points the whole agent at an isolated temp database for this run.
# ---------------------------------------------------------------------------
EVAL_DB_PATH = Path(tempfile.gettempdir()) / "university_agent_eval.db"
os.environ["DATABASE_PATH"] = str(EVAL_DB_PATH)

# Make sure the `app` package (ai_agent/app) is importable regardless of cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.db.init_db import build_database  # noqa: E402
from app.llm.client import LLMConfigurationError, get_chat_model  # noqa: E402
from app.workflow.graph import run_turn  # noqa: E402
from app.workflow.state import new_agent_state  # noqa: E402

TEST_CASES_PATH = Path(__file__).resolve().parent / "test_cases.json"
REPORT_PATH = Path(__file__).resolve().parent / "eval_report.json"


def _ollama_reachable(base_url: str, timeout: float = 3.0) -> bool:
    """Quick connectivity check for the default Ollama provider.

    Unlike OpenAI/Anthropic (which fail fast via LLMConfigurationError if an
    API key is missing), ``get_chat_model()`` never raises for "ollama" -
    construction always succeeds even if no server is listening at
    OLLAMA_BASE_URL. The real failure only happens later, inside
    classify_intent's try/except, where it is silently swallowed. So for
    ollama we proactively probe the server here.
    """
    import urllib.request

    try:
        urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def preflight_llm_check() -> bool:
    """Return True if the configured LLM provider is reachable.

    If it is not, the eval ABORTS by default (see main): running without a
    live LLM sends every turn to the fallback node and produces a garbage
    report that must never be committed or submitted. Use --allow-no-llm to
    override (debugging the runner itself only).
    """
    provider = config.LLM_PROVIDER

    if provider == "ollama":
        if _ollama_reachable(config.OLLAMA_BASE_URL):
            print(
                f"Ollama reachable at {config.OLLAMA_BASE_URL} (model: "
                f"{config.LLM_MODEL}) - intent classification will use the live model.\n"
            )
            return True
        print(
            f"ERROR: Ollama is not reachable at {config.OLLAMA_BASE_URL}.\n"
            "Without a live LLM, intent classification fails on every turn, every\n"
            "case is routed to the fallback node, and the resulting report is\n"
            "meaningless - so the eval will NOT run.\n"
            "Fix: start Ollama and pull the model, e.g.\n"
            "  docker compose up ollama ollama-pull   (Docker)\n"
            "  ollama serve  &&  ollama pull "
            f"{config.LLM_MODEL or 'llama3.1'}   (local install)\n"
            "Ollama is the default provider and needs NO API key - OpenAI/Anthropic\n"
            "are optional fallbacks only (set LLM_PROVIDER + the matching *_API_KEY\n"
            "in .env if you want to use one of those instead).\n"
            "(To force a run anyway for runner debugging: --allow-no-llm)\n"
        )
        return False

    # OpenAI / Anthropic (optional fallback providers): get_chat_model()
    # raises LLMConfigurationError immediately if the API key is missing.
    try:
        get_chat_model()
        print(
            f"LLM provider '{provider}' configured OK - intent classification "
            "will use the live model.\n"
        )
        return True
    except LLMConfigurationError as exc:
        print(
            "ERROR: LLM is not configured (" + str(exc) + ")\n"
            "Without a live LLM the eval report is meaningless, so the eval will\n"
            f"NOT run. '{provider}' is an OPTIONAL fallback provider - either fix its\n"
            "API key in .env, or set LLM_PROVIDER=ollama (the default, no API key\n"
            "required). (To force a run anyway for runner debugging: --allow-no-llm)\n"
        )
        return False


def _check_response_contains(final_response: str, fragments: list[str]) -> dict[str, bool]:
    return {f"contains:{frag}": (frag in final_response) for frag in fragments}


def run_case(case: dict) -> dict:
    session_id = f"eval-{case['id']}"
    state = new_agent_state(
        session_id, user_name=case.get("user_name", ""), user_role=case.get("user_role", "")
    )

    case_result: dict = {
        "id": case["id"],
        "category": case["category"],
        "description": case.get("description", ""),
        "lenient": bool(case.get("lenient", False)),
        "turns": [],
        "passed": True,
    }

    for turn in case["turns"]:
        pre_pending = state.get("pending_confirmation")

        state = run_turn(state, turn["message"])

        tool_names = [t["tool_name"] for t in state.get("tool_activity", [])]
        final_response = state.get("final_response") or ""
        fallback_reason = state.get("fallback_reason")

        checks: dict[str, bool] = {}

        if turn.get("expected_intent") is not None:
            checks["intent"] = state.get("current_intent") == turn["expected_intent"]

        if turn.get("expected_tools") is not None:
            checks["tools"] = set(turn["expected_tools"]) == set(tool_names)

        if turn.get("expect_fallback") is not None:
            checks["fallback"] = bool(fallback_reason) == bool(turn["expect_fallback"])

        checks.update(_check_response_contains(final_response, turn.get("response_contains", [])))

        if "expect_missing_fields" in turn:
            checks["missing_fields"] = state.get("missing_fields", []) == turn["expect_missing_fields"]

        if "expect_eligible" in turn:
            ltr = state.get("latest_tool_result") or {}
            checks["eligible"] = ltr.get("eligible") == turn["expect_eligible"]

        if "expect_pending_confirmation" in turn:
            checks["pending_confirmation"] = bool(state.get("pending_confirmation")) == turn[
                "expect_pending_confirmation"
            ]

        if "expect_confirm_with" in turn:
            expect = turn["expect_confirm_with"]
            checks["confirm_with"] = any(
                t["tool_name"] == expect["tool"] and t["tool_input"].get("confirm") == expect["confirm"]
                for t in state.get("tool_activity", [])
            )

        unsafe_action = False
        for t in state.get("tool_activity", []):
            if t["tool_name"] == "create_enrollment_request" and t["tool_input"].get("confirm") is True:
                if not pre_pending:
                    unsafe_action = True

        turn_passed = all(checks.values())
        if case.get("lenient"):
            # Lenient cases still record their checks for visibility, but a
            # non-empty final_response and no tool call (already reflected in
            # `checks["tools"]` if expected_tools == []) is all that's required.
            turn_passed = bool(final_response)

        if not turn_passed:
            case_result["passed"] = False

        case_result["turns"].append(
            {
                "message": turn["message"],
                "actual_intent": state.get("current_intent"),
                "actual_tools": tool_names,
                "final_response": final_response,
                "fallback_reason": fallback_reason,
                "checks": checks,
                "unsafe_action": unsafe_action,
                "passed": turn_passed,
            }
        )

    return case_result


def compute_metrics(results: list[dict]) -> dict:
    scored = [r for r in results if not r["lenient"]]

    task_completion = (sum(1 for r in scored if r["passed"]) / len(scored)) if scored else 0.0

    tool_checks: list[bool] = []
    fallback_checks: list[bool] = []
    unsafe_count = 0

    for r in results:
        for t in r["turns"]:
            if t["unsafe_action"]:
                unsafe_count += 1
            if r["lenient"]:
                continue
            if "tools" in t["checks"]:
                tool_checks.append(t["checks"]["tools"])
            if "fallback" in t["checks"]:
                fallback_checks.append(t["checks"]["fallback"])

    return {
        "task_completion_rate": round(task_completion, 4),
        "tool_selection_accuracy": round(sum(tool_checks) / len(tool_checks), 4) if tool_checks else None,
        "fallback_accuracy": round(sum(fallback_checks) / len(fallback_checks), 4) if fallback_checks else None,
        "unsafe_action_count": unsafe_count,
        "total_cases": len(results),
        "scored_cases": len(scored),
        "lenient_cases": len(results) - len(scored),
        "tool_checks_evaluated": len(tool_checks),
        "fallback_checks_evaluated": len(fallback_checks),
    }


def main() -> None:
    llm_ok = preflight_llm_check()
    if not llm_ok and "--allow-no-llm" not in sys.argv:
        sys.exit(1)

    build_database(force=True, seed=True)
    print(f"Isolated eval database built at: {EVAL_DB_PATH}\n")

    cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))["test_cases"]

    results = []
    for case in cases:
        result = run_case(case)
        if result["lenient"]:
            status = "PASS (lenient)" if result["passed"] else "FAIL (lenient)"
        else:
            status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {case['id']} - {case['category']}")

        if not result["passed"]:
            for t in result["turns"]:
                if not t["passed"]:
                    failed = [k for k, v in t["checks"].items() if not v]
                    print(f"    turn: {t['message']!r}")
                    print(f"      failed checks: {failed}")
                    print(f"      actual_intent={t['actual_intent']!r} actual_tools={t['actual_tools']}")
                    print(f"      final_response: {t['final_response']!r}")

        results.append(result)

    metrics = compute_metrics(results)

    report = {"metrics": metrics, "cases": results}
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 60)
    print("EVAL METRICS")
    print("=" * 60)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print(f"\nFull report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
