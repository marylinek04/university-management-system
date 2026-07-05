"""
Tool 1 - Information Tool

    get_university_information(query_type, identifier=None, semester_name=None)

Purpose
    Retrieve grounded information: course details, tuition fees, policies,
    enrollment rules, instructor information, programs, departments, and
    section/capacity information.

Input (structured query)
    query_type    : one of "course", "policy", "instructor", "program",
                    "department", "section", "semester"
    identifier    : optional name/code/id to look up (course code, instructor
                    name, policy key, program name, department name)
    semester_name : optional, used with query_type="section"

Output (structured response)
    {
      "found": bool,
      "query_type": str,
      "data": ... ,        # dict or list[dict] - only ever real DB/policy data
      "message": str
    }

No hallucinated information: every field returned comes directly from the
SQLite database (app/db/schema.sql) or the structured policy file
(app/db/policies.json). If nothing matches, ``found`` is False and ``data``
is empty - the agent must not invent a value.
"""

from __future__ import annotations

from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from . import db_helpers as h


class InformationQueryInput(BaseModel):
    query_type: Literal["course", "policy", "instructor", "program", "department", "section", "semester"] = Field(
        ..., description="The category of grounded information to retrieve."
    )
    identifier: Optional[str] = Field(
        None,
        description=(
            "Name/code/id to look up, depending on query_type: course code (e.g. 'CE410'), "
            "instructor name, policy key (e.g. 'enrollment_policy'), program name, "
            "department name, or semester name. Omit to list all items of that type."
        ),
    )
    semester_name: Optional[str] = Field(
        None, description="Required with query_type='section': the semester to look up the section in."
    )


