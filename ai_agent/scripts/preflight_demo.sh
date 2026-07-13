#!/usr/bin/env bash
# Demo preflight - verifies the stack is ready to record/present.
# Usage: ./scripts/preflight_demo.sh   (run from ai_agent/ with compose up)
set -u
fail=0
check() { if eval "$2" > /dev/null 2>&1; then echo "[OK]   $1"; else echo "[FAIL] $1  ->  $3"; fail=1; fi; }

check "docker installed"            "docker --version"                       "install Docker Desktop"
check "docker compose available"    "docker compose version"                 "update Docker Desktop"
check "compose services running"    "docker compose ps --status running | grep -q agent" "run: docker compose up --build"
check "agent UI healthy (:8501)"    "curl -fsS http://localhost:8501/_stcore/health"     "wait for the agent container to become healthy"
check "ollama reachable (:11434)"   "curl -fsS http://localhost:11434/api/tags"          "run: docker compose up ollama ollama-pull"
check "llama3.1 model pulled"       "curl -fsS http://localhost:11434/api/tags | grep -q llama3.1" "run: docker compose up ollama-pull"

if [ "$fail" -eq 0 ]; then
  echo; echo "READY - open http://localhost:8501, send one warm-up message, start recording."
else
  echo; echo "NOT READY - fix the [FAIL] lines above, then re-run."; exit 1
fi
