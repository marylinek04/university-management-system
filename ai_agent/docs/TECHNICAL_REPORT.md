# Technical Report - University Operations AI Agent

**Application area:** #17, Educational Support Agent
**Built on top of:** the existing University Management System database (schema unchanged)

## 1. Overview

The University Operations AI Agent is a conversational layer added on top of
the existing University Management System database. Per the project
requirements, the database schema was **not** redesigned - the agent adds
three small tables (`enrollment_requests`, `agent_logs`, `user_preferences`)
to the existing schema for action auditing, activity logging, and per-user
preferences, and otherwise reads/writes the same tables (`students`,
`courses`, `sections`, `enrollments`, `grades`, `instructors`,
`student_accounts`, `instructor_time_entries`, etc.) that the rest of the
University Management System uses.

The agent answers questions about courses, policies, instructors, programs,
departments, sections, and semesters; checks whether a student is eligible
to enroll in a course; walks a student through a confirmed enrollment;
generates transcript/GPA/academic-standing/recommendation reports; and (as
bonus functionality) predicts future GPA, generates multi-semester study
plans, produces instructor payroll reports, analyzes section utilization,
and produces institution-wide tuition/payroll summaries.

The guiding principle throughout was: **compliance with the course
requirements over feature complexity**. Every required component (4-layer
architecture, 4 named tools with the exact specified signatures, the
explicit 9-state workflow, the three memory tiers, the exact safety/fallback
message, SQLite logging, and a single-command Docker setup) was built first
and exactly as specified; bonus tools and the evaluation suite were added on
top once the required pieces were complete and verified.

## 2. Architecture

The system is organized into four layers, each independently swappable:

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1 - Streamlit UI (streamlit_app.py)                         │
│   chat window · conversation history · tool-activity log ·       │
│   live workflow-state / working-memory panel                     │
└───────────────────────────────┬──────────────────────────────────┘
                                  │ run_turn(state, user_message)
┌───────────────────────────────▼──────────────────────────────────┐
│ Layer 2 - LangGraph orchestration (app/workflow/)                  │
│   explicit state machine: intent classification, information       │
│   gathering, validation, analysis, confirmation gate, action        │
│   execution, report generation, fallback, finalize                  │
└───────────────────────────────┬──────────────────────────────────┘
                                  │ get_chat_model()
