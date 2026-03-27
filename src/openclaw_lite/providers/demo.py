"""Deterministic demo provider — runs with zero API keys."""
from __future__ import annotations

import re

from openclaw_lite.schemas import (
    AgentDecision,
    ChatMessage,
    DecisionType,
    MemoryContext,
    TaskItem,
    TaskStatus,
    ToolSpec,
)
from openclaw_lite.providers.base import Provider


class DemoProvider(Provider):
    """Pattern-matching provider for testing without an LLM API.

    Returns valid AgentDecision objects matching the full Pydantic schema,
    including delegation support.
    """

    def decide(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        memory_context: MemoryContext,
        tool_specs: list[ToolSpec],
        user_message: str,
    ) -> AgentDecision:
        lower = user_message.lower().strip()

        # Tool patterns
        write_match = re.search(
            r"write file ([^:]+):\s*(.+)", user_message,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if write_match:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="write_file",
                tool_input={
                    "path": write_match.group(1).strip(),
                    "content": write_match.group(2).strip(),
                },
                reasoning="User asked to write a file.",
                tasks=[TaskItem(description="Write file", status=TaskStatus.IN_PROGRESS)],
            )

        read_match = re.search(r"read file\s+(.+)", lower)
        if read_match:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="read_file",
                tool_input={"path": read_match.group(1).strip()},
                reasoning="User asked to read a file.",
                tasks=[TaskItem(description="Read file", status=TaskStatus.IN_PROGRESS)],
            )

        if "list files" in lower:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="list_files",
                tool_input={},
                reasoning="User asked to list files.",
                tasks=[TaskItem(description="List files", status=TaskStatus.IN_PROGRESS)],
            )

        if "time" in lower or "current utc" in lower:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="time_now",
                tool_input={},
                reasoning="User asked for time.",
            )

        if "system info" in lower:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="system_info",
                tool_input={},
                reasoning="User asked for system info.",
            )

        # Delegation pattern
        delegate_match = re.search(
            r"delegate (\w+):\s*(.+)", user_message, flags=re.IGNORECASE | re.DOTALL,
        )
        if delegate_match:
            return AgentDecision(
                type=DecisionType.DELEGATE,
                delegation_target=delegate_match.group(1).strip(),
                delegation_prompt=delegate_match.group(2).strip(),
                reasoning="User explicitly delegated a task.",
            )

        fetch_match = re.search(r"fetch\s+(https?://\S+)", user_message, flags=re.IGNORECASE)
        if fetch_match:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="web_fetch",
                tool_input={"url": fetch_match.group(1).strip()},
                reasoning="User asked to fetch a URL.",
            )

        calc_match = re.search(r"calculate\s+(.+)", user_message, flags=re.IGNORECASE)
        if calc_match:
            return AgentDecision(
                type=DecisionType.TOOL,
                tool_name="calculator",
                tool_input={"expression": calc_match.group(1).strip()},
                reasoning="User asked to calculate.",
            )

        # Default: respond
        content = (
            f"Demo agent response. "
            f"{len(history)} message(s) in history, "
            f"{len(memory_context.long_term)} long-term memory hit(s)."
        )
        return AgentDecision(
            type=DecisionType.RESPOND,
            content=content,
            reasoning="Fallback response.",
        )
