import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.audit_log import AuditLog
from app.models.case import Case, CasePriority, CaseStatus
from app.models.user import User


router = APIRouter(
    prefix="/cases",
    tags=["Cases"],
)


class CaseAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_reference: str
    risk_score: float
    severity: AlertSeverity
    status: AlertStatus


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: CaseStatus
    priority: CasePriority
    assigned_to: uuid.UUID | None
    created_by: uuid.UUID
    resolution_summary: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    alerts: list[CaseAlertResponse] = Field(default_factory=list)


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: CasePriority = CasePriority.MEDIUM
    assigned_to: uuid.UUID | None = None
    alert_ids: list[uuid.UUID] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    assigned_to: uuid.UUID | None = None
    resolution_summary: str | None = None
    alert_ids: list[uuid.UUID] | None = None


def validate_assignee(db: Session, assigned_to: uuid.UUID | None):
    if assigned_to is not None and db.get(User, assigned_to) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned investigator not found",
        )


def get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return case


def get_alerts_or_404(db: Session, alert_ids: list[uuid.UUID]) -> list[Alert]:
    if not alert_ids:
        return []

    unique_ids = list(dict.fromkeys(alert_ids))
    statement = select(Alert).where(Alert.id.in_(unique_ids))
    alerts = db.scalars(statement).all()

    if len(alerts) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more alerts were not found",
        )

    return alerts


@router.get("", response_model=list[CaseResponse])
def get_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Case).order_by(Case.created_at.desc())
    return db.scalars(statement).all()


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_assignee(db, payload.assigned_to)
    linked_alerts = get_alerts_or_404(db, payload.alert_ids)

    case = Case(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        created_by=current_user.id,
        alerts=linked_alerts,
    )

    db.add(case)
    db.flush()

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="case_created",
            resource_type="case",
            resource_id=case.id,
            event_metadata={
                "title": case.title,
                "priority": case.priority.value,
                "linked_alert_count": len(linked_alerts),
            },
        )
    )

    db.commit()
    db.refresh(case)

    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_case_or_404(db, case_id)


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: uuid.UUID,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = get_case_or_404(db, case_id)
    changes = payload.model_dump(exclude_unset=True)

    if "title" in changes and changes["title"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Case title cannot be null",
        )

    if "assigned_to" in changes:
        validate_assignee(db, changes["assigned_to"])

    if "alert_ids" in changes:
        case.alerts = get_alerts_or_404(db, changes.pop("alert_ids") or [])

    old_values = {
        key: (
            getattr(case, key).value
            if hasattr(getattr(case, key), "value")
            else str(getattr(case, key))
            if getattr(case, key) is not None
            else None
        )
        for key in changes
    }

    for key, value in changes.items():
        setattr(case, key, value)

    if "status" in changes:
        if case.status == CaseStatus.CLOSED:
            if case.closed_at is None:
                case.closed_at = datetime.now(timezone.utc)
        else:
            case.closed_at = None

    new_values = {
        key: value.value if hasattr(value, "value") else str(value) if value is not None else None
        for key, value in changes.items()
    }

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="case_updated",
            resource_type="case",
            resource_id=case.id,
            event_metadata={
                "old_values": old_values,
                "new_values": new_values,
            },
        )
    )

    db.commit()
    db.refresh(case)

    return case
