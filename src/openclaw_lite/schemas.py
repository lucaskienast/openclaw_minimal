"""Core data models and structured output schemas."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DecisionType(str, Enum):
    RESPOND = "respond"
    TOOL = "tool"
    DELEGATE = "delegate"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ---------------------------------------------------------------------------
# Chat primitives
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: MessageRole
    content: str


class ToolSpec(BaseModel):
    """Describes a tool available to the agent."""
    name: str
    description: str
    input_schema: dict[str, Any]


# ---------------------------------------------------------------------------
# Structured LLM output schemas
# ---------------------------------------------------------------------------

class TaskItem(BaseModel):
    """A single item in the agent's internal task checklist."""
    description: str
    status: TaskStatus = TaskStatus.PENDING


class AgentDecision(BaseModel):
    """Primary output schema enforced on every LLM call.

    The agent must return valid JSON matching this schema. The ``type``
    field determines which optional fields are relevant:

    - ``respond``: ``content`` contains the final answer.
    - ``tool``: ``tool_name`` and ``tool_input`` identify the tool call.
    - ``delegate``: ``delegation_target`` and ``delegation_prompt`` describe
      the sub-agent task.
    """
    type: DecisionType
    reasoning: str = ""
    content: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    delegation_target: str | None = None
    delegation_prompt: str | None = None
    tasks: list[TaskItem] = Field(default_factory=list)


class ExtractedFact(BaseModel):
    """A single user fact extracted by the memory extraction LLM call."""
    key: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class MemoryExtractionResult(BaseModel):
    """Output schema for the post-interaction user-fact extraction call."""
    facts: list[ExtractedFact] = Field(default_factory=list)


class SummarizationResult(BaseModel):
    """Output schema for session context compression."""
    summary: str
    key_topics: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Context passed to the provider
# ---------------------------------------------------------------------------

class MemoryContext(BaseModel):
    """Aggregated memory context supplied to the provider alongside the
    conversation history."""
    short_term: list[ChatMessage] = Field(default_factory=list)
    long_term: list[str] = Field(default_factory=list)
    session_summary: str = ""
