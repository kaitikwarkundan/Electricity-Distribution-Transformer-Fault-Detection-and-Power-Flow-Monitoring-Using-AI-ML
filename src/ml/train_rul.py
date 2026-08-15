"""
src/ml/train_rul.py
Trains 3 separate XGBoost Regressors to predict Remaining Useful Life (days):
  • insulation_rul_days
  • oil_rul_days
  • winding_rul_days
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from config import (DATA_DIR, MODELS_DIR,
                    RUL_INSULATION_PATH, RUL_OIL_PATH, RUL_WINDING_PATH,
                    SCALER_PATH,
                    RUL_INSULATION_FEATURES, RUL_OIL_FEATURES, RUL_WINDING_FEATURES)

DATASET_CSV = os.path.join(DATA_DIR, "training_dataset.csv")

RUL_TARGETS = [
    ("insulation", "insulation_rul_days", RUL_INSULATION_FEATURES, RUL_INSULATION_PATH),
    ("oil",        "oil_rul_days",        RUL_OIL_FEATURES,        RUL_OIL_PATH),
    ("winding",    "winding_rul_days",    RUL_WINDING_FEATURES,    RUL_WINDING_PATH),
]


def _train_rul(name: str, target_col: str, feature_cols: list, save_path: str, df: pd.DataFrame):
    print(f"\n[RUL-{name.upper()}] Features: {feature_cols}")

    # Validate columns exist
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        print(f"[RUL-{name.upper()}] WARNING: missing columns {missing}, skipping.")
        return

    X = df[feature_cols].values
    y = df[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    reg = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )
    reg.fit(X_train_s, y_train, eval_set=[(X_test_s, y_test)], verbose=False)

    y_pred = reg.predict(X_test_s)
    mae  = mean_absolute_error(y_test, y_pred)
    # the squared parameter is deprecated/removed in newer sklearn versions
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    print(f"[RUL-{name.upper()}] MAE={mae:.1f} days  RMSE={rmse:.1f} days")

    os.makedirs(MODELS_DIR, exist_ok=True)

    # Save (regressor, its own scaler) as a tuple
    joblib.dump((reg, scaler), save_path)
    print(f"[RUL-{name.upper()}] Saved -> {save_path}")


def train():
    print("[RUL] Loading dataset…")
    df = pd.read_csv(DATASET_CSV)

    # Add age_years column (approximate from i2t_acc as proxy if not present)
    if "age_years" not in df.columns:
        df["age_years"] = 10   # fallback

    for name, target, features, path in RUL_TARGETS:
        if target not in df.columns:
            print(f"[RUL] Column '{target}' not found — skipping {name}")
            continue
        _train_rul(name, target, features, path, df)

    print("\n[RUL] All RUL regressors trained successfully.")


if __name__ == "__main__":
    train()
