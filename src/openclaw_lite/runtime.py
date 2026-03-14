from __future__ import annotations

import logging

from .config import Settings
from .memory import MemoryStore
from .providers.base import Provider
from .schemas import ChatMessage
from .tools.base import ToolContext, ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are OpenClaw Lite, a tiny educational agent runtime.
Your job is to demonstrate a production-style agent loop in a safe and understandable way.
When helpful, use tools. Keep answers clear and grounded in the available context.
"""


class AgentRuntime:
    def __init__(self, settings: Settings, memory: MemoryStore, provider: Provider, tools: ToolRegistry) -> None:
        self.settings = settings
        self.memory = memory
        self.provider = provider
        self.tools = tools

    def handle_message(self, session_id: str, user_message: str) -> dict:
        self.memory.add_message(session_id, ChatMessage(role="user", content=user_message))
        history = self.memory.get_history(session_id, limit=20)
        memories = self.memory.search(session_id, user_message, limit=5)
        scratchpad: list[str] = []
        tool_context = ToolContext(session_id=session_id, workspace=str(self.settings.workspace))

        for step in range(1, self.settings.max_steps + 1):
            decision = self.provider.decide(
                system_prompt=SYSTEM_PROMPT,
                history=history,
                memories=memories,
                tool_specs=self.tools.specs(),
                user_message=user_message,
            )
            logger.info("step=%s decision=%s reasoning=%s", step, decision.type, decision.reasoning)

            if decision.type == "respond":
                self.memory.add_message(session_id, ChatMessage(role="assistant", content=decision.content))
                return {
                    "session_id": session_id,
                    "response": decision.content,
                    "scratchpad": scratchpad,
                    "steps": step,
                }

            if decision.type == "tool":
                tool = self.tools.get(decision.tool_name or "")
                result = tool.run(decision.tool_input, tool_context)
                observation = f"tool={tool.name} input={decision.tool_input} output={result}"
                scratchpad.append(observation)
                history.append(ChatMessage(role="tool", content=observation))
                self.memory.add_message(session_id, ChatMessage(role="tool", content=observation))
                user_message = f"The tool result was: {result}. Now continue helping the user."
                continue

            raise RuntimeError(f"Unsupported decision type: {decision.type}")

        fallback = "Stopped after max_steps to avoid an infinite loop."
        self.memory.add_message(session_id, ChatMessage(role="assistant", content=fallback))
        return {"session_id": session_id, "response": fallback, "scratchpad": scratchpad, "steps": self.settings.max_steps}
