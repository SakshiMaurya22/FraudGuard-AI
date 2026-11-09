from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from fraud_ai.data.preprocessing import prepare_data


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "ai_engine" / "data" / "banks"
ARTIFACT_ROOT = PROJECT_ROOT / "ai_engine" / "artifacts"


def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    return {
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1_score": float(f1_score(y_test, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": classification_report(
            y_test, predictions, zero_division=0, output_dict=True
        ),
    }


def train_bank(bank_id: str):
    data_path = DATA_ROOT / bank_id / "transactions.csv"

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    dataframe = pd.read_csv(data_path)

    X_train, X_test, y_train, y_test, preprocessor = prepare_data(dataframe)

    models = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }

    bank_artifact_dir = ARTIFACT_ROOT / bank_id
    bank_artifact_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for model_name, model in models.items():
        model.fit(X_train, y_train)

        metrics = evaluate_model(model, X_test, y_test)

        artifact = {
            "bank_id": bank_id,
            "model_name": model_name,
            "model": model,
            "preprocessor": preprocessor,
            "feature_columns": (
                dataframe.columns.drop(["transaction_id", "bank_id", "is_fraud"]).tolist()
            ),
        }

        artifact_path = bank_artifact_dir / f"{model_name}.joblib"
        joblib.dump(artifact, artifact_path)

        results[model_name] = metrics

        print(f"\n{bank_id.upper()} | {model_name}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall:    {metrics['recall']:.4f}")
        print(f"F1-score:  {metrics['f1_score']:.4f}")
        print(f"PR-AUC:    {metrics['pr_auc']:.4f}")
        print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
        print(f"Confusion matrix: {metrics['confusion_matrix']}")
        print(f"Saved model: {artifact_path}")

    results_path = bank_artifact_dir / "evaluation.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return results


def main():
    all_results = {}

    for bank_id in ("alpha", "beta", "gamma"):
        all_results[bank_id] = train_bank(bank_id)

    print("\nALL BANK MODEL TRAINING COMPLETED")
    print(f"Artifacts directory: {ARTIFACT_ROOT}")


if __name__ == "__main__":
    main()
