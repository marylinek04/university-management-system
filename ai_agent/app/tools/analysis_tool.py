"""
Tool 2 - Analysis Tool

    analyze_enrollment_eligibility(student_identifier, course_code, semester_name=None)

Purpose
    Determine whether a student can enroll in a given course/section.

Checks performed (all grounded in the database)
    - student exists
    - course / section exists for the requested semester (defaults to the
      current semester if not given)
    - the student is not already enrolled in that section (duplicate check)
    - the section has available capacity
    - the student has completed all prerequisite courses with a passing grade
    - the student's account balance covers the course fee

Output
    {
      "eligible": true/false,
      "reasons": [ ... ],   # human-readable reasons for ANY failed check
      "details": { ... }    # supporting data (balances, capacity, prereqs, etc.)
    }
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from . import db_helpers as h


class EnrollmentEligibilityInput(BaseModel):
    student_identifier: str = Field(..., description="Student id, full name, or email.")
    course_code: str = Field(..., description="Course code, e.g. 'CE410'.")
    semester_name: Optional[str] = Field(
        None, description="Semester name, e.g. 'Spring 2026'. Defaults to the current semester."
    )


def evaluate_eligibility(conn: sqlite3.Connection, student_identifier: str, course_code: str, semester_name: Optional[str]) -> dict:
    """Framework-agnostic eligibility evaluation, reusable by the action tool."""
    reasons: list[str] = []
    details: dict = {}

    student = h.find_student(conn, student_identifier)
    if not student:
        return {"eligible": False, "reasons": [f"No student found matching '{student_identifier}'."], "details": {}}
    details["student"] = {"student_id": student["student_id"], "name": f"{student['first_name']} {student['last_name']}"}

    course = h.find_course(conn, course_code)
    if not course:
        return {"eligible": False, "reasons": [f"No course found with code '{course_code}'."], "details": details}
    details["course"] = {"course_code": course["course_code"], "course_title": course["course_title"], "fee": course["course_fee"]}

    semester = h.find_semester(conn, semester_name)
    if not semester:
        msg = f"No semester found matching '{semester_name}'." if semester_name else "No current semester is configured."
        return {"eligible": False, "reasons": [msg], "details": details}
    details["semester"] = semester["semester_name"]

    section = conn.execute(
        "SELECT * FROM sections WHERE course_id = ? AND semester_id = ?",
        (course["course_id"], semester["semester_id"]),
    ).fetchone()
    if not section:
        return {"eligible": False,
                "reasons": [f"{course['course_code']} is not offered in {semester['semester_name']}."],
                "details": details}

    # 1. Duplicate enrollment check
    existing = conn.execute(
        "SELECT * FROM enrollments WHERE student_id = ? AND section_id = ? AND enrollment_status = 'ENROLLED'",
        (student["student_id"], section["section_id"]),
    ).fetchone()
    if existing:
        reasons.append(f"Student is already enrolled in {course['course_code']} for {semester['semester_name']}.")

    # 2. Capacity check
    enrolled = h.section_enrolled_count(conn, section["section_id"])
    seats_available = section["capacity"] - enrolled
    details["capacity"] = {"capacity": section["capacity"], "enrolled": enrolled, "seats_available": seats_available}
    if seats_available <= 0:
        reasons.append(f"Section for {course['course_code']} in {semester['semester_name']} is full "
                        f"({enrolled}/{section['capacity']}).")

    # 3. Prerequisite check
    prereqs = h.get_prerequisites(conn, course["course_id"])
    if prereqs:
        completed = h.student_completed_courses(conn, student["student_id"])
        completed_passed = {c["course_code"] for c in completed if c["grade_value"] in h.PASSING_GRADES}
        missing = [p["course_code"] for p in prereqs if p["course_code"] not in completed_passed]
        details["prerequisites"] = {"required": [p["course_code"] for p in prereqs], "missing": missing}
        if missing:
            reasons.append(f"Missing prerequisite(s): {', '.join(missing)}.")
    else:
        details["prerequisites"] = {"required": [], "missing": []}

    # 4. Balance check
    account = conn.execute("SELECT balance FROM student_accounts WHERE student_id = ?", (student["student_id"],)).fetchone()
    balance = account["balance"] if account else 0.0
    details["balance"] = {"current_balance": balance, "course_fee": course["course_fee"], "sufficient": balance >= course["course_fee"]}
    if balance < course["course_fee"]:
        reasons.append(
            f"Insufficient balance: current balance is {balance:.2f}, course fee is {course['course_fee']:.2f}."
        )

    return {"eligible": len(reasons) == 0, "reasons": reasons, "details": details}


@tool("analyze_enrollment_eligibility", args_schema=EnrollmentEligibilityInput)
def analyze_enrollment_eligibility(student_identifier: str, course_code: str, semester_name: Optional[str] = None) -> dict:
    """Analyze whether a student is eligible to enroll in a course/section: checks
    balance sufficiency, section capacity, duplicate enrollment, and prerequisite completion."""
    with h.get_connection() as conn:
        return evaluate_eligibility(conn, student_identifier, course_code, semester_name)
