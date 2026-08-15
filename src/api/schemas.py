"""
src/api/schemas.py
Pydantic request/response schemas for the DTMS API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FaultInjectRequest(BaseModel):
    transformer_id: str = Field(..., example="TR-N01")
    fault_mode: int     = Field(..., ge=0, le=5, description="0=Normal 1=Overload 2=SLG 3=OilHeat 4=Harmonic 5=Insulation")
    severity: float     = Field(1.0, ge=0.0, le=1.0)


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., example="Operator-1")


class WorkOrderCreate(BaseModel):
    transformer_id: str
    title: str
    description: Optional[str] = None
    priority: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class WorkOrderUpdate(BaseModel):
    status: Optional[str]      = Field(None, pattern="^(OPEN|IN_PROGRESS|CLOSED)$")
    assigned_to: Optional[str] = None
    priority: Optional[str]    = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    description: Optional[str] = None
