from __future__ import annotations

import platform
from datetime import datetime, UTC

from .base import Tool, ToolContext


class TimeTool(Tool):
    name = "time_now"
    description = "Return the current UTC time."
    input_schema = {"type": "object", "properties": {}}

    def run(self, tool_input: dict, context: ToolContext) -> str:
        return datetime.now(UTC).isoformat()


class SystemInfoTool(Tool):
    name = "system_info"
    description = "Return basic runtime information."
    input_schema = {"type": "object", "properties": {}}

    def run(self, tool_input: dict, context: ToolContext) -> str:
        return f"platform={platform.platform()} python={platform.python_version()} workspace={context.workspace}"
