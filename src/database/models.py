"""
src/database/models.py — SQLAlchemy ORM models for DTMS.
Defines all database tables: transformers, telemetry, alerts, work_orders, rul_predictions.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime,
    Boolean, ForeignKey, Text, create_engine,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

Base = declarative_base()


class Transformer(Base):
    """Fleet asset registry — one row per physical transformer."""
    __tablename__ = "transformers"

    id                      = Column(String(16), primary_key=True)   # e.g. "TR-N01"
    name                    = Column(String(128), nullable=False)
    zone                    = Column(String(32),  nullable=False)
    type                    = Column(String(32),  nullable=False)     # Residential/Commercial/Industrial/Mixed
    rated_kva               = Column(Integer,     nullable=False)
    rated_voltage_primary   = Column(Integer,     nullable=False)     # V
    rated_voltage_secondary = Column(Integer,     nullable=False)     # V
    install_year            = Column(Integer,     nullable=False)
    lat                     = Column(Float)
    lon                     = Column(Float)
    status                  = Column(String(16),  default="NORMAL")  # NORMAL/WARNING/FAULT/CRITICAL

    telemetry     = relationship("Telemetry",     back_populates="transformer", cascade="all, delete-orphan")
    alerts        = relationship("Alert",         back_populates="transformer", cascade="all, delete-orphan")
    work_orders   = relationship("WorkOrder",     back_populates="transformer", cascade="all, delete-orphan")
    rul_history   = relationship("RULPrediction", back_populates="transformer", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "zone": self.zone, "type": self.type,
            "rated_kva": self.rated_kva,
            "rated_voltage_primary": self.rated_voltage_primary,
            "rated_voltage_secondary": self.rated_voltage_secondary,
            "install_year": self.install_year, "lat": self.lat, "lon": self.lon,
            "status": self.status,
            "age_years": datetime.now().year - self.install_year,
        }


class Telemetry(Base):
    """Every sensor reading + ML inference result, stored permanently."""
    __tablename__ = "telemetry"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id  = Column(String(16), ForeignKey("transformers.id"), nullable=False, index=True)
    timestamp       = Column(DateTime,   nullable=False, index=True)

    # ── Raw 3-phase measurements ──────────────────────────────────────────────
    va = Column(Float)   # Phase A voltage (V)
    vb = Column(Float)   # Phase B voltage (V)
    vc = Column(Float)   # Phase C voltage (V)
    ia = Column(Float)   # Phase A current (A)
    ib = Column(Float)   # Phase B current (A)
    ic = Column(Float)   # Phase C current (A)

    # ── Derived / processed features ─────────────────────────────────────────
    oil_temp       = Column(Float)   # °C
    power_factor   = Column(Float)
    active_power   = Column(Float)   # kW
    reactive_power = Column(Float)   # kVAR
    loading_pct    = Column(Float)   # %
    thd            = Column(Float)   # Total Harmonic Distortion %
    vuf            = Column(Float)   # Voltage Unbalance Factor %
    h2_ppm         = Column(Float)   # Dissolved hydrogen (DGA)
    i2t_acc        = Column(Float)   # Thermal stress accumulation
    dv_dt          = Column(Float)   # dV/dt
    di_dt          = Column(Float)   # dI/dt
    dt_dt          = Column(Float)   # dT_oil/dt
    v_avg          = Column(Float)
    i_avg          = Column(Float)
    v_unbalance    = Column(Float)   # % unbalance
    i_unbalance    = Column(Float)   # % unbalance

    # ── ML inference outputs ──────────────────────────────────────────────────
    anomaly_score    = Column(Float)    # 0–1 from Isolation Forest
    fault_class      = Column(Integer)  # 0–5
    fault_confidence = Column(Float)    # XGBoost confidence
    fault_label      = Column(Integer, default=0)  # Ground truth (from simulator)

    transformer = relationship("Transformer", back_populates="telemetry")

    def to_dict(self):
        return {
            "id": self.id, "transformer_id": self.transformer_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "va": self.va, "vb": self.vb, "vc": self.vc,
            "ia": self.ia, "ib": self.ib, "ic": self.ic,
            "oil_temp": self.oil_temp, "power_factor": self.power_factor,
            "active_power": self.active_power, "reactive_power": self.reactive_power,
            "loading_pct": self.loading_pct, "thd": self.thd, "vuf": self.vuf,
            "h2_ppm": self.h2_ppm, "i2t_acc": self.i2t_acc,
            "dv_dt": self.dv_dt, "di_dt": self.di_dt, "dt_dt": self.dt_dt,
            "v_avg": self.v_avg, "i_avg": self.i_avg,
            "v_unbalance": self.v_unbalance, "i_unbalance": self.i_unbalance,
            "anomaly_score": self.anomaly_score,
            "fault_class": self.fault_class,
            "fault_confidence": self.fault_confidence,
            "fault_label": self.fault_label,
        }


class Alert(Base):
    """Fault event record generated by the ML inference engine."""
    __tablename__ = "alerts"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id  = Column(String(16), ForeignKey("transformers.id"), nullable=False, index=True)
    timestamp       = Column(DateTime,   nullable=False, index=True)
    severity        = Column(String(16), nullable=False)   # LOW/MEDIUM/HIGH/CRITICAL
    fault_type      = Column(String(64), nullable=False)
    fault_class     = Column(Integer)
    confidence      = Column(Float)
    message         = Column(Text)
    acknowledged    = Column(Boolean, default=False)
    acknowledged_by = Column(String(64))
    acknowledged_at = Column(DateTime)

    transformer = relationship("Transformer", back_populates="alerts")
    work_orders = relationship("WorkOrder",   back_populates="alert")

    def to_dict(self):
        return {
            "id": self.id, "transformer_id": self.transformer_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity, "fault_type": self.fault_type,
            "fault_class": self.fault_class, "confidence": self.confidence,
            "message": self.message, "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


class WorkOrder(Base):
    """Maintenance / repair task — auto-created by AI or manually by operators."""
    __tablename__ = "work_orders"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id = Column(String(16), ForeignKey("transformers.id"), nullable=False, index=True)
    alert_id       = Column(Integer,    ForeignKey("alerts.id"),        nullable=True)
    title          = Column(String(128), nullable=False)
    description    = Column(Text)
    priority       = Column(String(16), default="MEDIUM")  # LOW/MEDIUM/HIGH/CRITICAL
    status         = Column(String(16), default="OPEN")    # OPEN/IN_PROGRESS/CLOSED
    assigned_to    = Column(String(64))
    created_at     = Column(DateTime,   nullable=False)
    due_date       = Column(DateTime)
    closed_at      = Column(DateTime)

    transformer = relationship("Transformer", back_populates="work_orders")
    alert       = relationship("Alert",       back_populates="work_orders")

    def to_dict(self):
        return {
            "id": self.id, "transformer_id": self.transformer_id,
            "alert_id": self.alert_id, "title": self.title,
            "description": self.description, "priority": self.priority,
            "status": self.status, "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class RULPrediction(Base):
    """Remaining Useful Life predictions — stored every N seconds per transformer."""
    __tablename__ = "rul_predictions"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id      = Column(String(16), ForeignKey("transformers.id"), nullable=False, index=True)
    timestamp           = Column(DateTime,   nullable=False, index=True)
    insulation_rul_days = Column(Float)   # Days until insulation replacement needed
    oil_rul_days        = Column(Float)   # Days until oil change needed
    winding_rul_days    = Column(Float)   # Days until winding inspection / rewind needed
    overall_health_score= Column(Float)   # 0–100 composite score

    transformer = relationship("Transformer", back_populates="rul_history")

    def to_dict(self):
        return {
            "id": self.id, "transformer_id": self.transformer_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "insulation_rul_days": self.insulation_rul_days,
            "oil_rul_days": self.oil_rul_days,
            "winding_rul_days": self.winding_rul_days,
            "overall_health_score": self.overall_health_score,
        }
