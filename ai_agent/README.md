# University Operations AI Agent

An AI agent layer built on top of the existing **University Management
System** database, implementing course project application area **#17
(Educational Support Agent)**.

This project does **not** redesign the underlying database. It adds a
4-layer agent on top of it:

1. **Streamlit UI** - chat interface, conversation history, tool-activity
   log, and a live "workflow state" / working-memory panel.
2. **LangGraph orchestration** - an explicit state machine that classifies
   intent, gathers and validates information, runs analysis, gates
   state-changing actions behind a confirmation step, and generates the
   final response.
3. **Configurable LLM core** - **Ollama is the default and required
   backend** (local/offline, no API key, model `llama3.1`). OpenAI and
   Anthropic are available as **optional fallback providers**, used only if
   explicitly configured. Selected entirely via environment variables.
4. **Tools** - 4 required tools + 5 bonus tools, all grounded in the SQLite
   database and a structured policy file (no vector DB / RAG / embeddings).

## Team

| Member | Role | Owns |
| --- | --- | --- |
| **Maryline Karam** (6599) | Tools Engineer (Student 1) | The 9 typed tools (`app/tools/`), pydantic validation, database schema additions, seed data, `policies.json` |
| **Aseel Menhem** (6651) | Agent Engineer (Student 2) | LangGraph workflow & router (`app/workflow/`), prompts, confirmation gate, stopping rules, fallback & human-handoff logic |
| **Hana Tfaily** (6554) | Platform & Interface (Student 3) | Memory layers (`app/memory/`), Streamlit UI, Docker packaging, trace logging, evaluation suite (`tests/eval/`), demo recording |

Presentation: `docs/The_Transparent_Agent.pdf`. Full design rationale and
limitations: `docs/TECHNICAL_REPORT.md`.

## Quick start (Docker - recommended)

```bash
cd ai_agent
docker compose up --build
```

That's it - **no `.env` file or API key is required**. This single command
starts three services: a local `ollama` LLM server, a one-shot job that
pulls the default model (`llama3.1`), and the agent itself. The agent waits
for the model to be ready, then connects to Ollama internally at
`http://ollama:11434`.

Then open **http://localhost:8501**.

The SQLite database is created and seeded automatically on first run and
persisted in the `agent_data` Docker volume; pulled Ollama models persist in
the `ollama_data` volume, so subsequent runs are fully offline.

If you want to use OpenAI or Anthropic instead (optional fallback only):
copy `.env.example` to `.env`, set `LLM_PROVIDER=openai` (or `anthropic`)
and the matching `*_API_KEY`, then run `docker compose up --build` again.

## Quick start (local, without Docker)

```bash
cd ai_agent
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m app.db.init_db          # build + seed app/db/university.db
streamlit run streamlit_app.py
```

By default this uses `LLM_PROVIDER=ollama` against
`http://localhost:11434` - no `.env` file needed, just make sure Ollama is
installed, running (`ollama serve`), and has the model pulled
(`ollama pull llama3.1`). To use OpenAI/Anthropic instead (optional
fallback), copy `.env.example` to `.env` and set `LLM_PROVIDER` plus the
matching `*_API_KEY`.

## Folder structure

```
ai_agent/
├── app/
│   ├── config.py              # All settings, read from environment variables
│   ├── db/
│   │   ├── schema.sql          # University Management System schema (existing, untouched)
│   │   ├── seed_data.sql        # Sample data used for development and the eval suite
│   │   ├── policies.json        # Structured, human-authored policy text (grounding source)
│   │   ├── init_db.py           # Build/seed the SQLite database
│   │   └── connection.py        # Shared sqlite3 connection helper
│   ├── llm/
│   │   └── client.py            # get_chat_model() - provider-agnostic LLM factory (Layer 3)
│   ├── memory/
│   │   ├── short_term.py        # Conversation messages, user name/role, recent interactions
│   │   ├── working_memory.py    # current_intent, collected_information, missing_fields, ...
│   │   └── long_term.py         # SQLite-backed per-user preferences (bonus)
│   ├── tools/                   # Layer 4 - all grounded tools
│   │   ├── db_helpers.py         # Shared lookups: find_student, compute_gpa, eligibility helpers...
│   │   ├── information_tool.py   # get_university_information (required)
│   │   ├── analysis_tool.py      # analyze_enrollment_eligibility (required)
│   │   ├── action_tool.py         # create_enrollment_request (required, confirmation-gated)
│   │   ├── reporting_tool.py      # generate_student_report (required)
│   │   └── bonus_tools.py         # predict_future_gpa, generate_study_plan, generate_payroll_report,
│   │                               # analyze_section_utilization, generate_institution_report
│   ├── workflow/                # Layer 2 - LangGraph orchestration
│   │   ├── state.py              # AgentState, WORKFLOW_STATES, INTENTS, INTENT_REQUIRED_FIELDS
│   │   ├── router.py             # classify_intent (LLM) + conditional-edge routing functions
│   │   ├── nodes.py              # One function per workflow state
│   │   ├── prompts.py            # Intent-classification prompt templates
│   │   └── graph.py              # build_graph() / run_turn() - the compiled LangGraph
│   └── logging_system/
│       └── logger.py             # AgentLogger -> agent_logs SQLite table
├── streamlit_app.py             # Layer 1 - chat UI
├── tests/eval/                  # Evaluation suite (see tests/eval/README.md)
│   ├── test_cases.json           # 35 test conversations across 34 categories
│   ├── run_eval.py                # Runner - computes the 4 required metrics
│   └── README.md
├── docs/
│   └── TECHNICAL_REPORT.md       # Architecture, design rationale, controls, limitations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md                    # (this file)
```

## The 4 required tools

| Tool | Purpose |
| --- | --- |
| `get_university_information(query_type, identifier=None, semester_name=None)` | Grounded lookups: courses, policies, instructors, programs, departments, sections, semesters |
| `analyze_enrollment_eligibility(student_identifier, course_code, semester_name=None)` | Checks prerequisites, capacity, duplicate enrollment, and balance |
| `create_enrollment_request(student_identifier, course_code, semester_name=None, confirm=False)` | State-changing enrollment action - always previewed first (`confirm=False`), then gated behind an explicit user "yes" |
| `generate_student_report(student_identifier, report_type)` | Transcript summary, GPA summary, academic standing, or course recommendations |

## Bonus tools

`predict_future_gpa`, `generate_study_plan`, `generate_payroll_report`,
`analyze_section_utilization`, `generate_institution_report` (institution-wide
tuition and payroll summaries).

## Safety design (summary)

- Out-of-domain requests get the exact refusal:
  *"I cannot perform that action because it is outside my supported
  university operations domain."*
- Every fact in every response comes from `result["formatted_text"]` /
  `result["data"]["formatted_text"]` / `result["message"]` - nothing is
  invented by the LLM.
- `create_enrollment_request` is only ever called with `confirm=True` after
  an explicit "yes" in response to a `CONFIRMATION_REQUIRED` prompt.
- `MAX_ITERATIONS` and an intent-confidence threshold bound the workflow and
  force a graceful fallback if the agent can't make progress.
- Every intent, tool call, validation failure, and fallback is written to the
  `agent_logs` SQLite table.

See **`docs/TECHNICAL_REPORT.md`** for the full architecture write-up and
**`tests/eval/README.md`** for how to run the evaluation suite.
