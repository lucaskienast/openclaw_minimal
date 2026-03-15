from __future__ import annotations

import urllib.request

from openclaw_lite.tools.base import Tool, ToolContext, ToolRegistry


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch the text content of a URL."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    def run(self, tool_input: dict, context: ToolContext) -> str:
        with urllib.request.urlopen(tool_input["url"], timeout=10) as r:
            return r.read(4096).decode("utf-8", errors="replace")


def register(registry: ToolRegistry) -> None:
    registry.register(WebFetchTool())
