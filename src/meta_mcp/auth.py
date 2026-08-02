import os

import structlog
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

logger = structlog.get_logger(__name__)

WURST_AUTH_HEADER = "X-Wurst-Auth"

api_key_header = APIKeyHeader(name=WURST_AUTH_HEADER, auto_error=False)


def _expected_wurst_token() -> str | None:
    """Return configured token, or None when auth is disabled (local dev)."""
    value = os.getenv("WURST_AUTH_TOKEN", "").strip()
    return value or None


async def wurst_auth_middleware(request: Request, call_next):
    """
    Middleware to verify the Benny/Wurstsemmel security handshake.

    Protects destructive or high-resource operations.
    """
    # Define sensitive paths that REQUIRE auth
    # For now, we block most write operations and analyzers
    protected_paths = [
        "/api/analysis",
        "/api/remediation",
        "/api/patch",
        "/api/fleet/scan",
        "/api/v1/fleet/start",
        "/api/v1/fleet/stop",
        "/api/v1/fleet/restart",
    ]

    requires_auth = any(request.url.path.startswith(p) for p in protected_paths)

    if requires_auth:
        expected_token = _expected_wurst_token()
        if not expected_token:
            response = await call_next(request)
            return response

        token = request.headers.get(WURST_AUTH_HEADER)
        if not token or token != expected_token:
            logger.warning(
                "Unauthorized access attempt",
                path=request.url.path,
                client=request.client.host if request.client else "unknown",
            )
            # Standard SOTA response for unauthorized access
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "message": "Operation failed",
                    "error": "Security Handshake Failed: Invalid or missing X-Wurst-Auth header.",
                    "code": "AUTH_REQUIRED",
                },
            )

    response = await call_next(request)
    return response


async def get_wurst_token(api_key: str = Security(api_key_header)):
    """Dependency injection version for specific routes."""
    expected_token = _expected_wurst_token()
    if not expected_token:
        return api_key
    if not api_key or api_key != expected_token:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    return api_key
