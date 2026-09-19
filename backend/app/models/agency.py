from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.workflows import DEFAULT_WORKFLOW, workflow_config
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Agency(Base, TimestampMixin):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), default="starter")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Multi-workflow engine: which recruiting blueprint drives this tenant.
    workflow_type: Mapped[str] = mapped_column(
        String(40), default=DEFAULT_WORKFLOW, server_default=DEFAULT_WORKFLOW
    )
    workflow_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="agency")

    def ensure_workflow_config(self) -> dict[str, Any]:
        """Return the tenant's workflow blueprint, materialising it if unset."""
        if not self.workflow_config or self.workflow_config.get("key") != self.workflow_type:
            self.workflow_config = workflow_config(self.workflow_type)
        return self.workflow_config
