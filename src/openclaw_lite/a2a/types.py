"""A2A protocol data types — follows Agent-to-Agent semantics."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class A2ATaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentCard:
    """Describes a subagent's capabilities — follows A2A AgentCard semantics."""
    agent_type: str
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)


@dataclass
class A2AMessage:
    """A message exchanged in an A2A task."""
    role: str  # "user" or "agent"
    parts: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def text(role: str, text: str) -> A2AMessage:
        return A2AMessage(role=role, parts=[{"type": "text", "text": text}])


@dataclass
class A2ATask:
    """A task delegated to a subagent — follows A2A Task lifecycle."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: A2ATaskStatus = A2ATaskStatus.SUBMITTED
    agent_type: str = ""
    input_msg: str = ""
    output: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    timeout_s: float = 60.0

    def start(self) -> None:
        self.status = A2ATaskStatus.WORKING

    def complete(self, output: str, artifacts: list[dict[str, Any]] | None = None) -> None:
        self.status = A2ATaskStatus.COMPLETED
        self.output = output
        if artifacts:
            self.artifacts = artifacts

    def fail(self, error: str) -> None:
        self.status = A2ATaskStatus.FAILED
        self.output = f"Error: {error}"
