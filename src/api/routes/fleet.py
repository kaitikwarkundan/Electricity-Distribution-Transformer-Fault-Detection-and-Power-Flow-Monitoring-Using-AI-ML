"""
src/api/routes/fleet.py — Fleet-level REST endpoints.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from src.database.init_db import get_session
from src.database.models import Transformer, Telemetry, Alert
from src.simulator.orchestrator import get_latest, get_history, get_all_latest, inject_fault, clear_fault
from src.api.schemas import FaultInjectRequest
from config import FAULT_CLASSES, FAULT_SEVERITY, TRANSFORMER_FLEET
from sqlalchemy import desc

router = APIRouter(prefix="/api", tags=["fleet"])


@router.get("/fleet")
def get_fleet():
    """Return current status of all 12 transformers."""
    session = get_session()
    try:
        transformers = session.query(Transformer).all()
        result = []
        for tr in transformers:
            latest_pkt = get_latest(tr.id)
            d = tr.to_dict()
            if latest_pkt:
                d.update({
                    "loading_pct":  latest_pkt.get("loading_pct"),
                    "oil_temp":     latest_pkt.get("oil_temp"),
                    "power_factor": latest_pkt.get("power_factor"),
                    "active_power": latest_pkt.get("active_power"),
                    "fault_class":  latest_pkt.get("fault_class", 0),
                    "fault_name":   latest_pkt.get("fault_name", FAULT_CLASSES[0]),
                    "fault_confidence": latest_pkt.get("fault_confidence", 1.0),
                    "anomaly_score": latest_pkt.get("anomaly_score", 0.0),
                    "last_seen":    latest_pkt.get("timestamp"),
                })
            else:
                d["last_seen"] = None
            result.append(d)
        return {"transformers": result, "count": len(result)}
    finally:
        session.close()


@router.get("/transformer/{transformer_id}")
def get_transformer(transformer_id: str):
    """Detailed snapshot of a single transformer."""
    session = get_session()
    try:
        tr = session.query(Transformer).filter_by(id=transformer_id).first()
        if not tr:
            raise HTTPException(404, f"Transformer {transformer_id} not found")

        latest_pkt = get_latest(transformer_id) or {}
        d = tr.to_dict()
        d.update(latest_pkt)

        # Latest RUL prediction
        from src.database.models import RULPrediction
        rul = (session.query(RULPrediction)
               .filter_by(transformer_id=transformer_id)
               .order_by(desc(RULPrediction.timestamp))
               .first())
        d["rul"] = rul.to_dict() if rul else None

        # Active alert count
        active_alerts = (session.query(Alert)
                         .filter_by(transformer_id=transformer_id, acknowledged=False)
                         .count())
        d["active_alert_count"] = active_alerts

        return d
    finally:
        session.close()


@router.get("/transformer/{transformer_id}/history")
def get_transformer_history(transformer_id: str, n: int = 120):
    """Return last N telemetry records from in-memory ring buffer."""
    buf = get_history(transformer_id, n)
    return {"transformer_id": transformer_id, "count": len(buf), "data": buf}


@router.post("/inject-fault")
def inject_fault_endpoint(req: FaultInjectRequest):
    """Manually inject a fault into a transformer (for demo / testing)."""
    cfg_ids = [t["id"] for t in TRANSFORMER_FLEET]
    if req.transformer_id not in cfg_ids:
        raise HTTPException(404, f"Transformer {req.transformer_id} not found")
    if req.fault_mode == 0:
        clear_fault(req.transformer_id)
        return {"status": "cleared", "transformer_id": req.transformer_id}
    inject_fault(req.transformer_id, req.fault_mode, req.severity)
    return {
        "status": "injected",
        "transformer_id": req.transformer_id,
        "fault_mode": req.fault_mode,
        "fault_name": FAULT_CLASSES.get(req.fault_mode),
        "severity": req.severity,
    }


@router.get("/reports/summary")
def fleet_summary():
    """Fleet-wide KPI summary."""
    pkts = get_all_latest()
    if not pkts:
        return {"error": "No data yet"}

    import statistics
    total    = len(pkts)
    faulted  = sum(1 for p in pkts if p.get("fault_class", 0) != 0)
    critical = sum(1 for p in pkts if p.get("fault_severity") == "CRITICAL")
    avg_load = statistics.mean(p.get("loading_pct", 0) for p in pkts)
    avg_oil  = statistics.mean(p.get("oil_temp", 0) for p in pkts)

    return {
        "total_transformers": total,
        "healthy": total - faulted,
        "faulted": faulted,
        "critical": critical,
        "avg_loading_pct": round(avg_load, 1),
        "avg_oil_temp": round(avg_oil, 1),
        "total_active_power_kw": round(sum(p.get("active_power", 0) for p in pkts), 1),
    }
