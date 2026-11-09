from __future__ import annotations

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "is_fraud"

NUMERIC_FEATURES = [
    "amount",
    "hour",
    "day_of_week",
    "device_trusted",
    "country_mismatch",
    "recent_transaction_count",
    "average_historical_amount",
    "distance_from_home_km",
    "night_transaction",
]

CATEGORICAL_FEATURES = [
    "merchant_category",
    "payment_channel",
]

REQUIRED_COLUMNS = (
    NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET_COLUMN]
)


def build_preprocessor() -> ColumnTransformer:
    """Build transformations for numerical and categorical features."""
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def prepare_data(
    dataframe: pd.DataFrame,
    test_size: float = 0.20,
    random_state: int = 42,
):
    """Split one bank's data and fit preprocessing on training data only."""
    missing = set(REQUIRED_COLUMNS) - set(dataframe.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")

    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    if dataframe[TARGET_COLUMN].isna().any():
        raise ValueError("Fraud labels contain missing values")

    labels = set(dataframe[TARGET_COLUMN].unique())
    if not labels.issubset({0, 1}) or len(labels) != 2:
        raise ValueError("Fraud labels must contain both 0 and 1")

    X = dataframe[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y = dataframe[TARGET_COLUMN].astype("int64").copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    preprocessor = build_preprocessor()

    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)

    return (
        X_train_processed,
        X_test_processed,
        y_train.to_numpy(),
        y_test.to_numpy(),
        preprocessor,
    )
