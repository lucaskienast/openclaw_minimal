from __future__ import annotations
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

class KnowledgeStore:
    def __init__(self, knowledge_dir: Path) -> None:
        self._knowledge_dir = knowledge_dir
        self._client = None
        self._collection = None

    def _ensure_initialized(self) -> None:
        if self._collection is not None:
            return
        self._client = chromadb.PersistentClient(path=str(self._knowledge_dir))
        ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name="knowledge",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._ensure_initialized()
        self._collection.upsert(
            ids=[document_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def search(self, query: str, n_results: int = 3, max_chars_per_chunk: int = 1000) -> list[str]:
        self._ensure_initialized()
        if self._collection.count() == 0:
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )
        docs = results.get("documents", [[]])[0]
        return [d[:max_chars_per_chunk] for d in docs]

    def count(self) -> int:
        self._ensure_initialized()
        return self._collection.count()
