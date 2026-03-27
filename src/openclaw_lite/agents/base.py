"""Base agent class implementing the ReAct loop with structured output."""
from __future__ import annotations

import time
from typing import Any

import structlog

from openclaw_lite.logging.categories import LogCategory
from openclaw_lite.prompts.system import build_system_prompt
from openclaw_lite.providers.base import Provider
from openclaw_lite.providers.output_parser import parse_decision
from openclaw_lite.schemas import (
    AgentDecision,
    ChatMessage,
    DecisionType,
    MemoryContext,
    TaskItem,
    TaskStatus,
)
from openclaw_lite.tools.base import ToolContext, ToolRegistry

logger = structlog.get_logger(__name__)


class BaseAgent:
    """ReAct agent loop with structured output validation and task tracking.

    This is the foundation that both MainAgent and subagents extend.
    The loop follows: Reason → Plan → Act → Observe → repeat.
    """

    def __init__(
        self,
        provider: Provider,
        tools: ToolRegistry,
        *,
        max_steps: int = 10,
        subagent_types: list[str] | None = None,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._max_steps = max_steps
        self._subagent_types = subagent_types or []

    def build_system_prompt(self) -> str:
        return build_system_prompt(
            tool_names=self._tools.names(),
            subagent_types=self._subagent_types if self._subagent_types else None,
        )

    async def run(
        self,
        *,
        user_message: str,
        history: list[ChatMessage] | None = None,
        memory_context: MemoryContext | None = None,
        tool_context: ToolContext | None = None,
    ) -> AgentDecision:
        """Execute the ReAct loop and return the final decision."""
        system_prompt = self.build_system_prompt()
        current_message = user_message
        original_message = user_message
        hist = history or []
        mem_ctx = memory_context or MemoryContext()
        scratchpad: list[str] = []
        task_checklist: list[TaskItem] = []

        for step in range(1, self._max_steps + 1):
            decision = self._call_provider(
                system_prompt=system_prompt,
                history=hist,
                memory_context=mem_ctx,
                user_message=current_message,
            )

            # Log reasoning
            logger.info(
                decision.reasoning[:200] if decision.reasoning else "(no reasoning)",
                category=LogCategory.REASONING,
                step=step,
                decision_type=str(decision.type),
            )

            # Update task checklist from model output
            if decision.tasks:
                task_checklist = list(decision.tasks)
                pending_count = sum(
                    1 for t in task_checklist
                    if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
                )
                logger.info(
                    f"Tasks: {len(task_checklist)} total, {pending_count} pending",
                    category=LogCategory.TASK_UPDATE,
                    step=step,
                )

            if decision.type == DecisionType.RESPOND:
                pending = [
                    t for t in task_checklist
                    if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
                ]
                if pending:
                    remaining = "\n".join(f"- {t.description}" for t in pending)
                    scratchpad.append(f"intermediate: {decision.content[:200]}")
                    current_message = (
                        f"Your previous response: {decision.content}\n\n"
                        f"Remaining tasks:\n{remaining}\n\n"
                        f"Original request: {original_message}\n\n"
                        "Continue with the next task."
                    )
                    continue
                # Final answer
                logger.info(
                    decision.content[:200] if decision.content else "(empty response)",
                    category=LogCategory.FINAL_ANSWER,
                    step=step,
                )
                return decision

            if decision.type == DecisionType.TOOL:
                if tool_context is None:
                    return AgentDecision(
                        type=DecisionType.RESPOND,
                        reasoning="No tool context available",
                        content="Tool execution is not available in this context.",
                    )
                tool = self._tools.get(decision.tool_name or "")
                start = time.monotonic()
                result = tool.run(decision.tool_input, tool_context)
                duration_ms = int((time.monotonic() - start) * 1000)
                scratchpad.append(f"tool={tool.name} result={result}")

                logger.info(
                    f"{tool.name}({decision.tool_input}) → {result[:200]}",
                    category=LogCategory.TOOL_CALL,
                    tool=tool.name,
                    duration_ms=duration_ms,
                    step=step,
                )

                current_message = (
                    f"Tool result from {tool.name}: {result}\n\n"
                    f"Original request: {original_message}\n\n"
                    "Continue with the next task."
                )
                continue

            if decision.type == DecisionType.DELEGATE:
                return decision

            return AgentDecision(
                type=DecisionType.RESPOND,
                reasoning=f"Unknown decision type: {decision.type}",
                content="I encountered an unexpected state.",
            )

        return AgentDecision(
            type=DecisionType.RESPOND,
            reasoning="Reached maximum steps",
            content="I've reached the maximum number of steps. Here's what I accomplished so far.",
        )

    def _call_provider(
        self,
        *,
        system_prompt: str,
        history: list[ChatMessage],
        memory_context: MemoryContext,
        user_message: str,
    ) -> AgentDecision:
        """Call the provider and parse the structured output."""
        return self._provider.decide(
            system_prompt=system_prompt,
            history=history,
            memory_context=memory_context,
            tool_specs=self._tools.specs(),
            user_message=user_message,
        )
