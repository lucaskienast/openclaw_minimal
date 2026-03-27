"""Unit tests for A2A dispatcher."""
from __future__ import annotations

import asyncio

import pytest

from openclaw_lite.a2a.dispatcher import A2ADispatcher
from openclaw_lite.a2a.types import A2ATask, A2ATaskStatus


async def _mock_runner(task: A2ATask) -> A2ATask:
    task.complete(f"Completed by {task.agent_type}")
    return task


async def _slow_runner(task: A2ATask) -> A2ATask:
    await asyncio.sleep(10)
    task.complete("Should not reach here")
    return task


async def _failing_runner(task: A2ATask) -> A2ATask:
    raise RuntimeError("Subagent crashed")


class TestA2ADispatcher:
    async def test_dispatch_success(self) -> None:
        dispatcher = A2ADispatcher(run_fn=_mock_runner)
        task = A2ATask(agent_type="research", input_msg="find info")
        result = await dispatcher.dispatch(task)
        assert result.status == A2ATaskStatus.COMPLETED
        assert "research" in result.output

    async def test_dispatch_timeout(self) -> None:
        dispatcher = A2ADispatcher(run_fn=_slow_runner, timeout=0.1)
        task = A2ATask(agent_type="coding", input_msg="write code", timeout_s=0.1)
        result = await dispatcher.dispatch(task)
        assert result.status == A2ATaskStatus.FAILED
        assert "timed out" in result.output.lower()

    async def test_dispatch_failure(self) -> None:
        dispatcher = A2ADispatcher(run_fn=_failing_runner)
        task = A2ATask(agent_type="analysis", input_msg="analyze data")
        result = await dispatcher.dispatch(task)
        assert result.status == A2ATaskStatus.FAILED
        assert "crashed" in result.output.lower()

    async def test_dispatch_many_concurrent(self) -> None:
        dispatcher = A2ADispatcher(run_fn=_mock_runner)
        tasks = [
            A2ATask(agent_type="research", input_msg="task 1"),
            A2ATask(agent_type="coding", input_msg="task 2"),
            A2ATask(agent_type="analysis", input_msg="task 3"),
        ]
        results = await dispatcher.dispatch_many(tasks)
        assert len(results) == 3
        assert all(r.status == A2ATaskStatus.COMPLETED for r in results)

    async def test_task_transitions(self) -> None:
        dispatcher = A2ADispatcher(run_fn=_mock_runner)
        task = A2ATask(agent_type="research", input_msg="test")
        assert task.status == A2ATaskStatus.SUBMITTED
        result = await dispatcher.dispatch(task)
        # After dispatch, should be completed (went through working)
        assert result.status == A2ATaskStatus.COMPLETED
