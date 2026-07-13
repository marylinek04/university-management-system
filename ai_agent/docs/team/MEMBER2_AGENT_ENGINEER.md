# Member 2 - Agent Engineer: **Aseel**

**Presentation duty:** presents slides 6-10 (workflow, safety, memory,
evaluation & Docker, team) and voices over Demo Part B in Hana's recording.

## Role description
You own the agent's *brain and safety rails*: the LangGraph state machine,
the intent router, the prompts, the confirmation gate, stopping rules,
fallback, and the human-handoff path (`app/workflow/`). You are graded
mainly on **"Workflow and reasoning" (20%)** and share **"Evaluation, safety
controls" (15%)**. In Q&A, expect: "walk me through one turn", "what stops a
loop", "can the confirmation gate be bypassed".

Files you must know line-by-line:
- `app/workflow/graph.py`, `router.py`, `nodes.py`, `state.py`, `prompts.py`
- Technical Report §3 (state machine) and §5 (safety controls)

## Apps to install
| App | Why | Where |
| --- | --- | --- |
| Python 3.11+ | Run the workflow locally | python.org |
| Git | Repo access | git-scm.com |
| Ollama (native install) | Test routing/prompt changes fast, without Docker | ollama.com |
| VS Code | Code review during Q&A | code.visualstudio.com |

## Libraries (installed automatically from requirements.txt)
You directly use: `langgraph` (StateGraph, conditional edges),
`langchain-ollama` / `langchain-openai` / `langchain-anthropic` (via
`get_chat_model()`), and `re` for the deterministic yes/no/handoff regexes.

## Step-by-step setup
```bash
# 1-3. Same as Member 1: clone, venv, pip install -r requirements.txt

# 4. Install and start the local LLM
ollama pull llama3.1
ollama serve        # usually starts automatically after install

# 5. Build the database
python -m app.db.init_db --force

# 6. Run the app locally (fast edit-reload loop for prompt/routing work)
streamlit run streamlit_app.py
```

## Verify your part works
```bash
# Deterministic paths - no LLM needed:
python - << "PY"
from app.workflow.graph import run_turn
from app.workflow.state import new_agent_state
s = new_agent_state("t1", user_name="Maryline Karam", user_role="student")
s = run_turn(s, "Please connect me to a human staff member.")
assert s["current_intent"] == "human_handoff" and "HANDOFF-" in s["final_response"]
print("handoff OK:", s["final_response"][:60])
PY

# LLM path - with ollama running:
# open the Streamlit UI and type: "Book me a flight to Paris."
# -> exact fallback message, workflow panel shows the fallback route, zero tools.
```

## Your voice-over script

Superseded: use **`docs/SPEAKING_SCRIPTS.md`** (canonical, word-for-word) -
your slide scripts and Demo Part B narration are there, updated for the
Hana-enrolls-herself demo flow.
