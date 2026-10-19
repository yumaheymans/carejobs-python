"""The enums of the CareJobs.Now tools.

Copied from the ``inputSchema`` of the live ``tools/list`` answer at
https://carejobs.now/api/mcp. A test compares them with the live server, so drift is caught
instead of shipped.
"""

from __future__ import annotations

from typing import Literal, Tuple

__all__ = ["Kind", "KINDS", "Care", "CARE_TYPES", "EmployerType", "EMPLOYER_TYPES", "Sort", "SORTS"]

Kind = Literal[
    "nurses",
    "nurse-practitioners",
    "physicians",
    "nursing-assistants",
    "caregivers",
    "therapy-rehab",
    "mental-health",
    "pharmacy",
    "imaging",
    "lab",
    "surgical-techs",
    "emts-paramedics",
    "medical-assistants",
    "dental",
    "admin",
    "allied-health",
    "ai-training",
]
KINDS: Tuple[str, ...] = (
    "nurses",
    "nurse-practitioners",
    "physicians",
    "nursing-assistants",
    "caregivers",
    "therapy-rehab",
    "mental-health",
    "pharmacy",
    "imaging",
    "lab",
    "surgical-techs",
    "emts-paramedics",
    "medical-assistants",
    "dental",
    "admin",
    "allied-health",
    "ai-training",
)
"""Kinds of healthcare job (the ``kind`` enum of every tool that takes one)."""

Care = Literal[
    "health-system",
    "childrens-hospital",
    "outpatient",
    "specialty-care",
    "behavioral-health",
    "autism-care",
    "home-care",
    "senior-care",
    "rehab",
    "dental",
    "pharmacy-retail",
    "kidney-care",
    "labs-imaging",
    "telehealth",
    "staffing",
    "ai-training",
    "job-boards",
]
CARE_TYPES: Tuple[str, ...] = (
    "health-system",
    "childrens-hospital",
    "outpatient",
    "specialty-care",
    "behavioral-health",
    "autism-care",
    "home-care",
    "senior-care",
    "rehab",
    "dental",
    "pharmacy-retail",
    "kidney-care",
    "labs-imaging",
    "telehealth",
    "staffing",
    "ai-training",
    "job-boards",
)
"""Kinds of care for ``list_employers(care=...)``."""

EmployerType = Literal[
    "employer",
    "ai-program",
    "job-board",
]
EMPLOYER_TYPES: Tuple[str, ...] = (
    "employer",
    "ai-program",
    "job-board",
)
"""What an entry is: an employer, an AI-training program or a job board."""

Sort = Literal[
    "mixed",
    "newest",
    "highest_pay",
]
SORTS: Tuple[str, ...] = (
    "mixed",
    "newest",
    "highest_pay",
)
"""Sort orders for ``search_jobs(sort=...)``."""
