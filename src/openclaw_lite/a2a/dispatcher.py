"""A2A task dispatcher — routes tasks to subagents."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from openclaw_lite.a2a.types import A2ATask, A2ATaskStatus

logger = logging.getLogger(__name__)

SubagentRunFn = Callable[[A2ATask], Awaitable[A2ATask]]


class A2ADispatcher:
    """Dispatches A2A tasks to subagent runners.

    Manages task lifecycle (submitted → working → completed/failed),
    supports concurrent dispatch via asyncio.gather for independent tasks.
    """

    def __init__(self, run_fn: SubagentRunFn, timeout: float = 60.0) -> None:
        self._run_fn = run_fn
        self._timeout = timeout

    async def dispatch(self, task: A2ATask) -> A2ATask:
        """Dispatch a single task to the appropriate subagent."""
        task.start()
        logger.info(
            "Dispatching task %s to %s agent",
            task.task_id[:8], task.agent_type,
        )
        try:
            result = await asyncio.wait_for(
                self._run_fn(task),
                timeout=task.timeout_s or self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            task.fail(f"Timed out after {task.timeout_s}s")
            logger.warning("Task %s timed out", task.task_id[:8])
            return task
        except Exception as exc:
            task.fail(str(exc))
            logger.exception("Task %s failed", task.task_id[:8])
            return task

    async def dispatch_many(self, tasks: list[A2ATask]) -> list[A2ATask]:
        """Dispatch multiple independent tasks concurrently."""
        return list(await asyncio.gather(
            *(self.dispatch(t) for t in tasks),
            return_exceptions=False,
        ))
