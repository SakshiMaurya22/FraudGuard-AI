from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def liveness() -> dict[str, str]:
    """Process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Process can serve traffic: verifies the database answers a query."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable")
    return {"status": "ready", "database": "ok"}
