# Speaking Scripts - Word for Word

This is the canonical script. If anything here disagrees with an older doc,
this file wins. Slide numbers refer to `AI_Agent_Presentation.html`.

The presentation itself is RECORDED (not live): record the deck narration
over screen-captured slides, and splice Hana's demo recording in at slide 6.

Flow: **Maryline** narrates slides 1-5 → slide 6 introduces the demo, then
cut to the **demo recording** → **Aseel** narrates slides 7-10.
Voice-over split for the demo footage itself: Part A = Maryline,
Part B = Aseel, Part C = Hana (scripts below).

---

## MARYLINE - Opening & slides 1-5 (~5 min)

### Slide 1 - The hook + introductions

> Imagine it's registration week. You wait forty minutes in line at the
> registrar's office, you finally reach the desk — and you're told you can't
> enroll because you're missing one prerequisite. Which they could have seen
> in three seconds. Now imagine asking that same question from your phone
> and getting the answer instantly — checked against the real database, not
> guessed.
>
> That's what we built. Good morning — we are presenting the University
> Operations AI Agent: a Dockerized, domain-specific AI agent that answers
> university questions, checks enrollment eligibility, executes enrollments
> safely, and generates reports — all grounded in a real university
> database.
>
> I'm Maryline, the Tools Engineer — I built the nine tools and the data
> layer the agent stands on.

*(gesture to Aseel)*

> **Aseel:** I'm Aseel, the Agent Engineer — I built the workflow: the state
> machine that decides what the agent is allowed to do, and the safety rails
> that stop it doing anything else.

*(gesture to Hana)*

> **Hana:** And I'm Hana, Platform and Interface — I built the memory, the
> web interface, the Docker packaging, and the evaluation suite. The demo
> you'll watch in a few minutes is running live on my laptop — and yes, I
> enroll myself in a course during it.

> **Maryline:** Let's start with the problem.

### Slide 2 - The problem

> Every semester, students and staff ask the registrar the same questions
> over and over: what are the prerequisites for this course, what's the fee,
> am I eligible, can you enroll me, can I get my transcript. Every one of
> those answers lives in a database — but someone has to look it up, table
> by table.
>
> Our agent does four things about that. One: it answers questions with
> facts pulled from the database — never from the model's imagination. Two:
> it runs eligibility analysis — prerequisites, seat capacity, account
> balance, duplicates — as deterministic rules. Three: it takes real
> actions, like enrolling a student, but only behind an explicit
> confirmation gate. And four: it generates structured reports.
>
> One important framing: this is course project application area seventeen,
> an Educational Support Agent, and we built it as decision support — it
> states its sources, admits its limits, and escalates to humans. It is not
> an authority.

### Slide 3 - Architecture

> The system is seven layers, and the order matters. A Streamlit chat
> interface on top. Under it, a LangGraph orchestration layer — an explicit
> state machine, which Aseel will show you. Then the language model — and
> here is our key design decision: the LLM's only job is to classify what
> the user wants and extract the entities, as JSON. It never writes facts
> into an answer. Every fact comes from layer four — nine typed tools — which
> read layer six, a SQLite database and a structured policy file. Memory
> sits alongside, and the whole thing ships as one Docker Compose stack with
> a local model — no API keys anywhere.
>
> So if the model hallucinates — and small local models do — the worst it can
> do is misclassify an intent. It cannot invent a course fee.

### Slide 4 - The four required tools

> The spec requires four tool categories; here they are. The information
> tool does grounded lookups — courses, policies, instructors. Give it a
> course code that doesn't exist and it returns found-false, never a guess.
> The analysis tool checks enrollment eligibility with four deterministic
> rules: prerequisites, section capacity, account balance, and duplicate
> enrollment. Same input, same verdict, every time.
>
> The action tool is the only one that changes the database, and it works in
> two phases: a preview phase that writes nothing, and an execute phase that
> only runs after the user explicitly confirms — and it re-validates before
> writing. And the reporting tool builds transcripts, GPA summaries, and
> recommendations. Every tool has a pydantic input schema, a typed output,
> and defined error behavior. We also added five bonus tools — GPA
> prediction, study planning, payroll, utilization, and institution reports.

### Slide 5 - Why no RAG

