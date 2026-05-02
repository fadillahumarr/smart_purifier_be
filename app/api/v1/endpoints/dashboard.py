from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardGlobalSummary
from app.services.dashboard_service import get_global_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardGlobalSummary)
async def global_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_global_dashboard_summary(session, current_user)
