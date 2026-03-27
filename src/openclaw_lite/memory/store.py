"""Async multi-tenant database store backed by aiosqlite."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from openclaw_lite.memory.token_counter import TokenCounter

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id),
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS messages (
    message_id  TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'tool')),
    content     TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS session_memories (
    memory_id        TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    summary          TEXT NOT NULL,
    messages_covered INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_memories ON session_memories(session_id);

CREATE TABLE IF NOT EXISTS user_memories (
    memory_id  TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id),
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memories_unique
    ON user_memories(user_id, key);
"""


class MemoryStore:
    """Async multi-tenant storage for users, sessions, messages, and memories."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._token_counter = TokenCounter()

    async def initialize(self) -> None:
        """Open the database connection and create tables."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("MemoryStore not initialized. Call initialize() first.")
        return self._db

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def create_user(self, user_id: str | None = None) -> dict[str, Any]:
        uid = user_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.db.execute(
                "INSERT INTO users (user_id, created_at) VALUES (?, ?)",
                (uid, now),
            )
            await self.db.commit()
        except aiosqlite.IntegrityError:
            raise ValueError(f"User '{uid}' already exists")
        return {"user_id": uid, "created_at": now}

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        cursor = await self.db.execute(
            "SELECT user_id, created_at FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {"user_id": row["user_id"], "created_at": row["created_at"]}

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self, user_id: str, title: str = ""
    ) -> dict[str, Any]:
        sid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "INSERT INTO sessions (session_id, user_id, title, created_at) "
            "VALUES (?, ?, ?, ?)",
            (sid, user_id, title, now),
        )
        await self.db.commit()
        return {
            "session_id": sid,
            "user_id": user_id,
            "title": title,
            "created_at": now,
        }

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            "SELECT session_id, title, created_at FROM sessions "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "session_id": r["session_id"],
                "title": r["title"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def delete_session(self, session_id: str, user_id: str) -> None:
        cursor = await self.db.execute(
            "SELECT user_id FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise KeyError(f"Session '{session_id}' not found")
        if row["user_id"] != user_id:
            raise PermissionError("User does not own this session")
        await self.db.execute(
            "DELETE FROM messages WHERE session_id = ?", (session_id,)
        )
        await self.db.execute(
            "DELETE FROM session_memories WHERE session_id = ?", (session_id,)
        )
        await self.db.execute(
            "DELETE FROM sessions WHERE session_id = ?", (session_id,)
        )
        await self.db.commit()

    async def get_session_owner(self, session_id: str) -> str | None:
        cursor = await self.db.execute(
            "SELECT user_id FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row["user_id"] if row else None

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        # Verify ownership
        owner = await self.get_session_owner(session_id)
        if owner is not None and owner != user_id:
            raise PermissionError("User does not own this session")
        mid = str(uuid.uuid4())
        token_count = self._token_counter.count_tokens(content)
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "INSERT INTO messages "
            "(message_id, session_id, role, content, token_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mid, session_id, role, content, token_count, now),
        )
        await self.db.commit()
        return {
            "message_id": mid,
            "session_id": session_id,
            "role": role,
            "content": content,
            "token_count": token_count,
            "created_at": now,
        }

    async def get_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        # Verify ownership
        owner = await self.get_session_owner(session_id)
        if owner is not None and owner != user_id:
            return []
        cursor = await self.db.execute(
            "SELECT message_id, role, content, token_count, created_at "
            "FROM messages WHERE session_id = ? "
            "ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (session_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "message_id": r["message_id"],
                "role": r["role"],
                "content": r["content"],
                "token_count": r["token_count"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def get_message_count(
        self, session_id: str, user_id: str
    ) -> int:
        owner = await self.get_session_owner(session_id)
        if owner is not None and owner != user_id:
            return 0
        cursor = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def get_session_token_count(
        self, session_id: str, user_id: str
    ) -> int:
        owner = await self.get_session_owner(session_id)
        if owner is not None and owner != user_id:
            return 0
        cursor = await self.db.execute(
            "SELECT COALESCE(SUM(token_count), 0) as total "
            "FROM messages WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row["total"] if row else 0

    # ------------------------------------------------------------------
    # Session Memories (summaries)
    # ------------------------------------------------------------------

    async def add_session_memory(
        self,
        session_id: str,
        summary: str,
        messages_covered: int,
    ) -> dict[str, Any]:
        mid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "INSERT INTO session_memories "
            "(memory_id, session_id, summary, messages_covered, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (mid, session_id, summary, messages_covered, now),
        )
        await self.db.commit()
        return {
            "memory_id": mid,
            "session_id": session_id,
            "summary": summary,
            "messages_covered": messages_covered,
            "created_at": now,
        }

    async def get_session_memories(
        self, session_id: str
    ) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            "SELECT memory_id, summary, messages_covered, created_at "
            "FROM session_memories WHERE session_id = ? "
            "ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "memory_id": r["memory_id"],
                "summary": r["summary"],
                "messages_covered": r["messages_covered"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # User Memories (cross-session facts)
    # ------------------------------------------------------------------

    async def add_or_update_user_memory(
        self,
        user_id: str,
        key: str,
        value: str,
        confidence: float,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        mid = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO user_memories "
            "(memory_id, user_id, key, value, confidence, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET "
            "value = excluded.value, confidence = excluded.confidence, "
            "updated_at = excluded.updated_at",
            (mid, user_id, key, value, confidence, now),
        )
        await self.db.commit()
        return {
            "user_id": user_id,
            "key": key,
            "value": value,
            "confidence": confidence,
            "updated_at": now,
        }

    async def get_user_memories(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            "SELECT key, value, confidence, updated_at "
            "FROM user_memories WHERE user_id = ? "
            "ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "key": r["key"],
                "value": r["value"],
                "confidence": r["confidence"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    async def delete_user_memory(
        self, user_id: str, key: str
    ) -> None:
        await self.db.execute(
            "DELETE FROM user_memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        await self.db.commit()
