from __future__ import annotations

from openclaw_lite.tools.base import Tool, ToolContext, ToolRegistry


class EchoTool(Tool):
    name = "echo"
    description = "Echo text back. Useful as the smallest possible plugin example."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, tool_input: dict, context: ToolContext) -> str:
        return tool_input["text"]


def register(registry: ToolRegistry) -> None:
    registry.register(EchoTool())
