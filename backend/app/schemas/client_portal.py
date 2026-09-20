from datetime import datetime

from pydantic import BaseModel, Field


class PortalSessionIn(BaseModel):
    client_id: int
    expiry_days: int = Field(default=7, ge=1, le=90)


class PortalSessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agency_id: int
    client_id: int
    token_hash: str
    expires_at: datetime
    is_active: bool
    last_accessed_at: datetime | None = None
    created_at: datetime
    client_name: str | None = None


class PortalProfileOut(BaseModel):
    client_id: int
    client_name: str
    client_industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    submitted_matches: list[dict]


class FeedbackIn(BaseModel):
    match_id: int
    rating: int = Field(ge=1, le=5)
    feedback_text: str | None = None


class FeedbackOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agency_id: int
    client_id: int
    match_id: int
    session_id: int | None = None
    rating: int
    feedback_text: str | None = None
    status: str
    reviewed_by: int | None = None
    created_at: datetime
    client_name: str | None = None
    match_seeker_name: str | None = None
    match_contract_title: str | None = None
