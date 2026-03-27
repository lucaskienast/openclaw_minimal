"""User memory extractor — extracts key personal facts after each interaction."""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.schemas import MemoryExtractionResult

logger = logging.getLogger(__name__)

ExtractFn = Callable[[str, str], Awaitable[MemoryExtractionResult]]


class UserMemoryExtractor:
    """Extracts key personal facts from conversations and upserts them.

    After each interaction, makes a dedicated LLM call to extract only
    key personal facts (name, role, location, preferences). General
    conversational content is NOT stored as user memory.
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        extract_fn: ExtractFn,
    ) -> None:
        self._store = store
        self._extract_fn = extract_fn

    async def extract_after_interaction(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Extract user facts from the latest interaction and upsert them."""
        try:
            result = await self._extract_fn(user_message, assistant_response)
        except Exception:
            logger.exception("User memory extraction failed for user %s", user_id)
            return

        if not result.facts:
            return

        for fact in result.facts:
            await self._store.add_or_update_user_memory(
                user_id=user_id,
                key=fact.key,
                value=fact.value,
                confidence=fact.confidence,
            )
            logger.info(
                "Upserted user memory: user=%s key=%s value=%s conf=%.2f",
                user_id, fact.key, fact.value, fact.confidence,
            )
