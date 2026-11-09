from pathlib import Path

import numpy as np
import pandas as pd


BANKS = ("alpha", "beta", "gamma")

MERCHANT_CATEGORIES = (
    "grocery", "fuel", "shopping", "travel",
    "restaurant", "electronics", "online_services",
)

PAYMENT_CHANNELS = ("card", "online", "mobile", "bank_transfer")


def generate_bank_transactions(
    bank_id: str,
    n_samples: int = 6000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate reproducible synthetic transactions for one simulated bank."""
    if bank_id not in BANKS:
        raise ValueError(f"Unknown bank_id: {bank_id}")
    if n_samples < 100:
        raise ValueError("n_samples must be at least 100")

    rng = np.random.default_rng(seed + BANKS.index(bank_id) * 10_000)

    fraud_rate = (0.045, 0.055, 0.065)[BANKS.index(bank_id)]
    is_fraud = rng.random(n_samples) < fraud_rate

    hour = rng.integers(0, 24, n_samples)
    day_of_week = rng.integers(0, 7, n_samples)

    amount = rng.lognormal(mean=3.5, sigma=1.0, size=n_samples)
    amount *= rng.lognormal(
        mean=np.where(is_fraud, 0.35, 0.0),
        sigma=0.25,
    )

    merchant = rng.choice(
        MERCHANT_CATEGORIES,
        size=n_samples,
        p=[0.22, 0.12, 0.20, 0.08, 0.15, 0.10, 0.13],
    )

    channel = rng.choice(
        PAYMENT_CHANNELS,
        size=n_samples,
        p=[0.35, 0.30, 0.25, 0.10],
    )

    device_trusted = rng.binomial(
        1,
        np.where(is_fraud, 0.48, 0.94),
    )

    country_mismatch = rng.binomial(
        1,
        np.where(is_fraud, 0.32, 0.025),
    )

    recent_transaction_count = rng.poisson(
        np.where(is_fraud, 5.0, 2.0)
    )

    average_historical_amount = rng.lognormal(
        mean=3.4, sigma=0.85, size=n_samples
    )

    distance_from_home_km = rng.gamma(
        shape=1.5,
        scale=np.where(is_fraud, 35.0, 8.0),
    )

    # Introduce overlap: no individual feature perfectly identifies fraud.
    night_transaction = ((hour <= 5) | (hour >= 23)).astype(int)

    frame = pd.DataFrame({
        "transaction_id": [
            f"{bank_id.upper()}-{i:07d}" for i in range(n_samples)
        ],
        "bank_id": bank_id,
        "amount": np.round(amount, 2),
        "hour": hour,
        "day_of_week": day_of_week,
        "merchant_category": merchant,
        "payment_channel": channel,
        "device_trusted": device_trusted,
        "country_mismatch": country_mismatch,
        "recent_transaction_count": recent_transaction_count,
        "average_historical_amount": np.round(
            average_historical_amount, 2
        ),
        "distance_from_home_km": np.round(
            distance_from_home_km, 2
        ),
        "night_transaction": night_transaction,
        "is_fraud": is_fraud.astype(int),
    })

    return frame


def generate_all_banks(
    output_dir: Path | None = None,
    n_samples: int = 6000,
    seed: int = 42,
) -> dict[str, Path]:
    """Generate and save a separate CSV for each simulated bank."""
    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[2] / "data" / "banks"

    output_dir = Path(output_dir)
    saved_files = {}

    for bank_id in BANKS:
        bank_dir = output_dir / bank_id
        bank_dir.mkdir(parents=True, exist_ok=True)

        frame = generate_bank_transactions(
            bank_id=bank_id,
            n_samples=n_samples,
            seed=seed,
        )

        file_path = bank_dir / "transactions.csv"
        frame.to_csv(file_path, index=False)
        saved_files[bank_id] = file_path

    return saved_files


if __name__ == "__main__":
    paths = generate_all_banks()

    for bank_id, path in paths.items():
        frame = pd.read_csv(path)
        print(
            f"{bank_id}: {len(frame)} transactions | "
            f"fraud={frame['is_fraud'].sum()} | "
            f"saved={path}"
        )
