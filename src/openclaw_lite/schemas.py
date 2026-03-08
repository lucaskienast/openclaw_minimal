from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(slots=True)
class AgentDecision:
    type: str  # "respond" | "tool"
    content: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
