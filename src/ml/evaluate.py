"""
src/ml/evaluate.py
Loads saved test results and prints full model evaluation:
  - Classification report (precision, recall, F1 per class)
  - Confusion matrix
  - Anomaly detection recall
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score
)

from config import DATA_DIR, FAULT_CLASSES

RESULTS_NPZ = os.path.join(DATA_DIR, "classifier_test_results.npz")


def evaluate():
    if not os.path.exists(RESULTS_NPZ):
        print("[EVALUATE] No test results found. Run train_classifier.py first.")
        return

    data   = np.load(RESULTS_NPZ)
    y_test = data["y_test"]
    y_pred = data["y_pred"]

    target_names = [FAULT_CLASSES[i] for i in range(6)]

    print("=" * 65)
    print("  DTMS — Fault Classification Evaluation Report")
    print("=" * 65)
    print(f"\n  Accuracy: {accuracy_score(y_test, y_pred):.4f}\n")
    print(classification_report(y_test, y_pred, target_names=target_names, digits=4))

    print("\n  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(cm, index=target_names, columns=target_names)
    print(cm_df.to_string())
    print("=" * 65)


if __name__ == "__main__":
    evaluate()
