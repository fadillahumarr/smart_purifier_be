from enum import Enum

class TankType(str, Enum):
    raw = "raw"
    mixing = "mixing"
    settling = "settling"


class SensorType(str, Enum):
    tds = "tds"
    turbidity = "turbidity"
    water_volume = "water_volume"
    temperature = "temperature"
    ph = "ph"


class CycleStatus(str, Enum):
    running = "running"
    settling = "settling"
    completed = "completed"
    failed = "failed"


class CycleStage(str, Enum):
    raw_sampling = "raw_sampling"
    mixing = "mixing"
    settling = "settling"
    completed = "completed"
    failed = "failed"


class DeviceStatus(str, Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class SnapshotType(str, Enum):
    INITIAL_RAW = "initial_raw"
    FINAL_RESULT = "final_result"
    ALERT = "alert"
    MANUAL_SAMPLE = "manual_sample"
