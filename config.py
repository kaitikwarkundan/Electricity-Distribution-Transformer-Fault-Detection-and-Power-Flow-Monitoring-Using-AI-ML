"""
config.py — Central configuration for the DTMS project.
All paths, fleet definitions, and system parameters live here.
"""

import os

# ─── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
MODELS_DIR  = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

for _d in (DATA_DIR, MODELS_DIR, REPORTS_DIR):
    os.makedirs(_d, exist_ok=True)

# ─── Database ──────────────────────────────────────────────────────────────────
DB_PATH      = os.path.join(DATA_DIR, "dtms.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ─── API Settings ──────────────────────────────────────────────────────────────
API_HOST     = "127.0.0.1"
API_PORT     = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
WS_BASE_URL  = f"ws://{API_HOST}:{API_PORT}"

# ─── Simulation ────────────────────────────────────────────────────────────────
SIMULATION_INTERVAL_SEC  = 1.0    # seconds between telemetry packets per transformer
TELEMETRY_HISTORY_LIMIT  = 500    # in-memory ring buffer per transformer
FAULT_AUTO_CLEAR_SEC     = 120    # auto-clear injected faults after N seconds

# ─── ML Model Paths ────────────────────────────────────────────────────────────
ISOLATION_FOREST_PATH = os.path.join(MODELS_DIR, "isolation_forest.joblib")
CLASSIFIER_PATH       = os.path.join(MODELS_DIR, "xgb_classifier.joblib")
SCALER_PATH           = os.path.join(MODELS_DIR, "scaler.joblib")
RUL_INSULATION_PATH   = os.path.join(MODELS_DIR, "rul_insulation.joblib")
RUL_OIL_PATH          = os.path.join(MODELS_DIR, "rul_oil.joblib")
RUL_WINDING_PATH      = os.path.join(MODELS_DIR, "rul_winding.joblib")
LABEL_ENCODER_PATH    = os.path.join(MODELS_DIR, "label_encoder.joblib")

# ─── Fault Definitions ─────────────────────────────────────────────────────────
FAULT_CLASSES = {
    0: "Normal Operation",
    1: "Sustained Overload",
    2: "SLG Short Circuit",
    3: "Oil Overheating / Cooling Failure",
    4: "Harmonic Distortion / Phase Unbalance",
    5: "Incipient Insulation Breakdown",
}

FAULT_SEVERITY = {
    0: "NORMAL",
    1: "MEDIUM",
    2: "HIGH",
    3: "HIGH",
    4: "LOW",
    5: "CRITICAL",
}

FAULT_COLORS = {
    "NORMAL":   "#00ff88",
    "LOW":      "#ffe066",
    "MEDIUM":   "#ffb800",
    "HIGH":     "#ff6b35",
    "CRITICAL": "#ff2244",
}

# ─── RUL Thresholds ────────────────────────────────────────────────────────────
RUL_CRITICAL_DAYS = 30    # auto-create CRITICAL work order
RUL_WARNING_DAYS  = 90    # auto-create HIGH work order

# ─── Transformer Fleet ─────────────────────────────────────────────────────────
# 12 transformers across 4 city zones (North/South/East/West)
# install_year drives age-based degradation; type drives diurnal load curve
TRANSFORMER_FLEET = [
    # ── Zone North — Residential ──────────────────────────────────────────────
    {
        "id": "TR-N01", "name": "North Zone – Sector 1 (Residential)",
        "zone": "North",  "type": "Residential",
        "rated_kva": 250, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2015, "lat": 28.720, "lon": 77.100,
    },
    {
        "id": "TR-N02", "name": "North Zone – Sector 2 (Residential)",
        "zone": "North",  "type": "Residential",
        "rated_kva": 400, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2010, "lat": 28.730, "lon": 77.120,
    },
    {
        "id": "TR-N03", "name": "North Zone – Sector 3 (Residential)",
        "zone": "North",  "type": "Residential",
        "rated_kva": 250, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2018, "lat": 28.740, "lon": 77.090,
    },
    # ── Zone South — Commercial ───────────────────────────────────────────────
    {
        "id": "TR-S01", "name": "South Zone – Market Area (Commercial)",
        "zone": "South",  "type": "Commercial",
        "rated_kva": 630, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2012, "lat": 28.610, "lon": 77.200,
    },
    {
        "id": "TR-S02", "name": "South Zone – Hospital Complex (Commercial)",
        "zone": "South",  "type": "Commercial",
        "rated_kva": 400, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2016, "lat": 28.620, "lon": 77.220,
    },
    {
        "id": "TR-S03", "name": "South Zone – Shopping Mall (Commercial)",
        "zone": "South",  "type": "Commercial",
        "rated_kva": 630, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2019, "lat": 28.600, "lon": 77.210,
    },
    # ── Zone East — Industrial ────────────────────────────────────────────────
    {
        "id": "TR-E01", "name": "East Zone – Factory A (Industrial)",
        "zone": "East",   "type": "Industrial",
        "rated_kva": 1000, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2005, "lat": 28.650, "lon": 77.350,
    },
    {
        "id": "TR-E02", "name": "East Zone – Factory B (Industrial)",
        "zone": "East",   "type": "Industrial",
        "rated_kva": 630, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2008, "lat": 28.660, "lon": 77.370,
    },
    {
        "id": "TR-E03", "name": "East Zone – Warehouse District (Industrial)",
        "zone": "East",   "type": "Industrial",
        "rated_kva": 400, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2011, "lat": 28.640, "lon": 77.360,
    },
    # ── Zone West — Mixed ─────────────────────────────────────────────────────
    {
        "id": "TR-W01", "name": "West Zone – Residential Block (Mixed)",
        "zone": "West",  "type": "Mixed",
        "rated_kva": 250, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2020, "lat": 28.680, "lon": 77.050,
    },
    {
        "id": "TR-W02", "name": "West Zone – Commercial Hub (Mixed)",
        "zone": "West",  "type": "Mixed",
        "rated_kva": 400, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2014, "lat": 28.690, "lon": 77.070,
    },
    {
        "id": "TR-W03", "name": "West Zone – School & Offices (Mixed)",
        "zone": "West",  "type": "Mixed",
        "rated_kva": 250, "rated_voltage_primary": 11000, "rated_voltage_secondary": 415,
        "install_year": 2017, "lat": 28.700, "lon": 77.060,
    },
]

# Quick lookup by id
FLEET_BY_ID = {t["id"]: t for t in TRANSFORMER_FLEET}

# ─── Feature columns used by ML models ────────────────────────────────────────
ML_FEATURE_COLS = [
    "v_avg", "i_avg", "v_unbalance", "i_unbalance",
    "oil_temp", "power_factor", "loading_pct",
    "active_power", "reactive_power",
    "thd", "vuf", "h2_ppm",
    "dv_dt", "di_dt", "dt_dt", "i2t_acc",
]

RUL_INSULATION_FEATURES = ["h2_ppm", "thd", "age_years", "i2t_acc", "oil_temp"]
RUL_OIL_FEATURES        = ["oil_temp", "loading_pct", "age_years", "dt_dt", "thd"]
RUL_WINDING_FEATURES    = ["i2t_acc", "loading_pct", "age_years", "i_avg", "i_unbalance"]
