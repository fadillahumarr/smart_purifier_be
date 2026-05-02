import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.alert_engine import check_device_offline_alerts

logger = logging.getLogger(__name__)


async def run_alert_worker() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                count = await check_device_offline_alerts(session)
                if count:
                    logger.info(
                        "Created/checked %s device offline alerts", count)

        except Exception:
            logger.exception("Alert worker failed")

        await asyncio.sleep(60)
