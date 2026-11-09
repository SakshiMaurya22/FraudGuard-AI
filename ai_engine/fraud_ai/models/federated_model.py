"""Shared neural network architecture for federated fraud detection."""

import torch
from torch import nn


class FraudDetectionNet(nn.Module):
    """Binary classifier shared by all federated bank clients."""

    def __init__(self, input_dim: int = 20):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(1)
