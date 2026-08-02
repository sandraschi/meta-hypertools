import json
import os
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService


class ClientSettingsManager(MetaMCPService):
    """
    Service for managing MCP client configurations.

    Provides capabilities to read, modify, and validate MCP client
    configuration files for various IDEs and editors.
    """

    def __init__(self):
        self.client_configs = {
            "claude": {
                "config_file": "~/AppData/Roaming/Claude/claude_desktop_config.json",
                "backup_ext": ".backup",
            },
            "cursor": {
                "config_file": "~/AppData/Roaming/Cursor/User/globalStorage/cursor-storage/mcp_config.json",
                "backup_ext": ".backup",
            },
            "windsurf": {
                "config_file": "~/AppData/Roaming/Windsurf/mcp_config.json",
                "backup_ext": ".backup",
            },
            "zed": {
                "config_file": "~/AppData/Roaming/Zed/settings.json",
                "backup_ext": ".backup",
            },
            "antigravity": {
                "config_file": "~/.gemini/antigravity/mcp_config.json",
                "backup_ext": ".backup",
            },
            "opencode": {
                "config_file": "~/.config/opencode/opencode.jsonc",
                "backup_ext": ".backup",
            },
        }

    async def read_client_config(self, client_name: str) -> dict[str, Any]:
        """Read MCP configuration for a specific client."""
        try:
            if client_name not in self.client_configs:
                return self.create_response(False, f"Unknown client: {client_name}")

            config_info = self.client_configs[client_name]
            config_path = Path(config_info["config_file"]).expanduser()

            if not config_path.exists():
                return self.create_response(False, f"Configuration file not found: {config_path}")

            # Read and parse config
            config_data = await self._read_config_file(config_path)

            return self.create_response(
                True,
                f"Configuration loaded for {client_name}",
                {
                    "client": client_name,
                    "config_file": str(config_path),
                    "config": config_data,
                    "servers": self._extract_mcp_servers(config_data, client_name),
                },
            )

        except Exception as e:
            return self.create_response(False, f"Failed to read client config: {e!s}")

    async def update_client_config(
        self, client_name: str, updates: dict[str, Any], backup: bool = True
    ) -> dict[str, Any]:
        """Update MCP configuration for a specific client."""
        try:
            if client_name not in self.client_configs:
                return self.create_response(False, f"Unknown client: {client_name}")

            config_info = self.client_configs[client_name]
            config_path = Path(config_info["config_file"]).expanduser()

            # Read current config
            current_config = {}
            if config_path.exists():
                current_config = await self._read_config_file(config_path)

            # Create backup if requested
            if backup and config_path.exists():
                backup_path = config_path.with_suffix(config_path.suffix + config_info["backup_ext"])
                await self._backup_config_file(config_path, backup_path)

            # Apply updates
            updated_config = await self._merge_config_updates(current_config, updates, client_name)

            # Validate configuration
            validation_result = await self._validate_config(updated_config, client_name)
            if not validation_result["valid"]:
                return self.create_response(
                    False,
                    "Configuration validation failed",
                    {"errors": validation_result["errors"]},
                )

            # Write updated config
            await self._write_config_file(config_path, updated_config)

            return self.create_response(
                True,
                f"Configuration updated for {client_name}",
                {
                    "client": client_name,
                    "config_file": str(config_path),
                    "changes": updates,
                    "backup_created": backup,
                },
            )

        except Exception as e:
            return self.create_response(False, f"Failed to update client config: {e!s}")

    async def add_server_to_client(
        self, client_name: str, server_name: str, server_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Add an MCP server to a client's configuration."""
        try:
            updates = {"mcpServers": {server_name: server_config}}

            return await self.update_client_config(client_name, updates)

        except Exception as e:
            return self.create_response(False, f"Failed to add server to client: {e!s}")

    async def remove_server_from_client(self, client_name: str, server_name: str) -> dict[str, Any]:
        """Remove an MCP server from a client's configuration."""
        try:
            # Read current config
            current_result = await self.read_client_config(client_name)
            if not current_result.get("success"):
                return current_result

            current_config = current_result.get("data", {}).get("config", {})

            # Remove server from config
            if "mcpServers" in current_config and server_name in current_config["mcpServers"]:
                del current_config["mcpServers"][server_name]

                # Write updated config
                config_info = self.client_configs[client_name]
                config_path = Path(config_info["config_file"]).expanduser()
                await self._write_config_file(config_path, current_config)

                return self.create_response(True, f"Server {server_name} removed from {client_name}")
            else:
                return self.create_response(
                    False,
                    f"Server {server_name} not found in {client_name} configuration",
                )

        except Exception as e:
            return self.create_response(False, f"Failed to remove server from client: {e!s}")

    async def validate_client_config(self, client_name: str) -> dict[str, Any]:
        """Validate a client's MCP configuration."""
        try:
            config_result = await self.read_client_config(client_name)
            if not config_result.get("success"):
                return config_result

            config_data = config_result.get("data", {}).get("config", {})
            validation_result = await self._validate_config(config_data, client_name)

            return self.create_response(
                True,
                f"Configuration validation completed for {client_name}",
                {
                    "client": client_name,
                    "valid": validation_result["valid"],
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                },
            )

        except Exception as e:
            return self.create_response(False, f"Configuration validation failed: {e!s}")

    async def list_client_configs(self) -> dict[str, Any]:
        """List all available client configurations."""
        configs = []

        for client_name, config_info in self.client_configs.items():
            config_path = Path(config_info["config_file"]).expanduser()

            config_status = {
                "client": client_name,
                "config_file": str(config_path),
                "exists": config_path.exists(),
                "readable": False,
                "writable": False,
                "servers": [],
            }

            if config_path.exists():
                config_status["readable"] = os.access(config_path, os.R_OK)
                config_status["writable"] = os.access(config_path, os.W_OK)

                # Try to read server count
                try:
                    config_data = await self._read_config_file(config_path)
                    servers = self._extract_mcp_servers(config_data, client_name)
                    config_status["servers"] = servers
                except Exception:
                    pass

            configs.append(config_status)

        return self.create_response(
            True,
            f"Found {len(configs)} client configurations",
            {"configs": configs, "count": len(configs)},
        )

    async def _read_config_file(self, config_path: Path) -> dict[str, Any]:
        """Read and parse a configuration file."""
        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Handle JSON with comments (common in some configs)
        # Remove lines starting with //
        clean_content = "\n".join(line for line in content.split("\n") if not line.strip().startswith("//"))

        return json.loads(clean_content)

    async def _write_config_file(self, config_path: Path, config_data: dict[str, Any]) -> None:
        """Write configuration data to file."""
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

    async def _backup_config_file(self, original_path: Path, backup_path: Path) -> None:
        """Create a backup of a configuration file."""
        import shutil

        shutil.copy2(original_path, backup_path)

    async def _merge_config_updates(
        self, current_config: dict[str, Any], updates: dict[str, Any], client_name: str
    ) -> dict[str, Any]:
        """Merge configuration updates into existing config."""
        merged = current_config.copy()

        # Handle MCP servers specifically
        if "mcpServers" in updates:
            if "mcpServers" not in merged:
                merged["mcpServers"] = {}
            merged["mcpServers"].update(updates["mcpServers"])

        # Handle other updates
        for key, value in updates.items():
            if key != "mcpServers":
                merged[key] = value

        return merged

    async def _validate_config(self, config: dict[str, Any], client_name: str) -> dict[str, Any]:
        """Validate MCP configuration."""
        errors = []
        warnings = []

        # Check for required structure
        if client_name in ["claude", "cursor", "windsurf", "antigravity", "opencode"]:
            if "mcpServers" not in config:
                warnings.append("No mcpServers section found")
            elif not isinstance(config["mcpServers"], dict):
                errors.append("mcpServers must be an object")
            else:
                # Validate each server config
                for server_name, server_config in config["mcpServers"].items():
                    if not isinstance(server_config, dict):
                        errors.append(f"Server {server_name} configuration must be an object")
                        continue

                    # Check for required fields
                    if "command" not in server_config:
                        errors.append(f"Server {server_name} missing required 'command' field")

        elif client_name == "zed":
            # Zed has different structure
            if "context_servers" not in config and "mcp" not in config:
                warnings.append("No MCP configuration found in Zed settings")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _extract_mcp_servers(self, config: dict[str, Any], client_name: str) -> list[dict[str, Any]]:
        """Extract MCP server configurations."""
        servers = []

        if client_name in ["claude", "cursor", "windsurf", "antigravity", "opencode"]:
            mcp_servers = config.get("mcpServers", {})
            for name, server_config in mcp_servers.items():
                servers.append(
                    {
                        "name": name,
                        "command": server_config.get("command"),
                        "args": server_config.get("args", []),
                        "env": server_config.get("env", {}),
                        "config": server_config,
                    }
                )

        elif client_name == "zed":
            # Zed has different structure
            context_servers = config.get("context_servers", {})
            mcp_section = config.get("mcp", {})
            servers_section = mcp_section.get("servers", {}) if isinstance(mcp_section, dict) else {}

            for name, server_config in {**context_servers, **servers_section}.items():
                servers.append(
                    {
                        "name": name,
                        "command": server_config.get("command"),
                        "args": server_config.get("args", []),
                        "env": server_config.get("env", {}),
                        "config": server_config,
                    }
                )

        return servers
