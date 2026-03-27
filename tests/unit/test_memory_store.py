"""Unit tests for async MemoryStore."""
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


class TestUserCRUD:
    async def test_create_user(self, store: MemoryStore) -> None:
        user = await store.create_user()
        assert user["user_id"]
        assert user["created_at"]

    async def test_create_user_with_id(self, store: MemoryStore) -> None:
        user = await store.create_user(user_id="custom-id-123")
        assert user["user_id"] == "custom-id-123"

    async def test_create_duplicate_user_raises(self, store: MemoryStore) -> None:
        await store.create_user(user_id="dup-user")
        with pytest.raises(ValueError, match="already exists"):
            await store.create_user(user_id="dup-user")

    async def test_get_user(self, store: MemoryStore) -> None:
        created = await store.create_user(user_id="lookup-user")
        fetched = await store.get_user("lookup-user")
        assert fetched is not None
        assert fetched["user_id"] == created["user_id"]

    async def test_get_user_not_found(self, store: MemoryStore) -> None:
        result = await store.get_user("nonexistent")
        assert result is None


class TestSessionCRUD:
    async def test_create_session(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        assert session["session_id"]
        assert session["user_id"] == user_id

    async def test_create_session_with_title(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id, title="My Chat")
        assert session["title"] == "My Chat"

    async def test_list_sessions(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        await store.create_session(user_id, title="Chat 1")
        await store.create_session(user_id, title="Chat 2")
        sessions = await store.list_sessions(user_id)
        assert len(sessions) == 2

    async def test_list_sessions_isolation(
        self, store: MemoryStore, user_id: str, user_id_2: str
    ) -> None:
        await store.create_user(user_id=user_id)
        await store.create_user(user_id=user_id_2)
        await store.create_session(user_id, title="User1 Chat")
        await store.create_session(user_id_2, title="User2 Chat")
        sessions_1 = await store.list_sessions(user_id)
        sessions_2 = await store.list_sessions(user_id_2)
        assert len(sessions_1) == 1
        assert len(sessions_2) == 1
        assert sessions_1[0]["title"] == "User1 Chat"
        assert sessions_2[0]["title"] == "User2 Chat"

    async def test_delete_session(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        await store.delete_session(session["session_id"], user_id)
        sessions = await store.list_sessions(user_id)
        assert len(sessions) == 0

    async def test_delete_session_wrong_user(
        self, store: MemoryStore, user_id: str, user_id_2: str
    ) -> None:
        await store.create_user(user_id=user_id)
        await store.create_user(user_id=user_id_2)
        session = await store.create_session(user_id)
        with pytest.raises(PermissionError):
            await store.delete_session(session["session_id"], user_id_2)

    async def test_delete_session_cascades_messages(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        await store.add_message(sid, user_id, "user", "hello")
        await store.add_message(sid, user_id, "assistant", "hi there")
        await store.delete_session(sid, user_id)
        messages = await store.get_messages(sid, user_id)
        assert len(messages) == 0


class TestMessageCRUD:
    async def test_add_and_get_messages(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        await store.add_message(sid, user_id, "user", "hello")
        await store.add_message(sid, user_id, "assistant", "hi")
        messages = await store.get_messages(sid, user_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    async def test_get_messages_with_limit(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        for i in range(10):
            await store.add_message(sid, user_id, "user", f"msg {i}")
        messages = await store.get_messages(sid, user_id, limit=3)
        assert len(messages) == 3

    async def test_messages_ordered_by_creation(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        await store.add_message(sid, user_id, "user", "first")
        await store.add_message(sid, user_id, "assistant", "second")
        await store.add_message(sid, user_id, "user", "third")
        messages = await store.get_messages(sid, user_id)
        assert [m["content"] for m in messages] == ["first", "second", "third"]

    async def test_message_has_token_count(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        await store.add_message(sid, user_id, "user", "hello world")
        messages = await store.get_messages(sid, user_id)
        assert messages[0]["token_count"] > 0

    async def test_message_isolation_across_sessions(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        s1 = await store.create_session(user_id)
        s2 = await store.create_session(user_id)
        await store.add_message(s1["session_id"], user_id, "user", "session 1 msg")
        await store.add_message(s2["session_id"], user_id, "user", "session 2 msg")
        msgs1 = await store.get_messages(s1["session_id"], user_id)
        msgs2 = await store.get_messages(s2["session_id"], user_id)
        assert len(msgs1) == 1
        assert len(msgs2) == 1
        assert msgs1[0]["content"] == "session 1 msg"
        assert msgs2[0]["content"] == "session 2 msg"

    async def test_message_isolation_across_users(
        self, store: MemoryStore, user_id: str, user_id_2: str
    ) -> None:
        await store.create_user(user_id=user_id)
        await store.create_user(user_id=user_id_2)
        s1 = await store.create_session(user_id)
        s2 = await store.create_session(user_id_2)
        await store.add_message(s1["session_id"], user_id, "user", "user1 msg")
        await store.add_message(s2["session_id"], user_id_2, "user", "user2 msg")
        # User 2 cannot read user 1's messages
        msgs = await store.get_messages(s1["session_id"], user_id_2)
        assert len(msgs) == 0


class TestSessionTokenCount:
    async def test_token_count_increments(
        self, store: MemoryStore, user_id: str
    ) -> None:
        await store.create_user(user_id=user_id)
        session = await store.create_session(user_id)
        sid = session["session_id"]
        count_before = await store.get_session_token_count(sid, user_id)
        assert count_before == 0
        await store.add_message(sid, user_id, "user", "hello world")
        count_after = await store.get_session_token_count(sid, user_id)
        assert count_after > 0
