"""Core agent runtime — async ReAct loop with multi-tenant support."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from openclaw_lite.config import Settings
from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.providers.base import Provider
from openclaw_lite.schemas import ChatMessage, MemoryContext
from openclaw_lite.tools.base import ToolContext, ToolRegistry

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
    """Async agent runtime with multi-tenant session support."""

    def __init__(
        self,
        settings: Settings,
        store: MemoryStore,
        provider: Provider,
        tools: ToolRegistry,
    ) -> None:
        self._settings = settings
        self._store = store
        self._provider = provider
        self._tools = tools

    async def handle_message(
        self,
        *,
        user_id: str,
        session_id: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Process a user message through the agent loop.

        Returns a dict with response, session_id, steps, and metadata.
        """
        return await asyncio.wait_for(
            self._run_loop(user_id, session_id, user_message),
            timeout=self._settings.response_timeout,
        )

    async def _run_loop(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
    ) -> dict[str, Any]:
        original_message = user_message

        async def _get_history() -> list[ChatMessage]:
            rows = await self._store.get_messages(session_id, user_id, limit=25)
            msgs = [
                ChatMessage(role=r["role"], content=r["content"]) for r in rows
            ]
            if len(msgs) > 20:
                msgs = msgs[:5] + msgs[-15:]
            return msgs

        scratchpad: list[str] = []
        completed_responses: list[str] = []
        pending_tasks: list[str] = []
        tools_used: list[str] = []
        tool_context = ToolContext(
            session_id=session_id,
            workspace=str(self._settings.workspace / user_id),
        )

        for step in range(1, self._settings.max_steps + 1):
            history = await _get_history()
            memory_context = MemoryContext(short_term=history)

            decision = self._provider.decide(
                system_prompt=SYSTEM_PROMPT,
                history=memory_context.short_term,
                memory_context=memory_context,
                tool_specs=self._tools.specs(),
                user_message=user_message,
            )
            logger.info(
                "step=%s decision=%s reasoning=%s",
                step,
                decision.type,
                decision.reasoning,
            )

            if decision.tasks is not None:
                pending_tasks = [
                    t.description if hasattr(t, "description") else str(t)
                    for t in decision.tasks
                ]

            if decision.type == "respond":
                await self._store.add_message(
                    session_id, user_id, "assistant", decision.content
                )
                if pending_tasks:
                    remaining = "\n".join(f"- {t}" for t in pending_tasks)
                    scratchpad.append(f"intermediate_response={decision.content!r}")
                    if decision.content:
                        completed_responses.append(decision.content)
                    user_message = (
                        f"Your explanation: {decision.content}\n\n"
                        f"Remaining tasks:\n{remaining}\n\n"
                        f"Original request: {original_message}\n\n"
                        "Continue with the next task."
                    )
                    continue

                if decision.content:
                    completed_responses.append(decision.content)
                full_response = "\n\n".join(completed_responses)
                return {
                    "response": full_response,
                    "session_id": session_id,
                    "steps": step,
                    "tasks_completed": [],
                    "tools_used": tools_used,
                }

            if decision.type == "tool":
                tool = self._tools.get(decision.tool_name or "")
                result = tool.run(decision.tool_input, tool_context)
                observation = f"tool={tool.name} output={result}"
                scratchpad.append(observation)
                completed_responses.append(f"[{tool.name}] {result}")
                tools_used.append(tool.name)
                await self._store.add_message(
                    session_id, user_id, "tool", observation
                )
                remaining = (
                    "\n".join(f"- {t}" for t in pending_tasks)
                    if pending_tasks
                    else "(none)"
                )
                user_message = (
                    f"Tool result: {result}\n\n"
                    f"Remaining tasks:\n{remaining}\n\n"
                    f"Original request: {original_message}\n\n"
                    "Continue with the next task."
                )
                continue

            raise RuntimeError(f"Unsupported decision type: {decision.type}")

        fallback = "Stopped after max_steps to avoid an infinite loop."
        await self._store.add_message(session_id, user_id, "assistant", fallback)
        return {
            "response": fallback,
            "session_id": session_id,
            "steps": self._settings.max_steps,
            "tasks_completed": [],
            "tools_used": tools_used,
        }
