"""
src/api/routes/work_orders.py — Work order CRUD endpoints.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from src.database.init_db import get_session
from src.database.models import WorkOrder
from src.api.schemas import WorkOrderCreate, WorkOrderUpdate
from sqlalchemy import desc

router = APIRouter(prefix="/api", tags=["work_orders"])


@router.get("/work-orders")
def list_work_orders(
    transformer_id: str = Query(None),
    status:         str = Query(None),
    priority:       str = Query(None),
    limit:          int = Query(100, le=500),
):
    session = get_session()
    try:
        q = session.query(WorkOrder).order_by(desc(WorkOrder.created_at))
        if transformer_id:
            q = q.filter(WorkOrder.transformer_id == transformer_id)
        if status:
            q = q.filter(WorkOrder.status == status.upper())
        if priority:
            q = q.filter(WorkOrder.priority == priority.upper())
        wos = q.limit(limit).all()
        return {"work_orders": [w.to_dict() for w in wos], "count": len(wos)}
    finally:
        session.close()


@router.get("/work-orders/{wo_id}")
def get_work_order(wo_id: int):
    session = get_session()
    try:
        wo = session.query(WorkOrder).filter_by(id=wo_id).first()
        if not wo:
            raise HTTPException(404, "Work order not found")
        return wo.to_dict()
    finally:
        session.close()


@router.post("/work-orders", status_code=201)
def create_work_order(req: WorkOrderCreate):
    session = get_session()
    try:
        wo = WorkOrder(
            transformer_id = req.transformer_id,
            title          = req.title,
            description    = req.description,
            priority       = req.priority,
            status         = "OPEN",
            assigned_to    = req.assigned_to,
            created_at     = datetime.now(),
            due_date       = req.due_date,
        )
        session.add(wo)
        session.commit()
        session.refresh(wo)
        return wo.to_dict()
    finally:
        session.close()


@router.patch("/work-orders/{wo_id}")
def update_work_order(wo_id: int, req: WorkOrderUpdate):
    session = get_session()
    try:
        wo = session.query(WorkOrder).filter_by(id=wo_id).first()
        if not wo:
            raise HTTPException(404, "Work order not found")
        if req.status is not None:
            wo.status = req.status
            if req.status == "CLOSED":
                wo.closed_at = datetime.now()
        if req.assigned_to is not None:
            wo.assigned_to = req.assigned_to
        if req.priority is not None:
            wo.priority = req.priority
        if req.description is not None:
            wo.description = req.description
        session.commit()
        return wo.to_dict()
    finally:
        session.close()


@router.delete("/work-orders/{wo_id}")
def delete_work_order(wo_id: int):
    session = get_session()
    try:
        wo = session.query(WorkOrder).filter_by(id=wo_id).first()
        if not wo:
            raise HTTPException(404, "Work order not found")
        session.delete(wo)
        session.commit()
        return {"status": "deleted", "id": wo_id}
    finally:
        session.close()
