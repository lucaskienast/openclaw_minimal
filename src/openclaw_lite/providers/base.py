from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import AgentDecision, ChatMessage, MemoryContext, ToolSpec


class Provider(ABC):
    @abstractmethod
    def decide(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        memory_context: MemoryContext,
        tool_specs: list[ToolSpec],
        user_message: str,
    ) -> AgentDecision:
        raise NotImplementedError
