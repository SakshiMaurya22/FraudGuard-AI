import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

PROJECT_ROOT = Path(__file__).resolve().parents[5]
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"

if str(AI_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_PATH))

try:
    from fraud_ai.models.predict import predict_transaction
except ImportError as exc:
    raise RuntimeError(f"Unable to load the fraud prediction engine: {exc}") from exc


router = APIRouter(
    prefix="/predictions",
    tags=["Fraud Predictions"],
)


class TransactionInput(BaseModel):
    amount: float = Field(ge=0)
    hour: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    merchant_category: str = Field(min_length=1, max_length=100)
    payment_channel: str = Field(min_length=1, max_length=100)
    device_trusted: int = Field(ge=0, le=1)
    country_mismatch: int = Field(ge=0, le=1)
    recent_transaction_count: int = Field(ge=0)
    average_historical_amount: float = Field(ge=0)
    distance_from_home_km: float = Field(ge=0)
    night_transaction: int = Field(ge=0, le=1)


class PredictionResponse(BaseModel):
    bank_id: str
    model_name: str
    prediction: Literal["FRAUD", "LEGITIMATE"]
    is_fraud: int
    fraud_probability: float
    top_model_features: list[dict]


@router.post(
    "/{bank_id}",
    response_model=PredictionResponse,
)
def predict_fraud(
    bank_id: Literal["alpha", "beta", "gamma"],
    payload: TransactionInput,
    current_user: User = Depends(get_current_user),
):
    try:
        return predict_transaction(
            bank_id=bank_id,
            transaction=payload.model_dump(),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fraud prediction failed. Check the AI engine logs.",
        ) from exc
