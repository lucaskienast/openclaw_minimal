from __future__ import annotations

import subprocess

from openclaw_lite.tools.base import Tool, ToolContext, ToolRegistry


class ShellTool(Tool):
    name = "shell"
    description = "Run a shell command inside the workspace directory."
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def run(self, tool_input: dict, context: ToolContext) -> str:
        result = subprocess.run(
            tool_input["command"],
            shell=True,
            capture_output=True,
            text=True,
            cwd=context.workspace,
            timeout=30,
        )
        return result.stdout + result.stderr


def register(registry: ToolRegistry) -> None:
    registry.register(ShellTool())
