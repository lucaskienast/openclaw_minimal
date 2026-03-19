from __future__ import annotations
import uuid
from typing import Any
from .base import Tool, ToolContext
from ..memory import LongTermMemory
from ..knowledge_store import KnowledgeStore


class RememberTool(Tool):
    name = "remember"
    description = "Store a fact, preference, or decision in long-term memory for future sessions."
    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "importance": {"type": "number", "description": "0.0–1.0, default 1.0"},
            "tags": {"type": "string", "description": "Comma-separated tags (optional)"},
        },
        "required": ["content"],
    }

    def __init__(self, ltm: LongTermMemory) -> None:
        self._ltm = ltm

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        mid = self._ltm.store(
            content=tool_input["content"],
            importance=float(tool_input.get("importance", 1.0)),
            tags=tool_input.get("tags", ""),
        )
        return f"Stored memory id={mid}: {tool_input['content']}"


class RecallTool(Tool):
    name = "recall"
    description = "Semantically search long-term memory for relevant facts."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "description": "Max results, default 5"},
        },
        "required": ["query"],
    }

    def __init__(self, ltm: LongTermMemory) -> None:
        self._ltm = ltm

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        results = self._ltm.search(query=tool_input["query"], limit=int(tool_input.get("limit", 5)))
        return "\n".join(results) if results else "No matching memories found."


class IngestDocumentTool(Tool):
    name = "ingest_document"
    description = "Add a text document or chunk to the knowledge base for future semantic retrieval."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "doc_id": {"type": "string", "description": "Unique chunk ID (auto-generated if omitted)"},
            "source": {"type": "string", "description": "Optional label, e.g. filename"},
        },
        "required": ["text"],
    }

    def __init__(self, ks: KnowledgeStore) -> None:
        self._ks = ks

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        doc_id = tool_input.get("doc_id") or str(uuid.uuid4())
        self._ks.ingest(
            document_id=doc_id,
            text=tool_input["text"],
            metadata={"source": tool_input.get("source", ""), "session_id": context.session_id},
        )
        return f"Ingested id={doc_id} ({len(tool_input['text'])} chars)"


class SearchKnowledgeTool(Tool):
    name = "search_knowledge"
    description = "Semantically search the knowledge base. Use only when automatic context retrieval was insufficient."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "n_results": {"type": "integer", "description": "Max results, default 5"},
        },
        "required": ["query"],
    }

    def __init__(self, ks: KnowledgeStore) -> None:
        self._ks = ks

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        results = self._ks.search(query=tool_input["query"], n_results=int(tool_input.get("n_results", 5)))
        if not results:
            return "No relevant documents found."
        return "\n\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(results))
