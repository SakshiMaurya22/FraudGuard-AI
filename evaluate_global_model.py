import json
import torch
import numpy as np
from pathlib import Path

from fraud_ai.federated.client import (
    FraudBankClient,
    get_model_parameters,
    set_model_parameters,
)

ROOT = Path("ai_engine/artifacts/federated")
checkpoint = torch.load(
    ROOT / "global_model.pt",
    map_location="cpu",
    weights_only=False,
)

results = []
total = 0

print("=" * 55)
print("GLOBAL FEDERATED MODEL - TEST EVALUATION")
print("=" * 55)

for bank in ("alpha", "beta", "gamma"):
    client = FraudBankClient(bank)
    client.model.load_state_dict(
        checkpoint["model_state_dict"],
        strict=True,
    )

    parameters = get_model_parameters(client.model)
    loss, count, metrics = client.evaluate(parameters, {})

    results.append({
        "bank": bank,
        "test_samples": count,
        "loss": loss,
        **metrics,
    })
    total += count

    print(f"\n{bank.upper()} TEST RESULTS")
    for name, value in metrics.items():
        print(f"{name.upper():10}: {value:.4f} ({value*100:.2f}%)")

names = ("accuracy", "precision", "recall", "f1", "pr_auc")

overall = {
    name: float(
        sum(r[name] * r["test_samples"] for r in results) / total
    )
    for name in names
}

report = {
    "model": checkpoint["model_name"],
    "aggregation": checkpoint["aggregation"],
    "test_samples": total,
    "bank_results": results,
    "weighted_overall": overall,
}

(ROOT / "evaluation_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("\n" + "=" * 55)
print("WEIGHTED OVERALL TEST RESULTS")
for name, value in overall.items():
    print(f"{name.upper():10}: {value:.4f} ({value*100:.2f}%)")

print("TOTAL TEST SAMPLES:", total)
print("REPORT SAVED:", ROOT / "evaluation_report.json")
print("=" * 55)
