from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.monitoring import (
    MonitoringRealtimeOut,
    MonitoringSummaryOut,
)
from app.services.monitoring_service import (
    get_monitoring_realtime,
    get_monitoring_summary,
)

router = APIRouter(prefix="/purifiers", tags=["monitoring"])


@router.get(
    "/{purifier_id}/monitoring/summary",
    response_model=MonitoringSummaryOut,
    status_code=status.HTTP_200_OK,
)
async def read_monitoring_summary(
    purifier_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await get_monitoring_summary(session, purifier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{purifier_id}/monitoring/realtime",
    response_model=MonitoringRealtimeOut,
    status_code=status.HTTP_200_OK,
)
async def read_monitoring_realtime(
    purifier_id: UUID,
    trend_minutes: int = Query(default=5, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await get_monitoring_realtime(
            session,
            purifier_id,
            trend_minutes=trend_minutes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
