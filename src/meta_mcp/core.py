"""
Core orchestration for MetaMCP.
"""

import logging

from .services.config import ConfigService
from .services.discovery import DiscoveryService
from .services.management import ServerManagementService
from .services.sota import SOTAService
from .tools.builder import ServerBuilder
from .tools.fullstack import FullstackAppBuilder
from .tools.landing_page import LandingPageBuilder
from .tools.webshop import WebshopBuilder


class MetaMCP:
    """
    The main engine for MCP discovery, management, and analysis.
    """

    def __init__(self, config_path: str | None = None):
        self.config = ConfigService(config_path)
        self.discovery = DiscoveryService(self.config)
        self.management = ServerManagementService(self.config)
        self.sota = SOTAService()
        self.builder = ServerBuilder()
        self.landing_page = LandingPageBuilder()
        self.fullstack = FullstackAppBuilder()
        self.webshop = WebshopBuilder()

        self._logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize all internal services."""
        self._logger.info("Initializing MetaMCP engine")
        # Add initialization logic as needed
        pass

    async def shutdown(self):
        """Gracefully shutdown all services."""
        self._logger.info("Shutting down MetaMCP engine")
        await self.management.stop_all_servers()
