"""Runtime settings for a single AI-engine process (one bank client or the coordinator)."""
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BankId = Literal["alpha", "beta", "gamma"]
BANK_DISPLAY_NAMES: dict[str, str] = {"alpha": "Bank Alpha", "beta": "Bank Beta", "gamma": "Bank Gamma"}


class EngineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    bank_id: BankId | None = None            # set for clients; None for the coordinator
    fl_server_address: str = "localhost:8080"
    fl_num_rounds: int = 10
    fl_min_clients: int = 3
    fl_local_epochs: int = 2
    fl_seed: int = 42
    local_data_dir: Path = Path("/app/data/local")   # this bank's data (clients only)
    state_dir: Path = Path("/app/state")             # this bank's checkpoints / alerts
    model_registry_dir: Path = Path("/registry")     # coordinator output (global models)

    @model_validator(mode="after")
    def _validate(self) -> "EngineSettings":
        if self.fl_min_clients < 1 or self.fl_num_rounds < 1 or self.fl_local_epochs < 1:
            raise ValueError("FL rounds, min_clients and local_epochs must be >= 1")
        return self

    @property
    def is_client(self) -> bool:
        return self.bank_id is not None

    def require_client(self) -> BankId:
        if self.bank_id is None:
            raise RuntimeError("BANK_ID must be set (alpha | beta | gamma) to run a bank client")
        return self.bank_id
