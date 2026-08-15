"""
src/ml/inference.py
Unified inference interface — takes one raw telemetry packet dict and
returns anomaly score, fault class, confidence, and RUL predictions.

All models are loaded once (lazy) and cached in module-level variables.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import joblib
import logging

from config import (
    ISOLATION_FOREST_PATH, CLASSIFIER_PATH, SCALER_PATH,
    RUL_INSULATION_PATH, RUL_OIL_PATH, RUL_WINDING_PATH,
    ML_FEATURE_COLS,
    RUL_INSULATION_FEATURES, RUL_OIL_FEATURES, RUL_WINDING_FEATURES,
    FAULT_CLASSES, FAULT_SEVERITY,
    RUL_CRITICAL_DAYS, RUL_WARNING_DAYS,
)

log = logging.getLogger("inference")

# ─── Lazy-loaded model cache ───────────────────────────────────────────────────
_iso    = None
_clf    = None
_scaler = None
_rul_ins = None   # (regressor, scaler)
_rul_oil = None
_rul_wnd = None
_models_loaded = False


def load_models():
    global _iso, _clf, _scaler, _rul_ins, _rul_oil, _rul_wnd, _models_loaded
    if _models_loaded:
        return True

    all_ok = True
    for path, label in [
        (ISOLATION_FOREST_PATH, "Isolation Forest"),
        (CLASSIFIER_PATH,       "XGBoost Classifier"),
        (SCALER_PATH,           "Scaler"),
    ]:
        if not os.path.exists(path):
            log.warning(f"Model not found: {path} ({label})")
            all_ok = False

    if not all_ok:
        return False

    try:
        _iso    = joblib.load(ISOLATION_FOREST_PATH)
        _clf    = joblib.load(CLASSIFIER_PATH)
        _scaler = joblib.load(SCALER_PATH)

        if os.path.exists(RUL_INSULATION_PATH):
            _rul_ins = joblib.load(RUL_INSULATION_PATH)
        if os.path.exists(RUL_OIL_PATH):
            _rul_oil = joblib.load(RUL_OIL_PATH)
        if os.path.exists(RUL_WINDING_PATH):
            _rul_wnd = joblib.load(RUL_WINDING_PATH)

        _models_loaded = True
        log.info("[INFERENCE] All models loaded successfully.")
        return True
    except Exception as e:
        log.error(f"[INFERENCE] Model load error: {e}")
        return False


def _extract_features(pkt: dict, feature_cols: list) -> np.ndarray:
    return np.array([[pkt.get(c, 0.0) for c in feature_cols]], dtype=float)


def run_inference(pkt: dict) -> dict:
    """
    Run full 3-tier ML inference on a single telemetry packet.

    Parameters
    ----------
    pkt : dict   Output of TransformerTelemetryGenerator.generate()

    Returns
    -------
    dict with keys:
        anomaly_score, is_anomaly,
        fault_class, fault_name, fault_severity, fault_confidence,
        insulation_rul_days, oil_rul_days, winding_rul_days,
        overall_health_score, rul_alert
    """
    if not _models_loaded:
        load_models()

    result = {
        "anomaly_score":    0.0,
        "is_anomaly":       False,
        "fault_class":      0,
        "fault_name":       FAULT_CLASSES[0],
        "fault_severity":   "NORMAL",
        "fault_confidence": 1.0,
        "insulation_rul_days": None,
        "oil_rul_days":        None,
        "winding_rul_days":    None,
        "overall_health_score": None,
        "rul_alert":        None,
    }

    if not _models_loaded:
        return result

    # ── Tier 1: Isolation Forest ──────────────────────────────────────────────
    try:
        X = _extract_features(pkt, ML_FEATURE_COLS)
        X_s = _scaler.transform(X)

        iso_score = float(_iso.score_samples(X_s)[0])
        # score_samples returns raw anomaly score (more negative = more anomalous)
        # Map to 0–1 range: 0 = normal, 1 = highly anomalous
        anomaly_score = float(np.clip(-iso_score / 0.5, 0, 1))
        is_anomaly    = (_iso.predict(X_s)[0] == -1)

        result["anomaly_score"] = round(anomaly_score, 4)
        result["is_anomaly"]    = bool(is_anomaly)
    except Exception as e:
        log.error(f"[INFERENCE] Isolation Forest error: {e}")

    # ── Tier 2: XGBoost Classifier ────────────────────────────────────────────
    try:
        X   = _extract_features(pkt, ML_FEATURE_COLS)
        X_s = _scaler.transform(X)

        fault_class  = int(_clf.predict(X_s)[0])
        proba        = _clf.predict_proba(X_s)[0]
        confidence   = float(proba[fault_class])

        result["fault_class"]      = fault_class
        result["fault_name"]       = FAULT_CLASSES.get(fault_class, "Unknown")
        result["fault_severity"]   = FAULT_SEVERITY.get(fault_class, "NORMAL")
        result["fault_confidence"] = round(confidence, 4)
    except Exception as e:
        log.error(f"[INFERENCE] XGBoost Classifier error: {e}")

    # ── Tier 3: RUL Predictions ───────────────────────────────────────────────
    rul_vals = {}

    def _predict_rul(model_tuple, features, key):
        if model_tuple is None:
            return None
        reg, scaler = model_tuple
        X = _extract_features(pkt, features)
        X_s = scaler.transform(X)
        return max(0.0, float(reg.predict(X_s)[0]))

    rul_vals["insulation"] = _predict_rul(_rul_ins, RUL_INSULATION_FEATURES, "ins")
    rul_vals["oil"]        = _predict_rul(_rul_oil, RUL_OIL_FEATURES,        "oil")
    rul_vals["winding"]    = _predict_rul(_rul_wnd, RUL_WINDING_FEATURES,    "wnd")

    ins = rul_vals["insulation"]
    oil = rul_vals["oil"]
    wnd = rul_vals["winding"]

    result["insulation_rul_days"] = round(ins, 1) if ins is not None else None
    result["oil_rul_days"]        = round(oil, 1) if oil is not None else None
    result["winding_rul_days"]    = round(wnd, 1) if wnd is not None else None

    # Overall health score (0–100)
    valid = [v for v in [ins, oil, wnd] if v is not None]
    if valid:
        max_lives = [9125.0, 1825.0, 10950.0]
        normalized = []
        for v, mx in zip([ins or mx, oil or mx, wnd or mx], max_lives):
            normalized.append(min(1.0, v / mx))
        health = round(float(np.mean(normalized)) * 100, 1)
        result["overall_health_score"] = health

    # ── RUL Alert ─────────────────────────────────────────────────────────────
    min_rul = min([v for v in [ins, oil, wnd] if v is not None], default=None)
    if min_rul is not None:
        if min_rul <= RUL_CRITICAL_DAYS:
            result["rul_alert"] = "CRITICAL"
        elif min_rul <= RUL_WARNING_DAYS:
            result["rul_alert"] = "WARNING"

    return result


# ── Pre-load at import time if models are available ───────────────────────────
load_models()