> You might ask: where's the vector database? There isn't one — on purpose.
> Our domain knowledge is small, fully structured, and enumerable. For that,
> exact SQL beats semantic search on every axis that matters here:
> precision, reproducibility, auditability. An embedding can retrieve a
> paragraph *about* fees; it can't join, sum, or re-validate a fee like a
> row can.
>
> RAG becomes the right tool when the knowledge stops being structured — a
> four-hundred-page academic handbook, free-text advising notes. Even then
> it would complement our tools, not replace them: exact values stay in
> structured form.
>
> Enough slides — let's see the agent in action. We recorded this in one
> take, on one laptop, running fully offline in Docker: you'll see it answer
> from the database, enroll one of us in a real course behind a confirmation
> gate, refuse what it shouldn't do — and prove it with tests.

*(slide 6 stays up for that sentence, then cut to the demo recording)*

---

## ASEEL - Slides 7-10 (~4 min, after the video)

### Slide 7 - Workflow & safety

> What you just watched wasn't a model improvising — it was a state machine
> executing. Every turn follows this path: classify the intent, gather
> information, validate it, analyze, and only then act or report. If the
> classifier's confidence is below zero point four, or the request is out of
> domain, the turn is routed to a fallback that states the limitation and
> offers a human handoff — it never invents an answer. You saw that with the
> flight to Paris.
>
> The confirmation gate you watched — where Hana had to say yes before her
> enrollment executed — is enforced by the structure of the graph, not by
> prompt wording. The execute step is only reachable after a pending
> confirmation exists. In our test suite someone explicitly asks the agent
> to skip confirmation — it can't.
>
> Three more rails: a maximum of six iterations per turn, so no infinite
> loops; a yes or no with nothing pending routes to fallback; and the human
> handoff is matched by a regular expression, not the LLM — so escalation
> works even if the model is down. And everything — every intent, tool call,
> validation failure, fallback — is logged to an audit table.

### Slide 8 - Memory

> The spec requires two kinds of memory and offers a bonus for a third. We
> have all three. Short-term memory is the conversation: messages, the
> user's name and role — that's why Hana could say "my GPA" without saying
> who she was. Working memory is the explicit task state, six required
> fields: current intent, collected information, missing fields, pending
> confirmation, latest tool result, and workflow state — and we render it
> live in the side panel, so you can watch the agent think. Long-term
> memory, the bonus, persists user preferences in SQLite across sessions.

### Slide 9 - Evaluation & Docker

> How do we know it works? Thirty-five scripted test conversations across
> thirty-four categories — including the hostile ones: a prompt injection
> telling the agent to ignore its instructions, an attempt to bypass the
> confirmation gate, duplicate actions, ambiguous requests. Four required
> metrics come out; the one we're proudest of is zero unsafe actions — not
> once did the state-changing tool run without a confirmed gate. And one
> detail: the eval runner refuses to produce a report if the LLM isn't
> reachable, so the numbers can never be silently meaningless.
>
> And reproducibility: one command — docker compose up, dash dash build.
> Three services: a local Ollama model, a one-shot model pull, and the
> agent. Non-root user, health checks, named volumes, no API keys, no
> secrets in the repo.

### Slide 10 - Close

> To sum up who built what: Maryline built the tools and the data layer,
> I built the workflow and the safety rails, Hana built the platform, the
> memory, the interface, and the evaluation. But we each know the whole
> system — ask any of us about any part of it. We declared our use of AI
> development tools in the technical report. Thank you — we're happy to take
> questions.

---

## HANA - Demo runbook: step by step, with expected answers

You drive the demo and record it (see `docs/RECORDING_GUIDE.md` for OBS
settings and the voice-over workflow). You are in the database as student
**Hana Tfaily** (GPA 3.5, completed CE205 grade A and CE301 grade B,
balance 4000.00 — fully eligible for CE410).

### Before recording
1. `docker compose up` → wait healthy → open http://localhost:8501
2. Send one warm-up message (first model reply is slow), then click
   **clear/new conversation** so the recording starts clean.
3. **Important:** the enrollment demo writes to the database. To re-record,
   reset first: `docker compose down -v && docker compose up` (deletes the
   volume and reseeds — the model stays cached in `ollama_data`... if you
   also deleted it, re-pull happens automatically).

