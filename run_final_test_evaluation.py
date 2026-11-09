
"""Evaluate the final federated model on untouched test data."""

import json
from datetime import datetime, timezone
from pathlib import Path

import torch

from fraud_ai.federated.client import (
    FraudBankClient,
    get_model_parameters,
)
from fraud_ai.models.federated_model import FraudDetectionNet


PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACT_DIR = PROJECT_ROOT / "ai_engine" / "artifacts" / "federated"

MODEL_PATH = ARTIFACT_DIR / "global_model_validation_split.pt"
THRESHOLD_PATH = ARTIFACT_DIR / "decision_threshold_validation_split.json"
REPORT_PATH = ARTIFACT_DIR / "final_test_evaluation.json"

BANKS = ("alpha", "beta", "gamma")
METRIC_NAMES = ("accuracy", "precision", "recall", "f1", "pr_auc")


def main():
    print("=" * 60)
    print("FRAUDGUARD AI - FINAL HELD-OUT TEST EVALUATION")
    print("=" * 60)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not THRESHOLD_PATH.exists():
        raise FileNotFoundError(f"Threshold file not found: {THRESHOLD_PATH}")

    threshold_data = json.loads(
        THRESHOLD_PATH.read_text(encoding="utf-8")
    )
    threshold = float(threshold_data["threshold"])

    if not 0 < threshold < 1:
        raise ValueError(f"Invalid threshold: {threshold}")

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=False,
    )

    model = FraudDetectionNet(input_dim=checkpoint["input_dim"])
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()

    parameters = get_model_parameters(model)

    bank_results = {}
    total_rows = 0
    weighted_loss = 0.0
    weighted_metrics = {name: 0.0 for name in METRIC_NAMES}

    for bank in BANKS:
        client = FraudBankClient(bank)

        loss, count, metrics = client.evaluate(
            parameters,
            {"threshold": threshold},
        )

        if count != 1200:
            raise RuntimeError(
                f"{bank} expected 1200 test rows, got {count}"
            )

        bank_results[bank] = {
            "test_rows": int(count),
            "loss": float(loss),
            "metrics": {
                name: float(metrics[name])
                for name in METRIC_NAMES
            },
        }

        total_rows += count
        weighted_loss += float(loss) * count

        for name in METRIC_NAMES:
            weighted_metrics[name] += float(metrics[name]) * count

        print(f"\n{bank.upper()} TEST RESULTS")
        print(f"Test rows : {count}")
        print(f"Loss      : {loss:.4f}")
        for name in METRIC_NAMES:
            print(f"{name.upper():10}: {metrics[name]:.4f}")

    if total_rows != 3600:
        raise RuntimeError(
            f"Expected 3600 total test rows, got {total_rows}"
        )

    overall = {
        "test_rows": total_rows,
        "loss": weighted_loss / total_rows,
        "metrics": {
            name: weighted_metrics[name] / total_rows
            for name in METRIC_NAMES
        },
    }

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_file": MODEL_PATH.name,
        "threshold_file": THRESHOLD_PATH.name,
        "decision_threshold": threshold,
        "evaluation_split": "untouched_test",
        "test_rows": total_rows,
        "banks": bank_results,
        "overall": overall,
        "aggregation_note": (
            "Overall metrics are sample-weighted averages "
            "of the three bank-level metrics."
        ),
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("OVERALL HELD-OUT TEST RESULTS")
    print("=" * 60)
    print(f"Test rows : {total_rows}")
    print(f"Threshold : {threshold:.3f}")
    print(f"Loss      : {overall['loss']:.4f}")

    for name, value in overall["metrics"].items():
        print(f"{name.upper():10}: {value:.4f}")

    print("\nFinal report saved to:")
    print(REPORT_PATH)
    print("\nAll three untouched test datasets were evaluated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
