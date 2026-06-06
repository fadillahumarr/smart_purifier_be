from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.enums import AlertSeverity
from app.models.water_purifier import WaterPurifier
from app.schemas.alert import AlertListOut, AlertOut, AlertActiveCountOut


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def list_alerts(
    session: AsyncSession,
    user_id: UUID,
    status_filter: str = "all",
    severity: AlertSeverity | None = None,
    purifier_id: UUID | None = None,
) -> AlertListOut:
    stmt = (
        select(Alert, WaterPurifier.name)
        .join(WaterPurifier, Alert.water_purifier_id == WaterPurifier.id)
        .where(WaterPurifier.user_id == user_id)
        .order_by(Alert.is_resolved.asc(), desc(Alert.created_at))
    )

    if status_filter == "active":
        stmt = stmt.where(Alert.is_resolved.is_(False))
    elif status_filter == "resolved":
        stmt = stmt.where(Alert.is_resolved.is_(True))

    if severity:
        stmt = stmt.where(Alert.severity == severity)

    if purifier_id:
        stmt = stmt.where(Alert.water_purifier_id == purifier_id)

    result = await session.execute(stmt)

    items: list[AlertOut] = []

    for alert, purifier_name in result.all():
        items.append(
            AlertOut(
                id=alert.id,
                water_purifier_id=alert.water_purifier_id,
                purifier_name=purifier_name,
                purification_cycle_id=alert.purification_cycle_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                message=alert.message,
                is_resolved=alert.is_resolved,
                created_at=alert.created_at,
                resolved_at=alert.resolved_at,
            )
        )

    return AlertListOut(items=items)


async def resolve_alert(
    session: AsyncSession,
    alert_id: UUID,
    user_id: UUID,
) -> AlertOut:
    result = await session.execute(
        select(Alert, WaterPurifier.name)
        .join(WaterPurifier, Alert.water_purifier_id == WaterPurifier.id)
        .where(Alert.id == alert_id)
        .where(WaterPurifier.user_id == user_id)
    )

    row = result.one_or_none()

    if row is None:
        raise ValueError("Alert not found")

    alert, purifier_name = row

    if not alert.is_resolved:
        alert.is_resolved = True
        alert.resolved_at = now_utc()

    await session.commit()
    await session.refresh(alert)

    return AlertOut(
        id=alert.id,
        water_purifier_id=alert.water_purifier_id,
        purifier_name=purifier_name,
        purification_cycle_id=alert.purification_cycle_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        message=alert.message,
        is_resolved=alert.is_resolved,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )


async def get_active_alert_count(
    session: AsyncSession,
    user_id: UUID,
) -> AlertActiveCountOut:
    count = await session.scalar(
        select(func.count(Alert.id))
        .join(WaterPurifier, Alert.water_purifier_id == WaterPurifier.id)
        .where(WaterPurifier.user_id == user_id)
        .where(Alert.is_resolved.is_(False))
    )

    return AlertActiveCountOut(count=count or 0)