### The 11 steps

Sidebar for A1: Name **Maryline Karam**, Role **Student**.

| # | Do / type exactly | Expected answer (verbatim where fixed) | Check |
|---|---|---|---|
| A1 | `Can you tell me about course CE410?` | "CE410 - Operating Systems (4 credits) / Department: Computer Engineering / Course fee: 1800.00 / Prerequisites: CE301 / Description: Processes, scheduling, memory management, file systems and concurrency." | Tool activity shows `get_university_information` |
| A2 | Switch Role to **Registrar Staff**, type: `Is Nour Hamad eligible to enroll in CE410 for Spring 2026?` | "Nour Hamad is NOT eligible to enroll in CE410: Student is already enrolled in CE410 for Spring 2026." | `analyze_enrollment_eligibility` ran; verdict is deterministic |
| B1 | Switch Name to **Hana Tfaily**, Role **Student**, type: `I'd like to enroll in CE410 for Spring 2026.` | "Hana Tfaily is eligible to enroll in CE410 for Spring 2026. Please confirm to proceed. Reply 'yes' to confirm or 'no' to cancel." | Workflow panel = CONFIRMATION_REQUIRED; pending confirmation set; **nothing written yet** |
| B2 | `yes` | "Hana Tfaily has been enrolled in CE410 (Spring 2026). Fee of 1800.00 deducted; new balance is 2200.00." | `create_enrollment_request` with confirm=true |
| B3 | `Enroll me in CE410 again.` | "Hana Tfaily is NOT currently eligible to enroll in CE410 for Spring 2026: Student is already enrolled in CE410 for Spring 2026. If you'd like, reply 'no' to cancel this request." | Duplicate blocked by re-validation |
| B4 | `no` | "Okay, the enrollment request has been cancelled. No changes were made." | Clean cancel path |
| B5 | `Can you book me a flight to Paris?` | "I cannot perform that action because it is outside my supported university operations domain, and I won't guess an answer. If you'd like, I can forward your request to university staff - just say 'talk to a human' and I'll create a handoff ticket for you." | **Zero** tool calls; fallback logged |
| B6 | `talk to a human` | "I've created handoff ticket HANDOFF-<timestamp> and forwarded your request to university staff (simulated). A staff member would review the conversation and follow up with you..." | `create_handoff_ticket` in tool activity |
| C1 | `What is my GPA summary?` | "GPA Summary - Hana Tfaily / Current GPA: 3.5 / Completed courses: 2 / Academic standing: Dean's List" | You never typed your name — short-term memory + role default filled it |
| C2 | `And my transcript summary?` | "Transcript Summary - Hana Tfaily (ID 7) / CE205 Programming Fundamentals 3 cr Grade: A / CE301 Data Structures 3 cr Grade: B / Total credits earned: 6 / Cumulative GPA: 3.5" | Identifier carried over from C1 = working memory |
| C3 | Terminal: `python -m tests.eval.run_eval` | PASS lines scrolling, then the 4 metrics with `unsafe_action_count: 0` | End the recording on the metrics |

Notes: intent classification comes from a local llama3.1, so A1/A2/B1
phrasing can vary slightly — the tool results and numbers are deterministic
and will match exactly. If a reply takes 20-30 s, hold still; it gets
trimmed or covered by narration.

### Your voice-over (Part C of the video, ~40 s)

> Notice what I didn't do: I never told it who I am after switching my name
> once. Short-term memory holds my session identity, so "my GPA" resolves to
> me — three point five, Dean's List, straight from my grades in the
> database. My transcript request reused the same identifier from the
> previous turn — that's the working memory, and you can watch every field
> of it in the side panel: intent, collected information, pending
> confirmation, workflow state. Finally, the evaluation suite: thirty-five
> conversations, four metrics, zero unsafe actions.

### If an examiner asks you (likely Q&A)
- "What happens on restart?" → the database lives on a named volume, so my
  CE410 enrollment survives container restarts; `down -v` resets it.
- "Why was the first answer slow?" → local llama3.1 cold start; that's the
  cost of running with no API keys, fully offline.
- "Can it enroll me without asking?" → no — the execute step is unreachable
  in the graph until a pending confirmation exists; test MISUSE-02 proves it.
