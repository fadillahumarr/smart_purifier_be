import json

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.ai_decision import AIDecision
from app.models.cycle_result import CycleResult
from app.models.device_status_log import DeviceStatusLog
from app.models.enums import CycleStage, CycleStatus, TankType
from app.models.purification_cycle import PurificationCycle
from app.models.sensor_snapshot import SensorSnapshot, SnapshotType
from app.models.tank import Tank
from app.models.water_purifier import WaterPurifier
from app.schemas.mqtt import (
    MqttAIDecisionPayload,
    MqttCycleResultPayload,
    MqttCycleStatePayload,
    MqttDeviceStatusPayload,
    MqttSensorReadingsPayload,
)
from app.services.alert_engine import (
    TURBIDITY_THRESHOLD,
    create_cycle_failed_alert,
    create_high_turbidity_alert,
    create_water_not_clean_alert,
    resolve_active_device_offline_alerts,
)

REALTIME_TTL_SECONDS = 300
REALTIME_MAX_RECORDS = 300


def normalize_mac(mac: str) -> str:
    return mac.strip().upper().replace("-", ":")


def tank_key(tank_type: TankType) -> str:
    return tank_type.value if hasattr(tank_type, "value") else str(tank_type)


async def get_purifier_by_mac(
    session: AsyncSession,
    mac_address: str,
) -> WaterPurifier | None:
    normalized_mac = normalize_mac(mac_address)

    stmt = select(WaterPurifier).where(
        func.upper(WaterPurifier.mac_address) == normalized_mac
    )
    return await session.scalar(stmt)


async def get_tank_by_type(
    session: AsyncSession,
    purifier_id,
    tank_type: TankType,
) -> Tank | None:
    stmt = select(Tank).where(
        Tank.water_purifier_id == purifier_id,
        Tank.tank_type == tank_type,
    )
    return await session.scalar(stmt)


