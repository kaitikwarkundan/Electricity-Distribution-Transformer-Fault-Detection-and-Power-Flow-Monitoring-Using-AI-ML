"""
src/simulator/telemetry_generator.py
Generates realistic 3-phase distribution transformer telemetry.

Each TransformerTelemetryGenerator instance owns a single transformer's
state machine (oil temperature, DGA accumulation, I²t stress) and produces
one telemetry dict per call to .generate(timestamp).

Fault modes are applied on top of the normal diurnal load curves.
"""

import math
import numpy as np
from datetime import datetime

# ─── Diurnal load curves (24 hourly fractions, 0→1) ──────────────────────────

_CURVES = {
    "Residential": [
        0.25, 0.22, 0.20, 0.20, 0.22, 0.30, 0.55, 0.70,
        0.65, 0.50, 0.45, 0.42, 0.40, 0.42, 0.45, 0.50,
        0.58, 0.72, 0.85, 0.88, 0.80, 0.65, 0.50, 0.35,
    ],
    "Commercial": [
        0.10, 0.08, 0.08, 0.08, 0.10, 0.15, 0.30, 0.55,
        0.75, 0.85, 0.90, 0.88, 0.85, 0.82, 0.80, 0.78,
        0.75, 0.65, 0.50, 0.35, 0.25, 0.18, 0.12, 0.10,
    ],
    "Industrial": [
        0.55, 0.52, 0.50, 0.50, 0.52, 0.55, 0.65, 0.80,
        0.88, 0.90, 0.92, 0.90, 0.85, 0.88, 0.90, 0.88,
        0.85, 0.80, 0.75, 0.65, 0.60, 0.58, 0.56, 0.55,
    ],
    "Mixed": [
        0.30, 0.28, 0.25, 0.25, 0.27, 0.35, 0.50, 0.65,
        0.72, 0.75, 0.78, 0.75, 0.70, 0.72, 0.75, 0.72,
        0.68, 0.72, 0.78, 0.80, 0.70, 0.58, 0.45, 0.35,
    ],
}


def _load_factor(hour_float: float, zone_type: str) -> float:
    """Interpolated load fraction for fractional hours."""
    curve = _CURVES.get(zone_type, _CURVES["Mixed"])
    h     = int(hour_float) % 24
    nh    = (h + 1) % 24
    frac  = hour_float - int(hour_float)
    return curve[h] * (1 - frac) + curve[nh] * frac


