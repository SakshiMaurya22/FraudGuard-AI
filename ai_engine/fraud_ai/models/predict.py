"""Load trained bank-specific models and predict transaction fraud."""

from pathlib import Path
import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = PROJECT_ROOT / "ai_engine" / "artifacts"

BANKS = {"alpha", "beta", "gamma"}

IDENTIFIER_COLUMNS = {"transaction_id", "bank_id", "is_fraud"}


def load_model(bank_id: str):
    bank_id = bank_id.lower()

    if bank_id not in BANKS:
        raise ValueError(f"Unsupported bank: {bank_id}")

    artifact_path = ARTIFACT_DIR / bank_id / "random_forest.joblib"

    if not artifact_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

    artifact = joblib.load(artifact_path)

    return artifact


def predict_transaction(bank_id: str, transaction: dict) -> dict:
    artifact = load_model(bank_id)

    model = artifact["model"]
    preprocessor = artifact["preprocessor"]
    feature_columns = artifact["feature_columns"]

    missing = set(feature_columns) - set(transaction)

    if missing:
        raise ValueError(f"Missing transaction features: {sorted(missing)}")

    sample = pd.DataFrame(
        [{column: transaction[column] for column in feature_columns}]
    )

    transformed = preprocessor.transform(sample)

    prediction = int(model.predict(transformed)[0])
    probability = float(model.predict_proba(transformed)[0, 1])
    feature_names = preprocessor.get_feature_names_out()
    importances = model.feature_importances_

    top_indices = importances.argsort()[::-1][:5]

    top_features = [
        {
            "feature": str(feature_names[i]).replace("numeric__", "").replace("categorical__", ""),
            "importance": round(float(importances[i]), 4),
        }
        for i in top_indices
    ]

    return {
        "bank_id": bank_id.lower(),
        "model_name": artifact["model_name"],
        "prediction": "FRAUD" if prediction == 1 else "LEGITIMATE",
        "is_fraud": prediction,
        "fraud_probability": round(probability, 6),
        "top_model_features": top_features,
    }
