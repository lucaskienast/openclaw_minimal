"""Integration tests for tiered memory: session summaries and user facts."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from openclaw_lite.memory.session_memory import SessionMemoryManager
from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.memory.user_memory import UserMemoryExtractor
from openclaw_lite.schemas import (
    ExtractedFact,
    MemoryExtractionResult,
    SummarizationResult,
)


@pytest.fixture()
async def store(tmp_db_path: Path):
    s = MemoryStore(tmp_db_path)
    await s.initialize()
    yield s
    await s.close()


class TestSessionMemoryIntegration:
    async def test_full_summarization_flow(self, store: MemoryStore) -> None:
        """Send messages until threshold exceeded, verify summary created."""
        await store.create_user(user_id="u1")
        session = await store.create_session("u1")
        sid = session["session_id"]

        mock_summarizer = AsyncMock(return_value=SummarizationResult(
            summary="User discussed Python testing strategies.",
            key_topics=["python", "testing", "pytest"],
        ))
        mgr = SessionMemoryManager(
            store=store, context_window=10, summarize_fn=mock_summarizer
        )

        # Add messages to exceed threshold
        await store.add_message(sid, "u1", "user", "How do I write tests in Python with pytest?")
        result = await mgr.check_and_summarize(sid, "u1")
        assert result is not None
        assert "Python" in result.summary

        # Verify stored in DB
        memories = await store.get_session_memories(sid)
        assert len(memories) == 1
        assert memories[0]["messages_covered"] == 1


class TestUserMemoryIntegration:
    async def test_full_extraction_flow(self, store: MemoryStore) -> None:
        """Extract user facts and verify they persist across sessions."""
        await store.create_user(user_id="u1")

        mock_fn = AsyncMock(return_value=MemoryExtractionResult(
            facts=[
                ExtractedFact(key="name", value="Alice", confidence=0.95),
                ExtractedFact(key="role", value="Developer", confidence=0.88),
            ]
        ))
        extractor = UserMemoryExtractor(store=store, extract_fn=mock_fn)

        # Session 1: extract facts
        s1 = await store.create_session("u1", title="Session 1")
        await store.add_message(s1["session_id"], "u1", "user", "I'm Alice, a developer")
        await extractor.extract_after_interaction("u1", "I'm Alice, a developer", "Nice to meet you!")

        # Session 2: verify facts are available
        s2 = await store.create_session("u1", title="Session 2")
        memories = await store.get_user_memories("u1")
        assert len(memories) == 2
        keys = {m["key"] for m in memories}
        assert "name" in keys
        assert "role" in keys

    async def test_user_facts_not_leaked_across_users(
        self, store: MemoryStore
    ) -> None:
        """User 2's facts should not appear for User 1."""
        await store.create_user(user_id="u1")
        await store.create_user(user_id="u2")

        mock_fn = AsyncMock(return_value=MemoryExtractionResult(
            facts=[ExtractedFact(key="name", value="Bob", confidence=0.9)]
        ))
        extractor = UserMemoryExtractor(store=store, extract_fn=mock_fn)
        await extractor.extract_after_interaction("u2", "I'm Bob", "Hi!")

        u1_memories = await store.get_user_memories("u1")
        u2_memories = await store.get_user_memories("u2")
        assert len(u1_memories) == 0
        assert len(u2_memories) == 1

    async def test_delete_user_memory(self, store: MemoryStore) -> None:
        await store.create_user(user_id="u1")
        await store.add_or_update_user_memory("u1", "name", "Alice", 0.95)
        await store.add_or_update_user_memory("u1", "location", "Berlin", 0.85)

        await store.delete_user_memory("u1", "name")
        memories = await store.get_user_memories("u1")
        assert len(memories) == 1
        assert memories[0]["key"] == "location"
