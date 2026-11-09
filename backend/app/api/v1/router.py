from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    assistant,
    auth,
    cases,
    feedback,
    health,
    predictions,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(alerts.router)
api_router.include_router(auth.router)
api_router.include_router(feedback.router)
api_router.include_router(assistant.router)
api_router.include_router(cases.router)
api_router.include_router(predictions.router)


