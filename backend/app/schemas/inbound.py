from datetime import datetime

from pydantic import BaseModel


class InboundIn(BaseModel):
    agency_slug: str
    channel: str
    external_id: str | None = None
    phone_number: str | None = None
    sender_name: str | None = None
    body: str = ""


class InboundOut(BaseModel):
    id: int
    channel: str
    sender_name: str | None = None
    phone_number: str | None = None
    body: str
    status: str
    seeker_id: int | None = None
    received_at: datetime
