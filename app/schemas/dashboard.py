from pydantic import BaseModel
from uuid import UUID


class DashboardGlobalSummary(BaseModel):
    total_purifiers: int
    online_purifiers: int
    offline_purifiers: int
    active_alerts: int


class MetricValue(BaseModel):
    value: float | int | None
    unit: str = ""


class TankSummary(BaseModel):
    tds: MetricValue
    turbidity: MetricValue
    ph: MetricValue
    temperature: MetricValue
    water_volume: MetricValue


class PurifierDashboardSummary(BaseModel):
    purifier_id: UUID
    name: str
    device_code: str
    status: str | None
    last_cycle_status: str | None
    active_alerts: int
    raw_water: TankSummary | None
    settling_water: TankSummary | None
