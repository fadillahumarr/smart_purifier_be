from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import TankType


class TankRead(BaseModel):
    id: UUID
    water_purifier_id: UUID
    tank_type: TankType
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
