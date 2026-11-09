
"""In-process federated FedAvg training for FraudGuard AI."""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from fraud_ai.federated.client import FraudBankClient
from fraud_ai.models.federated_model import FraudDetectionNet


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACT_DIR = (
    PROJECT_ROOT / "ai_engine" / "artifacts" / "federated"
)

MODEL_FILENAME = "global_model_validation_split.pt"
HISTORY_FILENAME = "training_history_validation_split.json"

# Training configuration
SEED = 42
ROUNDS = 10
BANKS = ("alpha", "beta", "gamma")

CONFIG = {
    "local_epochs": 2,
    "learning_rate": 0.001,
    "seed": SEED,
}


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FRAUDGUARD AI - IN-PROCESS FEDERATED AVG")
    print("=" * 60)

    # Load the three bank clients.
    clients = {
        bank: FraudBankClient(bank)
        for bank in BANKS
    }

    # Verify the 60/20/20 data split.
    expected_sizes = {
        "train": 3600,
        "validation": 1200,
        "test": 1200,
    }

    for bank, client in clients.items():
        actual_sizes = {
            "train": len(client.X_train),
            "validation": len(client.X_val),
            "test": len(client.X_test),
        }

        if actual_sizes != expected_sizes:
            raise RuntimeError(
                f"{bank.upper()} has unexpected data sizes: "
                f"{actual_sizes}"
            )

    print("\nAll three bank data splits verified.")

    # Initialize the global model directly.
    global_model = FraudDetectionNet(input_dim=20)

    global_arrays = [
        value.detach().cpu().numpy().copy()
        for value in global_model.state_dict().values()
    ]

    history = []

    # Run federated training.
    for round_number in range(1, ROUNDS + 1):
        updates = []
        total_samples = 0
        weighted_loss = 0.0

        print(f"\n{'=' * 45}")
        print(f"FEDERATED ROUND {round_number}/{ROUNDS}")
        print(f"{'=' * 45}")

        for bank, client in clients.items():
            updated, samples, metrics = client.fit(
                global_arrays,
                CONFIG,
            )

            updates.append((updated, samples))
            total_samples += samples
            weighted_loss += samples * metrics["train_loss"]

            print(
                f"{bank.upper()}: {samples} training rows | "
                f"loss={metrics['train_loss']:.4f}"
            )

        if total_samples == 0:
            raise RuntimeError("No training samples were processed")

        # Weighted Federated Averaging.
        new_arrays = []

        for index in range(len(global_arrays)):
            weighted_sum = sum(
                np.asarray(parameters[index], dtype=np.float64) * samples
                for parameters, samples in updates
            )

            averaged = weighted_sum / total_samples

            new_arrays.append(
                averaged.astype(global_arrays[index].dtype)
            )

        global_arrays = new_arrays

        round_loss = weighted_loss / total_samples

        history.append({
            "round": round_number,
            "banks": list(BANKS),
            "training_samples": total_samples,
            "weighted_train_loss": float(round_loss),
        })

        print(
            f"AGGREGATED: {len(updates)} banks | "
            f"{total_samples} rows"
        )
        print(f"WEIGHTED TRAINING LOSS: {round_loss:.4f}")

    # Reconstruct the final global model.
    final_model = FraudDetectionNet(input_dim=20)
    current_state = final_model.state_dict()

    if len(global_arrays) != len(current_state):
        raise RuntimeError("Model parameter count mismatch")

    updated_state = {}

    for (name, current), received in zip(
        current_state.items(),
        global_arrays,
    ):
        received = np.asarray(received)

        if tuple(current.shape) != tuple(received.shape):
            raise RuntimeError(
                f"Model parameter shape mismatch: {name}"
            )

        updated_state[name] = torch.tensor(
            received,
            dtype=current.dtype,
        )

    final_model.load_state_dict(updated_state, strict=True)
    final_model.eval()

    # Save the new model separately.
    model_path = ARTIFACT_DIR / MODEL_FILENAME

    checkpoint = {
        "model_state_dict": final_model.state_dict(),
        "input_dim": 20,
        "model_name": "FraudDetectionNet",
        "aggregation": "FedAvg",
        "rounds": ROUNDS,
        "banks": list(BANKS),
        "local_epochs": CONFIG["local_epochs"],
        "learning_rate": CONFIG["learning_rate"],
        "seed": SEED,
        "data_split": {
            "training": 0.60,
            "validation": 0.20,
            "testing": 0.20,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    torch.save(checkpoint, model_path)

    # Save training history separately.
    history_path = ARTIFACT_DIR / HISTORY_FILENAME

    history_data = {
        "method": "in_process_fedavg",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rounds": ROUNDS,
        "banks": list(BANKS),
        "local_epochs": CONFIG["local_epochs"],
        "learning_rate": CONFIG["learning_rate"],
        "seed": SEED,
        "data_split": {
            "training": 0.60,
            "validation": 0.20,
            "testing": 0.20,
        },
        "round_metrics": history,
    }

    history_path.write_text(
        json.dumps(history_data, indent=2),
        encoding="utf-8",
    )

    # Verify both artifacts.
    if not model_path.exists() or model_path.stat().st_size == 0:
        raise RuntimeError("Model checkpoint was not saved correctly")

    if not history_path.exists() or len(history) != ROUNDS:
        raise RuntimeError("Training history validation failed")

    print("\n" + "=" * 60)
    print("FEDERATED TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("Rounds completed :", len(history))
    print("Banks trained    :", ", ".join(BANKS))
    print("Training rows    :", 10800)
    print("Validation rows  :", 3600)
    print("Test rows        :", 3600)
    print("New global model :", model_path)
    print("Training history :", history_path)
    print("\nPrevious model and history remain untouched.")
    print("=" * 60)


if __name__ == "__main__":
    main()
