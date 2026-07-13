# Member 1 - Tools Engineer: **Maryline**

**Presentation duty:** presents slides 1-5 (title, problem, architecture,
tools, data & no-RAG) and voices over Demo Part A in Hana's recording.

## Role description
You own everything the agent *knows* and *does*: the SQLite database (schema,
seed data), the structured policy file, and all nine tools (4 required +
5 bonus) in `app/tools/`. You are graded mainly on **"Tool correctness,
validation, and data integrity" (20%)**. In Q&A, expect questions about input
schemas, error behavior, and why the project uses deterministic SQL instead
of RAG.

Files you must know line-by-line:
- `app/tools/*.py` (all tools + `db_helpers.py`)
- `app/db/schema.sql`, `app/db/seed_data.sql`, `app/db/policies.json`
- Technical Report §6 (why no RAG) and §7 (database additions)

## Apps to install
| App | Why | Where |
| --- | --- | --- |
| Python 3.11+ | Run and test tools directly, without Docker | python.org |
| Git | Repo access | git-scm.com |
| DB Browser for SQLite | Inspect tables, verify enrollments/fees after tests | sqlitebrowser.org |
| VS Code (or any editor) | Code review during Q&A | code.visualstudio.com |

You do NOT need Docker or Ollama for your part - the tools are pure
Python + SQLite and testable without any LLM.

## Libraries (installed automatically from requirements.txt)
You only directly use: `pydantic` (input schemas), `langchain-core`
(the `@tool` decorator), and the standard-library `sqlite3` and `json`.

## Step-by-step setup
```bash
# 1. Clone and enter the project
git clone <repo-url>
cd <repo>/ai_agent

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build and seed the database
python -m app.db.init_db --force
```

## Verify your part works (no LLM needed)
```bash
python - << "PY"
from app.tools import (get_university_information, analyze_enrollment_eligibility,
                       create_enrollment_request, generate_student_report)
# Information tool
print(get_university_information.invoke({"query_type": "course", "identifier": "CE410"})["found"])
# Analysis tool - Nour Hamad is already enrolled in CE410 (seed data)
r = analyze_enrollment_eligibility.invoke({"student_identifier": "Nour Hamad", "course_code": "CE410"})
print("eligible:", r["eligible"], "| reasons:", r["reasons"])
# Action tool preview (confirm=False writes NO enrollment)
r = create_enrollment_request.invoke({"student_identifier": "Yousef Khalil", "course_code": "CE205", "confirm": False})
print("status:", r["status"])
# Reporting tool
print(generate_student_report.invoke({"student_identifier": "Yousef Khalil", "report_type": "gpa_summary"})["found"])
PY
```
Expected: `True`, `eligible: False` with an "already enrolled" reason,
`status: pending_confirmation`, `True`. Then open `app/db/university.db` in
DB Browser and show the `enrollment_requests` row that was created.

## Your voice-over script

Superseded: use **`docs/SPEAKING_SCRIPTS.md`** (canonical, word-for-word) -
your slide scripts and Demo Part A narration are there, updated for the
Hana-enrolls-herself demo flow.
