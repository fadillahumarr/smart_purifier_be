from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AlertSeverity


class AlertCreate(BaseModel):
    water_purifier_id: UUID
    purification_cycle_id: UUID | None = None
    alert_type: str = Field(max_length=50)
    severity: AlertSeverity
    title: str = Field(max_length=150)
    message: str | None = None


class AlertOut(BaseModel):
    id: UUID
    water_purifier_id: UUID
    purifier_name: str | None = None
    purification_cycle_id: UUID | None = None
    alert_type: str
    severity: AlertSeverity
    title: str
    message: str | None = None
    is_resolved: bool
    created_at: datetime
    resolved_at: datetime | None = None


class AlertListOut(BaseModel):
    items: list[AlertOut]

class AlertActiveCountOut(BaseModel):
    count: int