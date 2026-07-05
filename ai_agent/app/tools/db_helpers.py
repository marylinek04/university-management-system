"""
Shared, read-only lookup helpers used by every tool.

Centralizing lookups here keeps the tools grounded: a tool can only return
information that exists in the database (or policies.json), and "not found"
is always an explicit, structured result rather than a guess.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..db.connection import get_connection

POLICIES_PATH = Path(__file__).resolve().parent.parent / "db" / "policies.json"

GRADE_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
PASSING_GRADES = {"A", "B", "C", "D"}


def load_policies() -> dict[str, Any]:
    with open(POLICIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_student(conn: sqlite3.Connection, identifier: str) -> sqlite3.Row | None:
    """Find a student by id, full name, or email (case-insensitive)."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    if identifier.isdigit():
        row = conn.execute("SELECT * FROM students WHERE student_id = ?", (int(identifier),)).fetchone()
        if row:
            return row

    row = conn.execute(
        """
        SELECT * FROM students
        WHERE lower(email) = lower(?)
           OR lower(first_name || ' ' || last_name) = lower(?)
        """,
        (identifier, identifier),
    ).fetchone()
    return row


def find_instructor(conn: sqlite3.Connection, identifier: str) -> sqlite3.Row | None:
    """Find an instructor by id, full name, or email (case-insensitive)."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    if identifier.isdigit():
        row = conn.execute("SELECT * FROM instructors WHERE instructor_id = ?", (int(identifier),)).fetchone()
        if row:
            return row

    row = conn.execute(
        """
        SELECT * FROM instructors
        WHERE lower(email) = lower(?)
           OR lower(full_name) = lower(?)
           OR lower(full_name) LIKE lower(?)
        """,
        (identifier, identifier, f"%{identifier}%"),
    ).fetchone()
    return row


def find_course(conn: sqlite3.Connection, course_code: str) -> sqlite3.Row | None:
    course_code = (course_code or "").strip().upper()
    return conn.execute("SELECT * FROM courses WHERE upper(course_code) = ?", (course_code,)).fetchone()


def find_semester(conn: sqlite3.Connection, semester_name: str | None) -> sqlite3.Row | None:
    if semester_name:
        return conn.execute(
            "SELECT * FROM semesters WHERE lower(semester_name) = lower(?)", (semester_name.strip(),)
        ).fetchone()
    # default to the current semester
    return conn.execute("SELECT * FROM semesters WHERE is_current = 1 LIMIT 1").fetchone()


def find_section(conn: sqlite3.Connection, course_code: str, semester_name: str | None) -> sqlite3.Row | None:
    course = find_course(conn, course_code)
    semester = find_semester(conn, semester_name)
    if not course or not semester:
        return None
    return conn.execute(
        "SELECT * FROM sections WHERE course_id = ? AND semester_id = ?",
        (course["course_id"], semester["semester_id"]),
    ).fetchone()


def get_prerequisites(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.* FROM course_prerequisites cp
        JOIN courses c ON c.course_id = cp.prerequisite_course_id
        WHERE cp.course_id = ?
        """,
        (course_id,),
    ).fetchall()


def section_enrolled_count(conn: sqlite3.Connection, section_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM enrollments WHERE section_id = ? AND enrollment_status = 'ENROLLED'",
        (section_id,),
    ).fetchone()
    return row["n"] if row else 0


def student_completed_courses(conn: sqlite3.Connection, student_id: int) -> list[sqlite3.Row]:
    """All courses a student has COMPLETED, with their grade."""
    return conn.execute(
        """
        SELECT c.course_id, c.course_code, c.course_title, c.credits, g.grade_value
        FROM enrollments e
        JOIN sections sec ON sec.section_id = e.section_id
        JOIN courses c ON c.course_id = sec.course_id
        LEFT JOIN grades g ON g.enrollment_id = e.enrollment_id
        WHERE e.student_id = ? AND e.enrollment_status = 'COMPLETED'
        """,
        (student_id,),
    ).fetchall()


def student_active_enrollments(conn: sqlite3.Connection, student_id: int) -> list[sqlite3.Row]:
    """All sections a student is currently ENROLLED in."""
    return conn.execute(
        """
        SELECT e.enrollment_id, c.course_code, c.course_title, sem.semester_name, sec.section_id
        FROM enrollments e
        JOIN sections sec ON sec.section_id = e.section_id
        JOIN courses c ON c.course_id = sec.course_id
        JOIN semesters sem ON sem.semester_id = sec.semester_id
        WHERE e.student_id = ? AND e.enrollment_status = 'ENROLLED'
        """,
        (student_id,),
    ).fetchall()


def compute_gpa(completed_courses: list[sqlite3.Row]) -> float | None:
    total_points = 0.0
    total_credits = 0
    for row in completed_courses:
        grade = row["grade_value"]
        if grade is None:
            continue
        total_points += GRADE_POINTS.get(grade, 0.0) * row["credits"]
        total_credits += row["credits"]
    if total_credits == 0:
        return None
    return round(total_points / total_credits, 2)


def academic_standing(gpa: float | None) -> str:
    if gpa is None:
        return "No academic standing yet (no completed courses)."
    if gpa >= 3.5:
        return "Dean's List"
    if gpa >= 2.0:
        return "Good Standing"
    return "Academic Probation"


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


__all__ = [
    "get_connection",
    "load_policies",
    "find_student",
    "find_instructor",
    "find_course",
    "find_semester",
    "find_section",
    "get_prerequisites",
    "section_enrolled_count",
    "student_completed_courses",
    "student_active_enrollments",
    "compute_gpa",
    "academic_standing",
    "row_to_dict",
    "rows_to_list",
    "GRADE_POINTS",
    "PASSING_GRADES",
]
