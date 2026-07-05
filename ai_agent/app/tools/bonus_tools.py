"""
Optional bonus tools (implemented as time allowed):

  - predict_future_gpa(student_identifier, planned_courses)
  - generate_study_plan(student_identifier, max_credits_per_semester=15)
  - generate_payroll_report(instructor_identifier, period_start=None, period_end=None)
  - analyze_section_utilization(semester_name=None)

Plus one additional value-add reporting tool for Finance/Registrar staff:

  - generate_institution_report(report_type, semester_name=None, period_start=None, period_end=None)

All follow the same conventions as the four required tools: typed
pydantic input schemas, structured dict outputs, and validation against the
SQLite database / policy file (no hallucinated data).
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from . import db_helpers as h

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# =====================================================================
# GPA Prediction Tool
# =====================================================================
class PlannedCourse(BaseModel):
    course_code: str = Field(..., description="Course code, e.g. 'CE410'.")
    expected_grade: Literal["A", "B", "C", "D", "F"] = Field(..., description="Hypothetical grade for this course.")


class PredictFutureGPAInput(BaseModel):
    student_identifier: str = Field(..., description="Student id, full name, or email.")
    planned_courses: list[PlannedCourse] = Field(
        ..., description="Courses the student plans to take with a hypothetical grade for each, e.g. "
                          "[{'course_code': 'CE410', 'expected_grade': 'A'}]"
    )


@tool("predict_future_gpa", args_schema=PredictFutureGPAInput)
def predict_future_gpa(student_identifier: str, planned_courses: list[dict]) -> dict:
    """Predict a student's cumulative GPA if they earn the given hypothetical
    grades in the given planned courses, combined with their current completed coursework."""
    with h.get_connection() as conn:
        student = h.find_student(conn, student_identifier)
        if not student:
            return {"found": False, "message": f"No student found matching '{student_identifier}'.",
                    "current_gpa": None, "predicted_gpa": None, "details": {}}

        completed = h.student_completed_courses(conn, student["student_id"])
        current_points = sum(h.GRADE_POINTS.get(c["grade_value"], 0.0) * c["credits"] for c in completed)
        current_credits = sum(c["credits"] for c in completed)
        current_gpa = h.compute_gpa(completed)

        added_points = 0.0
        added_credits = 0
        breakdown = []
        unknown_courses = []
        for planned in planned_courses:
            code = planned["course_code"] if isinstance(planned, dict) else planned.course_code
            grade = planned["expected_grade"] if isinstance(planned, dict) else planned.expected_grade
            course = h.find_course(conn, code)
            if not course:
                unknown_courses.append(code)
                continue
            points = h.GRADE_POINTS.get(grade, 0.0) * course["credits"]
            added_points += points
            added_credits += course["credits"]
            breakdown.append({"course_code": course["course_code"], "credits": course["credits"], "expected_grade": grade})

        total_credits = current_credits + added_credits
        predicted_gpa = round((current_points + added_points) / total_credits, 2) if total_credits > 0 else None

        message = "Predicted GPA computed from current transcript plus planned courses."
        if unknown_courses:
            message += f" Ignored unknown course code(s): {', '.join(unknown_courses)}."

        lines = [
            f"GPA Prediction - {student['first_name']} {student['last_name']}",
            f"Current GPA: {current_gpa if current_gpa is not None else 'N/A'} ({current_credits} credits completed)",
        ]
        if breakdown:
            lines.append("Planned courses:")
            for b in breakdown:
                lines.append(f"  - {b['course_code']} ({b['credits']} cr): expected grade {b['expected_grade']}")
        lines.append(f"Predicted cumulative GPA: {predicted_gpa if predicted_gpa is not None else 'N/A'} "
                      f"({total_credits} total credits)")
        if unknown_courses:
            lines.append(f"Ignored unknown course code(s): {', '.join(unknown_courses)}.")

        return {
            "found": True,
            "message": message,
            "current_gpa": current_gpa,
            "predicted_gpa": predicted_gpa,
            "formatted_text": "\n".join(lines),
            "details": {
                "current_credits": current_credits,
                "added_credits": added_credits,
                "planned_courses": breakdown,
                "unknown_courses": unknown_courses,
            },
        }


# =====================================================================
# Study Plan Tool
# =====================================================================
class GenerateStudyPlanInput(BaseModel):
    student_identifier: str = Field(..., description="Student id, full name, or email.")
    max_credits_per_semester: int = Field(15, ge=1, le=30, description="Maximum credit load per planned semester.")


@tool("generate_study_plan", args_schema=GenerateStudyPlanInput)
def generate_study_plan(student_identifier: str, max_credits_per_semester: int = 15) -> dict:
    """Generate a multi-semester study plan: groups courses the student is
    currently eligible for (and courses that become eligible afterward) into
    semester-sized buckets based on prerequisites and a credit-load cap."""
    with h.get_connection() as conn:
        student = h.find_student(conn, student_identifier)
        if not student:
            return {"found": False, "message": f"No student found matching '{student_identifier}'.", "plan": []}

        completed = h.student_completed_courses(conn, student["student_id"])
        completed_passed = {c["course_code"] for c in completed if c["grade_value"] in h.PASSING_GRADES}
        active = h.student_active_enrollments(conn, student["student_id"])
        taken_or_active = {c["course_code"] for c in completed} | {a["course_code"] for a in active}

        all_courses = {c["course_code"]: c for c in conn.execute("SELECT * FROM courses").fetchall()}
        prereq_map = {
            code: [p["course_code"] for p in h.get_prerequisites(conn, course["course_id"])]
            for code, course in all_courses.items()
        }

        remaining = {code for code in all_courses if code not in taken_or_active}
        satisfied = set(completed_passed)

        plan = []
        semester_num = 1
        while remaining and semester_num <= 8:  # safety bound
            eligible_now = sorted(
                code for code in remaining
                if all(p in satisfied for p in prereq_map.get(code, []))
            )
            if not eligible_now:
                break  # remaining courses are blocked by prerequisites not on this plan

            bucket = []
            credits_used = 0
            for code in eligible_now:
                credits = all_courses[code]["credits"]
                if credits_used + credits > max_credits_per_semester and bucket:
                    continue
                bucket.append({"course_code": code, "course_title": all_courses[code]["course_title"], "credits": credits})
                credits_used += credits
                remaining.discard(code)
                satisfied.add(code)
                if credits_used >= max_credits_per_semester:
                    break

            if not bucket:
                break

            plan.append({"semester": semester_num, "courses": bucket, "total_credits": credits_used})
            semester_num += 1

        unscheduled = sorted(remaining)

        lines = [f"Study Plan - {student['first_name']} {student['last_name']} "
                 f"(max {max_credits_per_semester} credits/semester)", ""]
        if not plan:
            lines.append("No eligible courses to schedule based on completed prerequisites.")
        for sem in plan:
            lines.append(f"Semester {sem['semester']} ({sem['total_credits']} credits):")
            for c in sem["courses"]:
                lines.append(f"  - {c['course_code']}: {c['course_title']} ({c['credits']} cr)")
        if unscheduled:
            lines.append("")
            lines.append(f"Not yet schedulable (prerequisites not met by this plan): {', '.join(unscheduled)}")

        return {
            "found": True,
            "message": "Study plan generated from prerequisite chains and completed coursework.",
            "plan": plan,
            "unscheduled_courses": unscheduled,
            "formatted_text": "\n".join(lines),
        }


# =====================================================================
# Instructor Payroll Tool
# =====================================================================
class GeneratePayrollReportInput(BaseModel):
    instructor_identifier: str = Field(..., description="Instructor id, full name, or email.")
    period_start: Optional[str] = Field(None, description="Optional start date 'YYYY-MM-DD'.")
    period_end: Optional[str] = Field(None, description="Optional end date 'YYYY-MM-DD'.")

    @field_validator("period_start", "period_end")
    @classmethod
    def _validate_date(cls, v):
        if v is not None and not DATE_RE.match(v):
            raise ValueError("Dates must be in 'YYYY-MM-DD' format.")
        return v


@tool("generate_payroll_report", args_schema=GeneratePayrollReportInput)
def generate_payroll_report(instructor_identifier: str, period_start: Optional[str] = None, period_end: Optional[str] = None) -> dict:
    """Generate a payroll report for an instructor: sums APPROVED time entries
    (optionally within a date range) and multiplies by the instructor's hourly rate."""
    with h.get_connection() as conn:
        instr = h.find_instructor(conn, instructor_identifier)
        if not instr:
            return {"found": False, "message": f"No instructor found matching '{instructor_identifier}'.", "data": None}

        salary = conn.execute("SELECT * FROM instructor_salaries WHERE instructor_id = ?", (instr["instructor_id"],)).fetchone()
        if not salary:
            return {"found": False, "message": f"No salary record on file for {instr['full_name']}.", "data": None}

        query = """
            SELECT te.*, c.course_code, sem.semester_name
            FROM instructor_time_entries te
            JOIN sections sec ON sec.section_id = te.section_id
            JOIN courses c ON c.course_id = sec.course_id
            JOIN semesters sem ON sem.semester_id = sec.semester_id
            WHERE te.instructor_id = ? AND te.approved = 1
        """
        params: list = [instr["instructor_id"]]
        if period_start:
            query += " AND te.entry_date >= ?"
            params.append(period_start)
        if period_end:
            query += " AND te.entry_date <= ?"
            params.append(period_end)

        entries = conn.execute(query, params).fetchall()
        total_hours = sum(e["hours_worked"] for e in entries)
        amount = round(total_hours * salary["hourly_rate"], 2)

        breakdown: dict[str, dict] = {}
        for e in entries:
            key = e["course_code"]
            b = breakdown.setdefault(key, {"course_code": key, "hours": 0.0})
            b["hours"] += e["hours_worked"]

        lines = [
            f"Payroll Report - {instr['full_name']}",
            f"Period: {period_start or 'all time'} to {period_end or 'all time'}",
            f"Hourly rate: {salary['hourly_rate']:.2f}",
            f"Total approved hours: {total_hours:.2f}",
            f"Amount due: {amount:.2f}",
        ]
        if breakdown:
            lines.append("Breakdown by course:")
            for b in breakdown.values():
                lines.append(f"  - {b['course_code']}: {b['hours']:.2f} hrs")

        return {
            "found": True,
            "message": "Payroll report generated from approved time entries.",
            "data": {
                "instructor": instr["full_name"],
                "hourly_rate": salary["hourly_rate"],
                "total_hours": total_hours,
                "amount_due": amount,
                "breakdown": list(breakdown.values()),
                "formatted_text": "\n".join(lines),
            },
        }


