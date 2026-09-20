from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.scorecard import Scorecard, ScorecardTemplate

router = APIRouter(prefix="/scorecards", tags=["scorecards"])


class ScorecardTemplateIn(BaseModel):
    name: str
    criteria: list[dict[str, Any]]
    is_default: bool = False


class ScorecardTemplateUpdate(BaseModel):
    name: str | None = None
    criteria: list[dict[str, Any]] | None = None
    is_default: bool | None = None


class ScorecardIn(BaseModel):
    interview_id: int
    template_id: int
    scores: list[dict[str, Any]]
    overall_score: float = 0.0
    recommendation: str | None = None
    notes: str | None = None


class ScorecardUpdate(BaseModel):
    scores: list[dict[str, Any]] | None = None
    overall_score: float | None = None
    recommendation: str | None = None
    notes: str | None = None


def _template_out(t: ScorecardTemplate) -> dict[str, Any]:
    return {
        "id": t.id,
        "agency_id": t.agency_id,
        "name": t.name,
        "criteria": t.criteria,
        "is_default": t.is_default,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _scorecard_out(s: Scorecard) -> dict[str, Any]:
    return {
        "id": s.id,
        "agency_id": s.agency_id,
        "interview_id": s.interview_id,
        "template_id": s.template_id,
        "evaluator_id": s.evaluator_id,
        "scores": s.scores,
        "overall_score": s.overall_score,
        "recommendation": s.recommendation,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ── Template CRUD ──


@router.get("/templates")
def list_templates(
    user: CurrentUser,
    db: DbDep,
) -> list[dict[str, Any]]:
    q = select(ScorecardTemplate).where(ScorecardTemplate.agency_id == user.agency_id)
    q = q.order_by(ScorecardTemplate.created_at.desc())
    return [_template_out(t) for t in db.scalars(q).all()]


@router.post("/templates", status_code=201)
def create_template(
    data: ScorecardTemplateIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    t = ScorecardTemplate(
        agency_id=user.agency_id,
        name=data.name,
        criteria=data.criteria,
        is_default=data.is_default,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _template_out(t)


@router.get("/templates/{template_id}")
def get_template(
    template_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    t = db.get(ScorecardTemplate, template_id)
    if not t or t.agency_id != user.agency_id:
        raise HTTPException(404, "Template not found")
    return _template_out(t)


@router.patch("/templates/{template_id}")
def update_template(
    template_id: int,
    data: ScorecardTemplateUpdate,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    t = db.get(ScorecardTemplate, template_id)
    if not t or t.agency_id != user.agency_id:
        raise HTTPException(404, "Template not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return _template_out(t)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, str]:
    t = db.get(ScorecardTemplate, template_id)
    if not t or t.agency_id != user.agency_id:
        raise HTTPException(404, "Template not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ── Scorecard CRUD ──


@router.get("")
def list_scorecards(
    user: CurrentUser,
    db: DbDep,
    interview_id: int | None = None,
    evaluator_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = select(Scorecard).where(Scorecard.agency_id == user.agency_id)
    if interview_id:
        q = q.where(Scorecard.interview_id == interview_id)
    if evaluator_id:
        q = q.where(Scorecard.evaluator_id == evaluator_id)
    q = q.order_by(Scorecard.created_at.desc()).limit(limit)
    return [_scorecard_out(s) for s in db.scalars(q).all()]


@router.post("", status_code=201)
def create_scorecard(
    data: ScorecardIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    sc = Scorecard(
        agency_id=user.agency_id,
        interview_id=data.interview_id,
        template_id=data.template_id,
        evaluator_id=user.id,
        scores=data.scores,
        overall_score=data.overall_score,
        recommendation=data.recommendation,
        notes=data.notes,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return _scorecard_out(sc)


@router.get("/{scorecard_id}")
def get_scorecard(
    scorecard_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    sc = db.get(Scorecard, scorecard_id)
    if not sc or sc.agency_id != user.agency_id:
        raise HTTPException(404, "Scorecard not found")
    return _scorecard_out(sc)


@router.patch("/{scorecard_id}")
def update_scorecard(
    scorecard_id: int,
    data: ScorecardUpdate,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    sc = db.get(Scorecard, scorecard_id)
    if not sc or sc.agency_id != user.agency_id:
        raise HTTPException(404, "Scorecard not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sc, k, v)
    db.commit()
    db.refresh(sc)
    return _scorecard_out(sc)


@router.delete("/{scorecard_id}")
def delete_scorecard(
    scorecard_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, str]:
    sc = db.get(Scorecard, scorecard_id)
    if not sc or sc.agency_id != user.agency_id:
        raise HTTPException(404, "Scorecard not found")
    db.delete(sc)
    db.commit()
    return {"ok": True}


@router.get("/summary/{interview_id}")
def scorecard_summary(
    interview_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    scorecards = db.scalars(
        select(Scorecard).where(
            Scorecard.agency_id == user.agency_id,
            Scorecard.interview_id == interview_id,
        )
    ).all()

    if not scorecards:
        return {"interview_id": interview_id, "scorecards": [], "avg_overall": 0, "recommendations": {}}

    total_score = 0.0
    rec_counts: dict[str, int] = {}
    criterion_totals: dict[str, list[float]] = {}

    for sc in scorecards:
        total_score += sc.overall_score
        if sc.recommendation:
            rec_counts[sc.recommendation] = rec_counts.get(sc.recommendation, 0) + 1
        for entry in (sc.scores or []):
            crit = entry.get("criterion", "")
            score = entry.get("score", 0)
            criterion_totals.setdefault(crit, []).append(float(score))

    criterion_avgs = []
    for crit, scores in criterion_totals.items():
        criterion_avgs.append({
            "criterion": crit,
            "avg_score": round(sum(scores) / len(scores), 1),
            "count": len(scores),
        })

    return {
        "interview_id": interview_id,
        "total_scorecards": len(scorecards),
        "avg_overall": round(total_score / len(scorecards), 1),
        "recommendations": rec_counts,
        "criterion_averages": criterion_avgs,
    }
