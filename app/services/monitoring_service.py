import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.ai_decision import AIDecision
from app.models.cycle_result import CycleResult
from app.models.device_status_log import DeviceStatusLog
from app.models.enums import CycleStatus, SensorType, TankType
from app.models.purification_cycle import PurificationCycle
from app.models.sensor_snapshot import SensorSnapshot, SnapshotType
from app.models.water_purifier import WaterPurifier
from app.schemas.monitoring import (
    AIDecisionOut,
    CurrentCycleOut,
    DeviceStatusOut,
    LatestResultOut,
    MetricReadingOut,
    MonitoringRealtimeOut,
    MonitoringSummaryOut,
    PurifierMiniOut,
    RawSnapshotOut,
    SettlingRealtimeOut,
    TrendPointOut,
)

LIVE_THRESHOLD_MINUTES = 10


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def sensor_unit(sensor_type: SensorType) -> str:
    return {
        SensorType.turbidity: "NTU",
        SensorType.tds: "ppm",
        SensorType.ph: "",
        SensorType.temperature: "°C",
        SensorType.water_volume: "L",
    }[sensor_type]


def redis_tank_key(tank_type: TankType) -> str:
    return tank_type.value if hasattr(tank_type, "value") else str(tank_type)


def calculate_mixing_times(
    cycle: PurificationCycle | None,
    ai_decision: AIDecision | None,
) -> tuple[datetime | None, int | None]:
    if not cycle or not ai_decision or not cycle.mixing_started_at:
        return None, None

    mixing_end_at = cycle.mixing_started_at + timedelta(
        seconds=ai_decision.recommended_mixing_duration_seconds
    )

    remaining = int((mixing_end_at - utc_now()).total_seconds())
    remaining = max(remaining, 0)

    return mixing_end_at, remaining


async def get_purifier_or_none(
    session: AsyncSession,
    purifier_id: UUID,
) -> WaterPurifier | None:
    return await session.get(WaterPurifier, purifier_id)


async def get_latest_device_status(
    session: AsyncSession,
    purifier_id: UUID,
) -> DeviceStatusOut:
    status_log = await session.scalar(
        select(DeviceStatusLog)
        .where(DeviceStatusLog.water_purifier_id == purifier_id)
        .order_by(desc(DeviceStatusLog.recorded_at), desc(DeviceStatusLog.id))
        .limit(1)
    )

    if not status_log:
        return DeviceStatusOut(
            is_live=False,
            status=None,
            message=None,
            recorded_at=None,
        )

    is_live = status_log.recorded_at >= (
        utc_now() - timedelta(minutes=LIVE_THRESHOLD_MINUTES)
    )

    return DeviceStatusOut(
        is_live=is_live,
        status=status_log.status,
        message=status_log.message,
        recorded_at=status_log.recorded_at,
    )


def empty_metric(sensor_type: SensorType) -> MetricReadingOut:
    return MetricReadingOut(
        value=None,
        unit=sensor_unit(sensor_type),
        recorded_at=None,
    )


def redis_sensor_metric(
    data: dict,
    sensor_type: SensorType,
) -> MetricReadingOut:
    sensor_name = sensor_type.value
    item = data.get(sensor_name)

    if isinstance(item, dict):
        return MetricReadingOut(
            value=item.get("value"),
            unit=sensor_unit(sensor_type),
            recorded_at=parse_datetime(item.get("recorded_at")),
        )

    if item is not None:
        return MetricReadingOut(
            value=float(item),
            unit=sensor_unit(sensor_type),
            recorded_at=parse_datetime(data.get("recorded_at")),
        )

    return empty_metric(sensor_type)


async def get_latest_cycle(
    session: AsyncSession,
    purifier_id: UUID,
) -> PurificationCycle | None:
    return await session.scalar(
        select(PurificationCycle)
        .where(PurificationCycle.water_purifier_id == purifier_id)
        .order_by(desc(PurificationCycle.started_at))
        .limit(1)
    )


