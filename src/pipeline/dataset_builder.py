"""
src/pipeline/dataset_builder.py
Generates a large labelled synthetic training dataset by fast-forwarding
the simulator through multiple days and all fault modes.

Outputs:
  data/training_dataset.csv    — main labelled dataset (fault classification + RUL)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config import TRANSFORMER_FLEET, DATA_DIR, ML_FEATURE_COLS
from src.simulator.telemetry_generator import TransformerTelemetryGenerator

OUTPUT_CSV = os.path.join(DATA_DIR, "training_dataset.csv")

# ── Samples per class ──────────────────────────────────────────────────────────
NORMAL_PER_TRANSFORMER = 5_000    # 60_000 normal total across 12 transformers
FAULT_PER_TYPE         = 8_000    # 8_000 per fault class (classes 1-5)

# ── RUL label generation ───────────────────────────────────────────────────────
# We estimate RUL (days) from the generator state after N cycles of a fault.
# Real RUL = rated_life_days - accumulated_degradation

INSULATION_MAX_LIFE_DAYS = 9_125   # ~25 years
OIL_MAX_LIFE_DAYS        = 1_825   # ~5 years (oil change cycle)
WINDING_MAX_LIFE_DAYS    = 10_950  # ~30 years

def _compute_rul(pkt: dict) -> dict:
    """Heuristic RUL labels derived from simulator state features."""
    age   = pkt.get("age_years", 10)
    h2    = pkt.get("h2_ppm",    10.0)
    thd   = pkt.get("thd",       3.0)
    oil_t = pkt.get("oil_temp",  55.0)
    i2t   = pkt.get("i2t_acc",   1e6)

    # Insulation RUL: decreases with H2 ppm and age
    ins_consumed = (age / 25.0) * 0.7 + (min(h2, 500) / 500.0) * 0.2 + (min(thd, 20) / 20.0) * 0.1
    ins_rul = max(30, INSULATION_MAX_LIFE_DAYS * (1 - ins_consumed))

    # Oil RUL: decreases with thermal cycling
    oil_factor   = max(0, min(1, (oil_t - 40) / 60.0))    # 0 at 40°C, 1 at 100°C
    oil_consumed = (age % 5) / 5.0 * 0.6 + oil_factor * 0.4
    oil_rul = max(14, OIL_MAX_LIFE_DAYS * (1 - oil_consumed))

    # Winding RUL: decreases with I²t accumulation
    i2t_norm     = min(1.0, i2t / (WINDING_MAX_LIFE_DAYS * 86400 * (pkt.get("rated_i", 500) ** 2) * 0.5))
    wind_consumed= (age / 30.0) * 0.5 + i2t_norm * 0.5
    winding_rul  = max(60, WINDING_MAX_LIFE_DAYS * (1 - wind_consumed))

    # Overall health (0–100, 100 = perfect)
    health = 100.0 * (1 - (ins_consumed * 0.4 + oil_consumed * 0.3 + wind_consumed * 0.3))
    health = float(np.clip(health, 0, 100))

    return {
        "insulation_rul_days": round(ins_rul, 1),
        "oil_rul_days":        round(oil_rul, 1),
        "winding_rul_days":    round(winding_rul, 1),
        "overall_health_score": round(health, 1),
    }


def _generate_normal_samples(cfg: dict, n: int, rng) -> list:
    gen = TransformerTelemetryGenerator(cfg, rng=rng)
    rows = []
    base_ts = datetime(2026, 1, 1, 0, 0, 0)
    # Spread over 30 days to capture all hours
    step_sec = 30 * 24 * 3600 / n
    for i in range(n):
        ts = base_ts + timedelta(seconds=i * step_sec)
        pkt = gen.generate(ts)
        rul = _compute_rul(pkt)
        rows.append({**pkt, **rul})
    return rows


def _generate_fault_samples(cfg: dict, fault_mode: int, n: int, rng) -> list:
    gen = TransformerTelemetryGenerator(cfg, rng=rng)
    # Warm up for 60 steps at normal so state is realistic
    base_ts = datetime(2026, 3, 15, 14, 0, 0)
    for i in range(60):
        gen.generate(base_ts + timedelta(seconds=i))

    # Inject fault with varying severity
    rows = []
    for i in range(n):
        severity = rng.uniform(0.3, 1.0)
        gen.set_fault(fault_mode, severity)
        ts  = base_ts + timedelta(seconds=60 + i)
        pkt = gen.generate(ts)
        rul = _compute_rul(pkt)
        rows.append({**pkt, **rul})
    return rows


def build_dataset():
    print("[DATASET] Building training dataset…")
    all_rows = []
    master_rng = np.random.default_rng(42)

    # ── Normal samples (all 12 transformers) ──────────────────────────────────
    for cfg in TRANSFORMER_FLEET:
        rng  = np.random.default_rng(master_rng.integers(1e9))
        rows = _generate_normal_samples(cfg, NORMAL_PER_TRANSFORMER, rng)
        all_rows.extend(rows)
        print(f"  [OK] Normal — {cfg['id']} ({len(rows)} samples)")

    # ── Fault samples (spread across a subset of transformers) ────────────────
    for fault_mode in range(1, 6):
        # Use 2 transformers per fault type for diversity
        for cfg in TRANSFORMER_FLEET[::6][:2]:
            rng  = np.random.default_rng(master_rng.integers(1e9))
            rows = _generate_fault_samples(cfg, fault_mode, FAULT_PER_TYPE // 2, rng)
            all_rows.extend(rows)
        print(f"  [OK] Fault class {fault_mode} ({FAULT_PER_TYPE} samples)")

    df = pd.DataFrame(all_rows)

    # Drop metadata columns not needed for ML
    drop_cols = ["transformer_id", "timestamp", "rated_i"]
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # Ensure fault_label is the class column
    df.rename(columns={"fault_label": "label"}, inplace=True)

    # Fill any NaNs
    df.fillna(df.median(numeric_only=True), inplace=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    label_counts = df["label"].value_counts().sort_index()
    print(f"\n[DATASET] Saved -> {OUTPUT_CSV}")
    print(f"[DATASET] Total rows : {len(df):,}")
    print(f"[DATASET] Class distribution:\n{label_counts.to_string()}\n")
    return df


if __name__ == "__main__":
    build_dataset()
