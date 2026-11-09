
"""Run in-process federated FedAvg training for FraudGuard AI."""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from flwr.common import ndarrays_to_parameters, parameters_to_ndarrays

from fraud_ai.federated.client import FraudBankClient
from fraud_ai.federated import server as coordinator
from fraud_ai.models.federated_model import FraudDetectionNet


SEED = 42
ROUNDS = 10

BANKS = ("alpha", "beta", "gamma")

CONFIG = {
    "local_epochs": 2,
    "learning_rate": 0.001,
    "seed": SEED,
}

MODEL_FILENAME = "global_model_validation_split.pt"
HISTORY_FILENAME = "training_history_validation_split.json"


def set_seed(seed):
    """Set random seeds for reproducible training."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def save_new_global_model(parameters):
    """Save the new model without overwriting the previous checkpoint."""

    arrays = parameters_to_ndarrays(parameters)

    model = FraudDetectionNet(input_dim=20)
    state = model.state_dict()

    if len(arrays) != len(state):
        raise ValueError("Global model parameter count mismatch")

    updated_state = {}

    for (name, current), received in zip(state.items(), arrays):
        received = np.asarray(received)

        if tuple(current.shape) != tuple(received.shape):
            raise ValueError(f"Global model shape mismatch: {name}")

        updated_state[name] = torch.tensor(
            received,
            dtype=current.dtype,
        )

    model.load_state_dict(updated_state, strict=True)
    model.eval()

    model_path = coordinator.ARTIFACT_DIR / MODEL_FILENAME

    checkpoint = {
        "model_state_dict": model.state_dict(),
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

    if not model_path.exists() or model_path.stat().st_size == 0:
        raise RuntimeError("New global model was not saved correctly")

    print(f"\nNEW GLOBAL MODEL SAVED: {model_path}")

    return model_path


def save_new_training_history(history):
    """Save training history without overwriting the previous history."""

    history_path = coordinator.ARTIFACT_DIR / HISTORY_FILENAME

    result = {
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
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    if not history_path.exists() or len(history) != ROUNDS:
        raise RuntimeError("Training history validation failed")

    print(f"NEW TRAINING HISTORY SAVED: {history_path}")

    return history_path


def main():
    set_seed(SEED)

    coordinator.ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("FRAUDGUARD AI - IN-PROCESS FEDERATED AVG")
    print("=" * 60)

    print("Banks          :", ", ".join(BANKS))
    print("Federated rounds:", ROUNDS)
    print("Local epochs   :", CONFIG["local_epochs"])
    print("Learning rate  :", CONFIG["learning_rate"])
    print("Aggregation    : FedAvg")
    print("Data split     : 60% / 20% / 20%")
    print("=" * 60)

    # Load all three bank clients.
    clients = {
        bank: FraudBankClient(bank)
        for bank in BANKS
    }

    # Confirm that every client has the expected data split.
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
                f"{bank.upper()} has unexpected dataset sizes: "
                f"{actual_sizes}"
            )

    print("\nAll three bank data splits verified.")

    # Initialize the global model.
    global_parameters = coordinator.initial_parameters()
    global_arrays = parameters_to_ndarrays(global_parameters)

    history = []

    # Federated training.
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
                f"{bank.upper()}: "
                f"{samples} training rows | "
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

        global_parameters = ndarrays_to_parameters(global_arrays)

        round_loss = weighted_loss / total_samples

        history.append({
            "round": round_number,
            "banks": list(BANKS),
            "training_samples": total_samples,
            "weighted_train_loss": float(round_loss),
        })

        print("\nAGGREGATION COMPLETE")
        print("Participating banks:", len(updates))
        print("Total training rows:", total_samples)
        print(f"Weighted training loss: {round_loss:.4f}")

    # Save the new model and history separately.
    model_path = save_new_global_model(global_parameters)

    history_path = save_new_training_history(history)

    # Final artifact checks.
    assert model_path.exists()
    assert model_path.stat().st_size > 0

    assert history_path.exists()
    assert len(history) == ROUNDS

    print("\n" + "=" * 60)
    print("FEDERATED TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("Rounds completed :", len(history))
    print("Banks trained    :", ", ".join(BANKS))
    print("Training rows    :", 10800)
    print("Validation rows  :", 3600)
    print("Test rows        :", 3600)

    print("New global model :", model_path)
    print("New history      :", history_path)

    print("\nPrevious global model has not been overwritten.")
    print("=" * 60)


if __name__ == "__main__":
    main()