async def get_current_cycle(
    session: AsyncSession,
    purifier_id: UUID,
) -> PurificationCycle | None:
    cycle = await session.scalar(
        select(PurificationCycle)
        .where(
            PurificationCycle.water_purifier_id == purifier_id,
            PurificationCycle.status.in_(
                [CycleStatus.running, CycleStatus.settling]
            ),
        )
        .order_by(desc(PurificationCycle.started_at))
        .limit(1)
    )

    if cycle:
        return cycle

    return await get_latest_cycle(session, purifier_id)


async def get_ai_decision_for_cycle(
    session: AsyncSession,
    cycle_id: UUID | None,
) -> AIDecision | None:
    if not cycle_id:
        return None

    return await session.scalar(
        select(AIDecision)
        .where(AIDecision.purification_cycle_id == cycle_id)
        .limit(1)
    )


async def get_latest_result_for_purifier(
    session: AsyncSession,
    purifier_id: UUID,
) -> CycleResult | None:
    return await session.scalar(
        select(CycleResult)
        .join(
            PurificationCycle,
            CycleResult.purification_cycle_id == PurificationCycle.id,
        )
        .where(PurificationCycle.water_purifier_id == purifier_id)
        .order_by(desc(CycleResult.created_at))
        .limit(1)
    )


async def get_initial_raw_snapshot(
    session: AsyncSession,
    purifier_id: UUID,
    cycle: PurificationCycle | None,
) -> RawSnapshotOut:
    if not cycle:
        return RawSnapshotOut()

    snapshot = await session.scalar(
        select(SensorSnapshot)
        .where(
            SensorSnapshot.water_purifier_id == purifier_id,
            SensorSnapshot.cycle_id == cycle.id,
            SensorSnapshot.snapshot_type == SnapshotType.INITIAL_RAW,
        )
        .order_by(desc(SensorSnapshot.recorded_at), desc(SensorSnapshot.id))
        .limit(1)
    )

    if not snapshot:
        return RawSnapshotOut()

    return RawSnapshotOut(
        tds=snapshot.tds,
        turbidity=snapshot.turbidity,
        ph=snapshot.ph,
        temperature=snapshot.temperature,
        water_volume=snapshot.water_volume,
        recorded_at=snapshot.recorded_at,
    )


async def get_settling_realtime(
    session: AsyncSession,
    purifier_id: UUID,
) -> SettlingRealtimeOut:
    key = f"sensor:latest:{purifier_id}:{redis_tank_key(TankType.settling)}"

    raw = await redis_client.get(key)
    data = json.loads(raw) if raw else {}

    return SettlingRealtimeOut(
        turbidity=redis_sensor_metric(data, SensorType.turbidity),
        tds=redis_sensor_metric(data, SensorType.tds),
        ph=redis_sensor_metric(data, SensorType.ph),
        temperature=redis_sensor_metric(data, SensorType.temperature),
        water_volume=redis_sensor_metric(data, SensorType.water_volume),
    )


async def get_settling_trend(
    session: AsyncSession,
    purifier_id: UUID,
    minutes: int = 30,
) -> list[TrendPointOut]:
    key = f"sensor:window:{purifier_id}:{redis_tank_key(TankType.settling)}"

    rows = await redis_client.lrange(key, 0, -1)

    grouped: dict[str, dict] = {}

    for row in rows:
        item = json.loads(row)

        time_value = item.get("time") or item.get("recorded_at")
        if not time_value:
            continue

        point = grouped.setdefault(
            time_value,
            {
                "time": parse_datetime(time_value),
                "tds": None,
                "turbidity": None,
                "ph": None,
                "temperature": None,
                "water_volume": None,
            },
        )

        if "sensor_type" in item and "value" in item:
            sensor_name = item["sensor_type"]
            if sensor_name in point:
                point[sensor_name] = float(item["value"])
        else:
            for sensor_name in [
                "tds",
                "turbidity",
                "ph",
                "temperature",
                "water_volume",
            ]:
                if item.get(sensor_name) is not None:
                    value = item[sensor_name]

                    if isinstance(value, dict):
                        point[sensor_name] = value.get("value")
                    else:
                        point[sensor_name] = value

    points = [
        TrendPointOut(**point)
        for point in grouped.values()
        if point["time"] is not None
    ]

    points.sort(key=lambda point: point.time)

    return points


