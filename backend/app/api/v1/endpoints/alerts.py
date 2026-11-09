
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.audit_log import AuditLog
from app.models.user import User


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_reference: str
    pseudonymized_subject_key: str
    risk_score: float
    severity: AlertSeverity
    status: AlertStatus
    model_version: str
    feature_attributions: dict
    detected_at: datetime
    created_at: datetime


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Alert).order_by(Alert.created_at.desc())
    return db.scalars(statement).all()


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return alert


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(
    alert_id: uuid.UUID,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    old_status = alert.status
    new_status = payload.status

    def _val(s):
        return s.value if hasattr(s, "value") else str(s)

    alert.status = new_status

    if _val(old_status) != _val(new_status):
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="alert_status_changed",
                resource_type="alert",
                resource_id=alert.id,
                event_metadata={
                    "old_status": _val(old_status),
                    "new_status": _val(new_status),
                },
            )
        )

    db.commit()
    db.refresh(alert)

    return alert
