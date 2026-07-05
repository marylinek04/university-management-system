# University Operations AI Agent — Human Guide for Presentation & Defense

This guide is written for the team, not for the grader's code review. Its job is
to let **anyone on the team**, even someone who never opened a source file,
stand in front of the instructor and confidently explain, demo, and defend
this project.

Read it top to bottom once before the demo. The night before submission, skim
Sections H (Testing), I (Script), J (Defense Q&A), and K (Risk Checklist) again.

---

## How the project is framed

This is **application area #17 — Educational Support Agent**, built as an
add-on (`ai_agent/`) to an existing University Management System SQL Server
database. We did **not** touch the existing system's source schema — instead
we exported/re-derived the entities the agent needs into a self-contained
SQLite database (`app/db/schema.sql` + `app/db/seed_data.sql`), and built an
AI agent on top of it using:

- **LangGraph** for an explicit, auditable state-machine workflow (Layer 2)
- **A configurable LLM client** — Ollama (default/required, local/offline,
  no API key) with OpenAI / Anthropic as optional fallback (Layer 3)
- **9 tools** (4 required + 5 bonus) that are the *only* way the agent touches
  data — no tool call, no data, no hallucination
- **3-tier memory** (short-term, working, long-term)
- **A Streamlit chat UI** (Layer 1) with a live "working memory" / trace panel
- **Docker** for one-command startup
- **An evaluation suite** of 31 scripted test conversations

The single sentence to remember: **"The agent never makes anything up — every
fact it states comes from a database row, a policy file rule, or a tool
result, and every action that changes data requires the user to say yes."**

---

# Part 1 — Component-by-Component Explanation

For each component: **(1) why it exists, (2) which requirement it satisfies,
(3) what happens during execution, (4) which files implement it, (5) how to
demo it live.**

## 1. Streamlit Chat UI (Layer 1 — Presentation)

**1. Why it exists**
The project requires a usable interface for end users (students, instructors,
registrar/finance staff) to talk to the agent in natural language, and for
**us** to be able to show the instructor what's happening "under the hood"
during the defense — intent, confidence, memory, and tool calls — without
reading logs.

**2. Requirement satisfied**
Layer 1 (Web Interface) of the required architecture; also supports the
"explainability" expectation by exposing working memory and tool activity.

**3. What it does during execution**
- On first load, creates a `session_id` (UUID), default `user_name =
  "Maryline Karam"`, default `user_role = "Student"`, and an empty
  `AgentState` via `new_agent_state(...)`.
- Calls `ensure_database()` once to make sure the SQLite file exists and is
  initialized.
- Renders the conversation (`agent_state["messages"]`) as chat bubbles.
- On each user message, calls `run_turn(agent_state, user_message)` — this is
  the **single entry point** into the whole agent — and replaces
  `st.session_state.agent_state` with the returned state.
- The **sidebar** shows: the user's profile (name/role — used for role-based
  defaults), the active LLM provider/model/temperature (Layer 3 config), saved
  long-term preferences, and the full working-memory snapshot (workflow state,
  state history, current intent + confidence, iteration count, fallback
  reason, collected_information, missing_fields, pending_confirmation,
  latest_tool_result).
- Below the chat, a **"Tool activity (most recent turn)"** panel lists every
  tool call made this turn with its exact input and result — this is
  `state["tool_activity"]`, populated by `_record_tool_call`.
- "New conversation" button regenerates `session_id` and resets `agent_state`
  (a fresh Short-Term Memory), but long-term preferences (SQLite) persist.

**4. Files**
- `streamlit_app.py` (the entire UI, ~197 lines)
- Depends on: `app/config.py`, `app/db/connection.py`, `app/memory`
  (`LongTermMemory`), `app/workflow` (`new_agent_state`, `run_turn`)

**5. How to demo it live**
1. Run the app (see Section G for startup).
2. Open http://localhost:8501.
3. Point at the sidebar and say: "This is our working-memory panel — it's the
   literal `AgentState` object the LangGraph graph passes around."
4. Ask a question (e.g. "What is CE205?"), then immediately expand the **Tool
   activity** panel and show the exact tool name/input/output that produced
   the answer — this is the grounding proof.
5. Change the **Role** dropdown to "Instructor" and **Name** to "Dr. Hassan
   Nasser" to show role-based defaults later (see Component 6 / Section J).

---

## 2. LangGraph Orchestration — the State Machine (Layer 2)

**1. Why it exists**
The project requires an explicit, multi-step agent workflow with named states
and transitions — not "the LLM just decides everything end to end." LangGraph
gives us a typed graph of nodes and edges that we can draw, log, and reason
about, and which enforces our safety rules (confirmation gating, iteration
limits) structurally rather than by hoping the LLM behaves.

**2. Requirement satisfied**
Layer 2 (Orchestration / Agent Workflow) — specifically the required explicit
state machine: START → INTENT_CLASSIFICATION → INFORMATION_GATHERING →
VALIDATION → ANALYSIS → CONFIRMATION_REQUIRED → ACTION_EXECUTION →
REPORT_GENERATION → END.

**3. What it does during execution**
Every user message triggers exactly one `graph.invoke(state)` call. The graph
always starts at `intent_classification` and always ends at `finalize`, but
the path between them depends on the classified intent (full details in
Section E). Each node appends its name to `state["state_history"]` so the
exact path taken in a turn is visible afterward (and shown in the sidebar).

**4. Files**
- `app/workflow/graph.py` — builds and compiles the graph, exposes
  `run_turn(state, user_message)`
- `app/workflow/nodes.py` — the 9 node functions (the actual logic)
- `app/workflow/router.py` — the 3 conditional-edge routing functions +
  intent classification
- `app/workflow/state.py` — `AgentState` schema, `new_agent_state`,
  `start_turn`

**5. How to demo it live**
Ask three different questions in the same session and, after each, read the
sidebar's "State history (last turn)" line aloud:
- "What is CE205?" → `INTENT_CLASSIFICATION → INFORMATION_GATHERING →
  VALIDATION → REPORT_GENERATION → END` (skips ANALYSIS/CONFIRMATION)
- "Is Yousef Khalil eligible to enroll in CE205 for Spring 2026?" →
  `... → VALIDATION → ANALYSIS → REPORT_GENERATION → END`
- "Enroll Yousef Khalil in CE205 for Spring 2026" → `... → ANALYSIS →
  CONFIRMATION_REQUIRED → END`, then "yes" → `INTENT_CLASSIFICATION →
  ACTION_EXECUTION → REPORT_GENERATION → END`

This single exercise demonstrates the entire state machine without opening any
code.

---

## 3. The Nine Tools (Layer 4 — Capability / Action Layer)

**1. Why it exists**
The project requires the agent to have **4 mandatory tools** the LLM can call,
plus optional bonus tools. Tools are the *only* code paths that touch the
database — this is the architectural guarantee that the agent cannot
hallucinate data (every number/name in a response either came from a tool
result or is a generic phrase like "Could you tell me...").

**2. Requirement satisfied**
Layer 4 (Tools), the 4 required tools (information retrieval, analysis,
action/state-change, reporting), plus 5 bonus tools for extra credit.

**3. What it does during execution / 4. Files / 5. Demo**
Covered in full, tool-by-tool, in **Section C** below — this avoids repeating
the same material twice. The short summary:

| # | Tool | Type | File |
|---|------|------|------|
| 1 | `get_university_information` | Information retrieval (read-only) | `app/tools/information_tool.py` |
| 2 | `analyze_enrollment_eligibility` | Analysis (read-only) | `app/tools/analysis_tool.py` |
| 3 | `create_enrollment_request` | Action (state-changing, confirmation-gated) | `app/tools/action_tool.py` |
| 4 | `generate_student_report` | Reporting (read-only) | `app/tools/reporting_tool.py` |
| 5 | `predict_future_gpa` | Bonus — analysis | `app/tools/bonus_tools.py` |
| 6 | `generate_study_plan` | Bonus — planning | `app/tools/bonus_tools.py` |
| 7 | `generate_payroll_report` | Bonus — reporting | `app/tools/bonus_tools.py` |
| 8 | `analyze_section_utilization` | Bonus — analysis | `app/tools/bonus_tools.py` |
| 9 | `generate_institution_report` | Bonus — institution-wide reporting | `app/tools/bonus_tools.py` |

All 9 share one helper module, `app/tools/db_helpers.py`, which is the single
place that knows how to look up a student/instructor/course/semester by
id/name/email and how to compute GPA/standing — this is why **every tool gives
the same answer for the same entity** regardless of how it's named.

---

## 4. The Memory Layer (3 tiers)

Covered in full in **Section D**. Summary table:

| Tier | What it holds | Lifetime | File |
|------|----------------|----------|------|
| Short-term | Raw conversation messages + recent interaction log | One browser session (in `AgentState["messages"]`) | `app/memory/short_term.py` |
| Working | Current intent, confidence, collected fields, missing fields, pending confirmation, latest tool result, workflow state, iteration count | One turn → carried/merged into the next turn within a session | `app/memory/working_memory.py`, embedded in `AgentState` |
| Long-term | Per-user key/value preferences | Across sessions, in SQLite `user_preferences` table | `app/memory/long_term.py` |

---

## 5. Configurable LLM Client (Layer 3)

**1. Why it exists**
The project explicitly calls for a layer where the LLM provider/model can be
swapped via configuration, not code changes — proving the orchestration logic
is provider-agnostic.

**2. Requirement satisfied**
Layer 3 (LLM Integration), "configurable through environment variables."

