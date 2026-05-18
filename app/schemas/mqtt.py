from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    CycleStage,
    CycleStatus,
    DeviceStatus,
    SensorType,
    TankType,
)


class MqttDeviceStatusPayload(BaseModel):
    mac_address: str = Field(min_length=1, max_length=50)
    status: DeviceStatus
    message: str | None = None
    recorded_at: datetime


class MqttCycleStatePayload(BaseModel):
    mac_address: str = Field(min_length=1, max_length=50)
    stage: CycleStage
    status: CycleStatus
    recorded_at: datetime

class MqttSensorReadingsPayload(BaseModel):
    mac_address: str = Field(min_length=1, max_length=50)
    tank_type: TankType
    tds: float | None = None
    turbidity: float | None = None
    water_volume: float | None = None
    temperature: float | None = None
    ph: float | None = None
    recorded_at: datetime


class MqttAIDecisionPayload(BaseModel):
    mac_address: str = Field(min_length=1, max_length=50)
    recorded_at: datetime
    model_type: str = Field(min_length=1, max_length=50)
    model_version: str = Field(min_length=1, max_length=50)

    raw_tds: float
    raw_turbidity: float
    raw_water_volume: float
    raw_temperature: float
    raw_ph: float

    recommended_moringa_dose_mg_per_l: int
    recommended_mixing_duration_seconds: int
    predicted_is_clean_water: bool


class MqttCycleResultPayload(BaseModel):
    mac_address: str = Field(min_length=1, max_length=50)
    recorded_at: datetime
    final_tds: float | None = None
    final_turbidity: float | None = None
    final_ph: float | None = None
    is_clean_water: bool
