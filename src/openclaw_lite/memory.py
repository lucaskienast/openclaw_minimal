from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .schemas import ChatMessage


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    next_run_epoch INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                """
            )

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)",
                (session_id, message.role, message.content),
            )

    def get_history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in reversed(rows)]

    def search(self, session_id: str, query: str, limit: int = 5) -> list[ChatMessage]:
        like_query = f"%{' '.join(query.split())}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = ? AND content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, like_query, limit),
            ).fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]

    def add_task(self, session_id: str, name: str, prompt: str, interval_seconds: int, next_run_epoch: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks(session_id, name, prompt, interval_seconds, next_run_epoch)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, name, prompt, interval_seconds, next_run_epoch),
            )
            return int(cursor.lastrowid)

    def due_tasks(self, now_epoch: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM tasks WHERE enabled = 1 AND next_run_epoch <= ? ORDER BY id ASC",
                (now_epoch,),
            ).fetchall()

    def reschedule_task(self, task_id: int, next_run_epoch: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET next_run_epoch = ? WHERE id = ?",
                (next_run_epoch, task_id),
            )
