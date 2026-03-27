"""Integration tests for the agent runtime loop with structured output."""
from __future__ import annotations

from pathlib import Path

import pytest

from openclaw_lite.config import Settings
from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.providers.demo import DemoProvider
from openclaw_lite.runtime import AgentRuntime
from openclaw_lite.tools.base import ToolRegistry
from openclaw_lite.tools.files import ListFilesTool, ReadFileTool, WriteFileTool
from openclaw_lite.tools.system import TimeTool


@pytest.fixture()
async def runtime_env(tmp_db_path: Path, tmp_workspace: Path):
    """Set up a full runtime with demo provider."""
    store = MemoryStore(tmp_db_path)
    await store.initialize()

    settings = Settings()
    settings.db_path = tmp_db_path
    settings.workspace = tmp_workspace
    settings.max_steps = 5
    settings.response_timeout = 30

    provider = DemoProvider()

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListFilesTool())
    registry.register(TimeTool())

    runtime = AgentRuntime(
        settings=settings,
        store=store,
        provider=provider,
        tools=registry,
    )

    # Create user and session
    user = await store.create_user(user_id="test-runtime-user")
    session = await store.create_session("test-runtime-user")

    # Create per-user workspace
    user_workspace = tmp_workspace / "test-runtime-user"
    user_workspace.mkdir(parents=True, exist_ok=True)

    yield runtime, store, user["user_id"], session["session_id"]
    await store.close()


class TestRuntimeLoop:
    async def test_simple_respond(self, runtime_env) -> None:
        runtime, store, uid, sid = runtime_env
        result = await runtime.handle_message(
            user_id=uid, session_id=sid, user_message="hello agent"
        )
        assert "response" in result
        assert result["session_id"] == sid

    async def test_tool_call_produces_result(self, runtime_env) -> None:
        runtime, store, uid, sid = runtime_env
        result = await runtime.handle_message(
            user_id=uid, session_id=sid, user_message="what time is it"
        )
        assert "response" in result

    async def test_messages_persisted(self, runtime_env) -> None:
        runtime, store, uid, sid = runtime_env
        await runtime.handle_message(
            user_id=uid, session_id=sid, user_message="hello"
        )
        messages = await store.get_messages(sid, uid)
        # At least assistant response (user msg stored by gateway, not runtime)
        assert len(messages) >= 1
        assert any(m["role"] == "assistant" for m in messages)

    async def test_file_write_and_read(self, runtime_env) -> None:
        runtime, store, uid, sid = runtime_env
        result = await runtime.handle_message(
            user_id=uid,
            session_id=sid,
            user_message="write file notes.txt: hello world",
        )
        assert "response" in result

    async def test_max_steps_respected(self, runtime_env) -> None:
        runtime, store, uid, sid = runtime_env
        # The demo provider won't loop forever, but verify the step count
        result = await runtime.handle_message(
            user_id=uid, session_id=sid, user_message="hello"
        )
        assert result["steps"] <= 5


class TestStructuredOutput:
    async def test_demo_provider_returns_valid_decisions(self, runtime_env) -> None:
        """Verify DemoProvider produces valid AgentDecision for all patterns."""
        from openclaw_lite.schemas import DecisionType

        runtime, store, uid, sid = runtime_env
        provider = DemoProvider()

        test_inputs = [
            "hello agent",
            "read file test.txt",
            "list files",
            "what time is it",
        ]
        for msg in test_inputs:
            decision = provider.decide(
                system_prompt="test",
                history=[],
                memory_context=__import__("openclaw_lite.schemas", fromlist=["MemoryContext"]).MemoryContext(),
                tool_specs=[],
                user_message=msg,
            )
            assert decision.type in (DecisionType.RESPOND, DecisionType.TOOL, DecisionType.DELEGATE)
            assert isinstance(decision.reasoning, str)
