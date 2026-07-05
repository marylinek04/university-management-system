"""
Tool 4 - Reporting Tool

    generate_student_report(student_identifier, report_type)

Purpose
    Generate structured, grounded reports for a student.

Input
    student_identifier : student id, full name, or email
    report_type        : "transcript_summary" | "gpa_summary" |
                          "academic_standing" | "recommendations"

Output (formatted report)
    {
      "found": bool,
      "report_type": str,
      "student": {...},
      "data": {...},          # structured data backing the report
      "formatted_text": str   # human-readable rendering for the chat UI
    }
"""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from . import db_helpers as h


class GenerateStudentReportInput(BaseModel):
    student_identifier: str = Field(..., description="Student id, full name, or email.")
    report_type: Literal["transcript_summary", "gpa_summary", "academic_standing", "recommendations"] = Field(
        ..., description="Which report to generate."
    )


def _not_found(report_type: str, student_identifier: str) -> dict:
    return {
        "found": False,
        "report_type": report_type,
        "student": None,
        "data": None,
        "formatted_text": f"No student found matching '{student_identifier}'.",
    }


def _transcript_summary(conn, student) -> dict:
    completed = h.student_completed_courses(conn, student["student_id"])
    gpa = h.compute_gpa(completed)
    total_credits = sum(c["credits"] for c in completed)

    lines = [f"Transcript Summary - {student['first_name']} {student['last_name']} (ID {student['student_id']})", ""]
    if not completed:
        lines.append("No completed courses on record.")
    else:
        for c in completed:
            lines.append(f"  {c['course_code']:<8} {c['course_title']:<28} {c['credits']} cr   Grade: {c['grade_value']}")
        lines.append("")
        lines.append(f"Total credits earned: {total_credits}")
        lines.append(f"Cumulative GPA: {gpa if gpa is not None else 'N/A'}")

    return {
        "found": True,
        "report_type": "transcript_summary",
        "student": {"student_id": student["student_id"], "name": f"{student['first_name']} {student['last_name']}"},
        "data": {"completed_courses": h.rows_to_list(completed), "total_credits": total_credits, "gpa": gpa},
        "formatted_text": "\n".join(lines),
    }


def _gpa_summary(conn, student) -> dict:
    completed = h.student_completed_courses(conn, student["student_id"])
    gpa = h.compute_gpa(completed)
    standing = h.academic_standing(gpa)
    lines = [
        f"GPA Summary - {student['first_name']} {student['last_name']}",
        f"Current GPA: {gpa if gpa is not None else 'N/A'}",
        f"Completed courses: {len(completed)}",
        f"Academic standing: {standing}",
    ]
    return {
        "found": True,
        "report_type": "gpa_summary",
        "student": {"student_id": student["student_id"], "name": f"{student['first_name']} {student['last_name']}"},
        "data": {"gpa": gpa, "completed_courses": len(completed), "academic_standing": standing},
        "formatted_text": "\n".join(lines),
    }


def _academic_standing(conn, student) -> dict:
    completed = h.student_completed_courses(conn, student["student_id"])
    gpa = h.compute_gpa(completed)
    standing = h.academic_standing(gpa)
    policies = h.load_policies()
    rules = policies.get("academic_standing_policy", {}).get("rules", [])
    lines = [
        f"Academic Standing - {student['first_name']} {student['last_name']}",
        f"GPA: {gpa if gpa is not None else 'N/A'}",
        f"Standing: {standing}",
        "",
        "Policy reference:",
    ]
    lines.extend(f"  - {r}" for r in rules)
    return {
        "found": True,
        "report_type": "academic_standing",
        "student": {"student_id": student["student_id"], "name": f"{student['first_name']} {student['last_name']}"},
        "data": {"gpa": gpa, "academic_standing": standing, "policy_rules": rules},
        "formatted_text": "\n".join(lines),
    }


def _recommendations(conn, student) -> dict:
    completed = h.student_completed_courses(conn, student["student_id"])
    completed_codes = {c["course_code"] for c in completed}
    completed_passed = {c["course_code"] for c in completed if c["grade_value"] in h.PASSING_GRADES}
    active = h.student_active_enrollments(conn, student["student_id"])
    active_codes = {a["course_code"] for a in active}

    all_courses = conn.execute("SELECT * FROM courses").fetchall()
    recommended = []
    for course in all_courses:
        code = course["course_code"]
        if code in completed_codes or code in active_codes:
            continue
        prereqs = h.get_prerequisites(conn, course["course_id"])
        missing = [p["course_code"] for p in prereqs if p["course_code"] not in completed_passed]
        if not missing:
            recommended.append({"course_code": code, "course_title": course["course_title"], "credits": course["credits"]})

    gpa = h.compute_gpa(completed)
    lines = [f"Study Recommendations - {student['first_name']} {student['last_name']}", ""]
    if gpa is not None and gpa < 2.0:
        lines.append("Note: GPA is below 2.0 (Academic Probation). Consider prioritizing courses in your "
                      "weakest subjects and meeting with your academic advisor.")
        lines.append("")
    if active:
        lines.append("Currently enrolled (this semester):")
        for a in active:
            lines.append(f"  - {a['course_code']}: {a['course_title']} ({a['semester_name']})")
        lines.append("")
    if recommended:
        lines.append("Courses you are eligible to take next (prerequisites satisfied):")
        for r in recommended:
            lines.append(f"  - {r['course_code']}: {r['course_title']} ({r['credits']} credits)")
    else:
        lines.append("No additional courses are currently eligible based on completed prerequisites.")

    return {
        "found": True,
        "report_type": "recommendations",
        "student": {"student_id": student["student_id"], "name": f"{student['first_name']} {student['last_name']}"},
        "data": {"recommended_courses": recommended, "currently_enrolled": h.rows_to_list(active), "gpa": gpa},
        "formatted_text": "\n".join(lines),
    }


@tool("generate_student_report", args_schema=GenerateStudentReportInput)
def generate_student_report(student_identifier: str, report_type: str) -> dict:
    """Generate a structured report for a student: transcript_summary, gpa_summary,
    academic_standing, or recommendations (study recommendation)."""
    with h.get_connection() as conn:
        student = h.find_student(conn, student_identifier)
        if not student:
            return _not_found(report_type, student_identifier)

        if report_type == "transcript_summary":
            return _transcript_summary(conn, student)
        if report_type == "gpa_summary":
            return _gpa_summary(conn, student)
        if report_type == "academic_standing":
            return _academic_standing(conn, student)
        if report_type == "recommendations":
            return _recommendations(conn, student)

    return {"found": False, "report_type": report_type, "student": None, "data": None,
            "formatted_text": f"Unsupported report_type '{report_type}'."}
