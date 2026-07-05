"""
Tool layer (Layer 4) for the University Operations AI Agent.

Required tools
    1. get_university_information   - Information Tool
    2. analyze_enrollment_eligibility - Analysis Tool
    3. create_enrollment_request      - Action Tool (confirmation-gated)
    4. generate_student_report        - Reporting Tool

Bonus tools
    5. predict_future_gpa
    6. generate_study_plan
    7. generate_payroll_report
    8. analyze_section_utilization
    9. generate_institution_report

All tools are LangChain ``@tool``-decorated callables with pydantic
``args_schema`` input validation and structured dict outputs, suitable for
binding to a LangGraph-orchestrated LLM agent.
"""

from __future__ import annotations

from .information_tool import get_university_information
from .analysis_tool import analyze_enrollment_eligibility
from .action_tool import create_enrollment_request
from .reporting_tool import generate_student_report
from .bonus_tools import (
    predict_future_gpa,
    generate_study_plan,
    generate_payroll_report,
    analyze_section_utilization,
    generate_institution_report,
)

# Required tools (Layer 4 minimum of 4)
REQUIRED_TOOLS = [
    get_university_information,
    analyze_enrollment_eligibility,
    create_enrollment_request,
    generate_student_report,
]

# Optional bonus tools
BONUS_TOOLS = [
    predict_future_gpa,
    generate_study_plan,
    generate_payroll_report,
    analyze_section_utilization,
    generate_institution_report,
]

# Full registry used for LLM tool-binding and LangGraph ToolNode construction
TOOL_REGISTRY = REQUIRED_TOOLS + BONUS_TOOLS

# Convenience lookup by tool name (the name passed to @tool(...))
TOOLS_BY_NAME = {t.name: t for t in TOOL_REGISTRY}

# Names of tools that must never be executed without explicit user
# confirmation (mirrors app.config.CONFIRMATION_REQUIRED_TOOLS)
CONFIRMATION_REQUIRED_TOOL_NAMES = {"create_enrollment_request"}

__all__ = [
    "get_university_information",
    "analyze_enrollment_eligibility",
    "create_enrollment_request",
    "generate_student_report",
    "predict_future_gpa",
    "generate_study_plan",
    "generate_payroll_report",
    "analyze_section_utilization",
    "generate_institution_report",
    "REQUIRED_TOOLS",
    "BONUS_TOOLS",
    "TOOL_REGISTRY",
    "TOOLS_BY_NAME",
    "CONFIRMATION_REQUIRED_TOOL_NAMES",
]
