"""
src/ml/train_classifier.py
Trains an XGBoost multi-class classifier (Tier 2 — fault type identification).
6 classes: 0=Normal … 5=Incipient Insulation Breakdown.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier

from config import (DATA_DIR, MODELS_DIR, CLASSIFIER_PATH,
                    SCALER_PATH, ML_FEATURE_COLS, FAULT_CLASSES)

DATASET_CSV = os.path.join(DATA_DIR, "training_dataset.csv")


def train():
    print("[CLASSIFIER] Loading dataset…")
    df = pd.read_csv(DATASET_CSV)
    print(f"[CLASSIFIER] Total samples: {len(df):,}")
    print(f"[CLASSIFIER] Class distribution:\n{df['label'].value_counts().sort_index()}\n")

    X = df[ML_FEATURE_COLS].values
    y = df["label"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Load shared scaler (created by train_anomaly.py)
    if os.path.exists(SCALER_PATH):
        scaler = joblib.load(SCALER_PATH)
    else:
        scaler = StandardScaler()
        scaler.fit(X_train)
        joblib.dump(scaler, SCALER_PATH)

    X_train_s = scaler.transform(X_train)
    X_test_s  = scaler.transform(X_test)

    print("[CLASSIFIER] Training XGBoost classifier…")
    clf = XGBClassifier(
        n_estimators=400,
        max_depth=7,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        use_label_encoder=False,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(
        X_train_s, y_train,
        eval_set=[(X_test_s, y_test)],
        verbose=50,
    )

    y_pred = clf.predict(X_test_s)
    print("\n[CLASSIFIER] Classification Report:")
    target_names = [FAULT_CLASSES[i] for i in range(6)]
    print(classification_report(y_test, y_pred, target_names=target_names))

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(clf, CLASSIFIER_PATH)
    print(f"[CLASSIFIER] Saved -> {CLASSIFIER_PATH}")

    # Save test results for evaluation module
    results_path = os.path.join(DATA_DIR, "classifier_test_results.npz")
    np.savez(results_path, y_test=y_test, y_pred=y_pred)
    print(f"[CLASSIFIER] Test results saved -> {results_path}")


if __name__ == "__main__":
    train()
