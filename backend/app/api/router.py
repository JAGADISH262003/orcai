from fastapi import APIRouter

from app.api.v1 import (
    activity,
    audit_log,
    auth,
    billing,
    consent,
    contracts,
    dashboard_enhanced,
    documents,
    email_compose,
    hitl,
    inbound,
    interviews,
    jobs,
    matches,
    messaging,
    notes,
    notifications,
    scrapers,
    seekers,
    settings,
    tags,
    team,
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
api_router.include_router(interviews.router)
api_router.include_router(notes.router)
api_router.include_router(tags.router)
api_router.include_router(notifications.router)
api_router.include_router(settings.router)
api_router.include_router(team.router)
api_router.include_router(dashboard_enhanced.router)
api_router.include_router(activity.router)
api_router.include_router(documents.router)
api_router.include_router(email_compose.router)