**3. What it does during execution**
`get_chat_model()` reads `LLM_PROVIDER` (`ollama` | `openai` | `anthropic`;
default `ollama`), `LLM_MODEL` (defaults: `llama3.1`, `gpt-4o-mini`,
`claude-3-5-haiku-20241022`), and `LLM_TEMPERATURE` (default `0.1` — low,
for consistent JSON intent classification) from environment variables
(loaded via `.env` through `python-dotenv`, with built-in defaults if `.env`
doesn't exist), and returns the matching LangChain chat model instance.
`ollama` is the PRIMARY/REQUIRED provider — local/offline, no API key.
`openai`/`anthropic` are OPTIONAL fallback providers, only used if
explicitly selected. Two places call it: `classify_intent()` (router) for
intent classification, and nothing else — **tools never call the LLM**,
only the router does.

**4. Files**
- `app/llm/client.py` (`get_chat_model`, `LLMConfigurationError`)
- `app/config.py` (reads the env vars, defaults to `LLM_PROVIDER=ollama`)
- `.env.example` (documents every variable)

**5. How to demo it live**
By default (`LLM_PROVIDER=ollama`, no `.env` needed) the app talks to a
local/Docker Ollama server. To demo provider-swapping: create `.env` from
`.env.example`, set `LLM_PROVIDER=openai` + `OPENAI_API_KEY=...` (or
`LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=...`), and restart — that's
the *only* change needed to switch providers, no code changes. If asked
"what if the optional fallback's key is missing," explain
`LLMConfigurationError` is caught in `streamlit_app.py` and shown as a
friendly banner instead of a crash — note that this only applies to the
optional `openai`/`anthropic` providers; the default `ollama` provider
never raises this (an unreachable Ollama server instead causes
`classify_intent` to fall back to `intent="unsupported"`).

---

## 6. Database Layer (Layer 6)

Covered in full in **Section F**. One-line summary: a SQLite database
(`app/db/university.db`, built from `schema.sql` + `seed_data.sql` +
`policies.json` by `app/db/init_db.py`) that mirrors the core entities of the
existing University Management System (students, instructors, courses,
sections, enrollments, grades, accounts, payroll) and adds three new tables
the agent needs: `enrollment_requests`, `agent_logs`, `user_preferences`.

---

## 7. Logging / Audit Trail

**1. Why it exists**
For explainability and for the evaluation suite: every classified intent,
tool call, validation failure, and fallback needs to be recorded so we (and
the instructor) can audit *why* the agent did what it did, and so the eval
suite can compute metrics like tool-selection accuracy from real traces.

**2. Requirement satisfied**
Observability / explainability expectations called out in the architecture;
also backs the evaluation metrics required for grading.

**3. What it does during execution**
`AgentLogger(session_id, user_role, user_name)` is created once per turn
(`_logger(state)` in `nodes.py`, cached on `state["_logger"]`... actually
instantiated fresh and cheap). Every node calls one of:
- `log_intent(intent, workflow_state)` — after classification
- `log_tool_call(tool_name, tool_input, tool_result, workflow_state, intent)`
  — after every tool invocation
- `log_validation_failure(tool_name, reason, workflow_state, intent)` — when
  required fields are missing
- `log_fallback(reason, workflow_state, intent)` — when the graph falls back

Each call inserts one row into `agent_logs`. Logging is wrapped in
try/except — **a logging failure can never crash a conversation** (this is a
deliberate safety design point worth mentioning in the defense).

**4. Files**
- `app/logging_system/logger.py` (`AgentLogger`, `get_recent_logs`)
- `app/db/schema.sql` (`agent_logs` table)

**5. How to demo it live**
After a few chat turns, either (a) show the Streamlit "Tool activity" panel
(which is the in-memory equivalent for the current turn), or (b) if comfortable
with a terminal, run:
```
sqlite3 app/db/university.db "SELECT log_id, intent, workflow_state, tool_name, fallback FROM agent_logs ORDER BY log_id DESC LIMIT 10;"
```
and show the audit trail row-by-row.

---

## 8. Docker

Covered in full in **Section G**.

---

# Section A — System Architecture Explanation (Presentation-Ready)

Use this as your "architecture slide" narration. Draw or show this diagram:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1 — Presentation (Streamlit)                                    │
│   streamlit_app.py: chat UI, working-memory panel, tool-activity log  │
└───────────────────────────────┬───────────────────────────────────────┘
                                  │ run_turn(state, user_message)
┌───────────────────────────────▼───────────────────────────────────────┐
│ Layer 2 — Orchestration (LangGraph state machine)                      │
│   app/workflow/graph.py, nodes.py, router.py, state.py                 │
│   9 nodes: intent_classification → information_gathering → validation  │
│   → analysis → confirmation_required → action_execution →              │
│   report_generation → fallback → finalize                              │
└──────┬────────────────────────────┬────────────────────────────────────┘
       │ classify_intent()           │ tool.invoke(...)
┌──────▼─────────────┐    ┌──────────▼───────────────────────────────────┐
│ Layer 3 — LLM       │    │ Layer 4 — Tools (9 total)                     │
│ app/llm/client.py   │    │ information_tool, analysis_tool, action_tool, │
│ Ollama (default,    │    │ reporting_tool, bonus_tools (x5)              │
│ required) / OpenAI / │    │ all read/write ONLY through db_helpers.py     │
│ Anthropic (optional)│    │                                                │
└─────────────────────┘    └──────────┬───────────────────────────────────┘
                                        │
       ┌────────────────────────────────▼─────────────────────────────────┐
       │ Layer 5 — Memory                                                   │
       │ Short-term (messages, in AgentState) · Working (AgentState fields)│
       │ · Long-term (user_preferences table, app/memory/long_term.py)     │
       └────────────────────────────────┬─────────────────────────────────┘
                                          │
       ┌──────────────────────────────────▼───────────────────────────────┐
       │ Layer 6 — Data (SQLite)                                            │
       │ app/db/university.db built from schema.sql + seed_data.sql +      │
       │ policies.json. Existing UMS entities + 3 new agent tables:        │
       │ enrollment_requests, agent_logs, user_preferences                 │
       └─────────────────────────────────────────────────────────────────┘
```

**Talking points (≈60 seconds):**

1. "Every user turn enters at the top through Streamlit and calls one function,
   `run_turn`, which hands a single state object — `AgentState` — into a
   compiled LangGraph."
2. "The graph has 9 explicit nodes representing the required workflow states.
   The only place the LLM is called is intent classification — once per turn,
   not per tool call. This keeps cost and latency predictable and keeps the
   agent's behavior auditable."
3. "Tools are the only code that touches SQLite, and they all funnel through
   one shared lookup module, `db_helpers.py`, so a student can be found by ID,
   full name, or email consistently everywhere."
4. "Memory has three tiers: the conversation itself (short-term), the
   structured 'scratchpad' of the current task — intent, missing fields,
   pending confirmations (working), and cross-session user preferences stored
   in SQLite (long-term)."
5. "Everything is configurable through environment variables — LLM provider,
   model, database path, iteration limits, confidence thresholds — and the
   whole stack starts with one `docker compose up --build`."

**Why this architecture satisfies the brief:** it maps 1:1 onto the 6 layers
the project specification asks for, keeps the state machine *explicit* (not
implicit inside one big LLM prompt), and makes every factual claim traceable
to a tool call and every data-changing action traceable to a user
confirmation.

---

# Section B — End-to-End Workflow Explanation (User Message → Final Response)

Walk through this with a concrete example: the user (role = student, name =
"Yousef Khalil") types **"Can I enroll in CE205 for Spring 2026?"**

**Step 0 — Entry point.**
Streamlit calls `run_turn(agent_state, "Can I enroll in CE205 for Spring
2026?")`.

**Step 1 — `start_turn` (app/workflow/state.py).**
- Appends `{"role": "user", "content": "..."}` to `state["messages"]`.
- Resets per-turn fields: `workflow_state = "START"`, `state_history = []`,
  `tool_activity = []`, `final_response = None`, `fallback_reason = None`.
- **Preserves** cross-turn working memory: `collected_information`,
  `pending_confirmation`, `latest_tool_result` carry over (this is what makes
  multi-turn memory work, e.g. MULTI-01 in the eval suite).

**Step 2 — `node_intent_classification` (graph entry node).**
- Pushes `"INTENT_CLASSIFICATION"` onto `state_history`.
- Increments `iteration_count` (safety counter, capped at `MAX_ITERATIONS=6`).
- Calls `classify_intent(state)`:
  - First checks: is there a `pending_confirmation` AND does the message
    match the yes/no regex? (Not in this example — no pending confirmation
    yet.)
  - Otherwise builds a prompt from the last 8 messages and calls the LLM
    (`get_chat_model().invoke(...)`) asking it to return JSON:
    `{"intent": ..., "confidence": ..., "entities": {...}}`.
  - For our example, the LLM should return something like
    `{"intent": "enrollment_request", "confidence": 0.9, "entities":
    {"student_identifier": "Yousef Khalil", "course_code": "CE205",
    "semester_name": "Spring 2026"}}`. (The student's own name is inferred
    from "Can I..." plus the session's `user_name`.)
  - `_extract_json` strips markdown fences and parses; intent is validated
    against the `INTENTS` list (else `"unsupported"`); confidence clamped to
    [0,1].
- Non-empty entities are merged into `state["collected_information"]`.
- `_logger(state).log_intent("enrollment_request", "INTENT_CLASSIFICATION")`
  writes an audit row.

**Step 3 — `route_after_intent` (conditional edge).**
- `iteration_count (1) > MAX_ITERATIONS (6)`? No.
- Intent is `confirm_yes`/`confirm_no`? No.
- Intent `unsupported` or confidence < `INTENT_CONFIDENCE_THRESHOLD (0.4)`? No
  (confidence ~0.9).
- → routes to **`information_gathering`**.

**Step 4 — `node_information_gathering`.**
- Pushes `"INFORMATION_GATHERING"`.
- Role-based default: intent `enrollment_request` is in `_STUDENT_INTENTS`,
  role is `"student"`, and `student_identifier` is already present (Yousef
  said "Can I..." and the LLM filled it from his name) — if it *weren't*
  present, this node would default it to `state["user_name"]`.

**Step 5 — `node_validation`.**
- Pushes `"VALIDATION"`.
- `INTENT_REQUIRED_FIELDS["enrollment_request"] = ["student_identifier",
  "course_code"]`. Both present in `collected_information` → `missing_fields
  = []`.

**Step 6 — `route_after_validation`.**
- `missing_fields` empty.
- Intent in `(eligibility_check, enrollment_request)` → routes to
  **`analysis`**.

**Step 7 — `node_analysis`.**
- Pushes `"ANALYSIS"`.
- Calls `analyze_enrollment_eligibility.invoke({"student_identifier":
  "Yousef Khalil", "course_code": "CE205", "semester_name": "Spring 2026"})`.
- This tool (via `evaluate_eligibility` in `analysis_tool.py`) checks: student
  exists → course exists → section exists for Spring 2026 → not a duplicate
  enrollment → section has seats → all prerequisites (none for CE205) passed
  → balance (5000) ≥ fee (1200). All pass → `{"eligible": true, "reasons": [],
  "details": {...}}`.
- Result stored in `state["latest_tool_result"]`; tool call recorded via
  `_record_tool_call` (→ `tool_activity`, and logged to `agent_logs`).

**Step 8 — `route_after_analysis`.**
- Intent == `"enrollment_request"` → routes to **`confirmation_required`**.

**Step 9 — `node_confirmation_required`.**
- Pushes `"CONFIRMATION_REQUIRED"`.
- Calls `create_enrollment_request.invoke({..., "confirm": False})`. Because
  `eligible=True`, this **only inserts a `PENDING_CONFIRMATION` row** into
  `enrollment_requests` (no enrollment, no balance change yet) and returns a
  message: *"Yousef Khalil is eligible to enroll in CE205 for Spring 2026.
  Please confirm to proceed."*
- `state["pending_confirmation"] = {student_identifier, course_code,
  semester_name, request_id, eligible: True}`.
- `state["final_response"] = "Yousef Khalil is eligible to enroll in CE205
  for Spring 2026. Please confirm to proceed. Reply 'yes' to confirm or 'no'
  to cancel."`

**Step 10 — `confirmation_required → finalize` (direct edge).**
- `node_finalize` pushes `"END"`, appends the assistant message to
  `state["messages"]`. **Turn 1 ends here.**

---

**Turn 2 — user replies "yes".**

- `start_turn` resets per-turn fields but **keeps `pending_confirmation`**.
- `node_intent_classification`: `pending_confirmation` is set AND "yes"
  matches `_YES_RE` → **short-circuits without calling the LLM** →
  `("confirm_yes", 1.0, {})`.
- `route_after_intent`: intent is `confirm_yes` and `pending_confirmation`
  exists → routes directly to **`action_execution`** (skips
  information_gathering/validation/analysis entirely).
- `node_action_execution`: intent ≠ `confirm_no`, so calls
  `create_enrollment_request.invoke({student_identifier, course_code,
  semester_name, confirm: True})`. The tool **re-validates eligibility**
  (state may have changed since turn 1!), and because still eligible:
  inserts an `ENROLLED` row into `enrollments`, deducts 1200 from Yousef's
  balance (5000 → 3800), marks the request `EXECUTED`. Returns `{"status":
  "executed", "message": "Yousef Khalil has been enrolled in CE205 (Spring
  2026). Fee of 1200.00 deducted; new balance is 3800.00."}`.
- `state["pending_confirmation"] = None` (cleared).
- `action_execution → report_generation` (direct edge): intent is
  `enrollment_request`/`confirm_yes`, so `final_response =
  _phrase_from_result(latest_tool_result)` = the message above (grounded
  directly from the tool's `message` field — nothing invented).
- `report_generation → finalize → END`.

**This two-turn example is your single best live demo** — it touches intent
classification, role defaults, validation, analysis, the confirmation gate,
short-circuited yes/no routing, action execution, and grounded phrasing, all
in ~10 seconds of LLM time (one call in turn 1, **zero** LLM calls in turn 2).

---

# Section C — Tool-by-Tool Explanation (Inputs, Outputs, Validation, Safety)

Every tool is a LangChain `@tool` with a Pydantic `args_schema` (so arguments
are type-checked before execution), reads/writes exclusively through
`app/tools/db_helpers.py`, and returns a plain dict — never raw exceptions, and
never free-text the LLM invented.

### Tool 1 — `get_university_information` (Required)
*File: `app/tools/information_tool.py`*

- **Inputs**: `query_type` (required, one of `course | policy | instructor |
  program | department | section | semester`), `identifier` (optional —
  course code, name, policy key, etc.; omit to list all), `semester_name`
  (optional, required *in practice* for `section`).
- **Outputs**: `{"found": bool, "query_type": str, "data": dict|list,
  "message": str, "formatted_text": str}`. `formatted_text` is a
  human-readable rendering built *only* from fields already in `data` (see
  `_formatted_text` / `_fmt_course` etc.) — the agent's final response quotes
  this directly.
- **Validation**: Pydantic enforces `query_type` is one of the 7 literals.
  Unknown course codes / instructor names / policy keys return `found: False`
  with a helpful `message` (e.g. listing available policy keys) — never a
  guess.
- **Safety**: 100% read-only. No write statements anywhere in this file.

### Tool 2 — `analyze_enrollment_eligibility` (Required)
*File: `app/tools/analysis_tool.py`*

- **Inputs**: `student_identifier` (id/name/email, required), `course_code`
  (required), `semester_name` (optional, defaults to the current semester via
  `is_current=1`).
- **Outputs**: `{"eligible": bool, "reasons": [str,...], "details": {student,
  course, semester, capacity, prerequisites, balance}}`.
- **Validation / checks performed (in order, all grounded in SQL)**:
  1. Student exists (else early return, eligible=False).
  2. Course exists.
  3. Semester resolves (named or current).
  4. A section for that course+semester exists.
  5. Student isn't already `ENROLLED` in that section (duplicate check).
  6. Section capacity vs. enrolled count (`section_enrolled_count`).
  7. All prerequisite courses completed with a grade in `{A,B,C,D}`
     (`PASSING_GRADES` — F doesn't count, per `grading_policy`).
  8. `student_accounts.balance >= courses.course_fee`.
  `eligible = (len(reasons) == 0)` — i.e. **any** failed check makes it
  ineligible, and `reasons` lists *all* of them (not just the first), so the
  user gets a complete picture.
- **Safety**: read-only; this is also reused (imported as
  `evaluate_eligibility`) by Tool 3 so the *same* eligibility logic backs both
  the "can I?" question and the actual enrollment action — no logic
  duplication/drift.

### Tool 3 — `create_enrollment_request` (Required, state-changing)
*File: `app/tools/action_tool.py`*

- **Inputs**: `student_identifier`, `course_code`, `semester_name` (optional),
  `confirm` (bool, **default False**).
- **Outputs**: `{"status": "pending_confirmation"|"executed"|"rejected"|
  "error", "eligible": bool, "reasons": [...], "request_id": int|null,
  "enrollment_id": int|null, "new_balance": float|null, "message": str}`.
- **Validation / two-call protocol**:
  - **`confirm=False`** (first call, from `node_confirmation_required`):
    re-runs `evaluate_eligibility`, inserts a row into `enrollment_requests`
    with `status='PENDING_CONFIRMATION'` and the eligibility result as JSON
    (audit trail), and returns `status="pending_confirmation"` with a
    human-readable message — **no enrollment row, no balance change**.
  - **`confirm=True`** (second call, from `node_action_execution`, only after
    user says "yes"): re-runs eligibility **again** (state may have changed
    between the two calls — e.g. seat taken by someone else). If still
    eligible: inserts into `enrollments` (`ENROLLED`), deducts `course_fee`
    from `student_accounts.balance`, marks the request `EXECUTED`,
    `status="executed"`. If no longer eligible: marks the request `REJECTED`,
    `status="rejected"`, **no enrollment, no balance change**.
  - If the student can't be found at all: `status="error"`.
- **Safety (this is the centerpiece of the project's safety story)**:
  - This is the **only** tool in `CONFIRMATION_REQUIRED_TOOLS`
    (`app/config.py`).
  - It is structurally impossible to reach `confirm=True` without the user
    having sent a message matching `_YES_RE` while `pending_confirmation` was
    set (enforced by `route_after_intent` + `node_action_execution`).
  - Double-checking eligibility on the second call prevents race conditions
    (e.g. seat fills up between "are there seats?" and "yes, enroll me").
  - Every outcome (pending/executed/rejected) is persisted to
    `enrollment_requests` — nothing is silently dropped.

### Tool 4 — `generate_student_report` (Required)
*File: `app/tools/reporting_tool.py`*

- **Inputs**: `student_identifier` (required), `report_type` (required, one
  of `transcript_summary | gpa_summary | academic_standing |
  recommendations`).
- **Outputs**: `{"found": bool, "report_type": str, "student": {id, name}|
  null, "data": {...}, "formatted_text": str}`.
- **Validation**: Pydantic `Literal` restricts `report_type` to the 4 values.
  Unknown student → `found=False` with `formatted_text = "No student found
  matching '...'"`.
- **What each report computes (all via `db_helpers`)**:
  - `transcript_summary`: lists every `COMPLETED` enrollment with grade,
    total credits, and GPA (`compute_gpa`).
  - `gpa_summary`: GPA + completed-course count + `academic_standing(gpa)`.
  - `academic_standing`: standing + the actual rules from
    `policies.json["academic_standing_policy"]` quoted verbatim — policy text
    is never paraphrased by the LLM.
  - `recommendations`: courses whose prerequisites are *all* satisfied by
    passed courses, excluding ones already completed/active; adds a probation
    note if GPA < 2.0.
- **Safety**: read-only.

### Tool 5 — `predict_future_gpa` (Bonus)
*File: `app/tools/bonus_tools.py`*

- **Inputs**: `student_identifier`, `planned_courses` (list of
  `{course_code, expected_grade}` where `expected_grade ∈ {A,B,C,D,F}`).
- **Outputs**: `{"found": bool, "message": str, "current_gpa": float|null,
  "predicted_gpa": float|null, "formatted_text": str, "details": {...}}`.
- **Validation**: each `expected_grade` is Pydantic-validated against the
  literal grade set; unknown course codes are collected into
  `unknown_courses` and *excluded* from the calculation (never silently
  guessed), and called out in both `message` and `formatted_text`.
- **What it does**: combines the student's real completed-course grade points
  with the *hypothetical* points from `planned_courses`, recomputes a
  weighted GPA. This is clearly framed as a **prediction/what-if**, not a
  database write — nothing is persisted.
- **Safety**: read-only, purely a calculation over real + hypothetical data.

### Tool 6 — `generate_study_plan` (Bonus)
*File: `app/tools/bonus_tools.py`*

- **Inputs**: `student_identifier`, `max_credits_per_semester` (int, 1–30,
  default 15).
- **Outputs**: `{"found": bool, "message": str, "plan": [{semester, courses,
  total_credits}], "unscheduled_courses": [...], "formatted_text": str}`.
- **Validation**: Pydantic `ge=1, le=30` bounds the credit cap.
- **What it does**: greedily buckets courses the student hasn't taken/isn't
  currently taking into semesters, where a course can only be scheduled once
  all its prerequisites are scheduled in an earlier bucket and the bucket's
  total credits don't exceed the cap. Capped at **8 semesters** as a safety
  bound — if courses remain blocked after 8 semesters (cyclic or unreachable
  prereqs), they're reported in `unscheduled_courses` instead of looping
  forever.
- **Safety**: read-only planning aid; the 8-semester cap is a deliberate
  "stopping condition" worth mentioning in the defense (parallels
  `MAX_ITERATIONS`).

### Tool 7 — `generate_payroll_report` (Bonus)
*File: `app/tools/bonus_tools.py`*

- **Inputs**: `instructor_identifier` (id/name/email), `period_start`,
  `period_end` (both optional, `'YYYY-MM-DD'`).
- **Outputs**: `{"found": bool, "message": str, "data": {instructor,
  hourly_rate, total_hours, amount_due, breakdown: [{course_code, hours}],
  formatted_text}}`.
- **Validation**: a `field_validator` enforces `^\d{4}-\d{2}-\d{2}$` on both
  date fields — malformed dates raise a Pydantic validation error before the
  tool ever runs (caught by `_invoke_tool`'s try/except and logged, never
  crashes the conversation).
- **What it does**: sums `instructor_time_entries.hours_worked` **WHERE
  approved = 1** (per `teaching_load_policy`: "unapproved hours are not
  paid"), optionally filtered by date range, multiplied by
  `instructor_salaries.hourly_rate`. Breaks the total down per course.
- **Safety**: read-only — it reports what *would be* owed; it does not insert
  into `salary_payments`.
- **Verified example**: Dr. Hassan Nasser, all-time → 23.00 approved hours ×
  50.00/hr = **1150.00**, broken down CE205: 10.00 hrs, EE320: 13.00 hrs.

### Tool 8 — `analyze_section_utilization` (Bonus)
*File: `app/tools/bonus_tools.py`*

- **Inputs**: `semester_name` (optional, defaults to current semester).
- **Outputs**: `{"found": bool, "message": str, "semester_name": str,
  "sections": [{section_id, course_code, course_title, instructor_name,
  capacity, enrolled, utilization_pct, status}], "formatted_text": str}`.
- **Validation**: unresolvable semester → `found=False` with explicit message.
- **What it does**: for every section in the semester, computes
  `enrolled/capacity` and classifies per `section_utilization_policy`: **Full**
  if `enrolled >= capacity`, **Underutilized** if ratio `< 0.4`, otherwise
  **Optimal**. Also lists which sections are Full / Underutilized overall.
- **Safety**: read-only analytics.

### Tool 9 — `generate_institution_report` (Bonus — extra value-add)
*File: `app/tools/bonus_tools.py`*

- **Inputs**: `report_type` (`tuition_summary | payroll_summary |
  enrollment_overview`), plus `semester_name` (for enrollment_overview) or
  `period_start`/`period_end` (for payroll_summary, same date validation as
  Tool 7).
- **Outputs**: `{"found": bool, "message": str, "data": {...with
  formatted_text...}}` (shape depends on `report_type`).
- **What it does**:
  - `tuition_summary`: lists every student's `student_accounts.balance`,
    flags any below `LOW_BALANCE_THRESHOLD = 1000.0`, sums the total balance
    across all accounts.
  - `payroll_summary`: loops every instructor and **calls
    `generate_payroll_report.invoke(...)` for each** (tool composition — reuse,
    not reimplementation), sums a grand total.
  - `enrollment_overview`: calls `analyze_section_utilization.invoke(...)`
    (again, composition) and aggregates total enrolled/capacity plus
    full/underutilized section lists.
- **Safety**: read-only; intended audience is Registrar/Finance staff (a nice
  talking point: this tool demonstrates the agent serving *multiple user
  roles*, not just students).
- **Verified example**: `payroll_summary` (all time) → Dr. Hassan Nasser
  23.00 hrs / 1150.00, Dr. Maya Saad 19.00 hrs / 1045.00, Dr. Rami Fakhoury
  18.00 hrs / 1080.00, **grand total payroll: 3275.00**.

### Cross-cutting safety mechanisms (mention all of these in the defense)
1. **`db_helpers.py` is the single source of truth** for "what does
   identifier X resolve to" — every tool agrees on the same student/course/
   instructor/semester for the same input.
2. **Pydantic schemas validate every tool input** before any SQL runs.
3. **`_invoke_tool` (nodes.py)** wraps every `tool.invoke()` in try/except —
   an exception becomes a logged error and a graceful fallback message, never
   a crash.
4. **`_phrase_from_result`** grounds the final response in
   `formatted_text` → `data.formatted_text` → `message` → a generic
   "I couldn't find that" / raw JSON — the LLM is never asked to "describe"
   a tool result in its own words for factual content.
5. **Only one tool can write data**, and only with explicit confirmation.

---

# Section D — Memory Explanation (Short-Term, Working, Long-Term)

The project requires a layered memory design. All three tiers live inside (or
alongside) the single `AgentState` object that flows through the graph —
there is **no vector DB, no embeddings, no RAG**, by design (the project
explicitly scopes the agent to grounded SQL + policy lookups).

### 1. Short-Term Memory — the conversation itself
*File: `app/memory/short_term.py` (`ShortTermMemory` dataclass)*

- **What it holds**: `session_id`, `user_name`, `user_role`, `messages`
  (full chat history as `{"role": "user"|"assistant", "content": str}`), and
  `recent_interactions` (a capped list, max 10, of `{user_message,
  assistant_response}` pairs via `add_interaction`).
- **Why it exists**: the LLM needs recent conversation context to resolve
  pronouns/follow-ups ("What about CE301 instead?" after asking about CE410),
  and the UI needs the full transcript to render the chat.
- **How it's used**: `history_as_text(limit=20)` renders the last N messages
  as plain text and is fed into the intent-classification prompt
  (`build_intent_classification_messages`), so the LLM sees the conversation
  so far when classifying the *current* message's intent.
- **Lifetime**: one browser session / one `AgentState`. "New conversation"
  in the UI starts a fresh `session_id` and empty message list.
- **In practice**: in this implementation, `AgentState["messages"]` *is* the
  short-term memory — `ShortTermMemory` is the conceptual/dataclass form of
  the same data (useful if we ever persist sessions outside Streamlit's
  in-memory `session_state`).

### 2. Working Memory — the "scratchpad" for the current task
*File: `app/memory/working_memory.py` (`WorkingMemory` TypedDict), mirrored
directly as top-level keys on `AgentState`*

This is the most important tier for the defense — it's *why* the agent can
hold a multi-step task (eligibility → confirmation → execution) across turns
without re-deriving everything from scratch. Exactly 8 fields:

| Field | What it holds | Example |
|---|---|---|
| `current_intent` | last classified intent | `"enrollment_request"` |
| `intent_confidence` | LLM's confidence 0–1 | `0.92` |
| `collected_information` | entities gathered so far (merges across turns) | `{"student_identifier": "Yousef Khalil", "course_code": "CE205", "semester_name": "Spring 2026"}` |
| `missing_fields` | required fields not yet collected | `[]` or `["course_code"]` |
| `pending_confirmation` | staged action awaiting yes/no | `{"student_identifier":..., "request_id": 2, "eligible": true}` |
| `latest_tool_result` | most recent tool's raw dict result | the `analyze_enrollment_eligibility` output |
| `workflow_state` | current node name | `"CONFIRMATION_REQUIRED"` |
| `iteration_count` | turns processed this "task" (safety counter) | `1` |

- **Why it exists**: this is the literal embodiment of the required
  "Working Memory" component — it's what lets `confirm_yes`/`confirm_no`
  short-circuit straight to `action_execution` in turn 2 without re-asking
  the user for the course code.
- **What happens during execution**: `start_turn()` resets *transient*
  per-turn fields (`workflow_state`, `state_history`, `tool_activity`,
  `final_response`, `fallback_reason`) but **explicitly preserves**
  `collected_information`, `pending_confirmation`, and `latest_tool_result` —
  this is the one line in `state.py` that makes cross-turn memory work.
  `collected_information` is *merged into* (not replaced by) new entities
  each turn, so earlier-provided fields survive.
- **Demo**: the MULTI-01 eval case — ask "Is Aseel Menhem eligible to enroll
  in CE410 for Spring 2026?", then ask "What about CE301 instead?" — the
  second message has no student name in it, but `collected_information`
  already has `student_identifier: "Aseel Menhem"` from turn 1, so the agent
  answers about Aseel without re-asking.

### 3. Long-Term Memory — cross-session user preferences
*File: `app/memory/long_term.py` (`LongTermMemory` class) → SQLite
`user_preferences` table*

- **What it holds**: arbitrary `(user_name, preference_key) → JSON value`
  pairs, e.g. a preferred `max_credits_per_semester` for study plans, or a
  preferred report type.
- **Why it exists**: this is the **bonus** memory tier — it demonstrates
  memory that survives a "New conversation" reset and even a container
  restart (because SQLite is on a Docker volume).
- **What it does during execution**: `set_preference(key, value)` does an
  UPSERT (`INSERT ... ON CONFLICT(user_name, preference_key) DO UPDATE`);
  `get_preference(key, default)` reads and JSON-decodes; `all_preferences()`
  returns everything for a user — this is what the Streamlit sidebar's
  "Long-term memory (preferences)" panel calls and renders with `st.json`.
- **Controlled by**: `ENABLE_LONG_TERM_MEMORY` env var (default `True`).
- **Demo**: this tier currently has a *reading* UI surface (sidebar) and a
  data-layer write API; if asked live to "set" a preference, be honest that
  the current chat flow doesn't yet have a conversational trigger for writing
  one — frame it as "the storage and retrieval API is implemented and
  demoable via the sidebar / a short Python snippet; wiring a chat intent to
  it would be a natural next step."

### How the three tiers interact in one turn
1. Short-term memory gives the LLM conversational context for intent
   classification.
2. Working memory carries forward task state (`collected_information`,
   `pending_confirmation`) so the LLM doesn't need to re-extract everything
   each turn, and so `confirm_yes`/`confirm_no` can be handled **without an
   LLM call at all**.
3. Long-term memory is independent of any single conversation — it's keyed
   by `user_name`, persists in SQLite, and is read at UI render time.

---

# Section E — LangGraph Workflow Explanation (with State Transitions)

### The 9 nodes (`app/workflow/nodes.py`, wired in `app/workflow/graph.py`)

| Node | Pushes to `state_history` | Core action |
|---|---|---|
| `intent_classification` | `INTENT_CLASSIFICATION` | increments `iteration_count`; runs `classify_intent` (LLM call or yes/no short-circuit); merges entities into `collected_information`; logs intent |
| `information_gathering` | `INFORMATION_GATHERING` | applies role-based defaults (student → own name; instructor → own name for payroll) |
| `validation` | `VALIDATION` | checks `collected_information` against `INTENT_REQUIRED_FIELDS`; if fields missing, sets `final_response` to a clarifying question and logs a validation failure |
| `analysis` | `ANALYSIS` | calls `analyze_enrollment_eligibility`; stores result in `latest_tool_result` |
| `confirmation_required` | `CONFIRMATION_REQUIRED` | calls `create_enrollment_request(confirm=False)`; sets `pending_confirmation`; builds the "please confirm" message |
| `action_execution` | `ACTION_EXECUTION` | for `confirm_no`, synthesizes a cancellation result without calling the tool; for `confirm_yes`, calls `create_enrollment_request(confirm=True)` using the stored `pending_confirmation`; clears `pending_confirmation` |
| `report_generation` | `REPORT_GENERATION` | dispatches on `current_intent` to the correct tool (see table below) and sets `final_response` via `_phrase_from_result` |
| `fallback` | (sets `fallback_reason`) | one of 3 reasons; sets `final_response` to a fixed safe message; logs fallback |
| `finalize` | `END` | ensures `final_response` is non-null (defaults to `FALLBACK_MESSAGE`); appends the assistant message to `messages` |

### `report_generation`'s dispatch table (by `current_intent`)

| Intent | Tool called | Inputs taken from `collected_information` |
|---|---|---|
| `information_query` | `get_university_information` | `query_type`, `identifier` (falls back through `identifier`→`course_code`→`instructor_identifier`→`student_identifier`), `semester_name` |
| `eligibility_check` | (uses `latest_tool_result` from `analysis`) | — builds a custom sentence: "{student} is eligible/NOT eligible to enroll in {course}: {reasons}" |
| `enrollment_request` / `confirm_yes` / `confirm_no` | (uses `latest_tool_result` from `action_execution`) | `_phrase_from_result` |
| `student_report` | `generate_student_report` | `student_identifier`, `report_type` |
| `gpa_prediction` | `predict_future_gpa` | `student_identifier`, `planned_courses` (or `[]`) |
| `study_plan` | `generate_study_plan` | `student_identifier`, `max_credits_per_semester` (optional) |
| `payroll_report` | `generate_payroll_report` | `instructor_identifier`, `period_start`, `period_end` |
| `section_utilization` | `analyze_section_utilization` | `semester_name` |
| `institution_report` | `generate_institution_report` | `report_type`, `semester_name`, `period_start`, `period_end` |
| anything else | — | `{"found": False, "message": FALLBACK_MESSAGE}` |

### The 3 routing functions (`app/workflow/router.py`)

**`route_after_intent(state)`** — first fork after intent classification:
- `iteration_count > MAX_ITERATIONS (6)` → `"fallback"` (reason:
  `max_iterations_exceeded`)
- intent ∈ `{confirm_yes, confirm_no}`:
  - if `pending_confirmation` exists → `"action_execution"`
  - else → `"fallback"` (reason: `no_pending_confirmation`)
- intent == `"unsupported"` or `confidence < INTENT_CONFIDENCE_THRESHOLD
  (0.4)` → `"fallback"` (reason: `unsupported_or_low_confidence`)
- else → `"information_gathering"`

**`route_after_validation(state)`**:
- `missing_fields` non-empty → `"finalize"` (the clarifying question set in
  `node_validation` becomes the response — turn ends here, asking the user
  for more info)
- intent ∈ `{eligibility_check, enrollment_request}` → `"analysis"`
- else → `"report_generation"`

**`route_after_analysis(state)`**:
- intent == `"enrollment_request"` → `"confirmation_required"`
- else (i.e. `eligibility_check`) → `"report_generation"`

### Full topology diagram

```
START
  └─▶ intent_classification
        ├─(fallback)──────────────────▶ fallback ─▶ finalize ─▶ END
        ├─(action_execution)──────────▶ action_execution ─▶ report_generation ─▶ finalize ─▶ END
        └─(information_gathering)─────▶ information_gathering ─▶ validation
                                                                      ├─(finalize)──────────▶ finalize ─▶ END
                                                                      ├─(analysis)──────────▶ analysis
                                                                      │                          ├─(confirmation_required)─▶ confirmation_required ─▶ finalize ─▶ END
                                                                      │                          └─(report_generation)─────▶ report_generation ─▶ finalize ─▶ END
                                                                      └─(report_generation)─▶ report_generation ─▶ finalize ─▶ END
```

### Stopping conditions / safety guarantees (say all 3 in the defense)
1. **`MAX_ITERATIONS = 6`** — caps how many turns a single multi-step task can
   take before the agent forces a "please rephrase" fallback. Prevents
   infinite confirm/clarify loops.
2. **`INTENT_CONFIDENCE_THRESHOLD = 0.4`** — anything the LLM isn't reasonably
   sure about, or explicitly classifies as `unsupported`, never reaches a
   tool. The fallback message is fixed and policy-defined (from
   `agent_scope_policy`), never generated by the LLM.
3. **Confirmation gating** — `create_enrollment_request(confirm=True)` is
   reachable *only* via `confirm_yes` + an existing `pending_confirmation`,
   which itself can only be set by `confirmation_required`, which is only
   reached for `enrollment_request` after a passing `analysis`. There is no
   path from a single user message straight to a data-changing write.

---

# Section F — Database Explanation (Existing UMS vs. New AI Agent Additions)

**Important framing for the defense**: we did **not** modify the production
SQL Server schema (`sql/02_tables.sql` etc.) of the existing University
Management System. We re-derived an equivalent **SQLite** schema
(`ai_agent/app/db/schema.sql`) containing the subset of entities the agent
needs, seeded with consistent sample data (`seed_data.sql`), and **added
three new tables** specific to the agent. `app/db/init_db.py` builds
`app/db/university.db` from these files (`python -m app.db.init_db --force`
recreates it from scratch).

### Tables carried over from the existing UMS (read by the agent's tools)

| Table | Purpose | Used by |
|---|---|---|
| `roles`, `users` | login/role records | seed data only (not directly queried by tools) |
| `departments`, `programs` | org structure | `get_university_information` (program/department queries) |
| `students` | id, name, email, status, gpa, program | `find_student` — used by nearly every tool |
| `instructors`, `instructor_salaries` | id, name, dept, max_credits, hourly_rate | `find_instructor`, payroll tools |
| `courses`, `course_prerequisites` | catalog + prerequisite graph (**NEW relationship** added for this project) | information, eligibility, study plan, recommendations |
| `semesters` | terms, `is_current` flag | every tool that defaults to "current semester" |
| `sections` | course offered in a semester by an instructor, with `capacity` | eligibility, utilization, section info |
| `enrollments`, `grades` | enrollment status + locked grades | GPA, transcripts, eligibility (duplicate check), recommendations |
| `student_accounts`, `student_payments` | balances + payment history | eligibility (balance check), enrollment execution, tuition summary |
| `instructor_time_entries`, `salary_payments` | approved hours + payroll history | payroll report, institution payroll summary |

### New tables added specifically for the AI agent

| Table | Purpose | Created/used by |
|---|---|---|
| `course_prerequisites` | Explicit course→prerequisite graph (didn't exist before in queryable form) — powers prerequisite checks in eligibility and study-plan generation | `analysis_tool.py`, `bonus_tools.py` (study plan, recommendations) |
| `enrollment_requests` | Audit trail of every enrollment attempt: `student_id, course_code, semester_name, status (PENDING_CONFIRMATION/EXECUTED/REJECTED/CANCELLED), eligibility_json, created_at, decided_at` | `action_tool.py` — written on both the "stage" and "confirm" calls |
| `agent_logs` | Full observability log: `session_id, user_role, user_name, intent, workflow_state, tool_name, tool_input, tool_result, validation_failure, fallback, error, timestamp` | `app/logging_system/logger.py` — written by every workflow node |
| `user_preferences` | Long-term memory: `(user_name, preference_key) → preference_value (JSON)`, unique constraint for UPSERT | `app/memory/long_term.py` |

### How to show this live
```
sqlite3 app/db/university.db ".tables"
sqlite3 app/db/university.db "SELECT * FROM enrollment_requests;"
sqlite3 app/db/university.db "SELECT * FROM agent_logs ORDER BY log_id DESC LIMIT 5;"
```
Point out that `enrollment_requests` and `agent_logs` will have **new rows
after every demo run** — that's the live proof the agent is actually writing
to the database, not just chatting.

---

# Section G — Docker Explanation (How the System Starts)

**Files**: `Dockerfile`, `docker-compose.yml`, `.env` (copy from
`.env.example`).

### Build (`Dockerfile`)
1. `FROM python:3.11-slim` — small base image.
2. Sets `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, and
   `STREAMLIT_SERVER_*` env vars (headless mode, correct port/address).
3. `WORKDIR /app`; `pip install -r requirements.txt`.
4. Copies `app/` and `streamlit_app.py` into the image.
5. **`RUN python -m app.db.init_db --force`** — the SQLite database is built
   **into the image at build time** from `schema.sql` + `seed_data.sql` +
   `policies.json`, so the container starts with a ready, consistent demo
   database.
6. Creates a non-root user `agent` (uid 1000), `mkdir -p /app/data`, `chown`s
   it — the running container does **not** run as root (a security best
   practice worth mentioning).
7. `EXPOSE 8501`.
8. `HEALTHCHECK` — a small Python script that hits
   `http://localhost:8501/_stcore/health` and exits 0/1 based on the HTTP
   status; Docker uses this to mark the container healthy/unhealthy.
9. `CMD ["streamlit", "run", "streamlit_app.py"]`.

### Run (`docker-compose.yml`)
- **Three services**: `ollama` (local LLM server — the PRIMARY/REQUIRED LLM
  backend, no API key), `ollama-pull` (one-shot job that pulls `llama3.1`
  into `ollama` on first run, then exits), and `agent` (built from the local
  `Dockerfile`).
- `agent` maps port `8501:8501`; `ollama` maps `11434:11434`.
- `env_file: .env` on `agent` — configuration (LLM provider/model,
  thresholds, log level) comes from `.env` if present, but **`.env` is
  optional**: defaults (`LLM_PROVIDER=ollama`, no API key) work with no file
  at all. `OLLAMA_BASE_URL` is hardcoded to `http://ollama:11434` in the
  `agent` service so it always reaches the bundled Ollama container.
- Sets `DATABASE_PATH=/app/data/university.db` and mounts a **named volume**
  `agent_data:/app/data` — this means enrollment actions, logs, and
  preferences **persist across container restarts** (the image-baked DB at
  `/app/...` build path is the seed; the volume holds the live, mutable copy).
  A second named volume `ollama_data:/root/.ollama` persists pulled models so
  subsequent runs are fully offline.
- `agent`'s `healthcheck` mirrors the Dockerfile's, with `start_period: 30s`
  to allow Streamlit to boot. `ollama`'s healthcheck runs `ollama list`.
- `agent` and `ollama` use `restart: unless-stopped`; `ollama-pull` is a
  one-shot job (`restart: "no"`).

### Startup, step by step
1. `docker compose up --build` — **no `.env` file or API key needed**. This
   starts `ollama`, runs `ollama-pull` to fetch `llama3.1` (first run only),
   then starts `agent` once the model is ready.
2. Open **http://localhost:8501**.
3. To reset to a clean demo database (keeping the downloaded model):
   `docker compose down` then `docker compose up --build` again (the
   `agent_data` volume persists; `ollama_data` is untouched).
4. Full reset including re-downloading the model: `docker compose down -v`
   then `docker compose up --build`.

To use OpenAI/Anthropic instead (optional fallback only): `cp .env.example
.env`, set `LLM_PROVIDER=openai` (or `anthropic`) and the matching
`*_API_KEY`, then `docker compose up --build` again.

### Local (non-Docker) alternative
```
pip install -r requirements.txt
python -m app.db.init_db --force
streamlit run streamlit_app.py
```
Useful as a fallback if Docker isn't available during the defense (see Section
K — Risk Checklist).

---

# Section H — Testing Guide (Run Before Submission)

Run these in order. Each uses real seeded data so the expected results below
are exact. If anything diverges, re-run `python -m app.db.init_db --force`
first (you may have left-over data from a previous demo run that changed
balances/enrollments).

### H.0 — Environment sanity check
1. No `.env` file is required for the default setup (`LLM_PROVIDER=ollama`,
   no API key). Make sure Ollama is running with `llama3.1` pulled
   (`ollama serve` + `ollama pull llama3.1`, or `docker compose up ollama
   ollama-pull`). Only create `.env` (from `.env.example`) if you want to
   switch to the optional OpenAI/Anthropic fallback.
2. `python -m app.db.init_db --force` — should complete with no errors and
   create/refresh `app/db/university.db`.
3. `streamlit run streamlit_app.py` (or `docker compose up --build`) — confirm
   the sidebar shows `db_ready` with no error, and the LLM config block shows
   your provider/model.

### H.1 — Information queries (no LLM tool call needed beyond classification)
| # | Message | Expected |
|---|---|---|
| 1 | "What is CE205?" | `get_university_information(course, CE205)` → "CE205 - Programming Fundamentals (3 credits) / Department: Computer Engineering / Course fee: 1200.00 / Prerequisites: none / ..." |
| 2 | "What is the enrollment policy?" | Returns the 5 rules from `enrollment_policy` verbatim |
| 3 | "Tell me about Dr. Hassan Nasser" | Instructor detail incl. department (Electrical Engineering) and sections taught |
| 4 | "What courses are offered in the Computer Engineering department?" | Lists CE205, CE301, CE410 |
| 5 | "Is CE205 offered in Spring 2026?" | Section detail: instructor Dr. Hassan Nasser, capacity 30, enrolled 0, seats available 30 |

### H.2 — Eligibility checks (covering every failure reason)
| # | Message | Expected eligibility | Reason(s) |
|---|---|---|---|
| 1 | "Is Yousef Khalil eligible to enroll in CE205 for Spring 2026?" | **Eligible** | none — verified live: `eligible=true`, balance 5000 ≥ 1200, no prereqs, seats available |
| 2 | "Is Maryline Karam eligible to enroll in CE301 for Spring 2026?" | **Not eligible** | section full (capacity 1, Nour already enrolled) — note: prereq CE205 *is* satisfied, balance 2000 *is* sufficient, so this isolates the capacity check |
| 3 | "Is Yousef Khalil eligible to enroll in CE301 for Spring 2026?" | **Not eligible** | missing prerequisite CE205 |
| 4 | "Is Maryam Daaibes eligible to enroll in CE410 for Spring 2026?" | **Not eligible** | **two** reasons: missing prerequisite CE301, AND insufficient balance (500 < 1800) — good for showing `reasons` is a list, not just the first failure |
| 5 | "Is Nour Hamad eligible to enroll in CE410 for Spring 2026?" | **Not eligible** | already enrolled (duplicate) |

### H.3 — Enrollment request (confirmation flow) — **the centerpiece demo**
1. "Enroll Yousef Khalil in CE205 for Spring 2026" → agent responds eligible,
   asks to confirm (`pending_confirmation` set, `request_id` created with
   `PENDING_CONFIRMATION`).
2. Reply "yes" → agent confirms execution: *"Yousef Khalil has been enrolled
   in CE205 (Spring 2026). Fee of 1200.00 deducted; new balance is 3800.00."*
   Verify: `enrollments` has a new `ENROLLED` row, `student_accounts.balance`
   for Yousef is now 3800.00, `enrollment_requests` has an `EXECUTED` row.
3. **Cancellation variant** (run in a *fresh* conversation, or after resetting
   the DB, to avoid double-enrolling Yousef): repeat step 1 with a different
   student/course (e.g. Karim Saleh / CV220 — check seed data first for an
   open, eligible combination), then reply "no" → agent responds: *"Okay, the
   enrollment request has been cancelled. No changes were made."* Verify no
   new `enrollments` row and no balance change.
4. **Race-condition variant (optional, advanced)**: stage a request
   (`confirm=False`) for the last open seat in a small section, then (in a
   second session) have *another* student take that seat, then confirm the
   first request — it should come back `status="rejected"` because
   eligibility is re-checked at confirm time.

### H.4 — Student reports
| # | Message | Expected |
|---|---|---|
| 1 | "Give Yousef Khalil's transcript summary" | "No completed courses on record." (verified live) |
| 2 | "What is Aseel Menhem's GPA?" | GPA 3.5 (CE205=A, CE301=B → (4×3+3×3)/6 = 3.5), standing "Dean's List" |
| 3 | "What is Maryam Daaibes's academic standing?" | GPA 2.5 (CE205=B, EE320=C → (3×3+2×3)/6=2.5), standing "Good Standing", policy rules quoted |
| 4 | "What courses would you recommend for Karim Saleh?" | Courses whose prereqs Karim has passed and hasn't taken — e.g. CE410 (prereq CE301 ✓) |

### H.5 — Bonus tools
| # | Message | Expected |
|---|---|---|
| 1 | "If Aseel Menhem gets an A in CE410, what would the new GPA be?" | `predict_future_gpa` — current GPA 3.5 → predicted (37/10 = 3.7) |
| 2 | "Generate a study plan for Yousef Khalil" | Multi-semester plan starting with courses with no missing prereqs (CE205, CV220, EE320), then CE301, then CE410 |
| 3 | "Generate a payroll report for Hassan Nasser" | **Verified live**: 23.00 approved hrs × 50.00 = 1150.00; CE205: 10.00 hrs, EE320: 13.00 hrs |
| 4 | "What's the section utilization for Spring 2026?" | CE301 section → Full (1/1); others → Optimal/Underutilized depending on enrollment |
| 5 | "Give me a payroll summary for the whole institution" | **Verified live**: Hassan Nasser 23.00/1150.00, Maya Saad 19.00/1045.00, Rami Fakhoury 18.00/1080.00, grand total **3275.00** |
| 6 | "Give me a tuition summary" | Lists all 6 students' balances, flags any < 1000.00 (Maryam 500, and Karim 1000 is *not* `<` so not flagged — check `<` strictly) |

### H.6 — Multi-turn memory (MULTI-01)
1. "Is Aseel Menhem eligible to enroll in CE410 for Spring 2026?" →
   eligible (CE301 passed, balance 3000 ≥ 1800, seats available in section
   6).
2. "What about CE301 instead?" → agent reuses `student_identifier: "Aseel
   Menhem"` from `collected_information` without re-asking; answers about
   CE301 (likely **not eligible** — section 5 capacity 1 is already full).

### H.7 — Role-based defaults (ROLE-01/02)
1. In the sidebar, set Name = "Yousef Khalil", Role = "Student". Ask "Am I
   eligible to enroll in CE205 for Spring 2026?" → agent uses "Yousef Khalil"
   as `student_identifier` automatically.
2. Set Name = "Dr. Hassan Nasser", Role = "Instructor". Ask "What's my payroll
   report?" → agent uses "Dr. Hassan Nasser" as `instructor_identifier`.

### H.8 — Fallback / unsupported (UNSUP-01)
"Can you book me a flight to Paris?" → agent responds with the fixed message:
*"I cannot perform that action because it is outside my supported university
operations domain."* — confirm **no tool was called** (empty tool-activity
panel) and `agent_logs` has a row with `fallback=1`.

### H.9 — Low-confidence / ambiguous (LOWCONF-01)
A vague message (e.g. "do the thing") should either trigger a clarifying
question or the fallback message — confirm it does **not** crash and does
**not** call a tool with guessed parameters.

### H.10 — Automated evaluation suite
```
python -m tests.eval.run_eval
```
Reviews all 31 cases in `tests/eval/test_cases.json` and reports the 4
metrics: task completion rate, tool-selection accuracy, fallback accuracy,
unsafe-action count (should be **0**).

### H.11 — Docker smoke test
```
docker compose up --build
```
Wait for the healthcheck to pass (`docker compose ps` shows `healthy`), open
http://localhost:8501, run H.1 #1 and H.3 once to confirm the containerized
app behaves identically to local.

### H.12 — Final reset before submission/demo
Decide deliberately: either (a) leave the DB with demo data created during
testing (shows a "lived-in" system with `agent_logs`/`enrollment_requests`
history — good for the F section demo), or (b) run
`python -m app.db.init_db --force` (or `docker compose down -v`) for a clean
slate. **Pick one and tell the team** so nobody is surprised by Yousef's
balance being 3800 instead of 5000 during the live defense.

---

# Section I — Presentation Script (5-Minute Version)

Timings are approximate; practice once with a stopwatch.

**[0:00–0:30] — Framing**
> "We built a University Operations AI Agent — an Educational Support Agent
> that lets students, instructors, and staff ask natural-language questions
> about courses, eligibility, grades, and payroll, and even request
> enrollment, all grounded in a real database. Every fact it states comes
> from the database or our policy file — it never makes things up — and any
> action that changes data requires the user's explicit confirmation."

**[0:30–1:00] — Architecture (show Section A diagram)**
> "The system has 6 layers: a Streamlit chat UI, a LangGraph state-machine
> orchestrator with 9 explicit nodes, a configurable LLM client with a local
> Ollama model as the default/required backend (OpenAI or Anthropic
> available as an optional fallback), 9 tools — 4 required plus 5
> bonus — that are the only code touching the database, a 3-tier memory
> system, and a SQLite database extending the university's schema with 3 new
> tables for enrollment requests, audit logs, and preferences."

**[1:00–3:00] — Live demo: the confirmation-gated enrollment flow**
> "Let's enroll a student." Type: *"Enroll Yousef Khalil in CE205 for Spring
> 2026."*
> — While it processes: "Behind the scenes, the agent classified this as an
> `enrollment_request`, ran our eligibility tool — checking prerequisites,
> capacity, duplicate enrollment, and balance — and because Yousef is
> eligible, it's now staging the request and asking for confirmation, *not*
> executing it yet."
> — Show the response and the sidebar's `pending_confirmation` and
> `state_history`.
> Type: *"yes"*
> — "Notice this was instant — no AI call was needed. The agent recognized
> 'yes' as a confirmation for the pending request and went straight to
> execution." Show the new balance in the response and (optionally) the new
> row in `enrollment_requests`/`enrollments` via sqlite3.

**[3:00–3:45] — Multi-turn memory + role awareness**
> Ask: *"Is Aseel Menhem eligible to enroll in CE410 for Spring 2026?"* (show
> result), then: *"What about CE301 instead?"* — "Notice I never repeated
> Aseel's name — that's our working memory carrying `collected_information`
> across turns."
> Optionally: switch the sidebar role to "Instructor" / "Dr. Hassan Nasser"
> and ask *"What's my payroll report?"* to show role-based defaults.

**[3:45–4:30] — Bonus tools + safety**
> Ask: *"Give me a payroll summary for the whole institution"* — "This
> demonstrates tool composition — our institution report calls our payroll
> tool once per instructor and totals it." Then ask something out of scope,
> e.g. *"Book me a flight to Paris"* — "And here's our safety boundary: the
> agent declines with a fixed policy message and never calls a tool."

**[4:30–5:00] — Wrap-up**
> "Everything you saw — intent classification, tool calls, validation,
> confirmations, and fallbacks — is logged to an `agent_logs` audit table and
> visible live in the sidebar. The whole system starts with one command,
> `docker compose up --build`, and the LLM provider can be swapped via a
> single environment variable. That's our project."

---

# Section J — Defense Preparation (20 Likely Questions & Model Answers)

**1. Why did you use LangGraph instead of a single LLM prompt with function
calling?**
> "We needed an *explicit*, auditable state machine matching the required
> workflow (START → INTENT_CLASSIFICATION → ... → END), with hard safety
> guarantees like confirmation-gating and iteration limits. A single
> prompt-driven loop can't structurally *prevent* the LLM from calling the
> enrollment tool without confirmation — our graph can, because
> `action_execution` is only reachable via a specific routing condition."

**2. Why SQLite instead of a vector database / RAG?**
> "The project scope is structured operational data — students, courses,
> balances, policies — which is a perfect fit for relational queries with
> exact answers. RAG/embeddings are for *unstructured* document retrieval
> where approximate semantic match is acceptable; here we need exact,
> auditable numbers (a GPA, a balance), so SQL is strictly better and the
> project explicitly scoped out vector DBs."

**3. How do you prevent the LLM from hallucinating data?**
> "Two mechanisms. First, the LLM is only called once per turn, for intent
> classification — it never generates the factual content of a response.
> Second, `_phrase_from_result` builds the final response from the tool's
> `formatted_text`/`message` fields, which are built in Python directly from
> SQL query results. The LLM's only creative output is deciding *what the
> user wants* and extracting entity values like a course code."

**4. What happens if the LLM returns malformed JSON during intent
classification?**
> "`_extract_json` first strips markdown code fences, then tries
> `json.loads`, and falls back to a regex extraction of `\{.*\}`. If all of
> that fails, or the returned `intent` isn't in our `INTENTS` list, we default
> to `"unsupported"` with confidence 0, which routes straight to the fallback
> node — never to a tool with garbage arguments."

**5. Walk me through what happens if a student asks to enroll, says yes, but
in between something changes (e.g., the seat fills up).**
> "`create_enrollment_request` re-runs `evaluate_eligibility` on *both*
> calls — the staging call (`confirm=False`) and the execution call
> (`confirm=True`). If eligibility flips to false between the two, the second
> call returns `status="rejected"` with the specific reason, inserts a
> `REJECTED` row into `enrollment_requests`, and **does not** touch
> `enrollments` or the balance."

**6. Why is `create_enrollment_request` the only confirmation-gated tool?**
> "It's the only tool that writes to the database — `INSERT INTO enrollments`
> and `UPDATE student_accounts.balance`. All 8 other tools are read-only
> (information, analysis, reports, predictions). `CONFIRMATION_REQUIRED_TOOLS`
> in `app/config.py` is a set specifically so this list could grow if we added
> more write tools later — but currently it has exactly one entry."

**7. How does the agent know who "I" / "my" refers to?**
> "The Streamlit sidebar collects a `user_name` and `user_role` for the
> session, stored in `AgentState`. In `node_information_gathering`, if the
> intent is student-facing (`_STUDENT_INTENTS`) and no `student_identifier`
> was extracted, we default it to `state['user_name']`. Similarly for
> instructors and `payroll_report`."

**8. What's the difference between `intent_confidence` and
`INTENT_CONFIDENCE_THRESHOLD`?**
> "`intent_confidence` is a 0–1 value the LLM returns alongside its
> classification — its own estimate of how sure it is. We clamp it to [0,1]
> defensively. `INTENT_CONFIDENCE_THRESHOLD` (default 0.4, configurable via
> env var) is *our* policy cutoff — below it, regardless of which intent was
> guessed, we treat the request as too uncertain to act on and fall back."

**9. Why a maximum of 6 iterations? What happens at iteration 7?**
> "`MAX_ITERATIONS=6` caps how many times `intent_classification` can run for
> one logical task (counted via `iteration_count`, incremented each time that
> node runs and reset by `start_turn`... actually carried in
> `collected_information`/state across the multi-turn flow). If exceeded,
> `route_after_intent` sends us to `fallback` with reason
> `max_iterations_exceeded`, and the user gets: 'I've reached the maximum
> number of steps I can take for this request. Could you rephrase or simplify
> it?' This bounds worst-case latency/cost for one user request."

**10. How is "yes"/"no" handled — does it always go through the LLM?**
> "No — and that's deliberate. `classify_intent` first checks: is there a
> `pending_confirmation`, and does the latest message match `_YES_RE` or
> `_NO_RE` (simple regexes covering 'yes', 'yeah', 'ok', 'confirm', 'no',
> 'cancel', 'nevermind', etc.)? If so, we short-circuit to `confirm_yes`/
> `confirm_no` with confidence 1.0 — zero LLM calls. This is both faster and
> removes any chance of the LLM misreading a clear yes/no."

**11. What's stored in `agent_logs` and why does logging never crash the
app?**
> "Every intent classification, tool call (with input and result), validation
> failure, and fallback gets a row — `session_id, user_role, user_name,
> intent, workflow_state, tool_name, tool_input, tool_result,
> validation_failure, fallback, error, timestamp`. `AgentLogger._write` wraps
> the INSERT in try/except and logs to Python's logger on failure instead of
> raising — because an observability problem should never become a
> user-facing outage."

**12. How would I switch this from Ollama to OpenAI (or Anthropic)?**
> "Ollama (`llama3.1`, local/offline, no API key) is the default and
> required backend — that's what runs out of the box and in the eval suite.
> To use the optional OpenAI fallback instead: create `.env` from
> `.env.example`, set `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` (or
> whichever model), `OPENAI_API_KEY=...`, and restart. `get_chat_model()` in
> `app/llm/client.py` branches on `LLM_PROVIDER` and returns the matching
> LangChain chat model — no other code changes. There's no silent fallback
> between providers; exactly one is active per run."

**13. What's the prerequisite chain in your data, and how does it affect
eligibility?**
> "CE301 (Data Structures) requires CE205 (Programming Fundamentals); CE410
> (Operating Systems) requires CE301. `course_prerequisites` encodes this as
> `(course_id, prerequisite_course_id)` pairs. `analyze_enrollment_eligibility`
> fetches the prereqs for the target course, checks which ones the student has
> *completed with a passing grade* (A/B/C/D, not F), and lists any missing
> ones in `reasons`. The same prereq map drives `generate_study_plan`'s
> semester ordering and `recommendations`."

**14. How do `generate_payroll_report` and `generate_institution_report`
relate?**
> "`generate_institution_report(report_type='payroll_summary')` calls
> `generate_payroll_report.invoke(...)` once per instructor and sums the
> results — it's tool composition, not duplicated logic. Same pattern for
> `enrollment_overview`, which calls `analyze_section_utilization`."

**15. What's the difference between `formatted_text`, `data`, and
`message` in a tool's output, and why have all three?**
> "`data`/`details` is the structured payload for programmatic use (and for
> the Streamlit JSON viewers). `message` is a short human-readable summary
> (often used for short, special-case sentences, e.g. action results).
> `formatted_text` is a fuller, multi-line rendering for longer outputs
> (course details, reports). `_phrase_from_result` checks `formatted_text` →
> `data.formatted_text` → `message` → a generic not-found phrase, in that
> order — so whichever the tool provides, the response is grounded."

**16. How is academic standing computed, and where do the thresholds come
from?**
> "`db_helpers.academic_standing(gpa)`: GPA ≥ 3.5 → 'Dean's List'; 2.0 ≤ GPA <
> 3.5 → 'Good Standing'; GPA < 2.0 → 'Academic Probation'; no completed
> courses → 'No academic standing yet'. These exact thresholds are also
> documented in `policies.json`'s `academic_standing_policy`, and
> `generate_student_report(report_type='academic_standing')` quotes those
> policy rules verbatim alongside the computed standing — so the number and
> the policy text can never disagree."

**17. What would happen if two students try to take the last seat at the
same time?**
> "Both could pass the `confirm=False` staging call (both see 1 seat
> available), but at `confirm=True` time, `evaluate_eligibility` recomputes
> `section_enrolled_count` fresh from the database. Whichever confirms
> *second* will see the seat already taken and get `status='rejected'`. This
> isn't full transactional locking (SQLite + this app's simplicity), but the
> re-check at execution time avoids the most obvious stale-data bug."

**18. Why does the project explicitly avoid embeddings/RAG — isn't that less
'AI'?**
> "The brief scoped this application area to *operational* questions with
> exact, database-backed answers — eligibility, balances, GPAs, payroll.
> Embeddings/RAG add value for *unstructured* text search (e.g., 'find the
> paragraph in the handbook about X'), which isn't this project's need. Using
> RAG here would add complexity and a *new* hallucination surface (retrieval
> can return the wrong chunk) without solving a real problem we have — our
> policies fit in one small JSON file we can query exactly by key."

**19. How do you know your tool-selection logic is correct — did you test
it?**
> "Yes — `tests/eval/test_cases.json` has 31 scripted conversations across 30
> categories (information queries, eligibility checks of every failure type,
> enrollment confirm/cancel flows, reports, GPA prediction, study plans,
> payroll, utilization, institution reports, unsupported requests,
> multi-turn memory, and role defaults). `run_eval.py` replays them and
> computes task completion rate, tool-selection accuracy, fallback accuracy,
> and an unsafe-action count, which should be zero."

**20. If the instructor asks you to add a new tool, e.g. 'add a course
withdrawal tool' — what would you change?**
> "Five things: (1) write `withdraw_from_course` in a new/existing tools file
> following the existing pattern (Pydantic input, dict output, via
> `db_helpers`); (2) register it in `app/tools/__init__.py`'s registries;
> (3) since it writes data, add it to `CONFIRMATION_REQUIRED_TOOLS` in
> `app/config.py`; (4) add `"course_withdrawal"` to `INTENTS` and
> `INTENT_REQUIRED_FIELDS` in `state.py`, and a dispatch branch in
> `node_report_generation` / a new confirmation node if needed; (5) add eval
> cases. The layered design means each change is localized and the safety
> gating pattern is reusable."

---

# Section K — Risk Checklist (What Might Fail During the Demo, and Recovery)

| Risk | Likely cause | Recovery |
|---|---|---|
| **Ollama not reachable** → LLM call fails on intent classification, every message gets the fixed refusal | Ollama server not running / model not pulled (default provider, no `.env` needed) | Run `ollama serve` + `ollama pull llama3.1` locally, or `docker compose up ollama ollama-pull`. `classify_intent` catches the error and falls back to `intent="unsupported"` (no crash). Pre-pull the model *before* the defense so this never happens live. |
| **Optional fallback misconfigured** (only if you switched `LLM_PROVIDER` to `openai`/`anthropic`) | `*_API_KEY` invalid/missing, network blocked, provider down | `LLMConfigurationError` is caught gracefully (friendly banner, no crash). Switch `.env` back to `LLM_PROVIDER=ollama` (the default, no API key) and restart. Pre-test this switch *before* the defense. |
| **Demo data drifted** — Yousef's balance is 3800 not 5000, seats already taken from earlier testing | Previous test runs wrote to the same `university.db` | Run `python -m app.db.init_db --force` (or `docker compose down -v && docker compose up --build`) the night before, then **don't run H.3 more than once** before the actual defense, or pick a fresh student/course pair each time. |
| **Docker build is slow/fails on demo machine** | Cold image cache, no internet for `pip install` | Have the **local (non-Docker) path** (Section G) tested and ready as a fallback — same `.env`, just `streamlit run streamlit_app.py` after `pip install -r requirements.txt`. |
| **LLM misclassifies intent** (e.g., calls `information_query` instead of `eligibility_check`) | Ambiguous phrasing, low-temperature but not zero | Use the **exact phrasings from Section H** during the live demo — they were chosen because they classify reliably. If it still misclassifies live, treat it as a teaching moment: show the sidebar's `current_intent`/`confidence` and explain `INTENT_CONFIDENCE_THRESHOLD`'s role, then rephrase. |
| **Agent says "yes" was a `confirm_yes` but there's no `pending_confirmation`** (e.g., user said "yes" out of context) | User typed "yes" in a fresh conversation or after the confirmation already resolved | This is actually **correct behavior** — `route_after_intent` sends it to `fallback` with reason `no_pending_confirmation` and the message "There's nothing pending that needs confirmation right now." Frame it as a safety feature, not a bug, if it happens live. |
| **Iteration limit hit during a long demo Q&A chain** | Too many back-and-forth clarifications in one session | Click "New conversation" in the sidebar to reset `iteration_count` and `state_history` for a clean slate. |
| **`formatted_text` missing / KeyError on an edge case input** | An identifier that doesn't exist, or a course code typo | All tools return `found: False` with a `message` for unknown identifiers — if something instead throws, `_invoke_tool`'s try/except logs it and routes to a safe fallback message, so the conversation won't crash; just note the discrepancy for follow-up. |
| **Instructor asks to see the database live and `sqlite3` CLI isn't installed** | Demo machine lacks the `sqlite3` binary | Use Python instead: `python -c "import sqlite3; c=sqlite3.connect('app/db/university.db'); print(c.execute('SELECT * FROM agent_logs ORDER BY log_id DESC LIMIT 5').fetchall())"`, or show the Streamlit sidebar JSON panels, which display the same underlying state without a DB client. |
| **Port 8501 already in use** | Another Streamlit instance running | `streamlit run streamlit_app.py --server.port 8502` (or stop the other process / `docker compose down` first). |
| **Healthcheck shows "unhealthy" right after `docker compose up`** | Streamlit hasn't finished starting yet (cold start) | `start_period: 30s` accounts for this — wait ~30–45s and re-check `docker compose ps`. Don't panic-restart. |
| **Team member presenting wasn't the one who wrote a given component** | Division of labor across 12 implementation tasks | This guide's Part 1 + Sections A–G are written so any member can present any component — review the "Demo" bullet for your assigned section beforehand, and rehearse the Section I script as a group once. |

---

*End of guide. Good luck — remember the one-sentence pitch: the agent never
makes anything up, and never changes data without asking first.*
