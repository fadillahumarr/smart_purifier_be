from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.water_purifier import WaterPurifier
from app.schemas.device_provision import (
    DeviceProvisionRequest,
    DeviceProvisionResponse,
)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "/provision",
    response_model=DeviceProvisionResponse,
)
async def provision_device(
    payload: DeviceProvisionRequest,
    session: AsyncSession = Depends(get_session),
):
    purifier = await session.scalar(
        select(WaterPurifier).where(
            WaterPurifier.mac_address == payload.mac_address
        )
    )

    if not purifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device is not registered",
        )

    if payload.firmware_version:
        purifier.firmware_version = payload.firmware_version
        session.add(purifier)
        await session.commit()
        await session.refresh(purifier)

    return DeviceProvisionResponse(
        device_code=purifier.device_code,
        mqtt_topic_base=purifier.mqtt_topic_base,
        mqtt_host=settings.MQTT_PUBLIC_HOST,
        mqtt_port=settings.MQTT_PUBLIC_PORT,
    )
