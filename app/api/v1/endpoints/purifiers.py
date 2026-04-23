from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.water_purifier import WaterPurifier
from app.schemas.water_purifier import (
    WaterPurifierCreate,
    WaterPurifierRead,
    WaterPurifierUpdate,
)

router = APIRouter(prefix="/purifiers", tags=["purifiers"])


@router.post("", response_model=WaterPurifierRead, status_code=status.HTTP_201_CREATED)
async def create_purifier(
    payload: WaterPurifierCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conditions = [
        WaterPurifier.device_code == payload.device_code,
        WaterPurifier.mqtt_topic_base == payload.mqtt_topic_base,
    ]

    if payload.mac_address:
        conditions.append(WaterPurifier.mac_address == payload.mac_address)

    existing = await session.scalar(
        select(WaterPurifier).where(or_(*conditions))
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device code, MQTT topic, or MAC address already exists",
        )

    purifier = WaterPurifier(
        user_id=current_user.id,
        name=payload.name,
        location=payload.location,
        mac_address=payload.mac_address,
        device_code=payload.device_code,
        mqtt_topic_base=payload.mqtt_topic_base,
        firmware_version=payload.firmware_version,
    )

    session.add(purifier)
    await session.commit()
    await session.refresh(purifier)

    return purifier


@router.get("", response_model=list[WaterPurifierRead])
async def list_purifiers(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.scalars(
        select(WaterPurifier)
        .where(WaterPurifier.user_id == current_user.id)
        .order_by(WaterPurifier.created_at.desc())
    )
    return result.all()


@router.get("/{purifier_id}", response_model=WaterPurifierRead)
async def get_purifier(
    purifier_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    purifier = await session.scalar(
        select(WaterPurifier).where(
            WaterPurifier.id == purifier_id,
            WaterPurifier.user_id == current_user.id,
        )
    )

    if not purifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purifier not found",
        )

    return purifier


@router.put("/{purifier_id}", response_model=WaterPurifierRead)
async def update_purifier(
    purifier_id: UUID,
    payload: WaterPurifierUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    purifier = await session.scalar(
        select(WaterPurifier).where(
            WaterPurifier.id == purifier_id,
            WaterPurifier.user_id == current_user.id,
        )
    )

    if not purifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purifier not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(purifier, field, value)

    session.add(purifier)
    await session.commit()
    await session.refresh(purifier)

    return purifier


@router.delete("/{purifier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purifier(
    purifier_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    purifier = await session.scalar(
        select(WaterPurifier).where(
            WaterPurifier.id == purifier_id,
            WaterPurifier.user_id == current_user.id,
        )
    )

    if not purifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purifier not found",
        )

    await session.delete(purifier)
    await session.commit()
