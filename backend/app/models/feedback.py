import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedbackVerdict(str, enum.Enum):
    CONFIRMED_FRAUD = "confirmed_fraud"
    LEGITIMATE = "legitimate"


class InvestigatorFeedback(Base):
    __tablename__ = "investigator_feedback"

    __table_args__ = (
        UniqueConstraint(
            "alert_id",
            "investigator_id",
            name="uq_feedback_alert_investigator",
        ),
        Index(
            "ix_feedback_verdict_created_at",
            "verdict",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )

    investigator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    verdict: Mapped[FeedbackVerdict] = mapped_column(
        Enum(
            FeedbackVerdict,
            name="feedback_verdict",
            values_callable=lambda items: [item.value for item in items],
        ),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
