"""Shell tool — runs commands inside the workspace directory."""
from __future__ import annotations

import subprocess
from typing import Any

from openclaw_lite.tools.base import Tool, ToolContext


class ShellTool(Tool):
    name = "shell"
    description = "Run a shell command inside the workspace directory."
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        command = tool_input.get("command", "")
        if not command:
            return "Error: missing required parameter 'command'"
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=context.workspace,
                timeout=30,
            )
            output = result.stdout + result.stderr
            return output if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 30 seconds"
        except Exception as e:
            return f"Error: {e}"
