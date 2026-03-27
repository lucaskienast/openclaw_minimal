"""MCP tool server — exposes registered tools via MCP protocol semantics."""
from __future__ import annotations

import logging
from typing import Any

from openclaw_lite.tools.base import ToolContext, ToolRegistry

logger = logging.getLogger(__name__)


class MCPToolServer:
    """Wraps a ToolRegistry and exposes tools using MCP-compatible schemas.

    For the initial implementation, this provides the MCP data model
    (tool definitions, call/result format) without requiring a subprocess
    transport. The full stdio server can be added when external tool
    exposure is needed.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-formatted tool definitions for all registered tools."""
        tools = []
        for spec in self._registry.specs():
            tools.append({
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.input_schema,
            })
        return tools

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        """Invoke a tool and return MCP-formatted result.

        Returns a dict matching the MCP CallToolResult schema:
        {
            "content": [{"type": "text", "text": "..."}],
            "isError": false
        }
        """
        try:
            tool = self._registry.get(name)
        except KeyError:
            return {
                "content": [{"type": "text", "text": f"Error: tool '{name}' not found"}],
                "isError": True,
            }

        try:
            result = tool.run(arguments, context)
            return {
                "content": [{"type": "text", "text": result}],
                "isError": False,
            }
        except Exception as exc:
            logger.exception("Tool '%s' execution failed", name)
            return {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            }
