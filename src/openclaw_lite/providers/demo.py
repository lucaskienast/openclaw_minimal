from __future__ import annotations

import re

from ..schemas import AgentDecision, ChatMessage, ToolSpec
from .base import Provider


class DemoProvider(Provider):
    """A deterministic provider so the project runs with zero API keys.

    This is intentionally simple: it spots a few command-like intents and otherwise
    responds with an explanation based on the assembled context.
    """

    def decide(self,
               system_prompt: str,
               history: list[ChatMessage],
               memories: list[ChatMessage],
               tool_specs: list[ToolSpec],
               user_message: str,
               ) -> AgentDecision:
        lower = user_message.lower().strip()

        write_match = re.search(r"write file ([^:]+):\s*(.+)", user_message, flags=re.IGNORECASE | re.DOTALL)
        if write_match:
            return AgentDecision(type="tool",
                                 tool_name="write_file",
                                 tool_input={"path": write_match.group(1).strip(), "content": write_match.group(2).strip()},
                                 reasoning="User asked to write a file.")

        read_match = re.search(r"read file\s+(.+)", lower)
        if read_match:
            return AgentDecision(type="tool",
                                 tool_name="read_file",
                                 tool_input={"path": read_match.group(1).strip()},
                                 reasoning="User asked to read a file.")

        if "list files" in lower:
            return AgentDecision(type="tool",
                                 tool_name="list_files",
                                 tool_input={},
                                 reasoning="User asked to inspect workspace files.")

        if "time" in lower or "current utc" in lower:
            return AgentDecision(type="tool",
                                 tool_name="time_now",
                                 tool_input={},
                                 reasoning="User asked for the current time.")

        if "system info" in lower:
            return AgentDecision(type="tool",
                                 tool_name="system_info",
                                 tool_input={},
                                 reasoning="User asked for system info.")

        echo_match = re.search(r"echo\s+(.+)", user_message, flags=re.IGNORECASE)
        if echo_match:
            return AgentDecision(type="tool",
                                 tool_name="echo",
                                 tool_input={"text": echo_match.group(1).strip()},
                                 reasoning="User asked to echo text.")

        fetch_match = re.search(r"fetch\s+(https?://\S+)", user_message, flags=re.IGNORECASE)
        if fetch_match:
            return AgentDecision(type="tool",
                                 tool_name="web_fetch",
                                 tool_input={"url": fetch_match.group(1).strip()},
                                 reasoning="User asked to fetch a URL.")

        calc_match = re.search(r"calculate\s+(.+)", user_message, flags=re.IGNORECASE)
        if calc_match:
            return AgentDecision(type="tool",
                                 tool_name="calculator",
                                 tool_input={"expression": calc_match.group(1).strip()},
                                 reasoning="User asked to calculate an expression.")

        shell_match = re.search(r"shell\s+(.+)", user_message, flags=re.IGNORECASE)
        if shell_match:
            return AgentDecision(type="tool",
                                 tool_name="shell",
                                 tool_input={"command": shell_match.group(1).strip()},
                                 reasoning="User asked to run a shell command.")

        content = (
            "Demo Agent response.\n\n"
            f"Session context: {len(history)} message(s) in history, {len(memories)} relevant memory hit(s).\n\n."
        )
        return AgentDecision(type="respond",
                             content=content,
                             reasoning="Fallback explanatory response.")