# =====================================================================
# Section Capacity / Utilization Tool
# =====================================================================
class AnalyzeSectionUtilizationInput(BaseModel):
    semester_name: Optional[str] = Field(None, description="Semester name. Defaults to the current semester.")


@tool("analyze_section_utilization", args_schema=AnalyzeSectionUtilizationInput)
def analyze_section_utilization(semester_name: Optional[str] = None) -> dict:
    """Analyze enrollment vs. capacity for every section in a semester (default:
    current semester) and classify each as Full, Optimal, or Underutilized
    per the section_utilization_policy."""
    with h.get_connection() as conn:
        semester = h.find_semester(conn, semester_name)
        if not semester:
            msg = f"No semester found matching '{semester_name}'." if semester_name else "No current semester is configured."
            return {"found": False, "message": msg, "sections": []}

        rows = conn.execute(
            """
            SELECT sec.section_id, c.course_code, c.course_title, sec.capacity, i.full_name AS instructor_name
            FROM sections sec
            JOIN courses c ON c.course_id = sec.course_id
            JOIN instructors i ON i.instructor_id = sec.instructor_id
            WHERE sec.semester_id = ?
            ORDER BY c.course_code
            """,
            (semester["semester_id"],),
        ).fetchall()

        sections = []
        for row in rows:
            enrolled = h.section_enrolled_count(conn, row["section_id"])
            capacity = row["capacity"]
            ratio = enrolled / capacity if capacity else 0
            if enrolled >= capacity:
                status = "Full"
            elif ratio < 0.4:
                status = "Underutilized"
            else:
                status = "Optimal"
            sections.append({
                "section_id": row["section_id"],
                "course_code": row["course_code"],
                "course_title": row["course_title"],
                "instructor_name": row["instructor_name"],
                "capacity": capacity,
                "enrolled": enrolled,
                "utilization_pct": round(ratio * 100, 1),
                "status": status,
            })

        lines = [f"Section Utilization - {semester['semester_name']}", ""]
        for s in sections:
            lines.append(
                f"  {s['course_code']:<8} {s['course_title']:<26} "
                f"{s['enrolled']}/{s['capacity']} ({s['utilization_pct']}%) - {s['status']}  "
                f"[{s['instructor_name']}]"
            )
        full = [s["course_code"] for s in sections if s["status"] == "Full"]
        under = [s["course_code"] for s in sections if s["status"] == "Underutilized"]
        lines.append("")
        lines.append(f"Full sections: {', '.join(full) if full else 'none'}")
        lines.append(f"Underutilized sections: {', '.join(under) if under else 'none'}")

        return {
            "found": True,
            "message": f"Section utilization for {semester['semester_name']}.",
            "semester_name": semester["semester_name"],
            "sections": sections,
            "formatted_text": "\n".join(lines),
        }


