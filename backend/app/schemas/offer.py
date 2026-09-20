from datetime import datetime

from pydantic import BaseModel


class OfferIn(BaseModel):
    contract_id: int
    seeker_id: int
    match_id: int | None = None
    offered_salary: float | None = None
    offered_currency: str = "USD"
    start_date: str | None = None
    offer_expiry: str | None = None
    terms: str | None = None
    notes: str | None = None


class OfferOut(BaseModel):
    id: int
    agency_id: int
    contract_id: int
    seeker_id: int
    match_id: int | None = None
    status: str
    offered_salary: float | None = None
    offered_currency: str
    start_date: str | None = None
    offer_expiry: str | None = None
    terms: str | None = None
    notes: str | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime
    # Denormalized names
    contract_title: str | None = None
    seeker_name: str | None = None
    approvals: list["OfferApprovalOut"] = []


class OfferApprovalOut(BaseModel):
    id: int
    offer_id: int
    approver_id: int
    status: str
    comments: str | None = None
    decided_at: datetime | None = None
    created_at: datetime
    approver_name: str | None = None


class OfferApprovalIn(BaseModel):
    status: str  # approved|rejected
    comments: str | None = None


class OfferPipelineColumn(BaseModel):
    status: str
    label: str
    offers: list[OfferOut]
