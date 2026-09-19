from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

# Billing / subscription


class ConsentOut(BaseModel):
    id: int
    seeker_id: int
    seeker_name: str | None = None
    basis: str
    channel: str | None = None
    status: str
    consent_given_at: datetime
    retention_days: int
    erased_at: datetime | None = None


class ConsentCreateIn(BaseModel):
    seeker_id: int
    basis: str = "explicit_opt_in"
    channel: str | None = None
    retention_days: int = 30


class SubscriptionOut(BaseModel):
    id: int
    tier: str
    price_per_month: float
    billing_cycle_start: date
    billing_cycle_end: date | None = None
    status: str
    seats: int


class PlanOut(BaseModel):
    slug: str
    name: str
    price_per_month: float
    description: str


class DashboardOut(BaseModel):
    active_contracts: int
    total_seekers: int
    pending_hitl: int
    matches_this_week: int
    avg_match_score: float
    tier_a_matches: int
    recent_matches: list[Any] = []
