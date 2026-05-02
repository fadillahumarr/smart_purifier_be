from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.tank import Tank
from app.models.user import User
from app.models.water_purifier import WaterPurifier
from app.schemas.tank import TankRead

router = APIRouter(prefix="/purifiers", tags=["tanks"])


@router.get("/{purifier_id}/tanks", response_model=list[TankRead])
async def list_tanks(
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

    result = await session.scalars(
        select(Tank)
        .where(Tank.water_purifier_id == purifier_id)
        .order_by(Tank.created_at.asc())
    )
    return result.all()