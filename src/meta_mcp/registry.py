from collections.abc import Callable
from typing import Any

import structlog
from fastmcp import FastMCP

logger = structlog.get_logger(__name__)


class MetaMCPRegistry:
    """
    Decentralized registry for Meta MCP tool suites.
    Allows loading tools from different logical clusters into a FastMCP instance.
    """

    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
        self._suites: dict[str, list[Callable]] = {}

    def register_suite(self, name: str, registration_func: Callable[[FastMCP], Any]) -> Any:
        """Register a suite of tools using a provided registration function."""
        logger.info(f"Registering tool suite: {name}")
        result = registration_func(self.mcp)
        self._suites[name] = registration_func
        return result

    def get_registered_suites(self) -> list[str]:
        """Return a list of all registered suites."""
        return list(self._suites.keys())