class TransformerTelemetryGenerator:
    """
    State machine for one distribution transformer.

    Parameters
    ----------
    cfg : dict   One entry from config.TRANSFORMER_FLEET
    rng : np.random.Generator  Optional seeded RNG for reproducibility
    """

    def __init__(self, cfg: dict, rng=None):
        self.cfg         = cfg
        self.rng         = rng or np.random.default_rng()
        self.rated_kva   = cfg["rated_kva"]
        self.rated_v_sec = cfg["rated_voltage_secondary"]   # 415 V
        self.rated_i     = (self.rated_kva * 1000) / (math.sqrt(3) * self.rated_v_sec)
        self.zone_type   = cfg["type"]
        self.age_years   = max(1, datetime.now().year - cfg["install_year"])

        # Age-based baseline degradation (0–1)
        self.age_deg = min(0.95, self.age_years / 30.0)

        # ── Persistent state variables ────────────────────────────────────────
        self.oil_temp      = 42.0 + self.rng.uniform(-3, 3)
        self.h2_ppm        = 5.0 + self.age_years * 2.5 + self.rng.uniform(0, 5)
        self.i2t_acc       = self.age_years * 500_000 + self.rng.uniform(0, 50_000)

        # Previous-cycle values (for rate-of-change features)
        self._prev_v_avg  = self.rated_v_sec / math.sqrt(3)
        self._prev_i_avg  = self.rated_i * 0.5
        self._prev_oil    = self.oil_temp

        # Fault state
        self.fault_mode     = 0
        self.fault_severity = 0.0

    # ── Public control API ────────────────────────────────────────────────────

    def set_fault(self, mode: int, severity: float = 1.0):
        self.fault_mode     = mode
        self.fault_severity = float(np.clip(severity, 0, 1))

    def clear_fault(self):
        self.fault_mode     = 0
        self.fault_severity = 0.0

    # ── Core generator ────────────────────────────────────────────────────────

    def generate(self, timestamp: datetime) -> dict:
        rng = self.rng
        hour = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0

        # ── Diurnal load ──────────────────────────────────────────────────────
        lf = _load_factor(hour, self.zone_type)
        lf = float(np.clip(lf + rng.normal(0, 0.02), 0.05, 1.4))

        v_phase = self.rated_v_sec / math.sqrt(3)   # ~240 V nominal

        # ── Balanced 3-phase base values ─────────────────────────────────────
        va = v_phase + rng.normal(0, 0.8)
        vb = v_phase + rng.normal(0, 0.8)
        vc = v_phase + rng.normal(0, 0.8)

        i_base = self.rated_i * lf
        ia = max(0.0, i_base + rng.normal(0, i_base * 0.02))
        ib = max(0.0, i_base + rng.normal(0, i_base * 0.02))
        ic = max(0.0, i_base + rng.normal(0, i_base * 0.02))

        # ── Oil temperature thermal model ─────────────────────────────────────
        # Target temperature = 40 °C (no-load) + 37 °C (full-load)
        target_oil = 40.0 + 37.0 * lf + self.age_deg * 5.0
        alpha = 1.0 / 600.0                        # thermal time constant ~10 min
        self.oil_temp += alpha * (target_oil - self.oil_temp)
        self.oil_temp += rng.normal(0, 0.08)
        oil_temp = self.oil_temp

        # ── Power factor ──────────────────────────────────────────────────────
        pf_base = {"Industrial": 0.87, "Commercial": 0.90}.get(self.zone_type, 0.92)
        pf = float(np.clip(pf_base + rng.normal(0, 0.008), 0.70, 0.995))

        # ── THD — age-biased baseline ─────────────────────────────────────────
        thd = 2.5 + self.age_deg * 2.0 + rng.normal(0, 0.3)

        # ── DGA accumulation ──────────────────────────────────────────────────
        self.h2_ppm += rng.normal(0.002, 0.001) * (1 + self.age_deg)
        h2_ppm = float(max(0, self.h2_ppm + rng.normal(0, 0.4)))

        # ── I²t thermal stress ────────────────────────────────────────────────
        i_rms_now = (ia + ib + ic) / 3.0
        self.i2t_acc += i_rms_now ** 2 * 1.0   # Δt = 1 s

        # ━━━ Apply fault effects ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        fm  = self.fault_mode
        fsv = self.fault_severity

        if fm == 1:   # Sustained Overload
            ov = 1.22 + 0.40 * fsv
            ia *= ov; ib *= ov; ic *= ov
            va *= (1 - 0.06 * fsv)
            vb *= (1 - 0.06 * fsv)
            vc *= (1 - 0.06 * fsv)
            self.oil_temp += 0.25 * fsv

        elif fm == 2:  # SLG Short Circuit (Phase A)
            ia *= (3.5 + 2.5 * fsv)
            va *= max(0.1, 0.55 - 0.35 * fsv)
            pf  = float(np.clip(0.45 + rng.normal(0, 0.06), 0.30, 0.70))

        elif fm == 3:  # Oil Overheating / Cooling Failure
            self.oil_temp += 1.2 * fsv
            oil_temp = self.oil_temp

        elif fm == 4:  # Harmonic Distortion / Phase Unbalance
            ib *= (1 + 0.35 * fsv)
            ic *= (1 - 0.22 * fsv)
            va *= (1 - 0.03 * fsv)
            thd = 8.5 + 6.0 * fsv + rng.normal(0, 0.5)
            pf  = float(np.clip(pf - 0.18 * fsv, 0.60, 0.99))

        elif fm == 5:  # Incipient Insulation Breakdown (DGA spike)
            self.h2_ppm += 8.0 * fsv
            h2_ppm = float(max(0, self.h2_ppm + rng.normal(0, 1.5)))
            thd   += 2.0 * fsv

        # ── Clamp to physical limits ──────────────────────────────────────────
        va = float(np.clip(va, 0, v_phase * 1.5))
        vb = float(np.clip(vb, 0, v_phase * 1.5))
        vc = float(np.clip(vc, 0, v_phase * 1.5))
        ia = float(max(0, ia)); ib = float(max(0, ib)); ic = float(max(0, ic))
        thd = float(np.clip(thd, 0, 40))
        oil_temp = float(np.clip(oil_temp, 20, 140))
        pf = float(np.clip(pf, 0.30, 0.999))

        # ── Derived features ──────────────────────────────────────────────────
        v_avg = (va + vb + vc) / 3.0
        i_avg = (ia + ib + ic) / 3.0

        # Voltage Unbalance Factor (NEMA definition) %
        v_max_dev = max(abs(va - v_avg), abs(vb - v_avg), abs(vc - v_avg))
        vuf = (v_max_dev / v_avg * 100.0) if v_avg > 0 else 0.0

        # Current unbalance %
        i_max_dev = max(abs(ia - i_avg), abs(ib - i_avg), abs(ic - i_avg))
        i_unbalance = (i_max_dev / i_avg * 100.0) if i_avg > 0 else 0.0

        # Power (3-phase, using average phase quantities)
        active_power   = 3 * v_avg * i_avg * pf / 1000.0        # kW
        reactive_power = 3 * v_avg * i_avg * math.sqrt(max(0, 1 - pf**2)) / 1000.0  # kVAR
        apparent_power = math.sqrt(active_power**2 + reactive_power**2)
        loading_pct    = (apparent_power / self.rated_kva) * 100.0

        # Rate of change features (per second)
        dv_dt = v_avg - self._prev_v_avg
        di_dt = i_avg - self._prev_i_avg
        dt_dt = oil_temp - self._prev_oil

        self._prev_v_avg = v_avg
        self._prev_i_avg = i_avg
        self._prev_oil   = oil_temp

        return {
            "transformer_id": self.cfg["id"],
            "timestamp":      timestamp.isoformat(),
            # Raw 3-phase
            "va": round(va, 2), "vb": round(vb, 2), "vc": round(vc, 2),
            "ia": round(ia, 2), "ib": round(ib, 2), "ic": round(ic, 2),
            # Derived
            "oil_temp":       round(oil_temp, 2),
            "power_factor":   round(pf, 4),
            "active_power":   round(active_power, 2),
            "reactive_power": round(reactive_power, 2),
            "loading_pct":    round(loading_pct, 2),
            "thd":            round(thd, 2),
            "vuf":            round(vuf, 3),
            "h2_ppm":         round(h2_ppm, 2),
            "i2t_acc":        round(self.i2t_acc, 1),
            "dv_dt":          round(dv_dt, 3),
            "di_dt":          round(di_dt, 3),
            "dt_dt":          round(dt_dt, 4),
            "v_avg":          round(v_avg, 2),
            "i_avg":          round(i_avg, 2),
            "v_unbalance":    round(vuf, 3),
            "i_unbalance":    round(i_unbalance, 3),
            "fault_label":    self.fault_mode,
            # Metadata
            "rated_i":        round(self.rated_i, 1),
            "age_years":      self.age_years,
        }
