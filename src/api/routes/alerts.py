"""
src/api/routes/alerts.py — Alert management endpoints.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from src.database.init_db import get_session
from src.database.models import Alert
from src.api.schemas import AcknowledgeRequest
from sqlalchemy import desc

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts")
def list_alerts(
    transformer_id: str  = Query(None),
    severity:       str  = Query(None),
    acknowledged:   bool = Query(None),
    limit:          int  = Query(100, le=500),
):
    """List alerts with optional filters."""
    session = get_session()
    try:
        q = session.query(Alert).order_by(desc(Alert.timestamp))
        if transformer_id:
            q = q.filter(Alert.transformer_id == transformer_id)
        if severity:
            q = q.filter(Alert.severity == severity.upper())
        if acknowledged is not None:
            q = q.filter(Alert.acknowledged == acknowledged)
        alerts = q.limit(limit).all()
        return {"alerts": [a.to_dict() for a in alerts], "count": len(alerts)}
    finally:
        session.close()


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: int):
    session = get_session()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            raise HTTPException(404, "Alert not found")
        return alert.to_dict()
    finally:
        session.close()


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, req: AcknowledgeRequest):
    """Mark an alert as acknowledged."""
    session = get_session()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            raise HTTPException(404, "Alert not found")
        if alert.acknowledged:
            return {"status": "already_acknowledged", "id": alert_id}
        alert.acknowledged    = True
        alert.acknowledged_by = req.acknowledged_by
        alert.acknowledged_at = datetime.now()
        session.commit()
        return {"status": "acknowledged", "id": alert_id, "by": req.acknowledged_by}
    finally:
        session.close()
