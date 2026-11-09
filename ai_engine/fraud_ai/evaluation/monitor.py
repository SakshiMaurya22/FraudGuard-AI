import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
BANKS = ("alpha", "beta", "gamma")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "banks": {},
    }

    for bank in BANKS:
        bank_dir = ARTIFACTS / bank
        evaluation_file = bank_dir / "evaluation.json"
        bank_report = {"models": {}, "status": "OK"}

        if not evaluation_file.exists():
            bank_report["status"] = "MISSING_EVALUATION"
            report["banks"][bank] = bank_report
            continue

        evaluations = json.loads(evaluation_file.read_text(encoding="utf-8"))

        for model_name, metrics in evaluations.items():
            model_file = bank_dir / f"{model_name}.joblib"

            model_info = {
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1_score": metrics.get("f1_score"),
                "pr_auc": metrics.get("pr_auc"),
                "roc_auc": metrics.get("roc_auc"),
                "confusion_matrix": metrics.get("confusion_matrix"),
                "status": "OK",
            }

            if metrics.get("recall", 1) < 0.80:
                model_info["status"] = "LOW_RECALL"
            elif metrics.get("f1_score", 1) < 0.70:
                model_info["status"] = "LOW_F1"

            if model_file.exists():
                model_info["model_version"] = sha256_file(model_file)
                model_info["model_size_bytes"] = model_file.stat().st_size
                model_info["model_modified_at"] = datetime.fromtimestamp(
                    model_file.stat().st_mtime, timezone.utc
                ).isoformat()
            else:
                model_info["status"] = "MISSING_MODEL"

            bank_report["models"][model_name] = model_info

        report["banks"][bank] = bank_report

    output = ARTIFACTS / "monitoring_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("MODEL MONITORING REPORT")
    print("=" * 45)

    for bank, details in report["banks"].items():
        print(f"\n{bank.upper()}: {details['status']}")
        for name, metrics in details["models"].items():
            print(
                f"  {name}: F1={metrics['f1_score']:.4f}, "
                f"Recall={metrics['recall']:.4f}, "
                f"Status={metrics['status']}"
            )
            if "model_version" in metrics:
                print(f"  SHA-256: {metrics['model_version'][:16]}...")

    print(f"\nReport saved: {output}")


if __name__ == "__main__":
    main()
