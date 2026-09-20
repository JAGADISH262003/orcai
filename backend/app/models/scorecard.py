from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.interview import Interview
    from app.models.user import User


class ScorecardTemplate(Base, TimestampMixin):
    __tablename__ = "scorecard_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    is_default: Mapped[bool] = mapped_column(default=False)

    agency: Mapped["Agency"] = relationship(back_populates="scorecard_templates")


class Scorecard(Base, TimestampMixin):
    __tablename__ = "scorecards"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("scorecard_templates.id"), index=True)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scores: Mapped[list] = mapped_column(JSON, default=list)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="scorecards")
    interview: Mapped["Interview"] = relationship()
    template: Mapped["ScorecardTemplate"] = relationship()
    evaluator: Mapped["User"] = relationship()
