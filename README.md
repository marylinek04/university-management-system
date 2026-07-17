# 🎓 University Management System

A complete university operations platform — from the core SQL Server database all the way up to an AI-powered chat agent that students and staff can talk to directly.

> **Phase 1**: SQL Server + T-SQL + MongoDB — relational database, stored procedures, triggers, security — *built by Maryline Karam & Aseel Menhem*
> **Phase 2**: AI Agent Layer — conversational agent built on LangGraph + Streamlit + Ollama (local LLM, no API key required) — *Hana Tfaily joined the team for this phase*
>
> **Made by**: Maryline Karam · Aseel Menhem · Hana Tfaily

> 🎥 **[Watch the video presentation & live demo](https://drive.google.com/drive/folders/19YgM857kqSZUT-1LRUfBXqsiOPViCGoI?usp=sharing)**

---

## 📖 What is This?

This is a full university database that handles:

- 👨‍🎓 Student enrollment and grades
- 👨‍🏫 Instructor assignments and payroll
- 📚 Course management and scheduling
- 💰 Tuition payments and financial tracking
- 🔐 Role-based security (6 different user types)

Think of it as the backend system that powers a university's operations!

---

## ✨ What Makes It Special?

### Smart Enrollment System
When a student tries to enroll:
1. ✅ Checks if they have enough money
2. ✅ Checks if the class isn't full
3. ✅ Automatically deducts the course fee
4. ❌ Rejects if anything fails

### Automatic Grade Processing
When an instructor submits a grade:
1. 📝 Validates the grade (A, B, C, D, or F)
2. 🔒 Checks if grades are locked
3. 🧮 Automatically recalculates student's GPA
4. 📊 Updates transcript in real-time

### Payroll System
For instructor payments:
1. ⏰ Instructors log their work hours
2. ✅ Department head approves hours
3. 💵 System calculates payment (hours × rate)
4. 💰 Generates payroll automatically

---

## 🏗️ Database Structure

### Core Tables (15 Total)

**Security** 🔐
- `Role` - Defines 6 user roles
- `User` - All system users

**Academic** 📚
- `Department` - University departments
- `Program` - Degree programs (Bachelor, Master, PhD)
- `Student` - Student records with GPA
- `Instructor` - Instructor profiles
- `Course` - Course catalog
- `Semester` - Academic periods
- `Section` - Course sections per semester
- `Enrollment` - Student enrollments
- `Grade` - Grades and transcripts

**Financial** 💰
- `StudentAccount` - Student balances
- `StudentPayment` - Payment records
- `InstructorSalary` - Instructor pay rates
- `SalaryPayment` - Payroll history

### How They Connect

```
User → Student → Enrollment → Grade
              ↓
          Program
              ↓
         Department → Course → Section → Enrollment
                          ↓
                    Instructor → SalaryPayment
```

Full visual reference: [ERD diagram](docs/ERD_diag_UMS.png) · [Use-case diagram](docs/USE_CASE_UMS.png)

---

## 📊 Data Visualizations (MongoDB Charts)

To support data-driven decision-making, several analytical dashboards were created using MongoDB Charts. These visualizations provide clear insights into the university's financial status, faculty workload, and course utilization, transforming raw operational data into meaningful management information.

Static snapshots are included for documentation; the live dashboards allow real-time interaction during demonstrations.

### [Student Tuition Collection Status](docs/charts/student_tuition_collection.png)
Compares paid balances against outstanding tuition fees for a quick overview of cash flow.
**Key Insight:** the finance office can immediately identify unpaid balances, assess financial exposure, and prioritize collection efforts.

### [Instructor Workload Analysis](docs/charts/instructor_workload_analysis.png)
Summarizes total teaching hours logged by each instructor, based on approved time entries.
**Key Insight:** department heads can ensure fairness, detect overload, and validate hours before salary processing.

### [Course Utilization (Capacity vs. Enrollment)](docs/charts/course_utilization.png)
Compares section capacity against actual enrollment to evaluate resource use.
**Key Insight:** highlights underutilized sections and fully booked classes for better planning.

MongoDB playground: [`mongodb/university_management_playground.mongodb.js`](mongodb/university_management_playground.mongodb.js)

---

## 🤖 Phase 2 — AI Agent Layer ([`ai_agent/`](ai_agent/))

On top of the database we built a full AI agent that lets students and staff interact with the university system through natural language.

### What the agent can do
- Answer questions about courses, policies, programs, and academic rules
- Check whether a student is eligible to enroll in a course (prerequisites, capacity, balance, duplicates)
- Submit an enrollment request — gated behind a confirmation step so nothing mutates by accident
- Refuse out-of-domain requests and escalate to a (simulated) human with a traceable handoff ticket
- Generate student transcripts, institution-wide reports, payroll summaries, and study plans
- Predict future GPA and analyze section utilization

### Architecture (7 layers)

```
Layer 1 — Streamlit chat UI           (streamlit_app.py)
Layer 2 — LangGraph state machine     (app/workflow/)  ← intent → gather → validate → analyze → confirm → execute → report (+ fallback)
Layer 3 — Configurable LLM            (app/llm/client.py)
           Ollama (default, local, no API key) | OpenAI / Anthropic (optional fallback)
Layer 4 — 9 typed tools               (app/tools/)     ← all grounded in the database
Layer 5 — Memory                      (app/memory/)    ← short-term, working, long-term (bonus)
Layer 6 — SQLite database             (app/db/)        ← same schema as Phase 1 + policies.json
Layer 7 — Container                   (Dockerfile, docker-compose.yml) ← one-command startup
```

### Quickstart (Docker — recommended)

```bash
cd ai_agent
docker compose up --build
# open http://localhost:8501
```

No `.env` file or API key needed. Docker pulls and runs `llama3.1` locally via Ollama automatically.

### Quickstart (local, no Docker)

```bash
cd ai_agent
ollama serve && ollama pull llama3.1          # start local LLM
pip install -r requirements.txt
python -m app.db.init_db
streamlit run streamlit_app.py
```

See [`ai_agent/README.md`](ai_agent/README.md) for full setup details, environment variables, and the evaluation suite (35 documented test conversations, incl. prompt-injection and confirmation-bypass attempts).

---

## 🚀 Getting Started (Phase 1 — Database)

### Prerequisites
- SQL Server 2019 or later
- SQL Server Management Studio (SSMS)
- (Optional) MongoDB for visualizations

### Quick Setup

**Step 1: Run the SQL scripts in order**

1. [`sql/01_initialization.sql`](sql/01_initialization.sql) — Creates database
2. [`sql/02_tables.sql`](sql/02_tables.sql) — Creates tables
3. [`sql/03_security.sql`](sql/03_security.sql) — Sets up users and roles
4. [`sql/04_views.sql`](sql/04_views.sql) — Creates views
5. [`sql/05_functions.sql`](sql/05_functions.sql) — Creates functions
6. [`sql/06_procedures.sql`](sql/06_procedures.sql) — Creates stored procedures
7. [`sql/07_triggers.sql`](sql/07_triggers.sql) — Creates triggers
8. [`sql/08_sample_data.sql`](sql/08_sample_data.sql) — Loads test data
9. [`sql/10_permissions.sql`](sql/10_permissions.sql) — Grants role permissions

**Step 2: Verify it works**

```sql
:r sql/09_test_scripts.sql      -- run the test suite
SELECT * FROM Student;
SELECT * FROM Course;
SELECT * FROM Enrollment;
```

**Done!** ✅ Your database is ready.

---

## 🎮 How to Use It

### Example 1: Enroll a Student

```sql
-- First, make sure student has money
EXEC usp_RegisterStudentPayment
    @StudentFullName = 'John Doe',
    @Amount = 2000,
    @ProcessedByUserID = 1;

-- Check balance
SELECT dbo.fn_GetStudentBalance('John Doe');

-- Enroll in course
EXEC usp_EnrollStudent
    @StudentName = 'John Doe',
    @CourseCode = 'CE301',
    @SemesterName = 'Fall 2024';
```

**What happens behind the scenes:**
1. System checks balance ≥ course fee ($1,500)
2. System checks section has space
3. Enrollment is created
4. $1,500 is deducted from balance

### Example 2: Submit a Grade

```sql
EXEC usp_SetStudentGrade
    @InstructorID = 3,           -- Dr. Maya Saad
    @StudentID = 1,              -- John Doe
    @SemesterName = 'Fall 2024',
    @CourseCode = 'CE301',
    @GradeValue = 'A';
```

**What happens behind the scenes:**
1. Verifies instructor teaches this course
2. Checks grade isn't locked
3. Saves grade
4. **Automatically recalculates student's GPA!**

### Example 3: View Transcript

```sql
EXEC usp_GetMyTranscript
    @username = 'john.doe',
    @password = 'hashed_password';
```

**Returns:** student info and current GPA, all courses taken, grades received, total credits earned.

---

## 🔒 Security System

We have **6 different user roles**, each with specific permissions:

| Role | What They Can Do |
|------|------------------|
| 👨‍🎓 **Student** | View own transcript, request enrollment |
| 👨‍🏫 **Instructor** | Submit grades, view assigned classes, log work hours |
| 📝 **Registrar** | Enroll/drop students, view section capacity |
| 👔 **Admin** | Create users, lock/unlock grades, manage everything |
| 🏛️ **Head of Department** | Assign instructors, approve teaching loads |
| 💰 **Finance Officer** | Process payments, generate payroll |

### How Security Works

```sql
-- Students can ONLY see their own data
GRANT EXECUTE ON usp_GetMyTranscript TO role_student;

-- Instructors can ONLY grade their own classes
GRANT EXECUTE ON usp_SetStudentGrade TO role_instructor;

-- Finance handles money
GRANT EXECUTE ON usp_RegisterStudentPayment TO role_finance;
GRANT EXECUTE ON GenerateInstructorPayroll TO role_finance;
```

No one can access tables directly — everything goes through controlled procedures! Full grants: [`sql/03_security.sql`](sql/03_security.sql) and [`sql/10_permissions.sql`](sql/10_permissions.sql).

The AI agent applies the same philosophy one layer up: the LLM never touches the database directly — every read/write goes through a typed, validated tool, and the only state-changing tool is gated behind explicit user confirmation.

---

## 🤖 Automated Features

### 1. Automatic GPA Calculation
When any grade changes: trigger fires, recalculates the weighted average, updates the student's GPA — no manual calculation.

### 2. Capacity Enforcement
When enrolling: trigger checks the enrollment count against section capacity and **rejects** if the class is full.

### 3. Account Creation
Creating a new student user automatically creates the Student record and StudentAccount ($0 balance).

### 4. Balance Updates
Processing a payment automatically updates the balance — always accurate.

All triggers: [`sql/07_triggers.sql`](sql/07_triggers.sql)

---

## 📊 The Numbers

**Phase 1**
- **15 Tables** with proper relationships
- **10 Stored Procedures** for business logic
- **6 Functions** for calculations
- **5 Triggers** for automation
- **3 Views** for reporting
- **6 User Roles** with security
- **2,500+ lines** of SQL code

**Phase 2**
- **9 typed tools** (4 required + 5 bonus), all grounded in the database
- **Explicit LangGraph state machine** with confirmation gate, stopping rules, fallback, and human handoff
- **3 memory layers** (short-term, working, long-term bonus)
- **35 documented test conversations** across 34 categories, 4 required metrics, 0 unsafe actions
- **One-command Docker startup**, fully offline, no API keys

---

## 🗂️ Project Files

**Phase 1 — SQL Server** ([`sql/`](sql/))
- [`01_initialization.sql`](sql/01_initialization.sql) · [`02_tables.sql`](sql/02_tables.sql) · [`03_security.sql`](sql/03_security.sql) · [`04_views.sql`](sql/04_views.sql) · [`05_functions.sql`](sql/05_functions.sql)
- [`06_procedures.sql`](sql/06_procedures.sql) · [`07_triggers.sql`](sql/07_triggers.sql) · [`08_sample_data.sql`](sql/08_sample_data.sql) · [`09_test_scripts.sql`](sql/09_test_scripts.sql) · [`10_permissions.sql`](sql/10_permissions.sql)

**MongoDB** ([`mongodb/`](mongodb/))
- [`university_management_playground.mongodb.js`](mongodb/university_management_playground.mongodb.js) — NoSQL version + analytics

**Phase 1 docs** ([`docs/`](docs/))
- [`ERD_diag_UMS.png`](docs/ERD_diag_UMS.png) · [`USE_CASE_UMS.png`](docs/USE_CASE_UMS.png) · [`Presentation_Slides.pdf`](docs/Presentation_Slides.pdf) · [charts/](docs/charts/)
- [`Project_proposal_document.pdf`](Project_proposal_document.pdf)

**Phase 2 — AI Agent** ([`ai_agent/`](ai_agent/))
- [`docker-compose.yml`](ai_agent/docker-compose.yml) · [`Dockerfile`](ai_agent/Dockerfile) · [`streamlit_app.py`](ai_agent/streamlit_app.py) · [`requirements.txt`](ai_agent/requirements.txt) · [`.env.example`](ai_agent/.env.example) · [`README.md`](ai_agent/README.md)
- [`app/config.py`](ai_agent/app/config.py) — all settings via env vars
- [`app/llm/client.py`](ai_agent/app/llm/client.py) — Layer 3: Ollama / OpenAI / Anthropic
- [`app/workflow/`](ai_agent/app/workflow/) — Layer 2: LangGraph state machine ([`graph.py`](ai_agent/app/workflow/graph.py) · [`router.py`](ai_agent/app/workflow/router.py) · [`nodes.py`](ai_agent/app/workflow/nodes.py) · [`state.py`](ai_agent/app/workflow/state.py) · [`prompts.py`](ai_agent/app/workflow/prompts.py))
- [`app/tools/`](ai_agent/app/tools/) — Layer 4: 9 grounded tools ([`information_tool.py`](ai_agent/app/tools/information_tool.py) · [`analysis_tool.py`](ai_agent/app/tools/analysis_tool.py) · [`action_tool.py`](ai_agent/app/tools/action_tool.py) · [`reporting_tool.py`](ai_agent/app/tools/reporting_tool.py) · [`bonus_tools.py`](ai_agent/app/tools/bonus_tools.py))
- [`app/memory/`](ai_agent/app/memory/) — Layer 5: [`short_term.py`](ai_agent/app/memory/short_term.py) · [`working_memory.py`](ai_agent/app/memory/working_memory.py) · [`long_term.py`](ai_agent/app/memory/long_term.py)
- [`app/db/`](ai_agent/app/db/) — Layer 6: [`schema.sql`](ai_agent/app/db/schema.sql) · [`seed_data.sql`](ai_agent/app/db/seed_data.sql) · [`policies.json`](ai_agent/app/db/policies.json) · [`init_db.py`](ai_agent/app/db/init_db.py)
- [`app/logging_system/logger.py`](ai_agent/app/logging_system/logger.py) — observability / audit trail
- [`tests/eval/`](ai_agent/tests/eval/) — evaluation suite: [`test_cases.json`](ai_agent/tests/eval/test_cases.json) (35 cases) · [`run_eval.py`](ai_agent/tests/eval/run_eval.py) · [`README.md`](ai_agent/tests/eval/README.md)

**Phase 2 docs** ([`ai_agent/docs/`](ai_agent/docs/))
- [`TECHNICAL_REPORT.md`](ai_agent/docs/TECHNICAL_REPORT.md) — architecture, design rationale, controls, limitations, contributions
- [`The_Transparent_Agent.pdf`](ai_agent/docs/The_Transparent_Agent.pdf) — official presentation deck

---

## 🎯 Key Features Explained

### Smart Enrollment
**Problem**: Students enrolling without enough money, or in full classes.

```sql
IF dbo.fn_CanEnroll(@StudentName, @CourseFee) = 0
    THROW 50005, 'Insufficient balance';
IF enrollment_count > capacity
    ROLLBACK;
-- If both pass: enroll and deduct fee
INSERT INTO Enrollment...
UPDATE StudentAccount SET balance = balance - @CourseFee;
```

Result: only qualified students get enrolled ✅ — and in Phase 2, the AI agent adds prerequisite and duplicate-enrollment checks on top, plus a confirmation step before anything is written.

### Grade Protection
**Problem**: Accidentally changing final grades after semester ends.

```sql
INSERT INTO Grade (gradeStatus) VALUES ('Draft');
EXEC usp_LockGrades @SectionID = 1;
IF gradeStatus = 'Locked'
    THROW 50022, 'Cannot modify locked grade';
```

Result: final grades are protected 🔒

### Teaching Load Management
**Problem**: Instructors getting assigned too many courses.

```sql
INSERT INTO InstructorPolicy (maxCredits) VALUES (12);
IF (@CurrentLoad + @NewCourseCredits) > @MaxLoad
    THROW 60001, 'Teaching load exceeded';
```

Result: balanced workload for all instructors ⚖️

---

## 🍃 MongoDB Integration

We also built this system in **MongoDB** (NoSQL) to compare approaches!

**SQL (what we use):** structured tables with relationships, strong integrity, ACID guarantees — perfect for transactional data.
**MongoDB (for analytics):** flexible documents, embedded data, fast analytics queries — great for reporting.

Explore the playground: [`mongodb/university_management_playground.mongodb.js`](mongodb/university_management_playground.mongodb.js)

---

## 🎓 What We Learned

### Database Design
- How to normalize data properly, when to denormalize for performance
- Importance of foreign keys and constraints

### Business Logic
- Implementing real-world rules in code, transaction management (ACID), error handling

### Security
- Role-based access control, principle of least privilege, why direct table access is dangerous

### AI Agents (Phase 2)
- Why a standalone LLM is not enough: grounding, tool use, and explicit workflow state
- Keeping the LLM out of the facts: classification-only design against hallucination
- Safety engineering: confirmation gates, stopping rules, fallbacks, evaluation, observability

---

## 🛠️ Technical Details

### Technologies Used

**Phase 1 — Database**
- **Database**: SQL Server 2019 · **Language**: T-SQL · **Analytics**: MongoDB + MongoDB Charts

**Phase 2 — AI Agent**
- **Language**: Python 3.11 · **UI**: Streamlit · **Orchestration**: LangGraph
- **LLM (default)**: Ollama `llama3.1` (local/offline, no API key) · **LLM (optional)**: OpenAI / Anthropic
- **Database**: SQLite · **Containerisation**: Docker + Docker Compose · **Version Control**: Git / GitHub

### Design Patterns
- Three-tier architecture · repository pattern (via stored procedures) · trigger-based automation · role-based security
- Phase 2: layered agent architecture, typed tool interfaces, explicit state machine, confirmation-gated actions

### Best Practices Followed
- ✅ Normalized database design · comprehensive constraints · transaction management
- ✅ Error handling · code documentation · security by default
- ✅ Phase 2: input validation on every tool, audit logging, automated evaluation, no hard-coded secrets, non-root container

---

## 🧪 Testing

**Phase 1** — run [`sql/09_test_scripts.sql`](sql/09_test_scripts.sql) to test enrollment, payments, grades, payroll, transcripts, capacity enforcement, and teaching-load validation.

**Phase 2** — the agent ships with an automated evaluation suite ([`ai_agent/tests/eval/`](ai_agent/tests/eval/)):
- **35 scripted conversations** across 34 categories, seeded with 7 students (including Hana Tfaily 😄), 3 instructors, 5 courses, and 4 semesters
- Covers grounded Q&A, all eligibility outcomes, the full confirm/cancel flows, memory across turns, **prompt injection**, **confirmation-bypass attempts**, duplicate actions, and human handoff
- Reports task-completion rate, tool-selection accuracy, fallback accuracy, and unsafe-action count (must be 0)

```bash
cd ai_agent && python -m tests.eval.run_eval
```

---

## 🚧 Future Enhancements

- [x] ~~REST API~~ → implemented as LangGraph tool layer (Phase 2)
- [x] ~~Web dashboard~~ → Streamlit chat UI (Phase 2)
- [x] ~~Advanced analytics~~ → 5 bonus tools: GPA prediction, institution reports, utilization analysis (Phase 2)
- [x] ~~Course prerequisites system~~ → prerequisite chain + eligibility checking (Phase 2)
- [ ] Waitlist functionality
- [ ] Email notifications
- [ ] Degree audit (graduation checker)
- [ ] Mobile app

---

## 📝 Documentation

- [Phase 1 presentation slides](docs/Presentation_Slides.pdf) · [ERD diagram](docs/ERD_diag_UMS.png) · [Use-case diagram](docs/USE_CASE_UMS.png)
- [Phase 2 technical report](ai_agent/docs/TECHNICAL_REPORT.md) · [official presentation](ai_agent/docs/The_Transparent_Agent.pdf)
- 🎥 [Video presentation & live demo](https://drive.google.com/drive/folders/19YgM857kqSZUT-1LRUfBXqsiOPViCGoI?usp=sharing)
- [Project proposal](Project_proposal_document.pdf)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome`)
5. Open a Pull Request

---

## 👥 Authors

* **Maryline Karam** (6599) — *Phase 1*: database design, documentation, MongoDB integration & charts · *Phase 2*: **Tools Engineer** — the 9 typed tools, pydantic validation, domain data (`seed_data.sql`, `policies.json`), database schema additions
* **Aseel Menhem** (6651) — *Phase 1*: SQL implementation (procedures, triggers, views, security) · *Phase 2*: **Agent Engineer** — LangGraph workflow & router, prompts, confirmation gate, fallback & human handoff, stopping rules
* **Hana Tfaily** (6554) — *joined for Phase 2*: **Platform & Interface** — memory layers, Streamlit UI, Docker packaging, trace logging, evaluation suite, demo recording

---

## 🙏 Acknowledgments

- SQL Server documentation · MongoDB documentation · database design best practices
- Our instructor **Dr. Mohamad Aoude**
