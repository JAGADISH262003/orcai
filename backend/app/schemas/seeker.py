from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SeekerIn(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    visa_status: str | None = None
    location: str | None = None
    headline: str | None = None
    skills: list[str] = []
    experience_years: float | None = None
    summary: str | None = None
    education: str | None = None
    source: str = "manual"
    source_channel: str | None = None
    is_verified: bool = False


class SeekerOut(BaseModel):
    id: int
    agency_id: int
    name: str | None
    email: str | None
    phone: str | None
    visa_status: str | None
    location: str | None
    headline: str | None
    skills: list[Any] = []
    experience_years: float | None
    summary: str | None
    education: str | None
    source: str
    source_channel: str | None
    is_verified: bool
    is_active: bool
    created_at: datetime


class SeekerSearchOut(BaseModel):
    id: int
    name: str | None
    headline: str | None
    visa_status: str | None
    location: str | None
    skills: list[Any] = []
    experience_years: float | None
    source: str
    is_verified: bool
    created_at: datetime


class DedupeCheckOut(BaseModel):
    is_duplicate: bool
    existing_seeker_id: int | None = None
    existing_name: str | None = None
    dedupe_key: str | None = None
    matched_on: str | None = None
