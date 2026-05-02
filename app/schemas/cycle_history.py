from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import CycleStatus


class CycleHistoryItemOut(BaseModel):
    cycle_uuid: UUID
    cycle_code: str
    started_at: datetime
    status: CycleStatus
    predicted: str | None = None
    actual: str | None = None


class CycleHistoryResponseOut(BaseModel):
    purifier_id: UUID
    items: list[CycleHistoryItemOut]
