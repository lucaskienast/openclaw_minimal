"""Unit tests for MCP server tool exposure."""
from __future__ import annotations

from typing import Any

import pytest

from openclaw_lite.tools.base import Tool, ToolContext, ToolRegistry
from openclaw_lite.tools.mcp_server import MCPToolServer


class _DummyTool(Tool):
    name = "dummy_tool"
    description = "A dummy tool for testing"
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        return f"echo: {tool_input.get('text', '')}"


class _FailingTool(Tool):
    name = "failing_tool"
    description = "A tool that always fails"
    input_schema = {"type": "object", "properties": {}}

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        raise RuntimeError("Tool execution failed")


class TestMCPToolServer:
    def test_tool_registration_produces_valid_schema(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        server = MCPToolServer(registry)
        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "dummy_tool"
        assert "inputSchema" in tools[0]
        assert tools[0]["inputSchema"]["type"] == "object"

    def test_tool_invocation_returns_result(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        server = MCPToolServer(registry)
        ctx = ToolContext(session_id="test", workspace="/tmp")
        result = server.call_tool("dummy_tool", {"text": "hello"}, ctx)
        assert result["content"][0]["text"] == "echo: hello"
        assert not result["isError"]

    def test_tool_invocation_error_handling(self) -> None:
        registry = ToolRegistry()
        registry.register(_FailingTool())
        server = MCPToolServer(registry)
        ctx = ToolContext(session_id="test", workspace="/tmp")
        result = server.call_tool("failing_tool", {}, ctx)
        assert result["isError"]
        assert "failed" in result["content"][0]["text"].lower()

    def test_unknown_tool_returns_error(self) -> None:
        registry = ToolRegistry()
        server = MCPToolServer(registry)
        ctx = ToolContext(session_id="test", workspace="/tmp")
        result = server.call_tool("nonexistent", {}, ctx)
        assert result["isError"]

    def test_multiple_tools_listed(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        registry.register(_FailingTool())
        server = MCPToolServer(registry)
        tools = server.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"dummy_tool", "failing_tool"}
