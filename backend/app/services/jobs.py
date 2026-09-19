"""Background job plumbing.

Heavy work (parsing, matching, inbound ingestion) runs as rows in `jobs`,
claimed and executed by a worker loop — either the in-process background task
started in `app.main.lifespan`, or a standalone `python -m app.worker` process.

Postgres uses `FOR UPDATE SKIP LOCKED` for safe cross-process claiming; SQLite
(dev) uses a guarded UPDATE which is sufficient for a single worker.
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.job import Job
from app.models.mixins import utcnow

logger = logging.getLogger("orcai.jobs")
settings = get_settings()

Handler = Callable[[Session, Job], "dict[str, Any] | Awaitable[dict[str, Any]]"]
HANDLERS: dict[str, Handler] = {}


def register_handler(name: str):
    def register(fn: Handler) -> Handler:
        HANDLERS[name] = fn
        return fn

    return register


def submit_job(db: Session, *, agency_id: int, type_: str, params: dict[str, Any] | None = None) -> Job:
    job = Job(
        agency_id=agency_id,
        type=type_,
        params=params or {},
        max_attempts=settings.JOBS_MAX_ATTEMPTS,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, agency_id: int, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id, Job.agency_id == agency_id).first()


async def run_handler_inline(
    db: Session, type_: str, agency_id: int, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute a handler synchronously in the caller's session (no DB commit cycle).

    Used by endpoints when `?async=false` (CLI/tests) and by tests directly.
    """
    from app.services import job_handlers  # noqa: F401  (ensure registration)

    handler = HANDLERS.get(type_)
    if handler is None:
        raise RuntimeError(f"no handler registered for job type '{type_}'")
    stub = Job(agency_id=agency_id, type=type_, params=params or {}, status="running")
    result = handler(db, stub)
    if inspect.isawaitable(result):
        result = await result
    return result


def _claimable_filter(now):
    return and_(
        Job.max_attempts > Job.attempts,
        or_(Job.status == "pending", and_(Job.status == "running", Job.lease_until < now)),
    )


def claim_job(db: Session) -> Job | None:
    """Atomically claim the next eligible job for this process, or return None."""
    now = utcnow()
    lease = now + timedelta(seconds=settings.JOBS_LEASE_SECONDS)
    dialect = db.get_bind().dialect.name
    filt = _claimable_filter(now)

    if dialect == "postgresql":
        job_id = db.execute(
            select(Job.id).where(filt).order_by(Job.id).limit(1).with_for_update(skip_locked=True)
        ).scalar_one_or_none()
    else:
        candidate = db.query(Job).filter(filt).order_by(Job.id).limit(1).first()
        job_id = candidate.id if candidate else None

    if job_id is None:
        return None

    claimed = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status.in_(["pending", "running"]))
        .values(status="running", attempts=Job.attempts + 1, started_at=now, lease_until=lease)
        .returning(Job.id)
    ).scalar_one_or_none()
    db.commit()
    if claimed is None:
        return None
    return db.get(Job, job_id)


async def run_job(db: Session, job: Job) -> Job:
    from app.services import job_handlers  # noqa: F401  (ensure registration)

    handler = HANDLERS.get(job.type)
    now = utcnow()
    try:
        if handler is None:
            raise RuntimeError(f"no handler registered for job type '{job.type}'")
        result = handler(db, job)
        if inspect.isawaitable(result):
            result = await result
        job.status = "done"
        job.result = result if isinstance(result, dict) else {"value": result}
        job.error = None
    except Exception as exc:  # noqa: BLE001 - job failure is recorded, not raised
        logger.exception("job %s (%s) attempt %d/%d failed", job.id, job.type, job.attempts, job.max_attempts)
        job.error = str(exc)[:2000]
        if job.attempts >= job.max_attempts:
            job.status = "failed"
        else:
            job.status = "pending"
            job.started_at = None
            job.lease_until = None
    job.finished_at = now if job.status in ("done", "failed") else None
    db.commit()
    db.refresh(job)
    return job


async def process_available(db: Session) -> int:
    """Claim and run jobs until the queue is empty. Returns jobs executed."""
    processed = 0
    while True:
        job = claim_job(db)
        if job is None:
            return processed
        await run_job(db, job)
        processed += 1


async def worker_loop() -> None:
    """Infinite worker loop (used by lifespan task + `python -m app.worker`)."""
    poll = settings.JOBS_POLL_SECONDS
    while True:
        try:
            db = SessionLocal()
            try:
                await process_available(db)
            finally:
                db.close()
        except Exception:  # noqa: BLE001 - keep the loop alive
            logger.exception("worker iteration failed")
        await asyncio.sleep(poll)
