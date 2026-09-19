"""Scraper API endpoints: scrape jobs and candidates from external sources."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.services.audit import audit
from app.services.jobs import run_handler_inline, submit_job

router = APIRouter(prefix="/scrape", tags=["scrapers"])


class JobScrapeIn(BaseModel):
    source: str = Field(description="google_jobs, indeed, naukri, rss_feed, custom_url")
    query: str = ""
    location: str | None = None
    url: str | None = None
    feed_url: str | None = None
    max_results: int = Field(default=25, ge=1, le=100)
    country: str = "us"


class CandidateScrapeIn(BaseModel):
    source: str = Field(description="google_search, github, stackoverflow, linkedin, custom_url")
    query: str = ""
    location: str | None = None
    url: str | None = None
    max_results: int = Field(default=25, ge=1, le=100)
    language: str | None = None


@router.post("/jobs")
async def scrape_jobs(
    payload: JobScrapeIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))],
    async_: bool = Query(default=True, alias="async"),
):
    params = {"agency_id": agency.id, **payload.model_dump()}
    audit(db, agency_id=agency.id, user_id=user.id, action="scrape.jobs", meta={"source": payload.source, "query": payload.query})
    db.commit()
    if async_:
        from fastapi.responses import JSONResponse

        from app.schemas.job import JobOut
        job = submit_job(db, agency_id=agency.id, type_="scrape.jobs", params=params)
        return JSONResponse(status_code=202, content=JobOut.model_validate(job).model_dump(mode="json"))
    result = await run_handler_inline(db, "scrape.jobs", agency.id, params)
    return result


@router.post("/candidates")
async def scrape_candidates(
    payload: CandidateScrapeIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))],
    async_: bool = Query(default=True, alias="async"),
):
    params = {"agency_id": agency.id, **payload.model_dump()}
    audit(db, agency_id=agency.id, user_id=user.id, action="scrape.candidates", meta={"source": payload.source, "query": payload.query})
    db.commit()
    if async_:
        from fastapi.responses import JSONResponse

        from app.schemas.job import JobOut
        job = submit_job(db, agency_id=agency.id, type_="scrape.candidates", params=params)
        return JSONResponse(status_code=202, content=JobOut.model_validate(job).model_dump(mode="json"))
    result = await run_handler_inline(db, "scrape.candidates", agency.id, params)
    return result
