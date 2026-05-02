from fastapi import APIRouter

from app.api.v1.endpoints import alerts, auth, purifiers, tanks, dashboard, monitoring, cycle_history, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(purifiers.router)
api_router.include_router(tanks.router)
api_router.include_router(dashboard.router)
api_router.include_router(monitoring.router)
api_router.include_router(cycle_history.router)
api_router.include_router(alerts.router)
api_router.include_router(ws.router)