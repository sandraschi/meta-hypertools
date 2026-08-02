"""
MCP Tool Discovery and Management

This module provides functionality to discover, register, and manage MCP tools.
"""

import importlib
import inspect
import pkgutil
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

from meta_mcp.tools.decorators import ToolMetadata, tool

logger = structlog.get_logger(__name__)

# Type variable for generic functions
T = TypeVar("T")


class ToolRegistry:
    """Registry for MCP tools."""

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}
        self._tool_metadata: dict[str, ToolMetadata] = {}
        self._discovered = False

    def register(self, func: Callable, metadata: ToolMetadata | None = None) -> None:
        """
        Register a tool function with optional metadata.

        Args:
            func: The tool function to register
            metadata: Optional metadata for the tool
        """
        tool_name = func.__name__

        # Get or create metadata
        if metadata is None:
            metadata = getattr(func, "__mcp_metadata__", None) or ToolMetadata(
                name=tool_name, description=func.__doc__ or ""
            )

        # Store the tool and its metadata
        self._tools[tool_name] = {
            "function": func,
            "module": func.__module__,
            "docstring": func.__doc__ or "",
            "signature": str(inspect.signature(func)),
        }
        self._tool_metadata[tool_name] = metadata

        logger.debug(
            "tool_registered",
            extra={
                "tool": tool_name,
                "module": func.__module__,
                "metadata": metadata.to_dict() if hasattr(metadata, "to_dict") else str(metadata),
            },
        )

    def discover_tools(
        self,
        package: str | list[str],
        recursive: bool = True,
        skip_errors: bool = True,
    ) -> None:
        """
        Discover and register tools from Python packages.

        Args:
            package: Package name or list of package names to search for tools
            recursive: Whether to search subpackages recursively
            skip_errors: Whether to skip errors during discovery
        """
        if isinstance(package, str):
            packages = [package]
        else:
            packages = package

        for pkg in packages:
            try:
                self._discover_package(pkg, recursive, skip_errors)
            except Exception as e:
                if skip_errors:
                    logger.warning(
                        "package_discovery_failed",
                        extra={"package": pkg, "error": str(e)},
                        exc_info=True,
                    )
                else:
                    raise

        self._discovered = True
        logger.info(
            "tool_discovery_complete",
            extra={"tools_registered": len(self._tools), "packages_searched": packages},
        )

    def _discover_package(self, package: str, recursive: bool = True, skip_errors: bool = True) -> None:
        """Discover tools in a package."""
        try:
            # Import the package
            module = importlib.import_module(package)

            # Get the package path
            if not hasattr(module, "__path__"):
                return

            # Find all modules in the package
            for _, name, is_pkg in pkgutil.iter_modules(module.__path__):
                full_name = f"{package}.{name}"

                try:
                    # Import the module
                    mod = importlib.import_module(full_name)

                    # Register tools in the module
                    self._register_tools_in_module(mod)

                    # Recursively process subpackages
                    if recursive and is_pkg:
                        self._discover_package(full_name, recursive, skip_errors)

                except Exception as e:
                    if skip_errors:
                        logger.warning(
                            "module_import_failed",
                            extra={"module": full_name, "error": str(e)},
                            exc_info=True,
                        )
                    else:
                        raise

        except ImportError as e:
            if skip_errors:
                logger.warning(
                    "package_import_failed",
                    extra={"package": package, "error": str(e)},
                    exc_info=True,
                )
            else:
                raise

    def _register_tools_in_module(self, module: Any) -> None:
        """Register all tools found in a module."""
        for name, obj in inspect.getmembers(module):
            # Skip private members
            if name.startswith("_"):
                continue

            # Check if the object is a function with MCP metadata
            if inspect.isfunction(obj) and hasattr(obj, "__mcp_metadata__"):
                self.register(obj)

            # Check if the object is a class with MCP metadata
            elif inspect.isclass(obj) and hasattr(obj, "__mcp_metadata__"):
                # Register the class itself if it's callable
                if callable(obj):
                    self.register(obj)

                # Register class methods with MCP metadata
                for _method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    if hasattr(method, "__mcp_metadata__"):
                        self.register(method)

    def get_tool(self, name: str) -> Callable | None:
        """
        Get a tool function by name.

        Args:
            name: Name of the tool to get

        Returns:
            The tool function if found, None otherwise
        """
        if not self._discovered:
            self.discover_tools(["meta_mcp.tools"])

        return self._tools.get(name, {}).get("function")

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """
        Get metadata for a tool.

        Args:
            name: Name of the tool

        Returns:
            The tool's metadata if found, None otherwise
        """
        if not self._discovered:
            self.discover_tools(["meta_mcp.tools"])

        return self._tool_metadata.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with their metadata.

        Returns:
            List of dictionaries containing tool information
        """
        if not self._discovered:
            self.discover_tools(["meta_mcp.tools"])

        result = []
        for name, tool_info in self._tools.items():
            metadata = self._tool_metadata.get(name, {})
            result.append(
                {
                    "name": name,
                    "module": tool_info["module"],
                    "description": metadata.description if hasattr(metadata, "description") else "",
                    "version": metadata.version if hasattr(metadata, "version") else "1.0.0",
                    "tags": metadata.tags if hasattr(metadata, "tags") else [],
                    "signature": tool_info["signature"],
                }
            )

        return result

    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        """
        Execute a tool by name with the given arguments.

        Args:
            name: Name of the tool to execute
            *args: Positional arguments to pass to the tool
            **kwargs: Keyword arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            KeyError: If the tool is not found
            Exception: Any exception raised by the tool
        """
        if not self._discovered:
            self.discover_tools(["meta_mcp.tools"])

        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        tool_func = self._tools[name]["function"]

        # Log the tool execution
        logger.info(
            "tool_execution_start",
            extra={
                "tool": name,
                "args": args,
                "kwargs": kwargs,
                "metadata": self._tool_metadata.get(name, {}).to_dict()
                if hasattr(self._tool_metadata.get(name), "to_dict")
                else str(self._tool_metadata.get(name)),
            },
        )

        try:
            # Execute the tool
            result = tool_func(*args, **kwargs)

            # Log successful execution
            logger.info(
                "tool_execution_success",
                extra={
                    "tool": name,
                    "result": str(result)[:1000],  # Limit result size
                },
            )

            return result

        except Exception as e:
            # Log the error
            logger.error(
                "tool_execution_error",
                extra={"tool": name, "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise


# Global registry instance
registry = ToolRegistry()


def get_tool(name: str) -> Callable | None:
    """Get a tool function by name."""
    return registry.get_tool(name)


def get_metadata(name: str) -> ToolMetadata | None:
    """Get metadata for a tool."""
    return registry.get_metadata(name)


def list_tools() -> list[dict[str, Any]]:
    """List all registered tools with their metadata."""
    return registry.list_tools()


def execute_tool(name: str, *args, **kwargs) -> Any:
    """Execute a tool by name with the given arguments."""
    return registry.execute_tool(name, *args, **kwargs)


def discover_tools(package: str | list[str], recursive: bool = True, skip_errors: bool = True) -> None:
    """
    Discover and register tools from Python packages.

    Args:
        package: Package name or list of package names to search for tools
        recursive: Whether to search subpackages recursively
        skip_errors: Whether to skip errors during discovery
    """
    registry.discover_tools(package, recursive, skip_errors)


def discover_servers(
    search_paths: list[str] | None = None,
    config_files: list[str] | None = None,
    recursive: bool = True,
) -> list[dict[str, Any]]:
    """
    Discover MCP servers across the system.

    Args:
        search_paths: List of directories to search for MCP servers
        config_files: List of MCP configuration files to parse
        recursive: Whether to search subdirectories recursively

    Returns:
        List of discovered MCP server configurations
    """
    import json
    from pathlib import Path

    servers = []

    # Default search paths - only check reasonable locations to avoid hanging
    if search_paths is None:
        search_paths = [
            str(Path.home() / ".gemini" / "antigravity"),
            str(Path.home() / "AppData" / "Roaming" / "Claude"),
            str(Path.home() / "AppData" / "Roaming" / "Cursor"),
            str(Path.home() / "AppData" / "Roaming" / "Windsurf"),
            str(Path.home() / "AppData" / "Roaming" / "Zed"),
            str(Path.cwd()),  # Current working directory only
        ]

    # Default config files
    if config_files is None:
        config_files = [
            str(Path.home() / ".gemini" / "antigravity" / "mcp_config.json"),
            str(Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"),
            str(
                Path.home()
                / "AppData"
                / "Roaming"
                / "Cursor"
                / "User"
                / "globalStorage"
                / "cursor-storage"
                / "mcp_config.json"
            ),
            str(Path.home() / "AppData" / "Roaming" / "Windsurf" / "mcp_config.json"),
            str(Path.home() / "AppData" / "Roaming" / "Zed" / "settings.json"),
            # Fallback for older Cursor versions
            str(Path.home() / "AppData" / "Roaming" / "Cursor" / "logs" / "mcp_config.json"),
        ]

    # Search configuration files
    for config_file in config_files:
        try:
            if Path(config_file).exists():

                def load_json_robust(p: Path) -> dict[str, Any]:
                    with open(p, encoding="utf-8") as f:
                        lines = f.readlines()
                    clean = []
                    for line in lines:
                        if "//" in line:
                            line = line[: line.find("//")]
                        clean.append(line)
                    content = "".join(clean).strip()
                    return json.loads(content) if content else {}

                config = load_json_robust(Path(config_file))

                # Handle standard mcpServers key
                mcp_servers = config.get("mcpServers", {})

                # Handle Zed-specific keys
                if "context_servers" in config:
                    mcp_servers.update(config["context_servers"])
                if "mcp" in config and isinstance(config["mcp"], dict):
                    if "servers" in config["mcp"]:
                        mcp_servers.update(config["mcp"]["servers"])

                for server_name, server_config in mcp_servers.items():
                    servers.append(
                        {
                            "name": server_name,
                            "config": server_config,
                            "source": config_file,
                            "type": "config_file",
                        }
                    )

        except Exception as e:
            logger.warning(f"Failed to parse config file {config_file}: {e}")

    # Search directories for MCP servers (limited to avoid hanging)
    servers_found = 0
    max_servers = 50  # Limit to prevent excessive scanning

    for search_path in search_paths:
        if servers_found >= max_servers:
            break

        try:
            path = Path(search_path)
            if path.exists() and path.is_dir():
                # Look for common MCP server patterns (non-recursive for speed)
                patterns = [
                    "*mcp*.py",
                    "*mcp*.js",
                    "*mcp*.ts",
                    "package.json",  # Node.js MCP servers
                    "pyproject.toml",  # Python MCP servers
                    "Cargo.toml",  # Rust MCP servers
                ]

                for pattern in patterns:
                    if servers_found >= max_servers:
                        break

                    # Use glob instead of rglob to avoid deep recursion
                    for file_path in path.glob(pattern):
                        if servers_found >= max_servers:
                            break

                        if file_path.is_file():
                            # Basic server detection
                            server_info = {
                                "name": file_path.stem,
                                "path": str(file_path),
                                "source": search_path,
                                "type": "file_discovery",
                                "config": {},
                                "execution": None,
                            }

                            # Try to extract more info from package files
                            if file_path.name == "package.json":
                                try:
                                    with open(file_path, encoding="utf-8") as f:
                                        package_data = json.load(f)
                                    server_info["config"] = {
                                        "package_name": package_data.get("name", ""),
                                        "version": package_data.get("version", ""),
                                        "description": package_data.get("description", ""),
                                        "scripts": package_data.get("scripts", {}),
                                    }

                                    # Infer Node execution
                                    if "bin" in package_data:
                                        # If bin is a specific file
                                        bin_entry = package_data["bin"]
                                        if isinstance(bin_entry, str):
                                            server_info["execution"] = {
                                                "command": "node",
                                                "args": [str(path / bin_entry)],
                                                "env": {},
                                            }
                                        elif isinstance(bin_entry, dict):
                                            # Pick the first one corresponding to package name if possible
                                            cmd_script = next(iter(bin_entry.values()))
                                            server_info["execution"] = {
                                                "command": "node",
                                                "args": [str(path / cmd_script)],
                                                "env": {},
                                            }
                                    elif "main" in package_data:
                                        server_info["execution"] = {
                                            "command": "node",
                                            "args": [str(path / package_data["main"])],
                                            "env": {},
                                        }

                                except Exception:
                                    pass

                            elif file_path.name == "pyproject.toml":
                                try:
                                    import toml

                                    with open(file_path, encoding="utf-8") as f:
                                        pyproject_data = toml.load(f)

                                    project_name = pyproject_data.get("project", {}).get("name", "")

                                    server_info["config"] = {
                                        "package_name": project_name,
                                        "version": pyproject_data.get("project", {}).get("version", ""),
                                        "description": pyproject_data.get("project", {}).get("description", ""),
                                    }

                                    # Infer Python/UV execution
                                    if project_name:
                                        # Assume 'uv run' for pyproject.toml based projects in this environment
                                        server_info["execution"] = {
                                            "command": "uv",
                                            "args": ["run", project_name],
                                            "env": {},
                                        }

                                except Exception:
                                    pass

                            servers.append(server_info)
                            servers_found += 1

        except Exception as e:
            logger.warning(f"Failed to search path {search_path}: {e}")

    # Remove duplicates
    unique_servers = []
    seen_names = set()

    for server in servers:
        server_key = f"{server['name']}_{server.get('path', server.get('source', ''))}"
        if server_key not in seen_names:
            unique_servers.append(server)
            seen_names.add(server_key)

    logger.info(f"Discovered {len(unique_servers)} MCP servers")
    return unique_servers


# Example usage
if __name__ == "__main__":
    import logging

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("tool_discovery.log")],
    )

    # Example tool
    @tool(
        name="example_tool",
        description="An example MCP tool",
        version="1.0.0",
        tags=["example", "test"],
    )
    def example_tool(text: str, repeat: int = 1) -> str:
        """Repeat the input text the specified number of times."""
        if repeat < 0:
            raise ValueError("Repeat count must be non-negative")
        return " ".join([text] * repeat)

    # Discover and register tools
    discover_tools(["__main__"])

    # List all tools
    logger.info("Registered tools:")
    for tool_info in list_tools():
        logger.info(f"- {tool_info['name']}: {tool_info['description']}")

    # Execute a tool
    logger.info("Executing example_tool:")
    result = execute_tool("example_tool", "Hello", repeat=3)
    logger.info(f"Result: {result}")
