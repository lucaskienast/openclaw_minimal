"""Web fetch tool — retrieve content from URLs."""
from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from openclaw_lite.tools.base import Tool, ToolContext


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch the text content of a URL."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        url = tool_input.get("url", "")
        if not url:
            return "Error: missing required parameter 'url'"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OpenClaw-Lite/1.0)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read(4096).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return f"HTTP Error {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return f"URL Error: {e.reason}"
