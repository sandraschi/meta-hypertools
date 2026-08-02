import abc
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MetaMCPService(abc.ABC):
    """
    Base class for all Meta MCP services.
    Provides standard patterns for response generation and diagnostic metadata.
    """

    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)

    def create_response(
        self,
        success: bool,
        message: str,
        data: dict[str, Any] | None = None,
        errors: list | None = None,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a standard SOTA-compliant response dictionary."""
        result: dict[str, Any] = {
            "success": success,
            "message": message,
            "data": data or {},
            "errors": errors or [],
            "metadata": {
                "service": self.__class__.__name__,
                "timestamp": __import__("time").time(),
            },
        }
        if error_type:
            result["error_type"] = error_type
        return result

    async def get_health_status(self) -> dict[str, Any]:
        """Get basic health status for this service."""
        return {
            "healthy": True,
            "service": self.__class__.__name__,
            "status": "operational",
        }
