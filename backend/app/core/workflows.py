"""Workflow engine: per-tenant recruiting blueprints.

The tenant's `workflow_type` (set at onboarding) selects one blueprint here;
`pipeline_stages`, entry/terminal stages, required candidate fields and job
fields all branch on this single field, so one codebase serves every company
type (see ORCAI Master Architecture & Build Plan §02/§03).
"""

from __future__ import annotations

from typing import Any


def _stages(*keys_and_labels: tuple[str, str]) -> list[dict[str, str]]:
    return [{"key": k, "label": label} for k, label in keys_and_labels]


# Ordered pipeline columns for each company type (the kanban stages a match
# advances through). `entry_stage` is the status a freshly computed match gets;
# `fill_stage` is the stage whose first reached opening count marks the contract
# "filled". `reject_stage` is not rendered as a column.
WORKFLOWS: dict[str, dict[str, Any]] = {
    "domestic_it": {
        "key": "domestic_it",
        "label": "Domestic IT Staffing",
        "description": "Permanent, contract & C2H placements for Indian companies. Shortlist-driven matching pipeline.",
        "icon": "▣",
        "stages": _stages(
            ("pending", "Pending Match"),
            ("approved", "Approved for Submission"),
            ("submitted", "Submitted to Employer"),
            ("placed", "Placed on Contract"),
        ),
        "entry_stage": "pending",
        "fill_stage": "placed",
        "terminal_stages": ["placed"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
    "us_bench_sales": {
        "key": "us_bench_sales",
        "label": "US Bench Sales / C2C",
        "description": "H1B/OPT/GC consultants on the bench matched to US C2C/W2 requirements from bench to on-project.",
        "icon": "◈",
        "stages": _stages(
            ("bench", "Bench Pool"),
            ("hotlisted", "Hotlist"),
            ("submitted", "Submitted to Client"),
            ("rtr_signed", "RTR Signed"),
            ("interview", "Interview"),
            ("on_project", "On Project"),
        ),
        "entry_stage": "bench",
        "fill_stage": "on_project",
        "terminal_stages": ["on_project"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
    "rpo": {
        "key": "rpo",
        "label": "RPO / Enterprise Recruiting",
        "description": "White-label, SLA-driven recruiting outsourcing for enterprise clients.",
        "icon": "⚙",
        "stages": _stages(
            ("intake", "Requisition Intake"),
            ("screening", "Screening"),
            ("client_interview", "Client Interview"),
            ("offer", "Offer"),
            ("onboarded", "Onboarded"),
            ("filled", "Filled"),
        ),
        "entry_stage": "intake",
        "fill_stage": "filled",
        "terminal_stages": ["filled"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
    "inhouse": {
        "key": "inhouse",
        "label": "Product / In-house Hiring",
        "description": "Direct hiring for startups, GCCs and product companies with structured screening.",
        "icon": "◆",
        "stages": _stages(
            ("applied", "Applied"),
            ("screening", "Screening"),
            ("interviews", "Interviews"),
            ("offer", "Offer"),
            ("joined", "Joined"),
        ),
        "entry_stage": "applied",
        "fill_stage": "joined",
        "terminal_stages": ["joined"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
    "campus": {
        "key": "campus",
        "label": "Campus / Fresher Hiring",
        "description": "Bulk college drives: assessments, shortlists and cohort offers at scale.",
        "icon": "◉",
        "stages": _stages(
            ("registered", "Registered"),
            ("assessed", "Assessed"),
            ("shortlisted", "Shortlisted"),
            ("interviewed", "Interviewed"),
            ("offered", "Offered"),
            ("joined", "Joined"),
        ),
        "entry_stage": "registered",
        "fill_stage": "joined",
        "terminal_stages": ["joined"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
    "exec_search": {
        "key": "exec_search",
        "label": "Executive Search / Headhunting",
        "description": "Retained C-suite / VP / Director mandates with market mapping and candidate dossiers.",
        "icon": "★",
        "stages": _stages(
            ("mandate", "Retained Mandate"),
            ("mapped", "Market Mapped"),
            ("outreach", "Confidential Outreach"),
            ("shortlist", "Shortlist"),
            ("presented", "Presented to Client"),
            ("placed", "Placed"),
        ),
        "entry_stage": "mandate",
        "fill_stage": "placed",
        "terminal_stages": ["placed"],
        "reject_stage": "rejected",
        "candidate_fields": ["name", "visa_status", "location", "headline", "skills", "experience_years"],
        "job_fields": ["title", "skills", "experience_min", "rate_bill", "rate_pay", "duration_months", "openings"],
    },
}

DEFAULT_WORKFLOW = "domestic_it"


def _validate() -> None:
    for wf in WORKFLOWS.values():
        keys = [s["key"] for s in wf["stages"]]
        if len(keys) != len(set(keys)):
            raise RuntimeError(f"duplicate stage in {wf['key']}")
        if wf["entry_stage"] not in keys:
            raise RuntimeError(f"entry_stage {wf['entry_stage']} not in stages for {wf['key']}")
        if wf["fill_stage"] not in keys:
            raise RuntimeError(f"fill_stage {wf['fill_stage']} not in stages for {wf['key']}")
        for t in wf["terminal_stages"]:
            if t not in keys:
                raise RuntimeError(f"terminal {t} not in stages for {wf['key']}")
        if wf["reject_stage"] == wf["entry_stage"]:
            raise RuntimeError(f"reject_stage must differ from entry_stage in {wf['key']}")


_validate()


def workflow_by_type(workflow_type: str) -> dict[str, Any]:
    """Return the blueprint for a type, falling back to the default."""
    wf = WORKFLOWS.get(workflow_type or "")
    return wf if wf is not None else WORKFLOWS[DEFAULT_WORKFLOW]


def workflow_config(workflow_type: str) -> dict[str, Any]:
    """JSON-serialisable tenant copy of the blueprint."""
    wf = workflow_by_type(workflow_type)
    return {
        "key": wf["key"],
        "label": wf["label"],
        "stages": wf["stages"],
        "entry_stage": wf["entry_stage"],
        "fill_stage": wf["fill_stage"],
        "reject_stage": wf["reject_stage"],
        "candidate_fields": wf["candidate_fields"],
    }


def pipeline_stages(workflow_type: str) -> list[dict[str, str]]:
    return workflow_by_type(workflow_type)["stages"]


def pipeline_keys(workflow_type: str) -> set[str]:
    return {s["key"] for s in pipeline_stages(workflow_type)}


def entry_stage(workflow_type: str) -> str:
    return workflow_by_type(workflow_type)["entry_stage"]


def fill_stage(workflow_type: str) -> str:
    return workflow_by_type(workflow_type)["fill_stage"]


def next_stage(workflow_type: str, current: str) -> str | None:
    keys = [s["key"] for s in pipeline_stages(workflow_type)]
    try:
        idx = keys.index(current)
    except ValueError:
        return None
    return keys[idx + 1] if idx + 1 < len(keys) else None


def valid_match_statuses(workflow_type: str) -> set[str]:
    wf = workflow_by_type(workflow_type)
    return pipeline_keys(workflow_type) | {wf["reject_stage"]}
