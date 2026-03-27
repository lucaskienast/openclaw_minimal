"""MCP client — discovers and invokes tools from external MCP servers."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPToolClient:
    """Client for consuming tools from external MCP servers.

    For the initial implementation, this manages a registry of externally
    declared tools. Full stdio subprocess transport can be added when
    connecting to real external MCP servers.
    """

    def __init__(self) -> None:
        self._external_tools: dict[str, dict[str, Any]] = {}

    def register_external_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
    ) -> None:
        """Register an external tool definition (from MCP server discovery)."""
        self._external_tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all discovered external tool definitions."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["input_schema"],
            }
            for t in self._external_tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke an external tool.

        In the current implementation, this is a placeholder that returns
        an error for unregistered tools. Full implementation would use
        stdio_client() transport to communicate with the server process.
        """
        if name not in self._external_tools:
            return f"Error: tool '{name}' not found in external MCP tools"

        # Placeholder — real implementation would send via MCP protocol
        logger.info("External MCP tool call: %s(%s)", name, arguments)
        return f"External tool '{name}' called (stub — no server connected)"
