from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.cycle_history import CycleHistoryResponseOut
from app.services.cycle_history_service import get_cycle_history

router = APIRouter(prefix="/purifiers", tags=["cycle-history"])


@router.get(
    "/{purifier_id}/cycles/history",
    response_model=CycleHistoryResponseOut,
    status_code=status.HTTP_200_OK,
)
async def read_cycle_history(
    purifier_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await get_cycle_history(
            session=session,
            purifier_id=purifier_id,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