async def get_active_cycle(
    session: AsyncSession,
    purifier_id,
) -> PurificationCycle | None:
    stmt = (
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
    return await session.scalar(stmt)


async def get_latest_cycle(
    session: AsyncSession,
    purifier_id,
) -> PurificationCycle | None:
    stmt = (
        select(PurificationCycle)
        .where(PurificationCycle.water_purifier_id == purifier_id)
        .order_by(desc(PurificationCycle.started_at))
        .limit(1)
    )
    return await session.scalar(stmt)


async def handle_device_status(
    session: AsyncSession,
    payload: MqttDeviceStatusPayload,
) -> DeviceStatusLog:
    purifier = await get_purifier_by_mac(session, payload.mac_address)

    if not purifier:
        raise ValueError("Purifier not found for this mac_address")

    row = DeviceStatusLog(
        water_purifier_id=purifier.id,
        status=payload.status,
        message=payload.message,
        recorded_at=payload.recorded_at,
    )

    session.add(row)

    status_value = (
        payload.status.value
        if hasattr(payload.status, "value")
        else str(payload.status)
    )

    if status_value == "online":
        await resolve_active_device_offline_alerts(
            session=session,
            water_purifier_id=purifier.id,
        )

    await session.commit()
    await session.refresh(row)

    return row


async def handle_cycle_state(
    session: AsyncSession,
    payload: MqttCycleStatePayload,
) -> PurificationCycle:
    purifier = await get_purifier_by_mac(session, payload.mac_address)
    if not purifier:
        raise ValueError("Purifier not found for this mac_address")

    cycle = await get_active_cycle(session, purifier.id)

    if payload.stage == CycleStage.raw_sampling:
        if cycle is None:
            cycle = PurificationCycle(
                water_purifier_id=purifier.id,
                started_at=payload.recorded_at,
                current_stage=payload.stage,
                status=payload.status,
            )
            session.add(cycle)
            await session.commit()
            await session.refresh(cycle)
            return cycle

        cycle.current_stage = payload.stage
        cycle.status = payload.status

        if cycle.started_at is None:
            cycle.started_at = payload.recorded_at

    else:
        if cycle is None:
            cycle = PurificationCycle(
                water_purifier_id=purifier.id,
                started_at=payload.recorded_at,
                current_stage=payload.stage,
                status=payload.status,
            )
            session.add(cycle)
            await session.flush()

        cycle.current_stage = payload.stage
        cycle.status = payload.status

        if payload.stage == CycleStage.mixing:
            if cycle.mixing_started_at is None:
                cycle.mixing_started_at = payload.recorded_at

        elif payload.stage == CycleStage.settling:
            if cycle.settled_at is None:
                cycle.settled_at = payload.recorded_at
            cycle.status = CycleStatus.settling

        elif payload.stage == CycleStage.completed:
            cycle.finished_at = payload.recorded_at
            cycle.status = CycleStatus.completed

        elif payload.stage == CycleStage.failed:
            cycle.finished_at = payload.recorded_at
            cycle.status = CycleStatus.failed

            await create_cycle_failed_alert(
                session=session,
                water_purifier_id=purifier.id,
                purification_cycle_id=cycle.id,
            )

    await session.commit()
    await session.refresh(cycle)

    return cycle


async def handle_sensor_readings(
    session: AsyncSession,
    payload: MqttSensorReadingsPayload,
) -> int:
    purifier = await get_purifier_by_mac(
        session,
        payload.mac_address,
    )

    if not purifier:
        raise ValueError("Purifier not found for this mac_address")

    tank = await get_tank_by_type(
        session,
        purifier.id,
        payload.tank_type,
    )

    if not tank:
        raise ValueError(
            "Tank not found for this purifier and tank_type"
        )

    tank_type = tank_key(payload.tank_type)

    latest_key = (
        f"sensor:latest:{purifier.id}:{tank_type}"
    )

    window_key = (
        f"sensor:window:{purifier.id}:{tank_type}"
    )

    recorded_at = payload.recorded_at.isoformat()

    latest_data = {
        "water_purifier_id": str(purifier.id),
        "tank_id": str(tank.id),
        "tank_type": tank_type,
        "recorded_at": recorded_at,

        "tds": payload.tds,
        "turbidity": payload.turbidity,
        "ph": payload.ph,
        "temperature": payload.temperature,
        "water_volume": payload.water_volume,
    }

    payload_json = json.dumps(latest_data)

    async with redis_client.pipeline(
        transaction=False
    ) as pipe:

        pipe.set(
            latest_key,
            payload_json,
            ex=REALTIME_TTL_SECONDS,
        )

        pipe.publish(
            f"sensor:realtime:{purifier.id}",
            payload_json,
        )

        pipe.rpush(
            window_key,
            payload_json,
        )

        pipe.ltrim(
            window_key,
            -REALTIME_MAX_RECORDS,
            -1,
        )

        pipe.expire(
            window_key,
            REALTIME_TTL_SECONDS,
        )

        await pipe.execute()

    sensor_count = sum(
        value is not None
        for value in [
            payload.tds,
            payload.turbidity,
            payload.ph,
            payload.temperature,
            payload.water_volume,
        ]
    )

    return sensor_count


async def save_initial_raw_snapshot(
    session: AsyncSession,
    purifier: WaterPurifier,
    cycle: PurificationCycle,
    payload: MqttAIDecisionPayload,
) -> None:
    raw_tank = await get_tank_by_type(session, purifier.id, TankType.raw)
    if not raw_tank:
        return

    existing_snapshot = await session.scalar(
        select(SensorSnapshot).where(
            SensorSnapshot.cycle_id == cycle.id,
            SensorSnapshot.snapshot_type == SnapshotType.INITIAL_RAW,
        )
    )

    if existing_snapshot:
        existing_snapshot.tds = payload.raw_tds
        existing_snapshot.turbidity = payload.raw_turbidity
        existing_snapshot.ph = payload.raw_ph
        existing_snapshot.temperature = payload.raw_temperature
        existing_snapshot.water_volume = payload.raw_water_volume
        existing_snapshot.recorded_at = payload.recorded_at
        return

    session.add(
        SensorSnapshot(
            water_purifier_id=purifier.id,
            tank_id=raw_tank.id,
            cycle_id=cycle.id,
            snapshot_type=SnapshotType.INITIAL_RAW,
            tds=payload.raw_tds,
            turbidity=payload.raw_turbidity,
            ph=payload.raw_ph,
            temperature=payload.raw_temperature,
            water_volume=payload.raw_water_volume,
            recorded_at=payload.recorded_at,
        )
    )


async def handle_ai_decision(
    session: AsyncSession,
    payload: MqttAIDecisionPayload,
) -> AIDecision:
    purifier = await get_purifier_by_mac(session, payload.mac_address)
    if not purifier:
        raise ValueError("Purifier not found for this mac_address")

    cycle = await get_active_cycle(session, purifier.id)

    if cycle is None:
        cycle = PurificationCycle(
            water_purifier_id=purifier.id,
            started_at=payload.recorded_at,
            current_stage=CycleStage.raw_sampling,
            status=CycleStatus.running,
        )
        session.add(cycle)
        await session.flush()

    await save_initial_raw_snapshot(
        session=session,
        purifier=purifier,
        cycle=cycle,
        payload=payload,
    )

    existing = await session.scalar(
        select(AIDecision).where(
            AIDecision.purification_cycle_id == cycle.id
        )
    )

    if existing:
        existing.model_type = payload.model_type
        existing.model_version = payload.model_version
        existing.raw_tds = payload.raw_tds
        existing.raw_turbidity = payload.raw_turbidity
        existing.raw_water_volume = payload.raw_water_volume
        existing.raw_temperature = payload.raw_temperature
        existing.raw_ph = payload.raw_ph
        existing.recommended_moringa_dose_mg_per_l = (
            payload.recommended_moringa_dose_mg_per_l
        )
        existing.recommended_mixing_duration_seconds = (
            payload.recommended_mixing_duration_seconds
        )
        existing.predicted_is_clean_water = payload.predicted_is_clean_water
        existing.created_at = payload.recorded_at

        await session.commit()
        await session.refresh(existing)

        return existing

    row = AIDecision(
        purification_cycle_id=cycle.id,
        model_type=payload.model_type,
        model_version=payload.model_version,
        raw_tds=payload.raw_tds,
        raw_turbidity=payload.raw_turbidity,
        raw_water_volume=payload.raw_water_volume,
        raw_temperature=payload.raw_temperature,
        raw_ph=payload.raw_ph,
        recommended_moringa_dose_mg_per_l=(
            payload.recommended_moringa_dose_mg_per_l
        ),
        recommended_mixing_duration_seconds=(
            payload.recommended_mixing_duration_seconds
        ),
        predicted_is_clean_water=payload.predicted_is_clean_water,
        created_at=payload.recorded_at,
    )

    session.add(row)
    await session.commit()
    await session.refresh(row)

    return row


async def save_final_result_snapshot(
    session: AsyncSession,
    purifier: WaterPurifier,
    cycle: PurificationCycle,
    payload: MqttCycleResultPayload,
) -> None:
    settling_tank = await get_tank_by_type(session, purifier.id, TankType.settling)
    if not settling_tank:
        return

    existing_snapshot = await session.scalar(
        select(SensorSnapshot).where(
            SensorSnapshot.cycle_id == cycle.id,
            SensorSnapshot.snapshot_type == SnapshotType.FINAL_RESULT,
        )
    )

    if existing_snapshot:
        existing_snapshot.tds = payload.final_tds
        existing_snapshot.turbidity = payload.final_turbidity
        existing_snapshot.ph = payload.final_ph
        existing_snapshot.recorded_at = payload.recorded_at
        return

    session.add(
        SensorSnapshot(
            water_purifier_id=purifier.id,
            tank_id=settling_tank.id,
            cycle_id=cycle.id,
            snapshot_type=SnapshotType.FINAL_RESULT,
            tds=payload.final_tds,
            turbidity=payload.final_turbidity,
            ph=payload.final_ph,
            temperature=None,
            water_volume=None,
            recorded_at=payload.recorded_at,
        )
    )


async def handle_cycle_result(
    session: AsyncSession,
    payload: MqttCycleResultPayload,
) -> CycleResult:
    purifier = await get_purifier_by_mac(session, payload.mac_address)
    if not purifier:
        raise ValueError("Purifier not found for this mac_address")

    cycle = await get_active_cycle(session, purifier.id)
    if cycle is None:
        cycle = await get_latest_cycle(session, purifier.id)

    if cycle is None:
        raise ValueError("No cycle found for this purifier")

    existing = await session.scalar(
        select(CycleResult).where(
            CycleResult.purification_cycle_id == cycle.id
        )
    )

    if existing:
        existing.final_tds = payload.final_tds
        existing.final_turbidity = payload.final_turbidity
        existing.final_ph = payload.final_ph
        existing.is_clean_water = payload.is_clean_water
        existing.created_at = payload.recorded_at

        await save_final_result_snapshot(
            session=session,
            purifier=purifier,
            cycle=cycle,
            payload=payload,
        )

        await session.commit()
        await session.refresh(existing)

        return existing

    row = CycleResult(
        purification_cycle_id=cycle.id,
        final_tds=payload.final_tds,
        final_turbidity=payload.final_turbidity,
        final_ph=payload.final_ph,
        is_clean_water=payload.is_clean_water,
        created_at=payload.recorded_at,
    )

    session.add(row)

    if cycle.finished_at is None:
        cycle.finished_at = payload.recorded_at

    if cycle.current_stage != CycleStage.failed:
        cycle.current_stage = CycleStage.completed
        cycle.status = CycleStatus.completed

    await save_final_result_snapshot(
        session=session,
        purifier=purifier,
        cycle=cycle,
        payload=payload,
    )

    if payload.is_clean_water is False:
        await create_water_not_clean_alert(
            session=session,
            water_purifier_id=purifier.id,
            purification_cycle_id=cycle.id,
        )

    if (
        payload.final_turbidity is not None
        and payload.final_turbidity > TURBIDITY_THRESHOLD
    ):
        await create_high_turbidity_alert(
            session=session,
            water_purifier_id=purifier.id,
            purification_cycle_id=cycle.id,
            final_turbidity=payload.final_turbidity,
        )

    await session.commit()
    await session.refresh(row)

    return row
