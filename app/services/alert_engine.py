from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.base import utc_now
from app.models.device_status_log import DeviceStatusLog
from app.models.enums import AlertSeverity
from app.models.water_purifier import WaterPurifier

DEVICE_OFFLINE_MINUTES = 10
TURBIDITY_THRESHOLD = 5.0


async def create_alert_if_not_exists(
    session: AsyncSession,
    water_purifier_id,
    alert_type: str,
    severity: AlertSeverity,
    title: str,
    message: str | None = None,
    purification_cycle_id=None,
) -> tuple[Alert, bool]:
    existing = await session.scalar(
        select(Alert).where(
            Alert.water_purifier_id == water_purifier_id,
            Alert.alert_type == alert_type,
            Alert.is_resolved.is_(False),
        )
    )

    if existing:
        return existing, False

    alert = Alert(
        water_purifier_id=water_purifier_id,
        purification_cycle_id=purification_cycle_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        is_resolved=False,
        created_at=utc_now(),
    )

    session.add(alert)
    await session.flush()

    return alert, True


async def create_water_not_clean_alert(
    session: AsyncSession,
    water_purifier_id,
    purification_cycle_id,
) -> Alert:
    alert, _ = await create_alert_if_not_exists(
        session=session,
        water_purifier_id=water_purifier_id,
        purification_cycle_id=purification_cycle_id,
        alert_type="water_not_clean",
        severity=AlertSeverity.warning,
        title="Cycle failed to produce clean water",
        message="Latest cycle result indicates the water is still not clean.",
    )

    return alert


async def create_high_turbidity_alert(
    session: AsyncSession,
    water_purifier_id,
    purification_cycle_id,
    final_turbidity: float,
) -> Alert:
    alert, _ = await create_alert_if_not_exists(
        session=session,
        water_purifier_id=water_purifier_id,
        purification_cycle_id=purification_cycle_id,
        alert_type="high_turbidity_after_settling",
        severity=AlertSeverity.warning,
        title="High turbidity after settling",
        message=f"Settling tank turbidity is {final_turbidity}, above threshold {TURBIDITY_THRESHOLD}.",
    )

    return alert


async def create_cycle_failed_alert(
    session: AsyncSession,
    water_purifier_id,
    purification_cycle_id,
) -> Alert:
    alert, _ = await create_alert_if_not_exists(
        session=session,
        water_purifier_id=water_purifier_id,
        purification_cycle_id=purification_cycle_id,
        alert_type="cycle_failed",
        severity=AlertSeverity.warning,
        title="Purification cycle failed",
        message="The latest purification cycle was marked as failed.",
    )

    return alert


async def create_device_offline_alert(
    session: AsyncSession,
    water_purifier_id,
) -> tuple[Alert, bool]:
    return await create_alert_if_not_exists(
        session=session,
        water_purifier_id=water_purifier_id,
        alert_type="device_offline",
        severity=AlertSeverity.critical,
        title="Device offline detected",
        message=f"ESP32 has not sent status updates for more than {DEVICE_OFFLINE_MINUTES} minutes.",
    )


async def check_device_offline_alerts(session: AsyncSession) -> int:
    purifiers = await session.scalars(select(WaterPurifier))
    cutoff = utc_now() - timedelta(minutes=DEVICE_OFFLINE_MINUTES)

    created_count = 0

    for purifier in purifiers:
        latest_status = await session.scalar(
            select(DeviceStatusLog)
            .where(DeviceStatusLog.water_purifier_id == purifier.id)
            .order_by(
                desc(DeviceStatusLog.recorded_at),
                desc(DeviceStatusLog.id),
            )
            .limit(1)
        )

        if latest_status is None:
            continue

        status_value = (
            latest_status.status.value
            if hasattr(latest_status.status, "value")
            else str(latest_status.status)
        )

        if status_value == "offline":
            continue

        if status_value == "online" and latest_status.recorded_at < cutoff:
            _, created = await create_device_offline_alert(
                session=session,
                water_purifier_id=purifier.id,
            )

            if created:
                created_count += 1

    await session.commit()

    return created_count


async def resolve_active_device_offline_alerts(
    session: AsyncSession,
    water_purifier_id,
) -> int:
    result = await session.execute(
        select(Alert).where(
            Alert.water_purifier_id == water_purifier_id,
            Alert.alert_type == "device_offline",
            Alert.is_resolved.is_(False),
        )
    )

    alerts = result.scalars().all()

    for alert in alerts:
        alert.is_resolved = True
        alert.resolved_at = utc_now()

    await session.flush()

    return len(alerts)
