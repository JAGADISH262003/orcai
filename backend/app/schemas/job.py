from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_id: int
    type: str
    status: str
    attempts: int = 0
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
