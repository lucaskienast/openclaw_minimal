"""Unit tests for session memory summarization trigger logic."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_lite.memory.session_memory import SessionMemoryManager
from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.schemas import SummarizationResult


@pytest.fixture()
async def store(tmp_db_path: Path):
    s = MemoryStore(tmp_db_path)
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture()
def mock_summarizer() -> AsyncMock:
    """Mock LLM summarization call."""
    summarizer = AsyncMock()
    summarizer.return_value = SummarizationResult(
        summary="Discussion about Python programming.",
        key_topics=["python", "coding"],
    )
    return summarizer


class TestSummarizationTrigger:
    async def test_no_trigger_below_threshold(
        self, store: MemoryStore, mock_summarizer: AsyncMock
    ) -> None:
        await store.create_user(user_id="u1")
        session = await store.create_session("u1")
        sid = session["session_id"]
        # Add a small message — well below 75% of any context window
        await store.add_message(sid, "u1", "user", "hello")

        mgr = SessionMemoryManager(
            store=store,
            context_window=128000,
            summarize_fn=mock_summarizer,
        )
        result = await mgr.check_and_summarize(sid, "u1")
        assert result is None
        mock_summarizer.assert_not_called()

    async def test_trigger_above_threshold(
        self, store: MemoryStore, mock_summarizer: AsyncMock
    ) -> None:
        await store.create_user(user_id="u1")
        session = await store.create_session("u1")
        sid = session["session_id"]

        # Use a very small context window so even a short msg triggers
        mgr = SessionMemoryManager(
            store=store,
            context_window=10,  # 75% = 7 tokens threshold
            summarize_fn=mock_summarizer,
        )
        # 13 tokens > 7 token threshold
        await store.add_message(sid, "u1", "user", "hello world this is a test message with many words to exceed threshold")
        result = await mgr.check_and_summarize(sid, "u1")
        assert result is not None
        assert result.summary == "Discussion about Python programming."
        mock_summarizer.assert_called_once()

    async def test_exact_threshold_no_trigger(
        self, store: MemoryStore, mock_summarizer: AsyncMock
    ) -> None:
        """At exactly the threshold, should not trigger (only above)."""
        await store.create_user(user_id="u1")
        session = await store.create_session("u1")
        sid = session["session_id"]

        mgr = SessionMemoryManager(
            store=store,
            context_window=100000,
            summarize_fn=mock_summarizer,
        )
        await store.add_message(sid, "u1", "user", "hello")
        result = await mgr.check_and_summarize(sid, "u1")
        assert result is None

    async def test_summary_stored_in_db(
        self, store: MemoryStore, mock_summarizer: AsyncMock
    ) -> None:
        await store.create_user(user_id="u1")
        session = await store.create_session("u1")
        sid = session["session_id"]

        mgr = SessionMemoryManager(
            store=store,
            context_window=10,
            summarize_fn=mock_summarizer,
        )
        await store.add_message(sid, "u1", "user", "a long message with many words to exceed the small threshold value")
        await mgr.check_and_summarize(sid, "u1")

        # Verify it was stored
        memories = await store.get_session_memories(sid)
        assert len(memories) >= 1
        assert "Python" in memories[0]["summary"]
