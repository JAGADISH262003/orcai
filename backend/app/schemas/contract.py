from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ContractIn(BaseModel):
    raw_text: str
    client_id: int | None = None
    client_name: str | None = None


class ContractOut(BaseModel):
    id: int
    agency_id: int
    client_id: int | None = None
    title: str | None = None
    status: str
    location: str | None = None
    is_remote: bool | None = None
    duration_months: int | None = None
    rate_bill: float | None = None
    rate_pay: float | None = None
    currency: str
    experience_min: int | None = None
    openings: int
    start_by: date | None = None
    skills: list[Any] = []
    ai_summary: str | None = None
    parse_method: str | None = None
    created_at: datetime
    client_name: str | None = None


class ContractUpdateIn(BaseModel):
    title: str | None = None
    status: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    duration_months: int | None = None
    rate_bill: float | None = None
    rate_pay: float | None = None
    experience_min: int | None = None
    openings: int | None = None
    start_by: date | None = None
    skills: list[str] | None = None


class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class ClientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agency_id: int
    name: str
    industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    created_at: datetime
