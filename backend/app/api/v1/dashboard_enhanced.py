from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep
from app.models.contract import Contract
from app.models.match import Match
from app.models.seeker import Seeker

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard_stats(user: CurrentUser, db: DbDep) -> dict[str, Any]:
    aid = user.agency_id
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    active_contracts = db.scalar(
        select(func.count(Contract.id)).where(Contract.agency_id == aid, Contract.status == "active")
    ) or 0
    total_seekers = db.scalar(
        select(func.count(Seeker.id)).where(Seeker.agency_id == aid, Seeker.is_active)
    ) or 0
    pending_hitl = db.scalar(
        select(func.count(Match.id)).where(
            Match.agency_id == aid, Match.hitl_required, Match.hitl_status == "pending_review"
        )
    ) or 0
    matches_this_week = db.scalar(
        select(func.count(Match.id)).where(Match.agency_id == aid, Match.created_at >= week_ago)
    ) or 0
    avg_score = db.scalar(
        select(func.avg(Match.score)).where(Match.agency_id == aid)
    ) or 0
    tier_a = db.scalar(
        select(func.count(Match.id)).where(Match.agency_id == aid, Match.tier == "A")
    ) or 0

    pipeline_dist = {}
    for status, cnt in db.execute(
        select(Match.status, func.count(Match.id))
        .where(Match.agency_id == aid)
        .group_by(Match.status)
    ).all():
        pipeline_dist[status] = cnt

    tier_dist = {}
    for tier, cnt in db.execute(
        select(Match.tier, func.count(Match.id))
        .where(Match.agency_id == aid)
        .group_by(Match.tier)
    ).all():
        tier_dist[tier] = cnt

    source_dist = {}
    for source, cnt in db.execute(
        select(Seeker.source, func.count(Seeker.id))
        .where(Seeker.agency_id == aid)
        .group_by(Seeker.source)
    ).all():
        source_dist[source] = cnt

    recent_matches = db.scalars(
        select(Match)
        .where(Match.agency_id == aid)
        .order_by(Match.created_at.desc())
        .limit(5)
    ).all()

    return {
        "active_contracts": active_contracts,
        "total_seekers": total_seekers,
        "pending_hitl": pending_hitl,
        "matches_this_week": matches_this_week,
        "avg_match_score": round(float(avg_score), 1),
        "tier_a_matches": tier_a,
        "pipeline_distribution": pipeline_dist,
        "tier_distribution": tier_dist,
        "source_distribution": source_dist,
        "recent_matches": [
            {
                "id": m.id,
                "score": m.score,
                "tier": m.tier,
                "status": m.status,
                "contract_id": m.contract_id,
                "seeker_id": m.seeker_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in recent_matches
        ],
    }


@router.get("/timeline")
def dashboard_timeline(user: CurrentUser, db: DbDep, days: int = 30) -> list[dict[str, Any]]:
    aid = user.agency_id
    start = datetime.now(UTC) - timedelta(days=days)

    matches = db.scalars(
        select(Match)
        .where(Match.agency_id == aid, Match.created_at >= start)
        .order_by(Match.created_at)
    ).all()

    day_map: dict[str, dict[str, int]] = {}
    for m in matches:
        day = m.created_at.strftime("%Y-%m-%d") if m.created_at else "unknown"
        if day not in day_map:
            day_map[day] = {"created": 0, "placed": 0, "rejected": 0}
        day_map[day]["created"] += 1
        if m.status == "placed":
            day_map[day]["placed"] += 1
        elif m.status == "rejected":
            day_map[day]["rejected"] += 1

    return [{"date": k, **v} for k, v in sorted(day_map.items())]
