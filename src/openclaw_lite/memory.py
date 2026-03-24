from __future__ import annotations

import sqlite3
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from .schemas import ChatMessage


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
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

                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 1.0,
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS long_term_memories_fts
                    USING fts5(content, content=long_term_memories, content_rowid=id);

                CREATE TRIGGER IF NOT EXISTS ltm_ai AFTER INSERT ON long_term_memories BEGIN
                    INSERT INTO long_term_memories_fts(rowid, content) VALUES (new.id, new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS ltm_au AFTER UPDATE ON long_term_memories BEGIN
                    INSERT INTO long_term_memories_fts(long_term_memories_fts, rowid, content)
                        VALUES ('delete', old.id, old.content);
                    INSERT INTO long_term_memories_fts(rowid, content) VALUES (new.id, new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS ltm_ad AFTER DELETE ON long_term_memories BEGIN
                    INSERT INTO long_term_memories_fts(long_term_memories_fts, rowid, content)
                        VALUES ('delete', old.id, old.content);
                END;

                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary    TEXT NOT NULL DEFAULT '',
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def get_session_summary(self, session_id: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary FROM session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row["summary"] if row else ""

    def upsert_session_summary(self, session_id: str, summary: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_summaries(session_id, summary, turn_count)
                VALUES (?, ?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                    summary = excluded.summary,
                    turn_count = turn_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session_id, summary),
            )


class LongTermMemory:
    # TODO: auto compaction of short term memory into summarised long term memory of conversation main points and events
    SIMILARITY_DEDUP_THRESHOLD = 0.08  # cosine distance; lower = more similar

    def __init__(self, db_path: Path, knowledge_dir: Path) -> None:
        self.db_path = db_path
        self._knowledge_dir = knowledge_dir
        self._chroma_client = None
        self._collection = None

    def _ensure_initialized(self) -> None:
        if self._collection is not None:
            return
        self._chroma_client = chromadb.PersistentClient(path=str(self._knowledge_dir))
        ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._chroma_client.get_or_create_collection(
            name="long_term_memory",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def store(self, content: str, importance: float = 1.0, tags: str = "") -> int:
        self._ensure_initialized()
        # 1. Exact-match dedup in SQLite
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM long_term_memories WHERE content = ?", (content,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE long_term_memories SET last_accessed = CURRENT_TIMESTAMP, "
                    "importance = MAX(importance, ?) WHERE id = ?",
                    (importance, existing["id"]),
                )
                return existing["id"]

        # 2. Near-duplicate check via ChromaDB similarity
        if self._collection.count() > 0:
            result = self._collection.query(query_texts=[content], n_results=1)
            distances = result.get("distances", [[]])[0]
            if distances and distances[0] < self.SIMILARITY_DEDUP_THRESHOLD:
                existing_id = int(result["ids"][0][0].split("-")[1])
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE long_term_memories SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                        (existing_id,),
                    )
                return existing_id

        # 3. Insert new
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO long_term_memories(content, importance, tags) VALUES (?, ?, ?)",
                (content, importance, tags),
            )
            memory_id = int(cursor.lastrowid)

        self._collection.upsert(
            ids=[f"ltm-{memory_id}"],
            documents=[content],
            metadatas=[{"importance": importance, "tags": tags, "memory_id": memory_id}],
        )
        return memory_id

    def search(self, query: str, limit: int = 5, max_chars_per_item: int = 500) -> list[str]:
        self._ensure_initialized()
        if self._collection.count() == 0:
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(limit, self._collection.count()),
        )
        ids_raw = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        if not ids_raw:
            return []

        memory_ids = [int(r.split("-")[1]) for r in ids_raw]
        placeholders = ",".join("?" * len(memory_ids))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT id, content, importance, created_at FROM long_term_memories WHERE id IN ({placeholders})",
                memory_ids,
            ).fetchall()
            conn.execute(
                f"UPDATE long_term_memories SET last_accessed = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
                memory_ids,
            )
        row_map = {row["id"]: row for row in rows}

        formatted = []
        for mid, doc in zip(memory_ids, docs):
            row = row_map.get(mid)
            if row:
                date = str(row["created_at"])[:10]
                imp = f"{row['importance']:.1f}"
                # TODO could we just store embedding representation in chroma and fetch content from sql db?
                text = doc[:max_chars_per_item]
                formatted.append(f"[{date}, importance={imp}] {text}")
        return formatted

    # TODO: not use anywhere so far? where would it?
    def list_all(self, limit: int = 50) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT content, importance FROM long_term_memories "
                "ORDER BY importance DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [f"[importance={r['importance']:.1f}] {r['content']}" for r in rows]
