"""
src/api/routes/rul.py — RUL prediction endpoints.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException, Query
from src.database.init_db import get_session
from src.database.models import RULPrediction, Transformer
from sqlalchemy import desc

router = APIRouter(prefix="/api", tags=["rul"])


@router.get("/rul/{transformer_id}")
def get_rul(transformer_id: str):
    """Latest RUL predictions for a transformer."""
    session = get_session()
    try:
        tr = session.query(Transformer).filter_by(id=transformer_id).first()
        if not tr:
            raise HTTPException(404, f"Transformer {transformer_id} not found")

        latest = (session.query(RULPrediction)
                  .filter_by(transformer_id=transformer_id)
                  .order_by(desc(RULPrediction.timestamp))
                  .first())
        return {
            "transformer_id": transformer_id,
            "rul": latest.to_dict() if latest else None
        }
    finally:
        session.close()


@router.get("/rul/{transformer_id}/history")
def get_rul_history(transformer_id: str, limit: int = Query(30, le=200)):
    """Historical RUL trend for charts."""
    session = get_session()
    try:
        records = (session.query(RULPrediction)
                   .filter_by(transformer_id=transformer_id)
                   .order_by(desc(RULPrediction.timestamp))
                   .limit(limit).all())
        records.reverse()
        return {
            "transformer_id": transformer_id,
            "count": len(records),
            "data": [r.to_dict() for r in records],
        }
    finally:
        session.close()


@router.get("/rul/fleet/summary")
def fleet_rul_summary():
    """Fleet-wide RUL summary — flag any transformers with critical RUL."""
    session = get_session()
    try:
        transformers = session.query(Transformer).all()
        summary = []
        for tr in transformers:
            latest = (session.query(RULPrediction)
                      .filter_by(transformer_id=tr.id)
                      .order_by(desc(RULPrediction.timestamp))
                      .first())
            if latest:
                min_rul = min(
                    v for v in [
                        latest.insulation_rul_days,
                        latest.oil_rul_days,
                        latest.winding_rul_days,
                    ] if v is not None
                )
                summary.append({
                    "transformer_id": tr.id,
                    "name": tr.name,
                    "overall_health_score": latest.overall_health_score,
                    "min_rul_days": round(min_rul, 1),
                    "insulation_rul_days": latest.insulation_rul_days,
                    "oil_rul_days": latest.oil_rul_days,
                    "winding_rul_days": latest.winding_rul_days,
                })
        summary.sort(key=lambda x: x["min_rul_days"])
        return {"fleet_rul": summary}
    finally:
        session.close()