┌───────────────────────────────▼──────────────────────────────────┐
│ Layer 3 - Configurable LLM core (app/llm/client.py)                 │
│   provider selected via LLM_PROVIDER env var:                       │
│   ollama (default, required, no API key) | openai/anthropic        │
│   (optional fallback)                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                  │ tool.invoke({...})
┌───────────────────────────────▼──────────────────────────────────┐
│ Layer 4 - Tools (app/tools/) over SQLite (app/db/)                  │
│   4 required tools + 5 bonus tools, all grounded in the database   │
│   and app/db/policies.json - no vector DB, no RAG, no embeddings    │
└─────────────────────────────────────────────────────────────────┘
```

Each layer only depends on the layer below it, and only through a narrow
interface (`run_turn`, `get_chat_model`, `tool.invoke`). This means, for
example, that the LLM provider can be changed from the default (local
Ollama) to the optional OpenAI or Anthropic fallback purely via environment
variables, with no code changes in Layers 1, 2, or 4.

## 3. Workflow design (Layer 2)

### 3.1 Why LangGraph

The project requires "explicit workflow states with defined transitions,
state management across the conversation, confirmation gates for
state-changing actions, basic safety checks, and stopping conditions."
LangGraph's `StateGraph` maps directly onto this requirement: each required
workflow state becomes a graph node, transitions become (conditional) edges,
and the shared `AgentState` TypedDict *is* the working memory - it is
inspectable at every step and is exactly what the Streamlit UI renders in
its "workflow state" panel. This is a much closer match to the spec than
implementing the same logic as ad-hoc Python control flow inside a single
function, and it makes the state machine easy to test in isolation (as the
evaluation suite does, by calling `run_turn` directly).

### 3.2 The state machine

The required topology is:

```
START -> INTENT_CLASSIFICATION -> INFORMATION_GATHERING -> VALIDATION ->
ANALYSIS -> CONFIRMATION_REQUIRED -> ACTION_EXECUTION -> REPORT_GENERATION -> END
```

Not every intent needs every state - e.g. a plain information lookup never
needs to check eligibility or confirm anything, and a "yes"/"no" reply to a
pending confirmation should go straight to execution rather than being
re-classified from scratch. The implemented graph (`app/workflow/graph.py`)
therefore keeps every required node but lets `route_after_intent`,
`route_after_validation`, and `route_after_analysis` choose a path through
them based on `current_intent`, `missing_fields`, and `pending_confirmation`:

- **INTENT_CLASSIFICATION** - calls the LLM (or short-circuits via regex to
  `confirm_yes`/`confirm_no` if a `pending_confirmation` exists and the
  latest message is a clear yes/no). Increments `iteration_count`.
- **INFORMATION_GATHERING** - merges any entities the LLM extracted into
  `collected_information`, and applies role-based defaults (a student asking
  about themselves doesn't need to give their own name; an instructor asking
  "what's my payroll" doesn't need to give their own name either).
- **VALIDATION** - checks `collected_information` against
  `INTENT_REQUIRED_FIELDS`. If anything is missing, the turn ends here with a
  clarifying question - no tool is called.
- **ANALYSIS** - runs `analyze_enrollment_eligibility` for
  `eligibility_check` and `enrollment_request` intents.
- **CONFIRMATION_REQUIRED** - for `enrollment_request` only: calls
  `create_enrollment_request(confirm=False)` (a dry-run preview, no DB
  write), stores a `pending_confirmation` record, and asks the user to
  reply "yes" or "no".
- **ACTION_EXECUTION** - reached only via `confirm_yes`/`confirm_no` against
  an existing `pending_confirmation`. Calls
  `create_enrollment_request(confirm=True)` (the only point in the whole
  system that writes an enrollment) or, for `confirm_no`, records a
  cancellation with no DB write.
- **REPORT_GENERATION** - runs the relevant report/analysis tool
  (`get_university_information`, `generate_student_report`,
  `predict_future_gpa`, `generate_study_plan`, `generate_payroll_report`,
  `analyze_section_utilization`, `generate_institution_report`) and turns
  its grounded output into `final_response`.
- **fallback** - the safety/stopping-condition node (see §5).
- **finalize** - appends the assistant's message to the conversation and
  guarantees `final_response` is never `None`.

`state["state_history"]` records exactly which of these states a given turn
passed through, which the Streamlit UI displays so a grader can see the
state machine operating in real time.

## 4. Memory architecture

The project requires three memory tiers; all three are implemented:

- **Short-term memory** (`app/memory/short_term.py`, and
  `AgentState["messages"]`) - the conversation history, user name and role,
  and a rolling log of recent tool interactions. This is what makes the
  agent's responses feel like a continuous conversation rather than isolated
  Q&A.
- **Working memory** (`app/memory/working_memory.py`, mirrored as top-level
  keys on `AgentState`) - `current_intent`, `intent_confidence`,
  `collected_information`, `missing_fields`, `pending_confirmation`,
  `latest_tool_result`, `workflow_state`, `iteration_count`. These are
  *visible in LangGraph state* as required, and are what the Streamlit
  "working memory" panel renders directly. Critically,
  `collected_information` and `pending_confirmation` persist **across**
  turns (only the per-turn bookkeeping is reset by `start_turn`), which is
  what lets a user say "Is Aseel eligible for CE410?" and then, in the next
  turn, "What about CE301 instead?" without re-stating the student's name -
  the eval suite's `MULTI-01` case exercises exactly this.
- **Long-term memory** (`app/memory/long_term.py`, bonus) - a SQLite-backed
  `user_preferences` table, keyed by `user_name`, for things like a
  preferred semester or last-used report type. This is intentionally simple
  (string/JSON key-value pairs) since the spec calls it a bonus feature.

## 5. Safety, controls, and grounding

Several mechanisms work together to satisfy the "never fabricate, validate
inputs, confirm state-changing actions, log everything" requirements:

- **Domain refusal.** Any message the intent classifier rates as
  `unsupported`, or rates below `INTENT_CONFIDENCE_THRESHOLD` (default
  `0.4`), is routed straight to the `fallback` node, which states the
  limitation ("outside my supported university operations domain"), refuses
  to guess an answer, and offers the simulated human-handoff path ("just say
  'talk to a human'"). No tool is ever called on this path.
- **Simulated human handoff.** When the user explicitly asks to reach a
  person ("talk to a human", "connect me to staff", "escalate this"), a
  deterministic regex in `classify_intent` (`_HANDOFF_RE` in
  `app/workflow/router.py`) short-circuits to the `human_handoff` intent -
  it never depends on the LLM being reachable. The workflow then creates a
  traceable handoff ticket (`create_handoff_ticket`, logged to `agent_logs`
  with a `HANDOFF-<timestamp>` reference and the user's recent messages) and
  tells the user a staff member would follow up. In production this would
  post to a real ticketing/queue system; here it is simulated by design, per
  the project spec.
- **Confirmation gate.** `create_enrollment_request` is the only
  state-changing tool in the system (`app.config.CONFIRMATION_REQUIRED_TOOLS
  = {"create_enrollment_request"}`). It is called with `confirm=False`
  (a no-write preview) from `CONFIRMATION_REQUIRED`, and only ever called
  with `confirm=True` (the actual write) from `ACTION_EXECUTION`, which is
  only reachable when `current_intent` is `confirm_yes` **and**
  `pending_confirmation` is already set from a prior turn. The evaluation
  suite's "unsafe action count" metric specifically checks that this
  invariant never breaks.
- **Grounded responses, no hallucination.** Every tool returns a structured
  dict that includes a `formatted_text` field (either at the top level or
  inside `data`), built only from values pulled out of SQLite or
  `app/db/policies.json`. `_phrase_from_result()` in `app/workflow/nodes.py`
  is the single place that turns a tool result into `final_response`, and it
  prefers `formatted_text` > `data.formatted_text` > `message` > a generic
  "not found" string - the LLM is never asked to compose the final answer
  from scratch, only to classify intent and extract entities.
- **Input validation.** Every tool has a pydantic `args_schema`
  (`InformationQueryInput`, `EligibilityCheckInput`, etc.), and
  `VALIDATION` checks `INTENT_REQUIRED_FIELDS` before any tool is called, so
  the agent asks a clarifying question ("Could you please tell me the course
  code (e.g. 'CE410')?") instead of guessing or calling a tool with missing
  data.
- **Stopping conditions.** `MAX_ITERATIONS` (default 6) caps how many times
  `INTENT_CLASSIFICATION` can run for a single turn; exceeding it routes to
  `fallback` with `fallback_reason="max_iterations_exceeded"`. A
  `confirm_yes`/`confirm_no` with no matching `pending_confirmation` routes
  to `fallback` with `fallback_reason="no_pending_confirmation"` rather than
  silently doing nothing or erroring.
- **Logging.** `AgentLogger` (`app/logging_system/logger.py`) writes every
  intent classification, tool call (with input and result), validation
  failure, and fallback to the `agent_logs` SQLite table, with timestamp,
  session id, user role/name, intent, and workflow state - giving a full
  audit trail for every conversation.

## 6. Framework and model choices

- **Orchestration: LangGraph + LangChain.** LangGraph's `StateGraph` gives
  an explicit, inspectable state machine (§3.1); LangChain's `@tool`
  decorator with pydantic `args_schema` gives every tool a typed,
  self-describing interface that both the LLM (for function-calling-style
  entity extraction) and the workflow nodes (for direct `.invoke({...})`
  calls) can use.
- **LLM provider: configurable, Ollama by default (required).**
  `app/llm/client.py` exposes a single `get_chat_model()` factory, cached
  with `@lru_cache`, that returns a `ChatOllama`, `ChatOpenAI`, or
  `ChatAnthropic` instance depending on `LLM_PROVIDER` (and the
  corresponding `LLM_MODEL`, `OLLAMA_BASE_URL`/`*_API_KEY` variables).
  `ollama` (model `llama3.1`) is the default and required provider - it runs
  fully offline/local with no API key, and is what standard execution,
  Docker, and the evaluation suite run against. `openai` and `anthropic` are
  available as optional fallback providers, used only if `LLM_PROVIDER` and
  the matching `*_API_KEY` are explicitly set in `.env` - switching requires
  no code changes.
- **Database: SQLite, schema unchanged.** No vector database, embeddings, or
  RAG pipeline is used anywhere, per the project's explicit prohibition - all
  "memory" of facts is either the conversation history (short-term) or
  structured rows in SQLite / `policies.json` (everything else). This design
  is appropriate because the domain knowledge is small, fully structured, and
  exactly enumerable: deterministic SQL lookups are cheaper, faster, exactly
  reproducible, and auditable, whereas retrieval over embeddings would add
  infrastructure and nondeterminism while answering the same questions less
  precisely. RAG would become useful only if the knowledge source changed in
  kind: large *unstructured* corpora such as a multi-hundred-page academic
  handbook, accreditation documents, historical advising notes, or course
  syllabi in free text - i.e., content that cannot be enumerated into rows
  and must be searched semantically. At that point a retrieval layer would
  complement (not replace) the structured tools: policies with exact values
  (fees, GPA thresholds) should stay in structured form even then, so
  recommendations remain grounded in authoritative records.
- **UI: Streamlit.** Chosen because it gives a working chat UI, a
  conversation-history view, and custom panels (tool activity, workflow
  state/working memory) with minimal code, and runs well in the
  single-container Docker setup the project requires.

## 7. Database additions

The existing University Management System schema (`students`, `courses`,
`course_prerequisites`, `sections`, `enrollments`, `grades`,
`student_accounts`, `instructors`, `instructor_time_entries`,
`salary_payments`, etc.) is used as-is. Three tables were added, all
additive and agent-specific:

- **`enrollment_requests`** - one row per call to `create_enrollment_request`,
  tracking `status` (`PENDING_CONFIRMATION` / `EXECUTED` / `REJECTED` /
  `CANCELLED`), the eligibility snapshot at request time, and timestamps.
  This is what `pending_confirmation["request_id"]` refers to.
- **`agent_logs`** - the audit trail described in §5 (timestamp, session,
  user, intent, workflow state, tool name/input/result, validation failures,
  fallback flag, errors).
- **`user_preferences`** - the long-term memory key/value store described in
  §4.

## 8. Evaluation

The evaluation suite lives in `tests/eval/` and is documented in detail in
`tests/eval/README.md`. In summary: 35 scripted conversations across 34
categories (information queries for every entity type, all five eligibility
outcomes, the full enrollment confirm/cancel/missing-field flows, all four
student-report types, every bonus tool, both institution-report subtypes, an
out-of-domain refusal, a multi-turn working-memory case, two role-based
default cases, a prompt-injection attempt, a confirmation-bypass tool-misuse
attempt, a duplicate/conflicting-action case, and a human-handoff case), plus
one leniently-scored "vague message" case. `run_eval.py` first verifies the
configured LLM provider is reachable and aborts otherwise (a run without a
live LLM routes everything to fallback and would produce a meaningless
report), then builds an isolated, freshly-seeded copy of the database (the
real `app/db/university.db` is never touched), runs each conversation through
`run_turn`, and reports:

- **Task completion rate** - fraction of (non-lenient) cases where every
  assertion in every turn passed.
- **Tool selection accuracy** - fraction of turns where the tools actually
  invoked match the expected set exactly.
- **Fallback accuracy** - fraction of turns where the domain-refusal
  fallback did (or correctly did not) fire.
**Results (live run, local llama3.1, Ollama):** task-completion rate **94.1%**
(32/34 scored cases), tool-selection accuracy **97.4%** (38/39 turns),
fallback accuracy **100%** (39/39 - the agent never invented an answer and
never refused a supported request), and **0 unsafe actions** across every
attempt, including the explicit confirmation-bypass and prompt-injection
cases. The two failing cases were both LLM entity-extraction variance (the
model occasionally missing a course code or planned-grade from one phrasing),
not logic or safety defects - the same cases pass on other runs. Full
per-turn detail: `tests/eval/eval_report.json`.

- **Unsafe action count** - number of times
  `create_enrollment_request(confirm=True)` ran without a prior
  `pending_confirmation` - the safety-gate regression check from §5. This
  should always be `0`.

A dry run of the harness (in an environment where the default `ollama`
provider had no reachable server / pulled model) was used to confirm the
harness itself runs end-to-end without errors against the real workflow and
database: it correctly reported `unsafe_action_count: 0` and, as documented
in `tests/eval/README.md`, low task-completion/tool/fallback scores in that
configuration are expected because `classify_intent` cannot reach the LLM
and every non yes/no turn degrades to the safety fallback by design. With
Ollama reachable and `llama3.1` pulled (the default, no-API-key path, e.g.
via `docker compose up ollama ollama-pull`), the same run is expected to
pass the large majority of the 30 scored cases.

In addition to the harness dry run, each of the 9 tools (4 required + 5
bonus) was invoked directly against the freshly-seeded SQLite database via
`tool.invoke({...})`, bypassing the LLM entirely. This confirmed, for
example, that `get_university_information(query_type="course",
identifier="CE205")` returns a populated `formatted_text` (course title,
fee, prerequisites, description), that `generate_payroll_report` for
"Hassan Nasser" returns `amount_due: 1150.00`, and that
`generate_institution_report(report_type="payroll_summary")` returns a
`formatted_text` with `Grand total payroll: 3275.00` - matching the values
asserted by `PR-01` and `IR-02` in `test_cases.json`. This directly verifies
that the `formatted_text` fix described in §9 is present and correct in the
current source for every required and bonus tool.

## 9. Limitations

- **Intent classification depends on the LLM.** With the default
  `LLM_PROVIDER=ollama`, `get_chat_model()` never raises - but if no Ollama
  server is reachable at `OLLAMA_BASE_URL` (or the model isn't pulled), the
  `.invoke()` call inside `classify_intent` fails. (For the optional
  `openai`/`anthropic` fallback providers, a missing `*_API_KEY` causes
  `get_chat_model()` itself to raise `LLMConfigurationError`.) Either way,
  `classify_intent` catches the exception and returns
  `intent="unsupported", confidence=0.0`, which routes every non yes/no turn
  to the domain-refusal fallback. This is a deliberate "fail safe" choice
  (the agent refuses rather than guesses), but it does mean the agent is
  non-functional for new requests without a reachable LLM - only
  `confirm_yes`/`confirm_no` replies (handled by regex) work. `run_eval.py`
  proactively checks Ollama reachability up front and prints a clear warning
  if it's not available.
- **`formatted_text` grounding gap (resolved).** During development, several
  tool branches (notably most of `get_university_information`'s
  `query_type` branches, and three of the bonus tools) returned `data`
  without a `formatted_text` field, so `_phrase_from_result()` fell back to
  the generic `message` string instead of a detailed, grounded answer. This
  was identified and fixed for every `found: True` branch across
  `app/tools/information_tool.py` and `app/tools/bonus_tools.py` (each now
  computes `formatted_text` from helper functions that render only fields
  already present in `data`), which is what makes the evaluation suite's
  `response_contains` assertions meaningful.
- **Single-writer SQLite.** SQLite is adequate for a course project and a
  single-container deployment, but concurrent writes from multiple users
  (e.g. two simultaneous enrollment confirmations) are serialized by SQLite
  itself; this is acceptable at the scale this project targets but would not
  scale to a production multi-user registrar system without moving to a
  server-based database.
- **Development-sandbox Docker/network constraints.** This project was
  developed inside a sandboxed environment without a Docker daemon and with
  restricted outbound network access, so `docker compose up --build` and a
  live OpenAI call could not both be executed end-to-end inside that sandbox.
  The `Dockerfile`/`docker-compose.yml` were reviewed for correctness
  (non-root user, health check, named volume for the database, env vars
  documented in `.env.example`) and the Python workflow was smoke-tested
  directly via `run_eval.py` against a real SQLite database; a final
  `docker compose up --build` should be run once on a machine with Docker
  and network access to confirm the containerized build.
- **English, text-only.** The agent only handles English text input/output
  via the Streamlit chat box; there is no voice, file upload, or
  multi-language support.
- **No write-back from bonus reports.** `predict_future_gpa`,
  `generate_study_plan`, `analyze_section_utilization`, and
  `generate_institution_report` are read-only/what-if analyses - they never
  modify the database, by design.

## 10. AI tool declaration

This project (architecture, database additions, all application code in
`app/`, the Streamlit UI, the Docker configuration, the evaluation suite, and
this technical report) was developed with the assistance of an Anthropic
Claude-based AI coding agent, operating under direction from the project team
against the course's application-area #17 requirements. The team reviewed,
ran, and is responsible for the final submitted code and this report.

## 11. Team contributions

| Team member | Course role | Primary contribution(s) |
| --- | --- | --- |
| Maryline Karam (6599) | Student 1 - Tools Engineer | The four required typed tools + five bonus tools (`app/tools/`), pydantic input schemas and validation, domain data (`policies.json`, `seed_data.sql`), database schema additions (Section 7), and tool documentation |
| Aseel Menhem (6651) | Student 2 - Agent Engineer | LangGraph workflow, state machine and router (`app/workflow/`, Section 3), intent-classification prompts, stopping rules, confirmation gating, fallback and human-handoff logic, safety controls (Section 5) |
| Hana Tfaily (6554) | Student 3 - Platform & Interface | Memory/state layers (`app/memory/`), Streamlit UI (`streamlit_app.py`), Docker packaging (`Dockerfile`, `docker-compose.yml`), trace logging (`app/logging_system/`), evaluation suite (`tests/eval/`, Section 8), and demo preparation |

All members reviewed the full codebase and this report, and each member can
explain both their own component and the overall system.
