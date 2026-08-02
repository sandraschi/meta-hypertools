from typing import Any

from meta_mcp.services.base import MetaMCPService
from meta_mcp.tools.client_integration import check_client_integration, discover_clients
from meta_mcp.tools.discovery import discover_servers


class DiscoveryService(MetaMCPService):
    """
    Service for discovering MCP servers and auditing client integrations.
    """

    async def discover_servers(self, discovery_paths: list[str] | None = None) -> list[dict[str, Any]]:
        """Discover MCP servers on the system."""
        return discover_servers(discovery_paths)

    async def check_integration(self, ide_name: str) -> dict[str, Any]:
        """Audit client integration status for a specific IDE."""
        # Note: check_client_integration in tools/client_integration.py does the heavy lifting
        return check_client_integration(ide_name)

    async def discover_servers_api(
        self,
        operation: str,
        client_type: str | None = None,
        discovery_path: str | None = None,
    ) -> dict[str, Any]:
        """Discover MCP servers with operation-based interface."""
        try:
            if operation == "scan" or operation == "scan_root":
                paths = [discovery_path] if discovery_path else None
                result = await self.discover_servers(paths)
                return self.create_response(True, "Server discovery completed", {"servers": result})
            elif operation == "list":
                paths = [discovery_path] if discovery_path else None
                result = await self.discover_servers(paths)
                return self.create_response(True, "Server list retrieved", {"servers": result})
            else:
                return self.create_response(False, f"Unsupported operation: {operation}")
        except Exception as e:
            return self.create_response(False, f"Server discovery failed: {e!s}")

    async def check_client_integration(self, operation: str, client_type: str | None = None) -> dict[str, Any]:
        """Check client integration status."""
        try:
            if operation == "check":
                # Discover all installed clients
                discovered_clients = discover_clients()

                # Convert to the expected format for compatibility
                clients_dict = {}
                for client in discovered_clients:
                    clients_dict[client["id"]] = {
                        "name": client["name"],
                        "status": client["status"],
                        "installed": client["installed"],
                        "config_exists": client["config_exists"],
                        "mcp_configured": client["mcp_configured"],
                        "executable_path": client["executable_path"],
                        "config_path": str(client.get("config_path", "")),
                        "version": client.get("version"),
                        "servers": [],  # Will be populated if MCP is configured
                        "error": None,
                    }

                    # If MCP is configured, populate server list
                    if client["mcp_configured"] and "mcp_servers" in client:
                        clients_dict[client["id"]]["servers"] = client["mcp_servers"]

                return self.create_response(
                    True,
                    f"Discovered {len(discovered_clients)} MCP clients",
                    clients_dict,
                )
                # Check all clients or specific client
                clients_to_check = [
                    "claude",
                    "cursor",
                    "windsurf",
                    "zed",
                    "antigravity",
                    "opencode",
                ]
                if client_type:
                    clients_to_check = [client_type]

                results = {}
                for client in clients_to_check:
                    try:
                        result = await self.check_integration(client)
                        results[client] = result
                    except Exception as e:
                        results[client] = {"error": str(e)}

                return self.create_response(True, "Client integration check completed", {"clients": results})
            elif operation == "diagnose":
                # More detailed diagnosis
                if not client_type:
                    return self.create_response(False, "diagnose operation requires client_type parameter")

                result = await self.check_integration(client_type)
                return self.create_response(
                    True,
                    f"Diagnosis completed for {client_type}",
                    {"diagnosis": result},
                )
            else:
                return self.create_response(False, f"Unsupported operation: {operation}")
        except Exception as e:
            return self.create_response(False, f"Client integration check failed: {e!s}")
