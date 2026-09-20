from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SeekerTag(Base):
    __tablename__ = "seeker_tags"
    __table_args__ = (
        PrimaryKeyConstraint("seeker_id", "tag_id", "agency_id"),
    )

    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id", ondelete="CASCADE"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"))
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"))
