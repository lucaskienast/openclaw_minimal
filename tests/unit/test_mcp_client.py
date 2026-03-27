"""Unit tests for MCP client tool discovery and invocation."""
from __future__ import annotations

import pytest

from openclaw_lite.tools.mcp_client import MCPToolClient


class TestMCPToolClient:
    def test_create_client(self) -> None:
        client = MCPToolClient()
        assert client is not None

    def test_list_tools_empty_when_no_servers(self) -> None:
        client = MCPToolClient()
        tools = client.list_tools()
        assert tools == []

    def test_add_external_tool(self) -> None:
        client = MCPToolClient()
        client.register_external_tool(
            name="ext_tool",
            description="External tool",
            input_schema={"type": "object", "properties": {}},
        )
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "ext_tool"

    def test_call_unregistered_tool_returns_error(self) -> None:
        client = MCPToolClient()
        result = client.call_tool("nonexistent", {})
        assert "error" in result.lower() or "not found" in result.lower()
