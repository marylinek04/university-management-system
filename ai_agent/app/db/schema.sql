-- =====================================================================
-- University Operations AI Agent - SQLite Schema
-- Derived from the SQL Server schema of the University Management
-- System (sql/02_tables.sql). Simplified for an AI-agent demo:
--   - keeps the entities the agent needs (students, instructors,
--     courses, sections, enrollments, payments, grades, etc.)
--   - adds course_prerequisites (new) so analyze_enrollment_eligibility
--     can check prerequisite completion
--   - adds enrollment_requests (new) to back create_enrollment_request
--   - adds agent_logs and user_preferences for the agent's
--     logging / long-term-memory layers
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------
-- Security
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id        INTEGER NOT NULL,
    username       TEXT NOT NULL UNIQUE,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    full_name      TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- ---------------------------------------------------------------
-- Academic
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    department_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name  TEXT NOT NULL UNIQUE,
    faculty_name      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS programs (
    program_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    program_name   TEXT NOT NULL,
    degree_level   TEXT NOT NULL CHECK (degree_level IN ('Bachelor','Master','PhD')),
    department_id  INTEGER NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS students (
    student_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL UNIQUE,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    status         TEXT NOT NULL CHECK (status IN ('Active','Graduated','Suspended')) DEFAULT 'Active',
    gpa            REAL,
    program_id     INTEGER NOT NULL,
    FOREIGN KEY (program_id) REFERENCES programs(program_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS instructors (
    instructor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    department_id   INTEGER NOT NULL,
    max_credits     INTEGER NOT NULL DEFAULT 12,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS courses (
    course_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code    TEXT NOT NULL UNIQUE,
    course_title   TEXT NOT NULL,
    credits        INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 6),
    course_fee     REAL NOT NULL DEFAULT 0,
    department_id  INTEGER NOT NULL,
    description    TEXT,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- NEW: explicit prerequisite graph (course -> required prerequisite course)
CREATE TABLE IF NOT EXISTS course_prerequisites (
    course_id               INTEGER NOT NULL,
    prerequisite_course_id  INTEGER NOT NULL,
    PRIMARY KEY (course_id, prerequisite_course_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (prerequisite_course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS semesters (
    semester_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_name  TEXT NOT NULL UNIQUE,
    start_date     TEXT NOT NULL,
    end_date       TEXT NOT NULL,
    is_current     INTEGER NOT NULL DEFAULT 0,
    CHECK (end_date > start_date)
);

CREATE TABLE IF NOT EXISTS sections (
    section_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id      INTEGER NOT NULL,
    semester_id    INTEGER NOT NULL,
    instructor_id  INTEGER NOT NULL,
    capacity       INTEGER NOT NULL CHECK (capacity > 0),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (semester_id) REFERENCES semesters(semester_id),
    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL,
    section_id        INTEGER NOT NULL,
    enrollment_date   TEXT NOT NULL DEFAULT (date('now')),
    enrollment_status TEXT NOT NULL DEFAULT 'ENROLLED' CHECK (enrollment_status IN ('ENROLLED','DROPPED','COMPLETED')),
    UNIQUE (student_id, section_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES sections(section_id)
);

CREATE TABLE IF NOT EXISTS grades (
    grade_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL UNIQUE,
    grade_value   TEXT CHECK (grade_value IN ('A','B','C','D','F')),
    grade_status  TEXT NOT NULL DEFAULT 'Draft' CHECK (grade_status IN ('Draft','Locked')),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
);

-- ---------------------------------------------------------------
-- Financial
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_accounts (
    student_id  INTEGER PRIMARY KEY,
    balance     REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS student_payments (
    payment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL,
    amount        REAL NOT NULL,
    payment_date  TEXT NOT NULL DEFAULT (datetime('now')),
    description   TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS instructor_salaries (
    instructor_id  INTEGER PRIMARY KEY,
    hourly_rate    REAL NOT NULL,
    bank_account   TEXT,
    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id)
);

CREATE TABLE IF NOT EXISTS instructor_time_entries (
    entry_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id  INTEGER NOT NULL,
    section_id     INTEGER NOT NULL,
    entry_date     TEXT NOT NULL,
    hours_worked   REAL NOT NULL CHECK (hours_worked > 0),
    approved       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id),
    FOREIGN KEY (section_id) REFERENCES sections(section_id)
);

CREATE TABLE IF NOT EXISTS salary_payments (
    payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id  INTEGER NOT NULL,
    period_start   TEXT NOT NULL,
    period_end     TEXT NOT NULL,
    total_hours    REAL NOT NULL,
    amount_paid    REAL NOT NULL,
    paid_on        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id)
);

-- ---------------------------------------------------------------
-- NEW: Agent-facing tables
-- ---------------------------------------------------------------

-- Enrollment requests created by create_enrollment_request().
-- A request starts as PENDING_CONFIRMATION, then becomes
-- CONFIRMED / EXECUTED / REJECTED / CANCELLED.
CREATE TABLE IF NOT EXISTS enrollment_requests (
    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,
    course_code     TEXT NOT NULL,
    semester_name   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING_CONFIRMATION'
                    CHECK (status IN ('PENDING_CONFIRMATION','EXECUTED','REJECTED','CANCELLED')),
    eligibility_json TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at      TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- Structured agent activity / audit log
CREATE TABLE IF NOT EXISTS agent_logs (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL DEFAULT (datetime('now')),
    session_id          TEXT,
    user_role           TEXT,
    user_name           TEXT,
    intent              TEXT,
    workflow_state      TEXT,
    tool_name           TEXT,
    tool_input          TEXT,
    tool_result         TEXT,
    validation_failure  TEXT,
    fallback            INTEGER NOT NULL DEFAULT 0,
    error               TEXT
);

-- Long-term memory: per-user preferences across sessions (bonus)
CREATE TABLE IF NOT EXISTS user_preferences (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name         TEXT NOT NULL,
    preference_key    TEXT NOT NULL,
    preference_value  TEXT NOT NULL,
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_name, preference_key)
);

-- ---------------------------------------------------------------
-- Helpful indexes
-- ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_section ON enrollments(section_id);
CREATE INDEX IF NOT EXISTS idx_sections_course ON sections(course_id);
CREATE INDEX IF NOT EXISTS idx_sections_semester ON sections(semester_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_session ON agent_logs(session_id);
