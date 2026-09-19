from fastapi import APIRouter, Query

from app.api.deps import CurrentAgency, DbDep
from app.models.job import Job
from app.schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    db: DbDep,
    agency: CurrentAgency,
    type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    q = db.query(Job).filter(Job.agency_id == agency.id)
    if type:
        q = q.filter(Job.type == type)
    return q.order_by(Job.created_at.desc()).limit(limit).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: DbDep, agency: CurrentAgency):
    job = db.query(Job).filter(Job.id == job_id, Job.agency_id == agency.id).first()
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")
    return job
