from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import Settings
from .knowledge_store import KnowledgeStore
from .memory import LongTermMemory, MemoryStore
from .providers.base import Provider
from .schemas import ChatMessage, MemoryContext
from .tools.base import ToolContext, ToolRegistry

if TYPE_CHECKING:
    from .extraction import MemoryExtractionAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are OpenClaw Lite, a capable agent that executes tasks using tools.

Rules you must always follow:
1. On your FIRST decision, set `tasks` to a complete checklist of EVERYTHING you need to do
   (e.g. ["task 1", "task 2", "task 3"]).
2. After completing each item, remove it from `tasks`. When `tasks` is empty, you are done.
3. Use `type=tool` to execute a tool. Use `type=respond` with non-empty `tasks` to give an
   explanation or summary BEFORE continuing work. Use `type=respond` with empty `tasks` ONLY
   as your FINAL response once every task is complete.
4. Keep final responses clear and grounded in what was actually done.
"""


class AgentRuntime:
    def __init__(
        self,
        settings: Settings,
        memory: MemoryStore,
        long_term_memory: LongTermMemory,
        knowledge_store: KnowledgeStore,
        provider: Provider,
        tools: ToolRegistry,
        extraction_agent: MemoryExtractionAgent | None = None,
    ) -> None:
        self.settings = settings
        self.memory = memory
        self.long_term_memory = long_term_memory
        self.knowledge_store = knowledge_store
        self.provider = provider
        self.tools = tools
        self.extraction_agent = extraction_agent

    def handle_message(self, session_id: str, user_message: str) -> dict:
        self.memory.add_message(session_id, ChatMessage(role="user", content=user_message))
        original_message = user_message

        def _get_history() -> list[ChatMessage]:
            msgs = self.memory.get_history(session_id, limit=25)
            if len(msgs) > 20:
                msgs = msgs[:5] + msgs[-15:]
            return msgs

        def _build_context(query: str) -> MemoryContext:
            return MemoryContext(
                short_term=_get_history(),
                long_term=self.long_term_memory.search(query, limit=5),
                knowledge=self.knowledge_store.search(query, n_results=3),
                session_summary=self.memory.get_session_summary(session_id),
            )

        scratchpad: list[str] = []
        completed_responses: list[str] = []
        pending_tasks: list[str] = []
        tool_context = ToolContext(session_id=session_id, workspace=str(self.settings.workspace))

        for step in range(1, self.settings.max_steps + 1):
            memory_context = _build_context(original_message)
            decision = self.provider.decide(
                system_prompt=SYSTEM_PROMPT,
                history=memory_context.short_term,
                memory_context=memory_context,
                tool_specs=self.tools.specs(),
                user_message=user_message,
            )
            logger.info("step=%s; decision=%s; reasoning=%s; remaining_tasks=%s", step, decision.type, decision.reasoning, decision.tasks)

            # Update pending tasks: model's list takes precedence when explicitly provided
            # None = model didn't include tasks (safety net preserves last known)
            # []   = model explicitly said "I'm done" (clears pending)
            if decision.tasks is not None:
                pending_tasks = list(decision.tasks)

            if decision.type == "respond":
                self.memory.add_message(session_id, ChatMessage(role="assistant", content=decision.content))
                if pending_tasks:
                    # Tasks remain — continue loop
                    remaining = "\n".join(f"- {t}" for t in pending_tasks)
                    scratchpad.append(f"intermediate_response={decision.content!r}")
                    if decision.content:
                        completed_responses.append(decision.content)
                    user_message = (
                        f"Your explanation: {decision.content}\n\n"
                        f"Remaining tasks (you MUST complete all of these):\n{remaining}\n\n"
                        f"Original request: {original_message}\n\n"
                        "Continue with the next task. Return JSON with type, content, and tasks fields."
                    )
                    continue
                # No pending tasks — final response
                if decision.content:
                    completed_responses.append(decision.content)
                full_response = "\n\n".join(completed_responses)
                if self.extraction_agent is not None:
                    self.extraction_agent.run_async(session_id, original_message, full_response)
                return {
                    "session_id": session_id,
                    "response": full_response,
                    "scratchpad": scratchpad,
                    "steps": step,
                }

            if decision.type == "tool":
                tool = self.tools.get(decision.tool_name or "")
                result = tool.run(decision.tool_input, tool_context)
                observation = f"tool={tool.name} input={decision.tool_input} output={result}"
                scratchpad.append(observation)
                completed_responses.append(f"[{tool.name}] {result}")
                self.memory.add_message(session_id, ChatMessage(role="tool", content=observation))
                remaining = "\n".join(f"- {t}" for t in pending_tasks) if pending_tasks else "(none specified)"
                user_message = (
                    f"Tool result: {result}\n\n"
                    f"Remaining tasks:\n{remaining}\n\n"
                    f"Original request: {original_message}\n\n"
                    "Continue with the next task. Return JSON with type, content, and tasks fields."
                )
                continue

            raise RuntimeError(f"Unsupported decision type: {decision.type}")

        fallback = "Stopped after max_steps to avoid an infinite loop."
        self.memory.add_message(session_id, ChatMessage(role="assistant", content=fallback))
        return {"session_id": session_id, "response": fallback, "scratchpad": scratchpad, "steps": self.settings.max_steps}
