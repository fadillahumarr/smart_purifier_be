from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WaterPurifierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=150)
    mac_address: str | None = Field(default=None, max_length=50)
    device_code: str = Field(min_length=1, max_length=100)
    mqtt_topic_base: str = Field(min_length=1, max_length=150)
    firmware_version: str | None = Field(default=None, max_length=50)


class WaterPurifierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=150)
    mac_address: str | None = Field(default=None, max_length=50)
    firmware_version: str | None = Field(default=None, max_length=50)


class WaterPurifierRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    location: str | None
    mac_address: str | None
    device_code: str
    mqtt_topic_base: str
    firmware_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
