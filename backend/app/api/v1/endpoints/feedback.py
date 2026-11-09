import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.feedback import FeedbackVerdict, InvestigatorFeedback
from app.models.user import User

router = APIRouter(prefix="/feedback", tags=["Investigator Feedback"])


class FeedbackCreate(BaseModel):
    alert_id: uuid.UUID
    verdict: FeedbackVerdict
    notes: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    investigator_id: uuid.UUID
    verdict: FeedbackVerdict
    notes: str | None
    created_at: datetime


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.get(Alert, payload.alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    existing = db.scalar(
        select(InvestigatorFeedback).where(
            InvestigatorFeedback.alert_id == payload.alert_id,
            InvestigatorFeedback.investigator_id == current_user.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted feedback for this alert.",
        )

    feedback = InvestigatorFeedback(
        alert_id=payload.alert_id,
        investigator_id=current_user.id,
        verdict=payload.verdict,
        notes=payload.notes,
    )

    try:
        db.add(feedback)

        # Generate the feedback UUID before creating the audit record.
        db.flush()

        audit_entry = AuditLog(
            actor_id=current_user.id,
            action="investigator_feedback_submitted",
            resource_type="alert",
            resource_id=payload.alert_id,
            event_metadata={
                "feedback_id": str(feedback.id),
                "verdict": payload.verdict.value,
            },
        )

        db.add(audit_entry)

        # Save feedback and audit record in one transaction.
        db.commit()
        db.refresh(feedback)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists or violates a database constraint.",
        )

    return feedback


@router.get("/me", response_model=list[FeedbackResponse])
def get_my_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(InvestigatorFeedback)
        .where(InvestigatorFeedback.investigator_id == current_user.id)
        .order_by(InvestigatorFeedback.created_at.desc())
        .limit(100)
    )

    return list(db.scalars(statement).all())
