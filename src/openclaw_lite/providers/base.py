from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import AgentDecision, ChatMessage, ToolSpec


class Provider(ABC):
    @abstractmethod
    def decide(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        memories: list[ChatMessage],
        tool_specs: list[ToolSpec],
        user_message: str,
        scratchpad: list[str],
    ) -> AgentDecision:
        raise NotImplementedError
