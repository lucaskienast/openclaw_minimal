"""Unit tests for todo list tool."""
from __future__ import annotations

from pathlib import Path

import pytest

from openclaw_lite.tools.todo import TodoTool
from openclaw_lite.tools.base import ToolContext


@pytest.fixture()
def tool() -> TodoTool:
    return TodoTool()


@pytest.fixture()
def ctx(tmp_workspace: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace=str(tmp_workspace))


class TestTodoTool:
    def test_create_todo_file(self, tool: TodoTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "action": "create",
                "filename": "tasks.md",
                "items": ["Buy milk", "Write tests", "Deploy app"],
            },
            ctx,
        )
        assert "created" in result.lower()
        content = (Path(ctx.workspace) / "tasks.md").read_text()
        assert "- [ ] Buy milk" in content
        assert "- [ ] Write tests" in content

    def test_read_todo_file(self, tool: TodoTool, ctx: ToolContext) -> None:
        # Create first
        tool.run(
            {"action": "create", "filename": "read_test.md", "items": ["Item 1"]},
            ctx,
        )
        result = tool.run({"action": "read", "filename": "read_test.md"}, ctx)
        assert "Item 1" in result

    def test_mark_item_done(self, tool: TodoTool, ctx: ToolContext) -> None:
        tool.run(
            {"action": "create", "filename": "toggle.md", "items": ["Task A", "Task B"]},
            ctx,
        )
        result = tool.run(
            {"action": "update", "filename": "toggle.md", "item_index": 0, "done": True},
            ctx,
        )
        assert "updated" in result.lower()
        content = (Path(ctx.workspace) / "toggle.md").read_text()
        assert "- [x] Task A" in content
        assert "- [ ] Task B" in content

    def test_add_item_to_existing(self, tool: TodoTool, ctx: ToolContext) -> None:
        tool.run(
            {"action": "create", "filename": "add_test.md", "items": ["First"]},
            ctx,
        )
        result = tool.run(
            {"action": "add", "filename": "add_test.md", "new_item": "Second"},
            ctx,
        )
        assert "added" in result.lower()
        content = (Path(ctx.workspace) / "add_test.md").read_text()
        assert "- [ ] First" in content
        assert "- [ ] Second" in content

    def test_read_nonexistent_file(self, tool: TodoTool, ctx: ToolContext) -> None:
        result = tool.run({"action": "read", "filename": "nonexistent.md"}, ctx)
        assert "error" in result.lower() or "not found" in result.lower()
