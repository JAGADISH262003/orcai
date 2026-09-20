from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.contract import Contract
from app.models.match import Match
from app.models.seeker import Seeker
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import DashboardOut, PlanOut, SubscriptionOut
from app.services.audit import audit

router = APIRouter(prefix="/billing", tags=["billing"])

RequireBillingWrite = Annotated[User, Depends(require_permission(Permission.BILLING_WRITE))]

PLANS: list[PlanOut] = [
    PlanOut(
        slug="starter",
        name="Starter",
        price_per_month=4999,
        description="1-3 recruiters, 3 active employer contracts, 200 seekers/mo.",
    ),
    PlanOut(
        slug="growth",
        name="Growth",
        price_per_month=14999,
        description="4-15 recruiters, 15 active contracts, WhatsApp + Voice screener.",
    ),
    PlanOut(
        slug="scale",
        name="Scale",
        price_per_month=34999,
        description="16-50 recruiters, RPO white-label, ATS bridge.",
    ),
]


@router.get("/plans", response_model=list[PlanOut])
def list_plans():
    return PLANS


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(db: DbDep, agency: CurrentAgency):
    sub = (
        db.query(Subscription)
        .filter(Subscription.agency_id == agency.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription found")
    return SubscriptionOut(
        id=sub.id,
        tier=sub.tier,
        price_per_month=sub.price_per_month,
        billing_cycle_start=sub.billing_cycle_start,
        billing_cycle_end=sub.billing_cycle_end,
        status=sub.status,
        seats=sub.seats,
    )


@router.post("/subscription/select/{tier}", response_model=SubscriptionOut)
def select_tier(tier: str, db: DbDep, agency: CurrentAgency, user: RequireBillingWrite):
    plan = next((p for p in PLANS if p.slug == tier), None)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown tier")

    sub = (
        db.query(Subscription)
        .filter(Subscription.agency_id == agency.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if sub is None:
        sub = Subscription(
            agency_id=agency.id,
            tier=tier,
            price_per_month=plan.price_per_month,
            status="active",
            seats={"starter": 3, "growth": 15, "scale": 50}.get(tier, 3),
            billing_cycle_start=date.today(),
            billing_cycle_end=date.today() + timedelta(days=30),
        )
        db.add(sub)
    else:
        sub.tier = tier
        sub.price_per_month = plan.price_per_month
        sub.status = "active"
        sub.seats = {"starter": 3, "growth": 15, "scale": 50}.get(tier, 3)
        sub.billing_cycle_start = date.today()
        sub.billing_cycle_end = date.today() + timedelta(days=30)
    agency.tier = tier
    audit(db, agency_id=agency.id, user_id=user.id, action="billing.plan_change", meta={"tier": tier})
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id,
        tier=sub.tier,
        price_per_month=sub.price_per_month,
        billing_cycle_start=sub.billing_cycle_start,
        billing_cycle_end=sub.billing_cycle_end,
        status=sub.status,
        seats=sub.seats,
    )


class CheckoutIn(BaseModel):
    tier: str
    success_url: str | None = None
    cancel_url: str | None = None


@router.post("/checkout/stripe")
def stripe_checkout(data: CheckoutIn, db: DbDep, agency: CurrentAgency, user: RequireBillingWrite):
    from app.services.billing import stripe_create_checkout

    plan = next((p for p in PLANS if p.slug == data.tier), None)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown tier")

    result = stripe_create_checkout(
        agency_id=agency.id,
        price_cents=plan.price_per_month,
        plan_name=plan.name,
        email=user.email,
        name=user.name or user.email,
        success_url=data.success_url or f"{agency.id}/billing?success=1",
        cancel_url=data.cancel_url or f"{agency.id}/billing?cancelled=1",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "checkout_failed"))
    return result


class RazorpayCheckoutIn(BaseModel):
    tier: str


@router.post("/checkout/razorpay")
def razorpay_checkout(data: RazorpayCheckoutIn, db: DbDep, agency: CurrentAgency, user: RequireBillingWrite):
    from app.services.billing import razorpay_create_subscription

    plan = next((p for p in PLANS if p.slug == data.tier), None)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown tier")

    result = razorpay_create_subscription(
        agency_id=agency.id,
        plan_id=data.tier,
        email=user.email,
        name=user.name or user.email,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "subscription_failed"))
    return result


class WebhookStripeIn(BaseModel):
    id: str
    type: str
    data: dict


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: DbDep):
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")
    from app.services.billing import stripe_verify_webhook
    event = stripe_verify_webhook(body, signature)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    if event_type == "checkout.session.completed":
        agency_id = event.get("data", {}).get("metadata", {}).get("agency_id")
        if agency_id:
            sub = (
                db.query(Subscription)
                .filter(Subscription.agency_id == int(agency_id))
                .order_by(Subscription.created_at.desc())
                .first()
            )
            if sub:
                sub.status = "active"
                db.commit()
    return {"ok": True}


class WebhookRazorpayIn(BaseModel):
    payload: dict


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: DbDep):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    from app.services.billing import razorpay_verify_webhook
    event = razorpay_verify_webhook(body, signature)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("event", "")
    if "subscription" in event_type and "activated" in event_type:
        payload_entity = event.get("payload", {}).get("subscription", {}).get("entity", {})
        notes = payload_entity.get("notes", {})
        agency_id = notes.get("agency_id")
        if agency_id:
            sub = (
                db.query(Subscription)
                .filter(Subscription.agency_id == int(agency_id))
                .order_by(Subscription.created_at.desc())
                .first()
            )
            if sub:
                sub.status = "active"
                db.commit()
    return {"ok": True}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbDep, agency: CurrentAgency):
    active_contracts = (
        db.query(func.count(Contract.id))
        .filter(Contract.agency_id == agency.id, Contract.status == "active")
        .scalar()
        or 0
    )
    total_seekers = (
        db.query(func.count(Seeker.id))
        .filter(Seeker.agency_id == agency.id, Seeker.is_active)
        .scalar()
        or 0
    )
    pending_hitl = (
        db.query(func.count(Match.id))
        .filter(
            Match.agency_id == agency.id,
            Match.hitl_required,
            Match.hitl_status.in_(["pending_review", None]),
        )
        .scalar()
        or 0
    )
    week_ago = datetime.now(UTC) - timedelta(days=7)
    matches_this_week = (
        db.query(func.count(Match.id))
        .filter(Match.agency_id == agency.id, Match.created_at >= week_ago)
        .scalar()
        or 0
    )
    avg = db.query(func.avg(Match.score)).filter(Match.agency_id == agency.id).scalar()
    tier_a = (
        db.query(func.count(Match.id))
        .filter(Match.agency_id == agency.id, Match.tier == "A")
        .scalar()
        or 0
    )
    recent = (
        db.query(Match)
        .filter(Match.agency_id == agency.id)
        .order_by(Match.created_at.desc())
        .limit(5)
        .all()
    )
    recent_matches = [
        {
            "id": m.id,
            "score": m.score,
            "tier": m.tier,
            "status": m.status,
            "seeker_name": m.seeker.name if m.seeker else None,
            "contract_title": m.contract.title if m.contract else None,
            "hitl_required": m.hitl_required,
        }
        for m in recent
    ]
    return DashboardOut(
        active_contracts=active_contracts,
        total_seekers=total_seekers,
        pending_hitl=pending_hitl,
        matches_this_week=matches_this_week,
        avg_match_score=round(avg or 0.0, 1),
        tier_a_matches=tier_a,
        recent_matches=recent_matches,
    )
