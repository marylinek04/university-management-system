# Presentation Plan - 3-Person Division, Run Guide, and Demo Scripts

Target: ~15 minutes total (12 min presentation + demo, 3 min Q&A buffer).
Every member must be able to answer questions about ANY component (10% of
the grade is individual understanding), so rehearse each other's parts once.

---

## 1. Who presents what

### Person 1 - Tools Engineer: Maryline (~4 min, slides 1-5)
Owns: `app/tools/`, `app/db/` (schema, seed data, policies.json)

1. Problem statement + application area (#17 Educational Support Agent on
   top of the existing University Management System DB). (30s)
2. The 4 required tools, one slide each row: name, category
   (information / analysis / action / reporting), input schema (pydantic),
   output schema, error behavior. (1.5 min)
3. Why structured data + deterministic tools instead of RAG, and when RAG
   would become useful (Technical Report §6). (1 min)
4. Bonus tools in one breath: GPA prediction, study plan, payroll,
   section utilization, institution report. (30s)
5. DEMO PART A (below). (1 min)

### Person 2 - Agent Engineer: Aseel (~4 min, slides 6-10)
Owns: `app/workflow/` (graph, router, nodes, prompts), safety controls

1. The 7-layer architecture diagram (Technical Report §2) - 30 seconds,
   point at layers, don't read them.
2. The state machine: INTENT_CLASSIFICATION -> INFORMATION_GATHERING ->
   VALIDATION -> ANALYSIS -> CONFIRMATION_REQUIRED -> ACTION_EXECUTION ->
   REPORT_GENERATION -> END, plus the fallback node. Emphasize: LLM only
   classifies intent and extracts entities - it NEVER writes facts into
   answers; every fact comes from a tool result. (1.5 min)
3. Safety controls: confidence threshold (0.4), MAX_ITERATIONS (6),
   confirmation gate on the only state-changing tool, deterministic
   human-handoff regex, exact-string fallback. (1 min)
4. DEMO PART B (below). (1.5 min)

### Person 3 - Platform & Interface: Hana (demo runner/recorder; content presented by Maryline & Aseel)
Owns: `app/memory/`, `streamlit_app.py`, Docker, `app/logging_system/`, `tests/eval/`

1. Memory: short-term (messages + user name/role), working memory (the 6
   required fields, visible live in the UI side panel), long-term bonus
   (per-user preferences in SQLite). (1 min)
2. Docker: one command, three services (ollama, ollama-pull, agent),
   non-root user, healthchecks, named volumes, no API keys. (1 min)
3. Evaluation: 35 cases / 34 categories incl. prompt injection,
   confirmation-bypass, duplicate action, handoff; the 4 metrics; the
   LLM preflight that refuses to produce a garbage report. Show one slide
   with the final metrics from `eval_report.json`. (1 min)
4. DEMO PART C (below) + closing slide (limitations + who did what). (1 min)

---

## 2. How to run (do this BEFORE the presentation)

### One-time setup on the demo machine
```bash
git clone <your-repo-url>
cd <repo>/ai_agent
docker compose up --build        # first run pulls llama3.1 (~4.7 GB) - do NOT do this live
```
Wait until the logs show the agent is healthy, then open http://localhost:8501
and send one test message so the model is warm.

### Day of the demo
```bash
cd <repo>/ai_agent
docker compose up                # no --build needed if nothing changed; starts in seconds
```
Open http://localhost:8501. Keep a terminal visible with
`docker compose logs -f agent` if asked about observability.

### Regenerate the eval report (required before submission)
```bash
cd ai_agent
docker compose up -d ollama ollama-pull        # make sure the LLM is up
pip install -r requirements.txt                 # once, on the host
python -m tests.eval.run_eval                   # writes tests/eval/eval_report.json
```
The runner ABORTS if no LLM is reachable - that is intentional. Commit the
resulting `eval_report.json`; put its 4 metrics on Person 3's slide.

### Fallback plan if the live demo breaks
Record a 2-minute screen capture of Demo Parts A-C the night before.
If Docker/Wi-Fi fails on stage, play the recording and show the code instead.

---

## 3. Demo script

Superseded: the full step-by-step demo (exact messages + verbatim expected
answers) now lives in **`docs/SPEAKING_SCRIPTS.md`** ("HANA - Demo runbook").
Summary of the flow: CE410 course lookup (as Maryline) → Nour duplicate
eligibility (as Registrar) → Hana enrolls HERSELF in CE410 with the
confirmation gate (eligible, fee 1800.00, new balance 2200.00) → duplicate
attempt rejected → Paris fallback → human handoff → "my GPA / my transcript"
memory demo (as Hana) → eval metrics.

## 4. Pre-demo checklist

- [ ] `docker compose up` tested on the actual presentation machine/network
- [ ] Model pulled and warm (send one message before presenting)
- [ ] `eval_report.json` regenerated with the live LLM and committed
- [ ] Team-contributions table in `docs/TECHNICAL_REPORT.md` §11 has real names
- [ ] Backup screen recording of Parts A-C exists
- [ ] Each member rehearsed the OTHER two parts once (individual Q&A is graded)

## 5. Likely Q&A per grading row (know these cold)

| Grading row (weight) | Likely question | One-line answer |
|---|---|---|
| Workflow & reasoning (20%) | "What stops an infinite loop?" | MAX_ITERATIONS=6 per turn; exceeding it routes to fallback with a logged reason. |
| Tool correctness (20%) | "What if I pass a nonsense course code?" | Pydantic validates shape; the tool returns found=false with a message - never a guess. |
| Memory & state (15%) | "Where is working memory, exactly?" | Top-level AgentState keys (intent, collected info, missing fields, pending confirmation, latest tool result, workflow state) - rendered live in the sidebar. |
| Eval & safety (15%) | "How do you know the confirmation gate can't be bypassed?" | MISUSE-02 asks to skip it; the unsafe-action metric counts any confirm=True without prior pending_confirmation - it's 0. |
| Docker (10%) | "Why three services?" | ollama (LLM), ollama-pull (one-shot model fetch), agent (UI+workflow); healthchecks + named volumes; non-root user; no API keys. |
| Interface (5%) | "Why Streamlit?" | Chat + custom state panels in minimal code, runs headless in the container. |
| Report (5%) | "Why no RAG?" | Small, structured, enumerable domain -> deterministic SQL is more precise and auditable; RAG only pays off for large unstructured corpora (handbook, syllabi). |
| Demo & Q&A (10%) | Anything about a teammate's part | That's why everyone rehearses all three parts. |
