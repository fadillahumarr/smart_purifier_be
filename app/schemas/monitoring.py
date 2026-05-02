from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import CycleStage, CycleStatus, DeviceStatus


class MetricReadingOut(BaseModel):
    value: float | None
    unit: str
    recorded_at: datetime | None


class DeviceStatusOut(BaseModel):
    is_live: bool
    status: DeviceStatus | None
    message: str | None
    recorded_at: datetime | None


class PurifierMiniOut(BaseModel):
    id: UUID
    name: str
    location: str | None = None
    device_code: str
    firmware_version: str | None = None


class RawSnapshotOut(BaseModel):
    tds: float | None = None
    turbidity: float | None = None
    ph: float | None = None
    temperature: float | None = None
    water_volume: float | None = None
    recorded_at: datetime | None = None


class CurrentCycleOut(BaseModel):
    id: UUID
    current_stage: CycleStage | None
    status: CycleStatus
    started_at: datetime
    mixing_started_at: datetime | None = None
    mixing_end_at: datetime | None = None
    remaining_mixing_seconds: int | None = None
    settled_at: datetime | None = None
    finished_at: datetime | None = None
    notes: str | None = None


class AIDecisionOut(BaseModel):
    id: UUID
    purification_cycle_id: UUID
    model_type: str
    model_version: str
    raw_tds: float
    raw_turbidity: float
    raw_water_volume: float
    raw_temperature: float
    raw_ph: float
    recommended_moringa_dose_mg_per_l: int
    recommended_mixing_duration_seconds: int
    predicted_is_clean_water: bool
    created_at: datetime


class LatestResultOut(BaseModel):
    id: UUID
    purification_cycle_id: UUID
    final_tds: float | None = None
    final_turbidity: float | None = None
    final_ph: float | None = None
    is_clean_water: bool
    created_at: datetime


class SettlingRealtimeOut(BaseModel):
    turbidity: MetricReadingOut
    tds: MetricReadingOut
    ph: MetricReadingOut
    temperature: MetricReadingOut
    water_volume: MetricReadingOut


class MonitoringSummaryOut(BaseModel):
    purifier: PurifierMiniOut
    device_status: DeviceStatusOut
    initial_raw_snapshot: RawSnapshotOut
    current_cycle: CurrentCycleOut | None = None
    ai_decision: AIDecisionOut | None = None
    latest_result: LatestResultOut | None = None


class TrendPointOut(BaseModel):
    time: datetime
    tds: float | None = None
    turbidity: float | None = None
    ph: float | None = None
    temperature: float | None = None
    water_volume: float | None = None


class MonitoringRealtimeOut(BaseModel):
    purifier_id: UUID
    device_status: DeviceStatusOut
    settling_realtime: SettlingRealtimeOut
    settling_trend: list[TrendPointOut]
