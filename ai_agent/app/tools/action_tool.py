"""
Tool 3 - Action Tool (state-changing, confirmation-gated)

    create_enrollment_request(student_identifier, course_code, semester_name=None, confirm=False)

Purpose
    Create (and, once confirmed, execute) a student enrollment request.

IMPORTANT - confirmation workflow
    1. User asks to enroll.
    2. The orchestration layer calls analyze_enrollment_eligibility (Tool 2).
    3. This tool is called with confirm=False: it re-checks eligibility,
       stores a PENDING_CONFIRMATION row in enrollment_requests, and returns
       that result WITHOUT writing an enrollment record.
    4. The agent asks the user for explicit confirmation.
    5. Only if the user confirms does the orchestration layer call this tool
       again with confirm=True, which re-validates eligibility one more time
       (state may have changed) and, if still eligible:
         - inserts the Enrollment row (status ENROLLED)
         - deducts the course fee from the student's account balance
         - marks the request EXECUTED
       If eligibility now fails, the request is marked REJECTED and no
       enrollment is created.

Output
    {
      "status": "pending_confirmation" | "executed" | "rejected" | "error",
      "eligible": true/false,
      "reasons": [...],
      "request_id": int | null,
      "enrollment_id": int | null,
      "new_balance": float | null,
      "message": "..."
    }
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from . import db_helpers as h
from .analysis_tool import evaluate_eligibility


class CreateEnrollmentRequestInput(BaseModel):
    student_identifier: str = Field(..., description="Student id, full name, or email.")
    course_code: str = Field(..., description="Course code, e.g. 'CE410'.")
    semester_name: Optional[str] = Field(
        None, description="Semester name, e.g. 'Spring 2026'. Defaults to the current semester."
    )
    confirm: bool = Field(
        False,
        description=(
            "Must be False the first time this tool is called for a request. "
            "Only set to True after the user has explicitly confirmed the enrollment."
        ),
    )


@tool("create_enrollment_request", args_schema=CreateEnrollmentRequestInput)
def create_enrollment_request(
    student_identifier: str, course_code: str, semester_name: Optional[str] = None, confirm: bool = False
) -> dict:
    """Create (confirm=False) or execute (confirm=True) a student enrollment request.
    Always re-validates eligibility. Only writes an Enrollment record and deducts the
    course fee when confirm=True and the student is still eligible."""

    with h.get_connection() as conn:
        eligibility = evaluate_eligibility(conn, student_identifier, course_code, semester_name)
        details = eligibility["details"]

        student_info = details.get("student")
        if not student_info:
            return {
                "status": "error",
                "eligible": False,
                "reasons": eligibility["reasons"],
                "request_id": None,
                "enrollment_id": None,
                "new_balance": None,
                "message": eligibility["reasons"][0] if eligibility["reasons"] else "Student not found.",
            }

        student_id = student_info["student_id"]
        resolved_semester = details.get("semester") or (semester_name or "current semester")
        eligibility_json = json.dumps(eligibility, default=str)

        if not confirm:
            cur = conn.execute(
                """
                INSERT INTO enrollment_requests (student_id, course_code, semester_name, status, eligibility_json)
                VALUES (?, ?, ?, 'PENDING_CONFIRMATION', ?)
                """,
                (student_id, course_code.strip().upper(), resolved_semester, eligibility_json),
            )
            request_id = cur.lastrowid
            if eligibility["eligible"]:
                message = (
                    f"{student_info['name']} is eligible to enroll in {course_code.upper()} "
                    f"for {resolved_semester}. Please confirm to proceed."
                )
            else:
                message = (
                    f"{student_info['name']} is NOT currently eligible to enroll in {course_code.upper()} "
                    f"for {resolved_semester}: " + "; ".join(eligibility["reasons"])
                )
            return {
                "status": "pending_confirmation",
                "eligible": eligibility["eligible"],
                "reasons": eligibility["reasons"],
                "request_id": request_id,
                "enrollment_id": None,
                "new_balance": None,
                "message": message,
            }

        # confirm == True: execute (or reject) the request
        if not eligibility["eligible"]:
            cur = conn.execute(
                """
                INSERT INTO enrollment_requests (student_id, course_code, semester_name, status, eligibility_json, decided_at)
                VALUES (?, ?, ?, 'REJECTED', ?, datetime('now'))
                """,
                (student_id, course_code.strip().upper(), resolved_semester, eligibility_json),
            )
            return {
                "status": "rejected",
                "eligible": False,
                "reasons": eligibility["reasons"],
                "request_id": cur.lastrowid,
                "enrollment_id": None,
                "new_balance": None,
                "message": (
                    f"Enrollment for {student_info['name']} in {course_code.upper()} ({resolved_semester}) "
                    f"was rejected: " + "; ".join(eligibility["reasons"])
                ),
            }

        # Eligible and confirmed -> execute
        course = h.find_course(conn, course_code)
        semester = h.find_semester(conn, semester_name)
        section = conn.execute(
            "SELECT * FROM sections WHERE course_id = ? AND semester_id = ?",
            (course["course_id"], semester["semester_id"]),
        ).fetchone()

        cur = conn.execute(
            "INSERT INTO enrollments (student_id, section_id, enrollment_status) VALUES (?, ?, 'ENROLLED')",
            (student_id, section["section_id"]),
        )
        enrollment_id = cur.lastrowid

        conn.execute(
            "UPDATE student_accounts SET balance = balance - ? WHERE student_id = ?",
            (course["course_fee"], student_id),
        )
        new_balance_row = conn.execute("SELECT balance FROM student_accounts WHERE student_id = ?", (student_id,)).fetchone()
        new_balance = new_balance_row["balance"] if new_balance_row else None

        cur2 = conn.execute(
            """
            INSERT INTO enrollment_requests (student_id, course_code, semester_name, status, eligibility_json, decided_at)
            VALUES (?, ?, ?, 'EXECUTED', ?, datetime('now'))
            """,
            (student_id, course_code.strip().upper(), resolved_semester, eligibility_json),
        )

        return {
            "status": "executed",
            "eligible": True,
            "reasons": [],
            "request_id": cur2.lastrowid,
            "enrollment_id": enrollment_id,
            "new_balance": new_balance,
            "message": (
                f"{student_info['name']} has been enrolled in {course['course_code']} "
                f"({resolved_semester}). Fee of {course['course_fee']:.2f} deducted; "
                f"new balance is {new_balance:.2f}."
            ),
        }
