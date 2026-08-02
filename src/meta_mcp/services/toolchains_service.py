import json
from pathlib import Path
from typing import Any

from meta_mcp.fleet_paths import master_mcp_config_path
from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.client_settings_manager import ClientSettingsManager

TOOLCHAINS_CONFIG_PATH = Path.home() / ".meta_mcp_toolchains.json"


class ToolchainService(MetaMCPService):
    """
    Service for managing toolchain presets.

    A toolchain preset is a named collection of MCP servers.
    This service allows creating, reading, updating, and deleting presets,
    as well as applying them to specific IDE clients.
    """

    def __init__(self):
        self.client_manager = ClientSettingsManager()
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not TOOLCHAINS_CONFIG_PATH.exists():
            TOOLCHAINS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOOLCHAINS_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"toolchains": {}}, f, indent=2)

    def _read_toolchains(self) -> dict[str, Any]:
        try:
            with open(TOOLCHAINS_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"toolchains": {}}

    def _write_toolchains(self, data: dict[str, Any]):
        with open(TOOLCHAINS_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _read_master_config(self) -> dict[str, Any]:
        path = master_mcp_config_path()
        if not path.is_file():
            return {"mcpServers": {}}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"mcpServers": {}}

    async def list_toolchains(self) -> dict[str, Any]:
        """List all saved toolchains."""
        try:
            data = self._read_toolchains()
            return self.create_response(True, "Listed toolchains", data)
        except Exception as e:
            return self.create_response(False, f"Failed to list toolchains: {e!s}")

    async def create_toolchain(self, name: str, servers: list[str], description: str = "") -> dict[str, Any]:
        """Create a new toolchain preset."""
        try:
            data = self._read_toolchains()
            if "toolchains" not in data:
                data["toolchains"] = {}

            data["toolchains"][name] = {
                "name": name,
                "description": description,
                "servers": servers,
            }
            self._write_toolchains(data)
            return self.create_response(True, f"Created toolchain '{name}'", data["toolchains"][name])
        except Exception as e:
            return self.create_response(False, f"Failed to create toolchain: {e!s}")

    async def delete_toolchain(self, name: str) -> dict[str, Any]:
        """Delete a toolchain preset."""
        try:
            data = self._read_toolchains()
            if "toolchains" in data and name in data["toolchains"]:
                del data["toolchains"][name]
                self._write_toolchains(data)
                return self.create_response(True, f"Deleted toolchain '{name}'")
            else:
                return self.create_response(False, f"Toolchain '{name}' not found")
        except Exception as e:
            return self.create_response(False, f"Failed to delete toolchain: {e!s}")

    async def apply_toolchain(self, toolchain_name: str, client_name: str) -> dict[str, Any]:
        """Apply a toolchain preset to an IDE client."""
        try:
            data = self._read_toolchains()
            if "toolchains" not in data or toolchain_name not in data["toolchains"]:
                return self.create_response(False, f"Toolchain '{toolchain_name}' not found")

            toolchain = data["toolchains"][toolchain_name]
            server_names = toolchain["servers"]

            master_config = self._read_master_config()
            available_servers = master_config.get("mcpServers", {})

            # Build the new servers dict
            new_servers_config = {}
            missing_servers = []

            for srv in server_names:
                if srv in available_servers:
                    new_servers_config[srv] = available_servers[srv]
                else:
                    missing_servers.append(srv)

            # Apply via ClientSettingsManager
            if client_name == "zed":
                updates = {"context_servers": new_servers_config}
            else:
                updates = {"mcpServers": new_servers_config}

            # We overwrite the server list entirely with the preset
            result = await self.client_manager.update_client_config(client_name, updates, backup=True)

            if not result.get("success"):
                return result

            # If there are missing servers, we should warn the user but consider it a success
            msg = f"Applied toolchain '{toolchain_name}' to {client_name}."
            if missing_servers:
                msg += f" Warning: the following servers were missing from MASTER config: {', '.join(missing_servers)}"

            return self.create_response(True, msg, result.get("data"))

        except Exception as e:
            return self.create_response(False, f"Failed to apply toolchain: {e!s}")

    async def get_available_servers(self) -> dict[str, Any]:
        """List all servers defined in MASTER_MCP_CONFIG.json."""
        try:
            master_config = self._read_master_config()
            servers = master_config.get("mcpServers", {})
            return self.create_response(
                True,
                "Extracted available servers",
                {"servers": list(servers.keys()), "details": servers},
            )
        except Exception as e:
            return self.create_response(False, f"Failed to get available servers: {e!s}")
