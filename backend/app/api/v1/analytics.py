from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep
from app.models.contract import Contract
from app.models.interview import Interview
from app.models.match import Match
from app.models.seeker import Seeker

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _days_ago(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


@router.get("/funnel")
def recruitment_funnel(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    applied = db.scalar(
        select(func.count(Match.id)).where(Match.agency_id == aid, Match.created_at >= start)
    ) or 0
    screened = db.scalar(
        select(func.count(Match.id)).where(
            Match.agency_id == aid, Match.created_at >= start, Match.status.in_(["submitted", "reviewed", "interviewed", "offered", "placed"])
        )
    ) or 0
    interviewed = db.scalar(
        select(func.count(Match.id)).where(
            Match.agency_id == aid, Match.created_at >= start, Match.status.in_(["interviewed", "offered", "placed"])
        )
    ) or 0
    offered = db.scalar(
        select(func.count(Match.id)).where(
            Match.agency_id == aid, Match.created_at >= start, Match.status.in_(["offered", "placed"])
        )
    ) or 0
    placed = db.scalar(
        select(func.count(Match.id)).where(
            Match.agency_id == aid, Match.created_at >= start, Match.status == "placed"
        )
    ) or 0

    return {
        "stages": [
            {"name": "Applied", "count": applied},
            {"name": "Screened", "count": screened},
            {"name": "Interviewed", "count": interviewed},
            {"name": "Offered", "count": offered},
            {"name": "Placed", "count": placed},
        ],
        "period_days": days,
    }


@router.get("/time-to-fill")
def time_to_fill(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    placed = db.scalars(
        select(Match).where(
            Match.agency_id == aid,
            Match.status == "placed",
            Match.created_at >= start,
        )
    ).all()

    if not placed:
        return {"avg_days": 0, "by_contract": {}, "by_skill": {}, "count": 0}

    total_days = 0.0
    by_contract: dict[int, list[float]] = {}

    for m in placed:
        if m.created_at:
            days_to_place = (datetime.utcnow() - m.created_at).days
            total_days += days_to_place
            by_contract.setdefault(m.contract_id, []).append(float(days_to_place))

    contracts = db.scalars(
        select(Contract).where(Contract.id.in_(by_contract.keys()))
    ).all()
    contract_map = {c.id: c for c in contracts}

    by_contract_out = {}
    for cid, durations in by_contract.items():
        c = contract_map.get(cid)
        title = c.title if c else f"Contract {cid}"
        by_contract_out[title] = round(sum(durations) / len(durations), 1)

    return {
        "avg_days": round(total_days / len(placed), 1),
        "by_contract": by_contract_out,
        "count": len(placed),
        "period_days": days,
    }


@router.get("/source-roi")
def source_roi(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    source_counts = dict(db.execute(
        select(Seeker.source, func.count(Seeker.id))
        .where(Seeker.agency_id == aid, Seeker.created_at >= start)
        .group_by(Seeker.source)
    ).all())

    placed_seekers = db.scalars(
        select(Match.seeker_id).where(
            Match.agency_id == aid,
            Match.status == "placed",
            Match.created_at >= start,
        )
    ).all()

    source_hires: dict[str, int] = {}
    for sid in placed_seekers:
        seeker = db.get(Seeker, sid)
        if seeker:
            src = seeker.source or "unknown"
            source_hires[src] = source_hires.get(src, 0) + 1

    results = []
    for src in source_counts:
        total = source_counts.get(src, 0)
        hires = source_hires.get(src, 0)
        results.append({
            "source": src,
            "total_candidates": total,
            "hires": hires,
            "conversion_rate": round(hires / total * 100, 1) if total > 0 else 0,
        })

    return {"sources": results, "period_days": days}


@router.get("/revenue")
def revenue_metrics(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    placed = db.scalars(
        select(Match).where(
            Match.agency_id == aid,
            Match.status == "placed",
            Match.created_at >= start,
        )
    ).all()

    if not placed:
        return {
            "total_placements": 0,
            "avg_bill_rate": 0,
            "total_revenue_est": 0,
            "monthly_trend": [],
        }

    total_placements = len(placed)
    bill_rates = []
    for m in placed:
        contract = db.get(Contract, m.contract_id)
        if contract and contract.rate_bill:
            bill_rates.append(float(contract.rate_bill))

    avg_bill_rate = round(sum(bill_rates) / len(bill_rates), 0) if bill_rates else 0
    total_revenue_est = round(avg_bill_rate * total_placements, 0) if bill_rates else 0

    monthly_trend: dict[str, dict[str, float]] = {}
    for m in placed:
        if m.created_at:
            month_key = m.created_at.strftime("%Y-%m")
            if month_key not in monthly_trend:
                monthly_trend[month_key] = {"placements": 0, "revenue": 0}
            monthly_trend[month_key]["placements"] += 1
            contract = db.get(Contract, m.contract_id)
            if contract and contract.rate_bill:
                monthly_trend[month_key]["revenue"] += float(contract.rate_bill)

    trend = [
        {"month": k, "placements": int(v["placements"]), "revenue": v["revenue"]}
        for k, v in sorted(monthly_trend.items())
    ]

    return {
        "total_placements": total_placements,
        "avg_bill_rate": avg_bill_rate,
        "total_revenue_est": total_revenue_est,
        "monthly_trend": trend,
        "period_days": days,
    }


@router.get("/consultant-performance")
def consultant_performance(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    interviews = db.scalars(
        select(Interview).where(
            Interview.agency_id == aid,
            Interview.created_at >= start,
        )
    ).all()

    evaluator_stats: dict[str, dict[str, Any]] = {}
    for iv in interviews:
        if iv.rating is not None:
            key = iv.interviewer_email or iv.interviewer_name or "unknown"
            if key not in evaluator_stats:
                evaluator_stats[key] = {"interviews": 0, "ratings": [], "placed": 0}
            evaluator_stats[key]["interviews"] += 1
            evaluator_stats[key]["ratings"].append(iv.rating)

    results = []
    for name, stats in evaluator_stats.items():
        avg_rating = round(sum(stats["ratings"]) / len(stats["ratings"]), 1) if stats["ratings"] else 0
        results.append({
            "recruiter": name,
            "interviews": stats["interviews"],
            "avg_rating": avg_rating,
            "placements": stats["placed"],
        })

    return {"performance": results, "period_days": days}


@router.get("/skills-demand")
def skills_demand(
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    aid = user.agency_id

    contracts = db.scalars(
        select(Contract).where(Contract.agency_id == aid, Contract.status == "active")
    ).all()

    seekers = db.scalars(
        select(Seeker).where(Seeker.agency_id == aid, Seeker.is_active)
    ).all()

    demand: dict[str, int] = {}
    for c in contracts:
        for s in (c.skills or []):
            skill = s.strip().lower()
            demand[skill] = demand.get(skill, 0) + 1

    supply: dict[str, int] = {}
    for s in seekers:
        for sk in (s.skills or []):
            skill = sk.strip().lower()
            supply[skill] = supply.get(skill, 0) + 1

    all_skills = sorted(set(demand.keys()) | set(supply.keys()))
    results = []
    for skill in all_skills:
        d = demand.get(skill, 0)
        sp = supply.get(skill, 0)
        gap = d - sp
        results.append({
            "skill": skill,
            "demand": d,
            "supply": sp,
            "gap": gap,
            "status": "shortage" if gap > 0 else "surplus" if gap < 0 else "balanced",
        })

    results.sort(key=lambda x: abs(x["gap"]), reverse=True)

    return {"skills": results[:30]}


@router.get("/pipeline-velocity")
def pipeline_velocity(
    user: CurrentUser,
    db: DbDep,
    days: int = 90,
) -> dict[str, Any]:
    aid = user.agency_id
    start = _days_ago(days)

    matches = db.scalars(
        select(Match).where(
            Match.agency_id == aid,
            Match.created_at >= start,
        ).order_by(Match.created_at)
    ).all()

    stage_times: dict[str, list[float]] = {}
    for m in matches:
        if m.created_at:
            stage = m.status or "unknown"
            elapsed = (datetime.utcnow() - m.created_at).days
            stage_times.setdefault(stage, []).append(float(elapsed))

    results = []
    for stage, durations in sorted(stage_times.items()):
        avg = round(sum(durations) / len(durations), 1)
        results.append({
            "stage": stage,
            "avg_days": avg,
            "count": len(durations),
        })

    bottleneck = max(results, key=lambda x: x["avg_days"]) if results else None

    return {
        "stages": results,
        "bottleneck": bottleneck["stage"] if bottleneck else None,
        "period_days": days,
    }
