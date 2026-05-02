from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.device_status_log import DeviceStatusLog
from app.models.user import User
from app.models.water_purifier import WaterPurifier
from app.schemas.dashboard import DashboardGlobalSummary


async def get_latest_status(
    session: AsyncSession,
    purifier_id,
) -> DeviceStatusLog | None:
    return await session.scalar(
        select(DeviceStatusLog)
        .where(DeviceStatusLog.water_purifier_id == purifier_id)
        .order_by(
            DeviceStatusLog.recorded_at.desc(),
            DeviceStatusLog.id.desc(),
        )
        .limit(1)
    )


async def get_global_dashboard_summary(
    session: AsyncSession,
    current_user: User,
) -> DashboardGlobalSummary:
    purifiers = (
        await session.scalars(
            select(WaterPurifier).where(
                WaterPurifier.user_id == current_user.id
            )
        )
    ).all()

    total = len(purifiers)
    online = 0

    for purifier in purifiers:
        latest_status = await get_latest_status(session, purifier.id)

        if latest_status and latest_status.status == "online":
            online += 1

    active_alerts = await session.scalar(
        select(func.count(Alert.id))
        .join(
            WaterPurifier,
            Alert.water_purifier_id == WaterPurifier.id,
        )
        .where(
            WaterPurifier.user_id == current_user.id,
            Alert.is_resolved == False,
        )
    )

    return DashboardGlobalSummary(
        total_purifiers=total,
        online_purifiers=online,
        offline_purifiers=max(total - online, 0),
        active_alerts=active_alerts or 0,
    )
