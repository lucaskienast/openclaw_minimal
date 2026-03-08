from __future__ import annotations

import tempfile
from pathlib import Path

from openclaw_lite.app_factory import build_runtime
from openclaw_lite.config import settings


def test_write_and_read_cycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings.db_path = Path(tmp) / "agent.db"
        settings.workspace = Path(tmp) / "workspace"
        runtime = build_runtime()
        out1 = runtime.handle_message("test", "write file notes.txt: hello world")
        assert "Wrote" in "\n".join(out1["scratchpad"])
        out2 = runtime.handle_message("test", "read file notes.txt")
        assert "hello world" in "\n".join(out2["scratchpad"])