def _list_courses(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM courses ORDER BY course_code").fetchall()
    out = []
    for row in rows:
        d = dict(row)
        prereqs = h.get_prerequisites(conn, row["course_id"])
        d["prerequisites"] = [p["course_code"] for p in prereqs]
        out.append(d)
    return out


def _course_detail(conn, course_row) -> dict:
    d = dict(course_row)
    prereqs = h.get_prerequisites(conn, course_row["course_id"])
    d["prerequisites"] = [p["course_code"] for p in prereqs]
    dept = conn.execute("SELECT department_name FROM departments WHERE department_id = ?", (course_row["department_id"],)).fetchone()
    d["department_name"] = dept["department_name"] if dept else None
    return d


def _instructor_detail(conn, instr_row) -> dict:
    d = dict(instr_row)
    dept = conn.execute("SELECT department_name FROM departments WHERE department_id = ?", (instr_row["department_id"],)).fetchone()
    d["department_name"] = dept["department_name"] if dept else None
    sections = conn.execute(
        """
        SELECT c.course_code, c.course_title, sem.semester_name, sec.capacity
        FROM sections sec
        JOIN courses c ON c.course_id = sec.course_id
        JOIN semesters sem ON sem.semester_id = sec.semester_id
        WHERE sec.instructor_id = ?
        ORDER BY sem.semester_id DESC
        """,
        (instr_row["instructor_id"],),
    ).fetchall()
    d["sections_taught"] = h.rows_to_list(sections)
    return d


def _fmt_course(c: dict) -> str:
    prereqs = ", ".join(c.get("prerequisites") or []) or "none"
    return (
        f"{c['course_code']} - {c['course_title']} ({c['credits']} credits)\n"
        f"  Department: {c.get('department_name', 'N/A')}\n"
        f"  Course fee: {c['course_fee']:.2f}\n"
        f"  Prerequisites: {prereqs}\n"
        f"  Description: {c.get('description') or 'N/A'}"
    )


def _fmt_instructor(i: dict) -> str:
    lines = [
        f"{i['full_name']} ({i.get('email', 'N/A')})",
        f"  Department: {i.get('department_name', 'N/A')}",
        f"  Max teaching load: {i.get('max_credits', 'N/A')} credits/semester",
    ]
    sections = i.get("sections_taught") or []
    if sections:
        lines.append("  Sections taught:")
        for s in sections:
            lines.append(f"    - {s['course_code']} ({s['course_title']}) - {s['semester_name']}, capacity {s['capacity']}")
    return "\n".join(lines)


def _fmt_program(p: dict) -> str:
    return f"{p['program_name']} - {p['degree_level']} (department_id {p['department_id']})"


def _fmt_department(d: dict) -> str:
    return f"{d['department_name']} - {d['faculty_name']}"


def _fmt_semester(s: dict) -> str:
    current = " (current)" if s.get("is_current") else ""
    return f"{s['semester_name']}: {s['start_date']} to {s['end_date']}{current}"


def _fmt_section(s: dict) -> str:
    full = " - FULL" if s.get("is_full") else ""
    return (
        f"{s['course_code']} - {s['course_title']} ({s['semester_name']})\n"
        f"  Instructor: {s.get('instructor_name', 'N/A')}\n"
        f"  Enrolled: {s['enrolled_count']}/{s['capacity']} (seats available: {s['seats_available']}){full}"
    )


def _fmt_policy(key: str, policy: dict) -> str:
    lines = [policy.get("title", key)]
    for rule in policy.get("rules", []):
        lines.append(f"  - {rule}")
    return "\n".join(lines)


def _formatted_text(query_type: str, data) -> str:
    """Render the grounded ``data`` payload as human-readable text for the chat
    response. Never adds information that isn't already present in ``data``."""
    if query_type == "course":
        if isinstance(data, list):
            return "\n\n".join(_fmt_course(c) for c in data) or "No courses found."
        return _fmt_course(data)

    if query_type == "instructor":
        if isinstance(data, list):
            return "\n\n".join(_fmt_instructor(i) for i in data) or "No instructors found."
        return _fmt_instructor(data)

    if query_type == "program":
        if isinstance(data, list):
            return "\n".join(_fmt_program(p) for p in data) or "No programs found."
        return _fmt_program(data)

    if query_type == "department":
        if isinstance(data, list):
            return "\n".join(_fmt_department(d) for d in data) or "No departments found."
        return _fmt_department(data)

    if query_type == "semester":
        if isinstance(data, list):
            return "\n".join(_fmt_semester(s) for s in data) or "No semesters found."
        return _fmt_semester(data)

    if query_type == "section":
        return _fmt_section(data)

    if query_type == "policy":
        return "\n\n".join(_fmt_policy(key, val) for key, val in data.items()) or "No policies found."

    return ""


def _section_detail(conn, course_row, semester_row) -> dict | None:
    section = conn.execute(
        "SELECT * FROM sections WHERE course_id = ? AND semester_id = ?",
        (course_row["course_id"], semester_row["semester_id"]),
    ).fetchone()
    if not section:
        return None
    instructor = conn.execute("SELECT full_name FROM instructors WHERE instructor_id = ?", (section["instructor_id"],)).fetchone()
    enrolled = h.section_enrolled_count(conn, section["section_id"])
    d = dict(section)
    d["course_code"] = course_row["course_code"]
    d["course_title"] = course_row["course_title"]
    d["semester_name"] = semester_row["semester_name"]
    d["instructor_name"] = instructor["full_name"] if instructor else None
    d["enrolled_count"] = enrolled
    d["seats_available"] = section["capacity"] - enrolled
    d["is_full"] = enrolled >= section["capacity"]
    return d


@tool("get_university_information", args_schema=InformationQueryInput)
def get_university_information(
    query_type: str, identifier: Optional[str] = None, semester_name: Optional[str] = None
) -> dict:
    """Retrieve grounded university information: courses, tuition fees, policies,
    enrollment rules, instructors, programs, departments, sections, and semesters."""

    with h.get_connection() as conn:
        if query_type == "course":
            if identifier:
                course = h.find_course(conn, identifier)
                if not course:
                    return {"found": False, "query_type": query_type, "data": None,
                            "message": f"No course found with code '{identifier}'."}
                data = _course_detail(conn, course)
                return {"found": True, "query_type": query_type, "data": data,
                        "message": "Course found.", "formatted_text": _formatted_text(query_type, data)}
            data = _list_courses(conn)
            return {"found": True, "query_type": query_type, "data": data,
                    "message": "All courses in the catalog.", "formatted_text": _formatted_text(query_type, data)}

        if query_type == "policy":
            policies = h.load_policies()
            if identifier:
                key = identifier.strip().lower().replace(" ", "_")
                if not key.endswith("policy") and not key.endswith("_policy"):
                    key = f"{key}_policy"
                if key in policies:
                    data = {key: policies[key]}
                    return {"found": True, "query_type": query_type, "data": data,
                            "message": "Policy found.", "formatted_text": _formatted_text(query_type, data)}
                # fall back to fuzzy match on title
                for pkey, pval in policies.items():
                    if identifier.strip().lower() in pval.get("title", "").lower():
                        data = {pkey: pval}
                        return {"found": True, "query_type": query_type, "data": data,
                                "message": "Policy found.", "formatted_text": _formatted_text(query_type, data)}
                return {"found": False, "query_type": query_type, "data": None,
                        "message": f"No policy found matching '{identifier}'. "
                                    f"Available policies: {', '.join(policies.keys())}."}
            return {"found": True, "query_type": query_type, "data": policies,
                    "message": "All university policies.", "formatted_text": _formatted_text(query_type, policies)}

        if query_type == "instructor":
            if identifier:
                instr = h.find_instructor(conn, identifier)
                if not instr:
                    return {"found": False, "query_type": query_type, "data": None,
                            "message": f"No instructor found matching '{identifier}'."}
                data = _instructor_detail(conn, instr)
                return {"found": True, "query_type": query_type, "data": data,
                        "message": "Instructor found.", "formatted_text": _formatted_text(query_type, data)}
            rows = conn.execute("SELECT * FROM instructors ORDER BY full_name").fetchall()
            data = [_instructor_detail(conn, r) for r in rows]
            return {"found": True, "query_type": query_type, "data": data,
                    "message": "All instructors.", "formatted_text": _formatted_text(query_type, data)}

        if query_type == "program":
            if identifier:
                row = conn.execute(
                    "SELECT * FROM programs WHERE lower(program_name) LIKE lower(?)", (f"%{identifier}%",)
                ).fetchone()
                if not row:
                    return {"found": False, "query_type": query_type, "data": None,
                            "message": f"No program found matching '{identifier}'."}
                data = dict(row)
                return {"found": True, "query_type": query_type, "data": data,
                        "message": "Program found.", "formatted_text": _formatted_text(query_type, data)}
            rows = conn.execute("SELECT * FROM programs ORDER BY program_name").fetchall()
            data = h.rows_to_list(rows)
            return {"found": True, "query_type": query_type, "data": data,
                    "message": "All programs.", "formatted_text": _formatted_text(query_type, data)}

        if query_type == "department":
            if identifier:
                row = conn.execute(
                    "SELECT * FROM departments WHERE lower(department_name) LIKE lower(?)", (f"%{identifier}%",)
                ).fetchone()
                if not row:
                    return {"found": False, "query_type": query_type, "data": None,
                            "message": f"No department found matching '{identifier}'."}
                data = dict(row)
                return {"found": True, "query_type": query_type, "data": data,
                        "message": "Department found.", "formatted_text": _formatted_text(query_type, data)}
            rows = conn.execute("SELECT * FROM departments ORDER BY department_name").fetchall()
            data = h.rows_to_list(rows)
            return {"found": True, "query_type": query_type, "data": data,
                    "message": "All departments.", "formatted_text": _formatted_text(query_type, data)}

        if query_type == "semester":
            if identifier:
                row = h.find_semester(conn, identifier)
                if not row:
                    return {"found": False, "query_type": query_type, "data": None,
                            "message": f"No semester found matching '{identifier}'."}
                data = dict(row)
                return {"found": True, "query_type": query_type, "data": data,
                        "message": "Semester found.", "formatted_text": _formatted_text(query_type, data)}
            rows = conn.execute("SELECT * FROM semesters ORDER BY semester_id").fetchall()
            data = h.rows_to_list(rows)
            return {"found": True, "query_type": query_type, "data": data,
                    "message": "All semesters.", "formatted_text": _formatted_text(query_type, data)}

        if query_type == "section":
            if not identifier:
                return {"found": False, "query_type": query_type, "data": None,
                        "message": "A course code ('identifier') is required for section lookups."}
            course = h.find_course(conn, identifier)
            if not course:
                return {"found": False, "query_type": query_type, "data": None,
                        "message": f"No course found with code '{identifier}'."}
            semester = h.find_semester(conn, semester_name)
            if not semester:
                return {"found": False, "query_type": query_type, "data": None,
                        "message": f"No semester found matching '{semester_name}'."
                                    if semester_name else "No current semester is configured."}
            detail = _section_detail(conn, course, semester)
            if not detail:
                return {"found": False, "query_type": query_type, "data": None,
                        "message": f"No section of {course['course_code']} is offered in {semester['semester_name']}."}
            return {"found": True, "query_type": query_type, "data": detail,
                    "message": "Section found.", "formatted_text": _formatted_text(query_type, detail)}

    return {"found": False, "query_type": query_type, "data": None, "message": "Unsupported query_type."}
