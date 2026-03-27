"""Unit tests for user memory extraction and upsert logic."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.memory.user_memory import UserMemoryExtractor
from openclaw_lite.schemas import ExtractedFact, MemoryExtractionResult


@pytest.fixture()
async def store(tmp_db_path: Path):
    s = MemoryStore(tmp_db_path)
    await s.initialize()
    await s.create_user(user_id="u1")
    yield s
    await s.close()


@pytest.fixture()
def mock_extractor_fn() -> AsyncMock:
    """Mock LLM extraction call that returns user facts."""
    fn = AsyncMock()
    fn.return_value = MemoryExtractionResult(
        facts=[
            ExtractedFact(key="name", value="Alice", confidence=0.95),
            ExtractedFact(key="location", value="Berlin", confidence=0.85),
        ]
    )
    return fn


class TestUserMemoryExtraction:
    async def test_extraction_stores_facts(
        self, store: MemoryStore, mock_extractor_fn: AsyncMock
    ) -> None:
        extractor = UserMemoryExtractor(
            store=store, extract_fn=mock_extractor_fn
        )
        await extractor.extract_after_interaction("u1", "I'm Alice from Berlin", "Nice to meet you!")
        mock_extractor_fn.assert_called_once()

        memories = await store.get_user_memories("u1")
        assert len(memories) == 2
        keys = {m["key"] for m in memories}
        assert "name" in keys
        assert "location" in keys

    async def test_upsert_on_conflict(
        self, store: MemoryStore, mock_extractor_fn: AsyncMock
    ) -> None:
        extractor = UserMemoryExtractor(
            store=store, extract_fn=mock_extractor_fn
        )
        # First extraction
        await extractor.extract_after_interaction("u1", "I'm Alice", "Hi!")

        # Update: name changes
        mock_extractor_fn.return_value = MemoryExtractionResult(
            facts=[ExtractedFact(key="name", value="Bob", confidence=0.90)]
        )
        await extractor.extract_after_interaction("u1", "Actually I'm Bob", "Noted!")

        memories = await store.get_user_memories("u1")
        name_mem = [m for m in memories if m["key"] == "name"]
        assert len(name_mem) == 1
        assert name_mem[0]["value"] == "Bob"

    async def test_confidence_stored(
        self, store: MemoryStore, mock_extractor_fn: AsyncMock
    ) -> None:
        extractor = UserMemoryExtractor(
            store=store, extract_fn=mock_extractor_fn
        )
        await extractor.extract_after_interaction("u1", "test", "test")
        memories = await store.get_user_memories("u1")
        name_mem = [m for m in memories if m["key"] == "name"][0]
        assert name_mem["confidence"] == 0.95

    async def test_empty_extraction(
        self, store: MemoryStore
    ) -> None:
        """When LLM returns no facts, nothing is stored."""
        empty_fn = AsyncMock(return_value=MemoryExtractionResult(facts=[]))
        extractor = UserMemoryExtractor(store=store, extract_fn=empty_fn)
        await extractor.extract_after_interaction("u1", "hello", "hi")
        memories = await store.get_user_memories("u1")
        assert len(memories) == 0

    async def test_only_personal_facts(
        self, store: MemoryStore
    ) -> None:
        """Extraction function should only return key personal facts."""
        fn = AsyncMock(return_value=MemoryExtractionResult(
            facts=[
                ExtractedFact(key="job_title", value="Engineer", confidence=0.88),
            ]
        ))
        extractor = UserMemoryExtractor(store=store, extract_fn=fn)
        await extractor.extract_after_interaction("u1", "I'm an engineer", "Cool!")
        memories = await store.get_user_memories("u1")
        assert len(memories) == 1
        assert memories[0]["key"] == "job_title"
