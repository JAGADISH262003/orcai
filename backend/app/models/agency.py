from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.workflows import DEFAULT_WORKFLOW, workflow_config
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.agency_settings import AgencySettings
    from app.models.audit import AuditLog
    from app.models.client import Client
    from app.models.consent import ConsentRecord
    from app.models.contract import Contract
    from app.models.document import Document
    from app.models.email_message import EmailMessage
    from app.models.inbound import InboundMessage
    from app.models.interview import Interview
    from app.models.job import Job
    from app.models.match import Match
    from app.models.note import Note
    from app.models.notification import Notification
    from app.models.seeker import Seeker
    from app.models.subscription import Subscription
    from app.models.tag import Tag
    from app.models.user import User


class Agency(Base, TimestampMixin):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), default="starter")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    workflow_type: Mapped[str] = mapped_column(
        String(40), default=DEFAULT_WORKFLOW, server_default=DEFAULT_WORKFLOW
    )
    workflow_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="agency")
    clients: Mapped[list["Client"]] = relationship(back_populates="agency")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="agency")
    seekers: Mapped[list["Seeker"]] = relationship(back_populates="agency")
    matches: Mapped[list["Match"]] = relationship(back_populates="agency")
    jobs: Mapped[list["Job"]] = relationship(back_populates="agency")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="agency")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="agency")
    consent_records: Mapped[list["ConsentRecord"]] = relationship(back_populates="agency")
    inbound_messages: Mapped[list["InboundMessage"]] = relationship(back_populates="agency")
    interviews: Mapped[list["Interview"]] = relationship(back_populates="agency")
    email_messages: Mapped[list["EmailMessage"]] = relationship(back_populates="agency")
    notes: Mapped[list["Note"]] = relationship(back_populates="agency")
    tags: Mapped[list["Tag"]] = relationship(back_populates="agency")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="agency")
    settings_rel: Mapped[list["AgencySettings"]] = relationship(back_populates="agency")
    activities: Mapped[list["Activity"]] = relationship(back_populates="agency")
    documents: Mapped[list["Document"]] = relationship(back_populates="agency")

    def ensure_workflow_config(self) -> dict[str, Any]:
        """Return the tenant's workflow blueprint, materialising it if unset."""
        if not self.workflow_config or self.workflow_config.get("key") != self.workflow_type:
            self.workflow_config = workflow_config(self.workflow_type)
        return self.workflow_config
