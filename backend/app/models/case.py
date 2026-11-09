import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING = "pending"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


case_alerts = Table(
    "case_alerts",
    Base.metadata,
    Column(
        "case_id",
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "alert_id",
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[CaseStatus] = mapped_column(
        Enum(
            CaseStatus,
            name="case_status",
            values_callable=lambda items: [item.value for item in items],
        ),
        default=CaseStatus.OPEN,
        nullable=False,
    )

    priority: Mapped[CasePriority] = mapped_column(
        Enum(
            CasePriority,
            name="case_priority",
            values_callable=lambda items: [item.value for item in items],
        ),
        default=CasePriority.MEDIUM,
        nullable=False,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    resolution_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        secondary=case_alerts,
    )
