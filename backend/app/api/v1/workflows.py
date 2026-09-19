from fastapi import APIRouter

from app.core.workflows import DEFAULT_WORKFLOW, WORKFLOWS

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
def list_workflows():
    """Public catalog of recruiting blueprint workflows (used by onboarding)."""
    blueprints = [
        {
            "key": wf["key"],
            "label": wf["label"],
            "description": wf["description"],
            "icon": wf["icon"],
            "stages": wf["stages"],
            "entry_stage": wf["entry_stage"],
            "fill_stage": wf["fill_stage"],
            "reject_stage": wf["reject_stage"],
            "candidate_fields": wf["candidate_fields"],
            "job_fields": wf["job_fields"],
        }
        for wf in WORKFLOWS.values()
    ]
    return {"default": DEFAULT_WORKFLOW, "workflows": blueprints}