# =====================================================================
# Institution-wide Reporting Tool (Finance Officer / Registrar)
# =====================================================================
LOW_BALANCE_THRESHOLD = 1000.0


class GenerateInstitutionReportInput(BaseModel):
    report_type: Literal["tuition_summary", "payroll_summary", "enrollment_overview"] = Field(
        ..., description="Which institution-wide report to generate."
    )
    semester_name: Optional[str] = Field(None, description="Used by 'enrollment_overview'. Defaults to current semester.")
    period_start: Optional[str] = Field(None, description="Used by 'payroll_summary'. 'YYYY-MM-DD'.")
    period_end: Optional[str] = Field(None, description="Used by 'payroll_summary'. 'YYYY-MM-DD'.")

    @field_validator("period_start", "period_end")
    @classmethod
    def _validate_date(cls, v):
        if v is not None and not DATE_RE.match(v):
            raise ValueError("Dates must be in 'YYYY-MM-DD' format.")
        return v


@tool("generate_institution_report", args_schema=GenerateInstitutionReportInput)
def generate_institution_report(
    report_type: str,
    semester_name: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> dict:
    """Generate an institution-wide report for Registrar/Finance staff:
    tuition_summary (student account balances, flags low-balance students),
    payroll_summary (approved payroll across all instructors), or
    enrollment_overview (per-section enrollment for a semester)."""
    with h.get_connection() as conn:
        if report_type == "tuition_summary":
            rows = conn.execute(
                """
                SELECT s.student_id, s.first_name, s.last_name, a.balance
                FROM student_accounts a
                JOIN students s ON s.student_id = a.student_id
                ORDER BY a.balance ASC
                """
            ).fetchall()
            students = []
            total_balance = 0.0
            low_balance_students = []
            for r in rows:
                d = dict(r)
                d["name"] = f"{r['first_name']} {r['last_name']}"
                d["low_balance"] = r["balance"] < LOW_BALANCE_THRESHOLD
                total_balance += r["balance"]
                students.append(d)
                if d["low_balance"]:
                    low_balance_students.append(d["name"])

            lines = [
                "Tuition / Account Balance Summary",
                f"Low-balance threshold: {LOW_BALANCE_THRESHOLD:.2f}",
                "",
            ]
            for d in students:
                flag = " (LOW BALANCE)" if d["low_balance"] else ""
                lines.append(f"  {d['name']:<20} balance: {d['balance']:.2f}{flag}")
            lines.append("")
            lines.append(f"Total balance across all student accounts: {total_balance:.2f}")
            if low_balance_students:
                lines.append(f"Students below the low-balance threshold: {', '.join(low_balance_students)}")

            return {
                "found": True,
                "message": "Tuition summary generated from student_accounts.",
                "data": {
                    "students": students,
                    "total_balance": round(total_balance, 2),
                    "low_balance_threshold": LOW_BALANCE_THRESHOLD,
                    "low_balance_students": low_balance_students,
                    "formatted_text": "\n".join(lines),
                },
            }

        if report_type == "payroll_summary":
            instructors = conn.execute("SELECT * FROM instructors ORDER BY full_name").fetchall()
            rows_out = []
            grand_total = 0.0
            for instr in instructors:
                result = generate_payroll_report.invoke({
                    "instructor_identifier": str(instr["instructor_id"]),
                    "period_start": period_start,
                    "period_end": period_end,
                })
                if result.get("found"):
                    data = result["data"]
                    rows_out.append({"instructor": data["instructor"], "total_hours": data["total_hours"], "amount_due": data["amount_due"]})
                    grand_total += data["amount_due"]

            lines = [
                "Payroll Summary",
                f"Period: {period_start or 'all time'} to {period_end or 'all time'}",
                "",
            ]
            for r in rows_out:
                lines.append(f"  {r['instructor']:<20} {r['total_hours']:.2f} hrs   {r['amount_due']:.2f}")
            lines.append("")
            lines.append(f"Grand total payroll: {grand_total:.2f}")

            return {
                "found": True,
                "message": "Payroll summary generated from approved time entries.",
                "data": {"instructors": rows_out, "grand_total": round(grand_total, 2), "formatted_text": "\n".join(lines)},
            }

        if report_type == "enrollment_overview":
            util = analyze_section_utilization.invoke({"semester_name": semester_name})
            if not util.get("found"):
                return {"found": False, "message": util.get("message"), "data": None}
            sections = util["sections"]
            total_enrolled = sum(s["enrolled"] for s in sections)
            total_capacity = sum(s["capacity"] for s in sections)
            full_sections = [s["course_code"] for s in sections if s["status"] == "Full"]
            underutilized = [s["course_code"] for s in sections if s["status"] == "Underutilized"]

            lines = [
                f"Enrollment Overview - {util['semester_name']}",
                f"Total enrolled: {total_enrolled} / {total_capacity} seats",
            ]
            if full_sections:
                lines.append(f"Full sections: {', '.join(full_sections)}")
            if underutilized:
                lines.append(f"Underutilized sections: {', '.join(underutilized)}")

            return {
                "found": True,
                "message": "Enrollment overview generated.",
                "data": {
                    "semester_name": util["semester_name"],
                    "total_enrolled": total_enrolled,
                    "total_capacity": total_capacity,
                    "full_sections": full_sections,
                    "underutilized_sections": underutilized,
                    "sections": sections,
                    "formatted_text": "\n".join(lines),
                },
            }

    return {"found": False, "message": f"Unsupported report_type '{report_type}'.", "data": None}