async def get_monitoring_summary(
    session: AsyncSession,
    purifier_id: UUID,
) -> MonitoringSummaryOut:
    purifier = await get_purifier_or_none(session, purifier_id)
    if not purifier:
        raise ValueError("Purifier not found")

    device_status = await get_latest_device_status(session, purifier_id)
    current_cycle = await get_current_cycle(session, purifier_id)

    ai_decision = await get_ai_decision_for_cycle(
        session,
        current_cycle.id if current_cycle else None,
    )

    latest_result = await get_latest_result_for_purifier(session, purifier_id)

    raw_snapshot = await get_initial_raw_snapshot(
        session,
        purifier_id,
        current_cycle,
    )

    mixing_end_at, remaining_mixing_seconds = calculate_mixing_times(
        current_cycle,
        ai_decision,
    )

    return MonitoringSummaryOut(
        purifier=PurifierMiniOut(
            id=purifier.id,
            name=purifier.name,
            location=purifier.location,
            device_code=purifier.device_code,
            firmware_version=purifier.firmware_version,
        ),
        device_status=device_status,
        initial_raw_snapshot=raw_snapshot,
        current_cycle=(
            CurrentCycleOut(
                id=current_cycle.id,
                current_stage=current_cycle.current_stage,
                status=current_cycle.status,
                started_at=current_cycle.started_at,
                mixing_started_at=current_cycle.mixing_started_at,
                mixing_end_at=mixing_end_at,
                remaining_mixing_seconds=remaining_mixing_seconds,
                settled_at=current_cycle.settled_at,
                finished_at=current_cycle.finished_at,
                notes=current_cycle.notes,
            )
            if current_cycle
            else None
        ),
        ai_decision=(
            AIDecisionOut(
                id=ai_decision.id,
                purification_cycle_id=ai_decision.purification_cycle_id,
                model_type=ai_decision.model_type,
                model_version=ai_decision.model_version,
                raw_tds=float(ai_decision.raw_tds),
                raw_turbidity=float(ai_decision.raw_turbidity),
                raw_water_volume=float(ai_decision.raw_water_volume),
                raw_temperature=float(ai_decision.raw_temperature),
                raw_ph=float(ai_decision.raw_ph),
                recommended_moringa_dose_mg_per_l=(
                    ai_decision.recommended_moringa_dose_mg_per_l
                ),
                recommended_mixing_duration_seconds=(
                    ai_decision.recommended_mixing_duration_seconds
                ),
                predicted_is_clean_water=ai_decision.predicted_is_clean_water,
                created_at=ai_decision.created_at,
            )
            if ai_decision
            else None
        ),
        latest_result=(
            LatestResultOut(
                id=latest_result.id,
                purification_cycle_id=latest_result.purification_cycle_id,
                final_tds=(
                    float(latest_result.final_tds)
                    if latest_result.final_tds is not None
                    else None
                ),
                final_turbidity=(
                    float(latest_result.final_turbidity)
                    if latest_result.final_turbidity is not None
                    else None
                ),
                final_ph=(
                    float(latest_result.final_ph)
                    if latest_result.final_ph is not None
                    else None
                ),
                is_clean_water=latest_result.is_clean_water,
                created_at=latest_result.created_at,
            )
            if latest_result
            else None
        ),
    )


async def get_monitoring_realtime(
    session: AsyncSession,
    purifier_id: UUID,
    trend_minutes: int = 30,
) -> MonitoringRealtimeOut:
    purifier = await get_purifier_or_none(session, purifier_id)
    if not purifier:
        raise ValueError("Purifier not found")

    device_status = await get_latest_device_status(session, purifier_id)

    settling_realtime = await get_settling_realtime(
        session,
        purifier_id,
    )

    settling_trend = await get_settling_trend(
        session,
        purifier_id,
        minutes=trend_minutes,
    )

    return MonitoringRealtimeOut(
        purifier_id=purifier_id,
        device_status=device_status,
        settling_realtime=settling_realtime,
        settling_trend=settling_trend,
    )
