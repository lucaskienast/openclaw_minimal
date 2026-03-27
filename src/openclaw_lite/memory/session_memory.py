"""Session memory manager — triggers summarization when token threshold exceeded."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.schemas import SummarizationResult

logger = logging.getLogger(__name__)

# Threshold ratio: summarize when session tokens exceed this fraction of context window
THRESHOLD_RATIO = 0.75

SummarizeFn = Callable[[list[dict[str, Any]]], Awaitable[SummarizationResult]]


class SessionMemoryManager:
    """Monitors session token usage and triggers summarization when needed.

    When the session's total token count exceeds 75% of the configured
    context window, the oldest messages are summarized via an LLM call
    and a SessionMemory record is created.
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        context_window: int,
        summarize_fn: SummarizeFn,
    ) -> None:
        self._store = store
        self._threshold = int(context_window * THRESHOLD_RATIO)
        self._summarize_fn = summarize_fn

    async def check_and_summarize(
        self, session_id: str, user_id: str
    ) -> SummarizationResult | None:
        """Check if summarization is needed and perform it if so.

        Returns the SummarizationResult if summarization was triggered,
        or None if the session is under threshold.
        """
        total_tokens = await self._store.get_session_token_count(
            session_id, user_id
        )

        if total_tokens <= self._threshold:
            return None

        logger.info(
            "Session %s exceeds threshold (%d > %d). Summarizing.",
            session_id, total_tokens, self._threshold,
        )

        messages = await self._store.get_messages(
            session_id, user_id, limit=200
        )
        if not messages:
            return None

        result = await self._summarize_fn(messages)

        await self._store.add_session_memory(
            session_id=session_id,
            summary=result.summary,
            messages_covered=len(messages),
        )

        logger.info(
            "Created session memory for %s: %d messages summarized.",
            session_id, len(messages),
        )

        return result

    async def get_context(
        self, session_id: str, user_id: str
    ) -> dict[str, Any]:
        """Get memory context for the session: summaries + recent messages."""
        summaries = await self._store.get_session_memories(session_id)
        summary_text = "\n".join(s["summary"] for s in summaries)
        return {"session_summary": summary_text}
