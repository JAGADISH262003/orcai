from fastapi import APIRouter

from app.api.v1 import (
    audit_log,
    auth,
    billing,
    consent,
    contracts,
    hitl,
    inbound,
    jobs,
    matches,
    messaging,
    scrapers,
    seekers,
    tools,
    workflows,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(contracts.router)
api_router.include_router(seekers.router)
api_router.include_router(matches.router)
api_router.include_router(jobs.router)
api_router.include_router(hitl.router)
api_router.include_router(inbound.router)
api_router.include_router(consent.router)
api_router.include_router(billing.router)
api_router.include_router(workflows.router)
api_router.include_router(scrapers.router)
api_router.include_router(tools.router)
api_router.include_router(messaging.router)
api_router.include_router(audit_log.router)
