from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from google import genai

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import get_settings
from app.models.user import User


router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


SYSTEM_PROMPT = """
You are FraudGuard AI, an assistant for investigators using an
academic federated AI fraud detection platform.

Help investigators understand:
- Fraud detection and risk scores.
- Fraud alerts and investigation workflows.
- Federated learning and FedAvg.
- Model performance and evaluation metrics.
- Financial data privacy and responsible AI.

Give simple, clear, professional answers.
A risk score is an indicator, not proof of fraud.
Never claim to have accessed live bank data or performed actions.
Do not request passwords, API keys, or confidential financial data.
"""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    provider: str


def rule_based_response(message: str) -> str:
    text = message.lower()

    if "federated" in text or "fedavg" in text:
        return (
            "Federated learning allows Alpha, Beta, and Gamma banks "
            "to train a shared fraud detection model without sharing "
            "their raw customer transaction data. Each bank trains "
            "locally and shares model updates. FedAvg combines these "
            "updates into a global model."
        )

    if "risk score" in text or "alert" in text or "fraud" in text:
        return (
            "FraudGuard AI uses risk scores to help investigators "
            "prioritize suspicious transactions. A high score is "
            "an indicator, not proof of fraud. Review the available "
            "evidence before making an investigation decision."
        )

    if "accuracy" in text or "precision" in text or "recall" in text:
        return (
            "Accuracy measures overall correct predictions. Precision "
            "measures how many predicted fraud cases were actually "
            "fraudulent. Recall measures how many actual fraud cases "
            "were detected. These metrics should be considered together."
        )

    if "privacy" in text or "data" in text:
        return (
            "The platform is designed around federated learning. "
            "Raw bank training data remains at the participating bank, "
            "while model parameter updates are used for aggregation. "
            "Protecting credentials and investigating data access "
            "remain important security responsibilities."
        )

    return (
        "I am FraudGuard AI Assistant. I can help explain fraud "
        "detection, alerts, risk scores, federated learning, FedAvg, "
        "model evaluation, and data privacy. "
        "Gemini is not currently available, so I am using the "
        "rule-based assistant."
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()

    if (
        settings.assistant_provider != "rules"
        and settings.gemini_api_key.strip()
    ):
        try:
            client = genai.Client(
                api_key=settings.gemini_api_key.strip()
            )

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=(
                    SYSTEM_PROMPT
                    + "\nInvestigator question: "
                    + payload.message
                ),
            )

            answer = response.text

            if answer and answer.strip():
                return ChatResponse(
                    reply=answer.strip(),
                    provider="gemini",
                )

        except Exception:
            pass

    return ChatResponse(
        reply=rule_based_response(payload.message),
        provider="rules",
    )
