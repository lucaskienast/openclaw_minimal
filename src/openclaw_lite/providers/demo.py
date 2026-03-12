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
               scratchpad: list[str]
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

        scratch = "\n".join(f"- {s}" for s in scratchpad) or "No tool activity."
        content = (
            "I am the lightweight educational runtime.\n\n"
            f"Session context: {len(history)} message(s) in history, {len(memories)} relevant memory hit(s).\n\n"
            f"Tool activity this turn:\n{scratch}\n\n"
            "To see tool calling, try: `list files`, `read file notes.txt`, or `write file notes.txt: hello`."
        )
        return AgentDecision(type="respond",
                             content=content,
                             reasoning="Fallback explanatory response.")
