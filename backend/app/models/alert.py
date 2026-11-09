
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Alert(Base):
    __tablename__ = "alerts"

    __table_args__ = (
        Index("ix_alerts_status_created_at", "status", "created_at"),
        Index("ix_alerts_bank_reference", "bank_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    bank_reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    pseudonymized_subject_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity",
            values_callable=lambda items: [item.value for item in items],
        ),
        nullable=False,
    )

    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status",
            values_callable=lambda items: [item.value for item in items],
        ),
        default=AlertStatus.NEW,
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    feature_attributions: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
