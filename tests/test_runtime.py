from __future__ import annotations

import tempfile
import time
from pathlib import Path

from openclaw_lite.app_factory import build_runtime
from openclaw_lite.config import settings
from openclaw_lite.extraction import HeuristicExtractor


def test_write_and_read_cycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "agent.db"
        settings.workspace = Path(tmp) / "workspace"
        settings.knowledge_dir = Path(tmp) / "knowledge"
        settings.provider = "demo"
        runtime = build_runtime()
        out1 = runtime.handle_message("test", "write file notes.txt: hello world")
        assert "Wrote" in "\n".join(out1["scratchpad"])
        out2 = runtime.handle_message("test", "read file notes.txt")
        assert "hello world" in "\n".join(out2["scratchpad"])


def test_session_summary_stored_after_response() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "agent.db"
        settings.workspace = Path(tmp) / "workspace"
        settings.knowledge_dir = Path(tmp) / "knowledge"
        settings.provider = "demo"
        settings.memory_extraction = True
        runtime = build_runtime()
        runtime.handle_message("sess1", "hello agent")
        time.sleep(0.15)  # allow daemon thread to complete
        summary = runtime.memory.get_session_summary("sess1")
        assert summary != ""


def test_memory_extraction_disabled() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "agent.db"
        settings.workspace = Path(tmp) / "workspace"
        settings.knowledge_dir = Path(tmp) / "knowledge"
        settings.provider = "demo"
        settings.memory_extraction = False
        runtime = build_runtime()
        runtime.handle_message("sess2", "hello agent")
        time.sleep(0.15)
        summary = runtime.memory.get_session_summary("sess2")
        assert summary == ""


def test_heuristic_extractor_directly() -> None:
    extractor = HeuristicExtractor()
    result = extractor.extract("I prefer dark mode always", "OK, noted.", "")
    preference_memories = [m for m in result.memories if "preference" in m["tags"]]
    assert len(preference_memories) >= 1
    assert result.updated_summary != ""


def test_session_summary_in_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "agent.db"
        settings.workspace = Path(tmp) / "workspace"
        settings.knowledge_dir = Path(tmp) / "knowledge"
        settings.provider = "demo"
        settings.memory_extraction = True
        runtime = build_runtime()
        runtime.handle_message("sess3", "hello agent")
        time.sleep(0.15)
        # Second message: session_summary should be available in context
        summary = runtime.memory.get_session_summary("sess3")
        assert summary != ""
