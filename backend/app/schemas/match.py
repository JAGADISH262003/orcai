from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MatchOut(BaseModel):
    id: int
    contract_id: int
    seeker_id: int
    score: float
    tier: str
    status: str
    hitl_required: bool
    rationale: str | None = None
    hitl_status: str | None = None
    human_review: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    seeker_name: str | None = None
    seeker_headline: str | None = None
    seeker_skills: list[Any] = []
    contract_title: str | None = None


class MatchReviewIn(BaseModel):
    decision: str  # approve | reject
    review: str | None = None


class MatchStatusIn(BaseModel):
    status: str  # pending|approved|rejected|submitted|placed
