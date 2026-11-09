
"""Tune the fraud decision threshold using validation data only."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from fraud_ai.federated.client import (
    FraudBankClient,
    get_model_parameters,
)
from fraud_ai.models.federated_model import FraudDetectionNet


PROJECT_ROOT = Path(__file__).resolve().parent

ARTIFACT_DIR = (
    PROJECT_ROOT / "ai_engine" / "artifacts" / "federated"
)

MODEL_PATH = ARTIFACT_DIR / "global_model_validation_split.pt"
OUTPUT_PATH = ARTIFACT_DIR / "decision_threshold_validation_split.json"

BANKS = ("alpha", "beta", "gamma")


def main():
    print("=" * 60)
    print("FRAUDGUARD AI - VALIDATION THRESHOLD TUNING")
    print("=" * 60)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"New federated model not found: {MODEL_PATH}"
        )

    # Load the newly trained global model.
    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=False,
    )

    model = FraudDetectionNet(
        input_dim=checkpoint["input_dim"]
    )

    model.load_state_dict(
        checkpoint["model_state_dict"],
        strict=True,
    )

    model.eval()

    parameters = get_model_parameters(model)

    all_probabilities = []
    all_actual = []

    # Collect validation predictions from all three banks.
    for bank in BANKS:
        client = FraudBankClient(bank)

        probabilities, actual = (
            client.get_validation_predictions(parameters)
        )

        all_probabilities.extend(
            np.asarray(probabilities).reshape(-1).tolist()
        )

        all_actual.extend(
            np.asarray(actual).reshape(-1).tolist()
        )

        print(
            f"{bank.upper()}: "
            f"{len(actual)} validation predictions collected"
        )

    probabilities = np.asarray(all_probabilities)
    actual = np.asarray(all_actual, dtype=int)

    if len(actual) == 0:
        raise RuntimeError("No validation predictions collected")

    if len(actual) != 3600:
        raise RuntimeError(
            f"Expected 3600 validation rows, got {len(actual)}"
        )

    if len(np.unique(actual)) != 2:
        raise RuntimeError(
            "Validation data must contain both classes"
        )

    # Search thresholds using validation data only.
    candidates = np.arange(0.05, 0.951, 0.005)

    results = []

    for threshold in candidates:
        predictions = (probabilities >= threshold).astype(int)

        precision = precision_score(
            actual,
            predictions,
            zero_division=0,
        )

        recall = recall_score(
            actual,
            predictions,
            zero_division=0,
        )

        f1 = f1_score(
            actual,
            predictions,
            zero_division=0,
        )

        results.append({
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        })

    # Select the threshold with the best validation F1.
    # If tied, prefer higher precision, then higher threshold.
    best = max(
        results,
        key=lambda item: (
            item["f1"],
            item["precision"],
            item["threshold"],
        ),
    )

    predictions = (
        probabilities >= best["threshold"]
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        actual,
        predictions,
        labels=[0, 1],
    ).ravel()

    output = {
        "method": "validation_f1_optimization",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_file": MODEL_PATH.name,
        "validation_rows": int(len(actual)),
        "threshold": best["threshold"],
        "validation_metrics": {
            "accuracy": float(
                accuracy_score(actual, predictions)
            ),
            "precision": best["precision"],
            "recall": best["recall"],
            "f1": best["f1"],
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "selection": (
            "Maximum validation F1; ties prefer higher precision "
            "and then higher threshold."
        ),
        "threshold_search": {
            "minimum": 0.05,
            "maximum": 0.95,
            "step": 0.005,
            "candidates_tested": len(candidates),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("BEST VALIDATION THRESHOLD")
    print("=" * 60)

    print(f"Threshold  : {best['threshold']:.3f}")
    print(f"Precision  : {best['precision']:.4f}")
    print(f"Recall     : {best['recall']:.4f}")
    print(f"F1 Score   : {best['f1']:.4f}")

    print("\nValidation confusion matrix:")
    print("True negatives :", int(tn))
    print("False positives:", int(fp))
    print("False negatives:", int(fn))
    print("True positives :", int(tp))

    print("\nThreshold saved to:")
    print(OUTPUT_PATH)

    print("\nThe test datasets were NOT used for threshold selection.")
    print("=" * 60)


if __name__ == "__main__":
    main()
