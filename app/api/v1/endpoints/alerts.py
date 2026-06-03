from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.enums import AlertSeverity
from app.models.user import User
from app.schemas.alert import AlertListOut, AlertOut, AlertActiveCountOut
from app.services.alert_service import (
    list_alerts,
    resolve_alert,
    get_active_alert_count,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListOut)
async def read_alerts(
    status_filter: str = Query(default="all", alias="status"),
    severity: AlertSeverity | None = Query(default=None),
    purifier_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if status_filter not in ["all", "active", "resolved"]:
        raise HTTPException(
            status_code=400,
            detail="status must be one of: all, active, resolved",
        )

    return await list_alerts(
        session=session,
        user_id=current_user.id,
        status_filter=status_filter,
        severity=severity,
        purifier_id=purifier_id,
    )


@router.patch("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert_endpoint(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return await resolve_alert(
            session=session,
            alert_id=alert_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/active-count", response_model=AlertActiveCountOut)
async def get_active_alert_count_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_active_alert_count(
        session=session,
        user_id=current_user.id,
    )
