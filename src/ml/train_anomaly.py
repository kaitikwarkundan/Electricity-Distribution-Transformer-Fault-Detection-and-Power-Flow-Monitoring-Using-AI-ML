"""
src/ml/train_anomaly.py
Trains an Isolation Forest on normal-operation data only.
Used as Tier 1 (unsupervised) anomaly detector at runtime.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from config import (DATA_DIR, MODELS_DIR, ISOLATION_FOREST_PATH,
                    SCALER_PATH, ML_FEATURE_COLS)

DATASET_CSV = os.path.join(DATA_DIR, "training_dataset.csv")


def train():
    print("[ANOMALY] Loading dataset…")
    df = pd.read_csv(DATASET_CSV)

    # Use only normal-operation samples for Isolation Forest
    normal = df[df["label"] == 0].copy()
    print(f"[ANOMALY] Normal samples: {len(normal):,}")

    X = normal[ML_FEATURE_COLS].values

    # Fit scaler on normal data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("[ANOMALY] Training Isolation Forest…")
    iso = IsolationForest(
        n_estimators=200,
        contamination=0.05,   # 5 % expected outlier rate
        max_features=0.85,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_scaled)

    # Quick sanity check on held-out data
    fault_subset = df[df["label"] != 0].sample(n=min(2000, len(df[df["label"] != 0])), random_state=42)
    X_fault = scaler.transform(fault_subset[ML_FEATURE_COLS].values)
    preds   = iso.predict(X_fault)           # -1 = anomaly
    recall  = (preds == -1).mean()
    print(f"[ANOMALY] Fault recall (anomaly detection): {recall:.2%}")

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(iso,    ISOLATION_FOREST_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"[ANOMALY] Saved -> {ISOLATION_FOREST_PATH}")
    print(f"[ANOMALY] Scaler -> {SCALER_PATH}")


if __name__ == "__main__":
    train()
