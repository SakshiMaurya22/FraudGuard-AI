
"""Flower client for one bank in the federated fraud platform."""

import argparse
from pathlib import Path

import flwr as fl
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
)

from fraud_ai.data.federated_preprocessing import prepare_federated_data
from fraud_ai.models.federated_model import FraudDetectionNet


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "ai_engine" / "data" / "banks"

BANKS = ("alpha", "beta", "gamma")
BATCH_SIZE = 128
LEARNING_RATE = 0.001


def get_model_parameters(model):
    """Convert model weights into NumPy arrays for Flower."""
    return [
        value.detach().cpu().numpy().copy()
        for value in model.state_dict().values()
    ]


def set_model_parameters(model, parameters):
    """Load received federated parameters into the local model."""
    state_dict = model.state_dict()

    if len(parameters) != len(state_dict):
        raise ValueError("Received parameter count does not match model")

    updated_state = {}

    for (name, current), received in zip(state_dict.items(), parameters):
        array = np.asarray(received)

        if array.shape != tuple(current.shape):
            raise ValueError(f"Parameter shape mismatch: {name}")

        updated_state[name] = torch.tensor(
            array,
            dtype=current.dtype,
        )

    model.load_state_dict(updated_state, strict=True)


class FraudBankClient(fl.client.NumPyClient):
    """One bank's local fraud detection training client."""

    def __init__(self, bank_id: str):
        if bank_id not in BANKS:
            raise ValueError(f"Unsupported bank: {bank_id}")

        self.bank_id = bank_id
        self.device = torch.device("cpu")

        csv_path = DATA_DIR / bank_id / "transactions.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Local dataset not found: {csv_path}")

        dataframe = pd.read_csv(csv_path)
        prepared = prepare_federated_data(dataframe)

        # Training data: used only for local model training.
        self.X_train = torch.tensor(
            prepared["X_train"], dtype=torch.float32
        )
        self.y_train = torch.tensor(
            prepared["y_train"], dtype=torch.float32
        )

        # Validation data: used for threshold selection.
        self.X_val = torch.tensor(
            prepared["X_val"], dtype=torch.float32
        )
        self.y_val = torch.tensor(
            prepared["y_val"], dtype=torch.float32
        )

        # Test data: reserved for final evaluation.
        self.X_test = torch.tensor(
            prepared["X_test"], dtype=torch.float32
        )
        self.y_test = torch.tensor(
            prepared["y_test"], dtype=torch.float32
        )

        self.model = FraudDetectionNet(
            input_dim=len(prepared["feature_names"])
        ).to(self.device)

        positives = self.y_train.sum().item()
        negatives = len(self.y_train) - positives

        self.pos_weight = torch.tensor(
            [negatives / max(positives, 1)],
            dtype=torch.float32,
            device=self.device,
        )

        print(
            f"{bank_id.upper()} client loaded: "
            f"{len(self.X_train)} training rows, "
            f"{len(self.X_val)} validation rows, "
            f"{len(self.X_test)} test rows"
        )

    def get_parameters(self, config):
        return get_model_parameters(self.model)

    def fit(self, parameters, config):
        """Train the local model using training data only."""
        set_model_parameters(self.model, parameters)

        epochs = int(config.get("local_epochs", 2))
        learning_rate = float(config.get("learning_rate", LEARNING_RATE))

        if epochs < 1 or learning_rate <= 0:
            raise ValueError("Invalid local training configuration")

        dataset = TensorDataset(self.X_train, self.y_train)

        generator = torch.Generator().manual_seed(
            int(config.get("seed", 42))
        )

        loader = DataLoader(
            dataset,
            batch_size=BATCH_SIZE,
            shuffle=True,
            generator=generator,
        )

        criterion = nn.BCEWithLogitsLoss(
            pos_weight=self.pos_weight
        )

        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
        )

        self.model.train()
        total_loss = 0.0
        total_samples = 0

        for _ in range(epochs):
            for features, labels in loader:
                features = features.to(self.device)
                labels = labels.to(self.device)

                optimizer.zero_grad()

                logits = self.model(features)
                loss = criterion(logits, labels)

                loss.backward()
                optimizer.step()

                total_loss += loss.item() * len(labels)
                total_samples += len(labels)

        average_loss = total_loss / max(total_samples, 1)

        print(
            f"{self.bank_id.upper()} local training complete: "
            f"loss={average_loss:.4f}, epochs={epochs}"
        )

        return (
            get_model_parameters(self.model),
            len(self.X_train),
            {"train_loss": float(average_loss)},
        )

    def get_validation_predictions(self, parameters=None):
        """Get validation probabilities and labels for threshold tuning."""
        if parameters is not None:
            set_model_parameters(self.model, parameters)

        self.model.eval()

        with torch.no_grad():
            logits = self.model(self.X_val)
            probabilities = torch.sigmoid(logits).cpu().numpy()

        actual = self.y_val.cpu().numpy().astype(int)

        return probabilities, actual

    def evaluate(self, parameters, config):
        """Evaluate the model on the untouched test dataset."""
        set_model_parameters(self.model, parameters)

        self.model.eval()

        criterion = nn.BCEWithLogitsLoss(
            pos_weight=self.pos_weight
        )

        with torch.no_grad():
            logits = self.model(self.X_test)
            loss = criterion(logits, self.y_test).item()
            probabilities = torch.sigmoid(logits).cpu().numpy()

        threshold = float(config.get("threshold", 0.5))

        if not 0 < threshold < 1:
            raise ValueError("Evaluation threshold must be between 0 and 1")

        predictions = (probabilities >= threshold).astype(int)
        actual = self.y_test.cpu().numpy().astype(int)

        metrics = {
            "accuracy": float(accuracy_score(actual, predictions)),
            "precision": float(
                precision_score(actual, predictions, zero_division=0)
            ),
            "recall": float(
                recall_score(actual, predictions, zero_division=0)
            ),
            "f1": float(f1_score(actual, predictions, zero_division=0)),
            "pr_auc": float(
                average_precision_score(actual, probabilities)
            ),
            "threshold": threshold,
        }

        print(
            f"{self.bank_id.upper()} evaluation: "
            f"loss={loss:.4f}, "
            f"threshold={threshold:.3f}, "
            f"F1={metrics['f1']:.4f}, "
            f"PR-AUC={metrics['pr_auc']:.4f}"
        )

        return float(loss), len(self.X_test), metrics


def main():
    parser = argparse.ArgumentParser(
        description="Run a federated fraud detection bank client"
    )

    parser.add_argument(
        "--bank",
        required=True,
        choices=BANKS,
    )

    parser.add_argument(
        "--server",
        default="127.0.0.1:8080",
    )

    args = parser.parse_args()

    client = FraudBankClient(args.bank)

    print(
        f"Connecting {args.bank.upper()} to Flower server "
        f"at {args.server}"
    )

    fl.client.start_client(
        server_address=args.server,
        client=client.to_client(),
    )


if __name__ == "__main__":
    main()
