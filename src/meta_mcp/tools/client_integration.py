"""
Client Integration Diagnostics for MCP Servers.

This module provides tools to verify if an MCP server is correctly configured
and starting up in various IDE clients (Antigravity, Claude, Windsurf, etc.).
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.tools import tool

logger = structlog.get_logger(__name__)


def load_json_with_comments(file_path: Path) -> dict[str, Any]:
    """Load JSON file, stripping single-line comments safely."""
    if not file_path.exists():
        return {}

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Regex to capture strings (group 1) OR comments (group 2)
    # We replace comments with empty string, keep strings as is.
    pattern = r'("(?:[^"\\]|\\.)*")|//.*'

    def replace(match):
        if match.group(1):
            return match.group(1)  # It's a string, keep it
        return ""  # It's a comment, remove it

    clean_content = re.sub(pattern, replace, content)

    if not clean_content.strip():
        return {}

    return json.loads(clean_content)


# IDE Client Configurations
CLIENT_CONFIGS = {
    "antigravity": {
        "name": "Antigravity",
        "config_path": Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        "log_dir": Path.home() / ".gemini" / "antigravity" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
    "claude": {
        "name": "Claude Desktop",
        "config_path": Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        "log_dir": Path.home() / "AppData" / "Roaming" / "Claude" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
    "windsurf": {
        "name": "Windsurf",
        "config_path": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        "log_dir": Path.home() / "AppData" / "Roaming" / "Windsurf" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
    "cursor": {
        "name": "Cursor",
        "config_path": Path.home()
        / "AppData"
        / "Roaming"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "cursor-storage"
        / "mcp_config.json",
        "log_dir": Path.home() / "AppData" / "Roaming" / "Cursor" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
    "zed": {
        "name": "Zed",
        "config_path": Path.home() / "AppData" / "Roaming" / "Zed" / "settings.json",
        "log_dir": Path.home() / "AppData" / "Local" / "Zed" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
    "opencode": {
        "name": "OpenCode",
        "config_path": Path.home() / ".config" / "opencode" / "opencode.jsonc",
        "log_dir": Path.home() / ".config" / "opencode" / "logs",
        "log_pattern": "mcp-server-{name}.log",
    },
}

# Startup Success Signatures
SUCCESS_SIGNATURES = [
    r"Message from server:",
    r"Tool Registration Success",
    r"JSON-RPC server listening",
    r"Initialized MCP server",
    r"Registering tools",
    r"Registering tool",
    r"server_started",
]


@tool(
    name="check_client_integration",
    description="Check if an MCP server is configured and starting in IDE clients.",
    tags=["diagnostics", "client", "integration"],
)
async def discover_clients() -> list[dict[str, Any]]:
    """
    Discover installed MCP client applications on the system.

    Returns:
        List of discovered client applications with installation status
    """

    discovered_clients = []

    # Client discovery paths and executables
    # Client discovery paths and executables
    # Use environment variables for robust path resolution
    local_app_data = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local"))
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))

    CLIENT_DISCOVERY = {
        "cursor": {
            "name": "Cursor",
            "paths": [
                local_app_data / "Programs" / "cursor" / "Cursor.exe",
                program_files / "Cursor" / "Cursor.exe",
                program_files_x86 / "Cursor" / "Cursor.exe",
            ],
            "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Cursor",
            "config_path": Path.home()
            / "AppData"
            / "Roaming"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "cursor-storage"
            / "mcp_config.json",
        },
        "windsurf": {
            "name": "Windsurf",
            "paths": [
                local_app_data / "Programs" / "windsurf" / "Windsurf.exe",
                program_files / "Windsurf" / "Windsurf.exe",
                program_files_x86 / "Windsurf" / "Windsurf.exe",
            ],
            "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Windsurf",
            "config_path": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        },
        "zed": {
            "name": "Zed",
            "paths": [
                user_profile / "scoop" / "shims" / "zed.exe",
                local_app_data / "Zed" / "Zed.exe",
                program_files / "Zed" / "Zed.exe",
                program_files_x86 / "Zed" / "Zed.exe",
            ],
            "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Zed",
            "config_path": Path.home() / "AppData" / "Roaming" / "Zed" / "settings.json",
        },
        "antigravity": {
            "name": "Antigravity IDE",
            "paths": [
                local_app_data / "Programs" / "Antigravity" / "bin" / "antigravity.cmd",
                user_profile / ".gemini" / "antigravity" / "antigravity.exe",
                program_files / "Gemini" / "Antigravity" / "antigravity.exe",
            ],
            "config_path": Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        },
        "claude": {
            "name": "Claude Desktop",
            "paths": [
                local_app_data / "AnthropicClaude" / "claude.exe",
                program_files / "Anthropic" / "Claude" / "claude.exe",
            ],
            "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Claude",
            "config_path": Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        },
        "vscode": {
            "name": "VS Code",
            "paths": [
                local_app_data / "Programs" / "Microsoft VS Code" / "Code.exe",
                program_files / "Microsoft VS Code" / "Code.exe",
                program_files_x86 / "Microsoft VS Code" / "Code.exe",
            ],
            "registry_key": (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                r"\{771FD6B0-FA20-440A-A002-3B3BAC16DC50}_is1"
            ),
            "config_path": Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json",
        },
        "opencode": {
            "name": "OpenCode",
            "paths": [
                local_app_data / "Programs" / "opencode" / "opencode.exe",
                user_profile / "scoop" / "shims" / "opencode.exe",
                user_profile / ".local" / "bin" / "opencode.exe",
            ],
            "config_path": Path.home() / ".config" / "opencode" / "opencode.jsonc",
        },
    }

    for client_id, client_info in CLIENT_DISCOVERY.items():
        client_status = {
            "id": client_id,
            "name": client_info["name"],
            "installed": False,
            "executable_path": None,
            "config_exists": False,
            "mcp_configured": False,
            "mcp_servers": [],  # List of configured MCP servers
            "version": None,
            "status": "not_found",
            "config_path": str(client_info.get("config_path", "")),
        }

        # Check if client is installed by looking for executables
        for path in client_info["paths"]:
            if path.exists():
                client_status["installed"] = True
                client_status["executable_path"] = str(path)
                client_status["status"] = "installed"
                break

        # Also check Windows registry for installation
        if not client_status["installed"] and "registry_key" in client_info:
            try:
                import winreg

                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, client_info["registry_key"])
                client_status["installed"] = True
                client_status["status"] = "installed"
                winreg.CloseKey(key)
            except Exception:
                pass

        # Check configuration
        config_path = client_info["config_path"]
        if config_path.exists():
            client_status["config_exists"] = True

            # Parse MCP configuration and extract servers
            try:
                config = load_json_with_comments(config_path)
                mcp_servers = []

                if client_id == "zed":
                    # Zed uses "context_servers" or "mcp.servers"
                    if "context_servers" in config:
                        for server_name, server_config in config["context_servers"].items():
                            mcp_servers.append(
                                {
                                    "name": server_name,
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {}),
                                }
                            )
                    elif "mcp" in config and "servers" in config["mcp"]:
                        for server_name, server_config in config["mcp"]["servers"].items():
                            mcp_servers.append(
                                {
                                    "name": server_name,
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {}),
                                }
                            )

                elif client_id == "vscode":
                    # VS Code uses "mcp.servers"
                    if "mcp" in config and "servers" in config["mcp"]:
                        for server_name, server_config in config["mcp"]["servers"].items():
                            mcp_servers.append(
                                {
                                    "name": server_name,
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {}),
                                }
                            )

                else:
                    # Standard MCP format (Cursor, Windsurf, Claude, etc.)
                    if "mcpServers" in config:
                        for server_name, server_config in config["mcpServers"].items():
                            mcp_servers.append(
                                {
                                    "name": server_name,
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {}),
                                }
                            )

                client_status["mcp_servers"] = mcp_servers

                if mcp_servers:
                    client_status["mcp_configured"] = True
                    client_status["status"] = "configured"

            except Exception as e:
                client_status["config_error"] = str(e)

        discovered_clients.append(client_status)

    return discovered_clients


async def check_client_integration(server_name: str) -> dict[str, Any]:
    """
    Check if a specific MCP server is integrated with known IDE clients.

    Checks:
    1. 'Config in Antigravity': Is it in mcp_config.json?
    2. 'Starts in Antigravity': Are there successful startup logs?
    (And analogous checks for Claude, Windsurf, etc.)

    Args:
        server_name: The name of the server to check (e.g., 'meta-mcp')

    Returns:
        Structured report of client integration status
    """
    report = {
        "server_name": server_name,
        "clients": {},
        "timestamp": time.time(),
        "summary": "",
    }

    configured_clients = []
    starting_clients = []

    for clientid, clientinfo in CLIENT_CONFIGS.items():
        client_name = clientinfo["name"]
        status = {
            "is_configured": False,
            "is_starting": False,
            "config_file": str(clientinfo["config_path"]),
            "log_file": None,
            "errors": [],
        }

        # 1. Check Configuration
        try:
            if clientinfo["config_path"].exists():
                config = load_json_with_comments(clientinfo["config_path"])

                # Check for server in config (handle different structures for Zed vs others)
                is_configured = False
                if clientid == "zed":
                    # Zed's settings.json uses 'context_servers'
                    if "context_servers" in config:
                        is_configured = server_name in config["context_servers"]
                else:
                    if "mcpServers" in config:
                        is_configured = server_name in config["mcpServers"]

                status["is_configured"] = is_configured
                if is_configured:
                    configured_clients.append(client_name)
        except Exception as e:
            status["errors"].append(f"Config check failed: {e!s}")

        # 2. Check Startup (Logs)
        if status["is_configured"]:
            try:
                log_dir = clientinfo["log_dir"]
                if log_dir.exists():
                    # Handle Zed's centralized log vs others' per-server logs
                    if clientid == "zed":
                        log_path = log_dir / "Zed.log"
                        if log_path.exists():
                            status["log_file"] = str(log_path)
                            with open(log_path, encoding="utf-8", errors="replace") as f:
                                f.seek(0, 2)
                                pos = max(0, f.tell() - 20000)  # Zed log can be large
                                f.seek(pos)
                                recent_logs = f.read()

                                # Zed success pattern: "Started {server_name} context server"
                                success_pattern = f"Started {server_name} context server"
                                if success_pattern.lower() in recent_logs.lower():
                                    status["is_starting"] = True
                                    starting_clients.append(client_name)
                    else:
                        # Look for server-specific log file
                        log_file_name = clientinfo["log_pattern"].format(name=server_name)
                        log_path = log_dir / log_file_name

                        if not log_path.exists():
                            # Try case-insensitive or partial match
                            for entry in log_dir.iterdir():
                                if server_name.lower() in entry.name.lower() and entry.suffix == ".log":
                                    log_path = entry
                                    break

                        if log_path.exists():
                            status["log_file"] = str(log_path)
                            # Read recent log lines
                            with open(log_path, encoding="utf-8", errors="replace") as f:
                                # Read last 10000 chars for efficiency
                                f.seek(0, 2)
                                pos = max(0, f.tell() - 10000)
                                f.seek(pos)
                                recent_logs = f.read()

                                # Check for success signatures
                                for signature in SUCCESS_SIGNATURES:
                                    if re.search(signature, recent_logs, re.IGNORECASE):
                                        status["is_starting"] = True
                                        starting_clients.append(client_name)
                                        break
            except Exception as e:
                status["errors"].append(f"Startup check failed: {e!s}")

        report["clients"][clientid] = status

    # Generate summary
    if not configured_clients:
        report["summary"] = f"Server '{server_name}' is not configured in any detected client."
    else:
        conf_str = ", ".join(configured_clients)
        if not starting_clients:
            report["summary"] = (
                f"Server '{server_name}' is configured in {conf_str} but no successful startup was detected in logs."
            )
        else:
            start_str = ", ".join(starting_clients)
            report["summary"] = (
                f"Server '{server_name}' is configured in {conf_str} and successfully started in {start_str}."
            )

    return report
