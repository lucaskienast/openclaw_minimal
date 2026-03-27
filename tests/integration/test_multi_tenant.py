"""Integration tests for multi-tenant data isolation."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openclaw_lite.memory.store import MemoryStore


@pytest.fixture()
async def store(tmp_db_path: Path):
    s = MemoryStore(tmp_db_path)
    await s.initialize()
    yield s
    await s.close()


class TestMultiTenantIsolation:
    async def test_two_users_two_sessions_concurrent(
        self, store: MemoryStore
    ) -> None:
        """Two users each with two sessions send messages concurrently.
        Verify zero data leakage."""
        u1 = (await store.create_user(user_id="user-1"))["user_id"]
        u2 = (await store.create_user(user_id="user-2"))["user_id"]

        s1a = (await store.create_session(u1, title="U1-A"))["session_id"]
        s1b = (await store.create_session(u1, title="U1-B"))["session_id"]
        s2a = (await store.create_session(u2, title="U2-A"))["session_id"]
        s2b = (await store.create_session(u2, title="U2-B"))["session_id"]

        # Send messages concurrently
        await asyncio.gather(
            store.add_message(s1a, u1, "user", "u1 session a msg"),
            store.add_message(s1b, u1, "user", "u1 session b msg"),
            store.add_message(s2a, u2, "user", "u2 session a msg"),
            store.add_message(s2b, u2, "user", "u2 session b msg"),
        )

        # Verify isolation: each session has exactly 1 message
        msgs_1a = await store.get_messages(s1a, u1)
        msgs_1b = await store.get_messages(s1b, u1)
        msgs_2a = await store.get_messages(s2a, u2)
        msgs_2b = await store.get_messages(s2b, u2)

        assert len(msgs_1a) == 1
        assert msgs_1a[0]["content"] == "u1 session a msg"
        assert len(msgs_1b) == 1
        assert msgs_1b[0]["content"] == "u1 session b msg"
        assert len(msgs_2a) == 1
        assert msgs_2a[0]["content"] == "u2 session a msg"
        assert len(msgs_2b) == 1
        assert msgs_2b[0]["content"] == "u2 session b msg"

    async def test_cross_user_message_access_blocked(
        self, store: MemoryStore
    ) -> None:
        """User 2 cannot read User 1's messages."""
        u1 = (await store.create_user(user_id="owner"))["user_id"]
        u2 = (await store.create_user(user_id="intruder"))["user_id"]

        session = await store.create_session(u1, title="Private")
        sid = session["session_id"]

        await store.add_message(sid, u1, "user", "secret message")

        # Intruder tries to read
        msgs = await store.get_messages(sid, u2)
        assert len(msgs) == 0

    async def test_cross_user_session_delete_blocked(
        self, store: MemoryStore
    ) -> None:
        """User 2 cannot delete User 1's session."""
        u1 = (await store.create_user(user_id="owner-del"))["user_id"]
        u2 = (await store.create_user(user_id="intruder-del"))["user_id"]

        session = await store.create_session(u1)
        with pytest.raises(PermissionError):
            await store.delete_session(session["session_id"], u2)

    async def test_session_listing_isolation(
        self, store: MemoryStore
    ) -> None:
        """Each user only sees their own sessions."""
        u1 = (await store.create_user(user_id="lister-1"))["user_id"]
        u2 = (await store.create_user(user_id="lister-2"))["user_id"]

        await store.create_session(u1, title="U1 only")
        await store.create_session(u1, title="U1 second")
        await store.create_session(u2, title="U2 only")

        sessions_1 = await store.list_sessions(u1)
        sessions_2 = await store.list_sessions(u2)

        assert len(sessions_1) == 2
        assert len(sessions_2) == 1
        assert all(s["title"].startswith("U1") for s in sessions_1)
        assert sessions_2[0]["title"] == "U2 only"

    async def test_cascade_delete_does_not_affect_other_users(
        self, store: MemoryStore
    ) -> None:
        """Deleting one user's session doesn't affect another user's data."""
        u1 = (await store.create_user(user_id="cascade-1"))["user_id"]
        u2 = (await store.create_user(user_id="cascade-2"))["user_id"]

        s1 = (await store.create_session(u1))["session_id"]
        s2 = (await store.create_session(u2))["session_id"]

        await store.add_message(s1, u1, "user", "u1 msg")
        await store.add_message(s2, u2, "user", "u2 msg")

        # Delete user 1's session
        await store.delete_session(s1, u1)

        # User 2's data untouched
        msgs = await store.get_messages(s2, u2)
        assert len(msgs) == 1
        assert msgs[0]["content"] == "u2 msg"
