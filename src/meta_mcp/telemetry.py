from fastapi import APIRouter, Depends

from meta_mcp.auth import get_wurst_token
from meta_mcp.logging_config import get_recent_logs

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/logs", response_model=list[dict])
async def read_logs(limit: int = 100, _=Depends(get_wurst_token)):
    """
    Retrieve recent buffered logs for the industrial dashboard.
    Requires Wurst-Auth.
    """
    return get_recent_logs(limit=limit)


@router.get("/status")
async def get_system_status():
    """
    Public health and version status.
    """
    return {"status": "online", "version": "1.4.1", "industrialized": True, "auth_enabled": True}
