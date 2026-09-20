from datetime import datetime

from pydantic import BaseModel, Field


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    channel: str = Field(default="email")
    template_subject: str | None = None
    template_body: str | None = None


class CampaignUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    template_subject: str | None = None
    template_body: str | None = None


class CampaignOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agency_id: int
    name: str
    description: str | None = None
    status: str
    channel: str
    template_subject: str | None = None
    template_body: str | None = None
    target_count: int
    sent_count: int
    opened_count: int
    replied_count: int
    created_at: datetime


class CampaignRecipientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agency_id: int
    campaign_id: int
    seeker_id: int
    status: str
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    replied_at: datetime | None = None
    response_text: str | None = None
    created_at: datetime
    seeker_name: str | None = None
    seeker_email: str | None = None


class CampaignAnalyticsOut(BaseModel):
    campaign_id: int
    name: str
    status: str
    channel: str
    target_count: int
    sent_count: int
    opened_count: int
    replied_count: int
    bounced_count: int
    unsubscribed_count: int
    open_rate: float
    reply_rate: float
    status_breakdown: dict[str, int]
    timeline: list[dict]


class AddRecipientsIn(BaseModel):
    seeker_ids: list[int]
