"""Todo list tool — manages markdown checkbox files."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from openclaw_lite.tools.base import Tool, ToolContext


class TodoTool(Tool):
    name = "todo"
    description = "Manage markdown todo lists: create, read, update items, add items."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "read", "update", "add"],
            },
            "filename": {"type": "string"},
            "items": {"type": "array", "items": {"type": "string"}},
            "item_index": {"type": "integer"},
            "done": {"type": "boolean"},
            "new_item": {"type": "string"},
        },
        "required": ["action", "filename"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        action = tool_input.get("action", "")
        filename = tool_input.get("filename", "todos.md")
        workspace = Path(context.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        filepath = workspace / filename

        if action == "create":
            return self._create(filepath, tool_input.get("items", []))
        elif action == "read":
            return self._read(filepath)
        elif action == "update":
            return self._update(
                filepath,
                tool_input.get("item_index", 0),
                tool_input.get("done", True),
            )
        elif action == "add":
            return self._add(filepath, tool_input.get("new_item", ""))
        else:
            return f"Error: unknown action '{action}'"

    def _create(self, filepath: Path, items: list[str]) -> str:
        lines = [f"- [ ] {item}" for item in items]
        filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"Created {filepath.name} with {len(items)} items"

    def _read(self, filepath: Path) -> str:
        if not filepath.exists():
            return f"Error: file not found: {filepath.name}"
        return filepath.read_text(encoding="utf-8")

    def _update(self, filepath: Path, index: int, done: bool) -> str:
        if not filepath.exists():
            return f"Error: file not found: {filepath.name}"
        lines = filepath.read_text(encoding="utf-8").splitlines()
        todo_indices = [
            i for i, line in enumerate(lines)
            if re.match(r"^- \[[ xX]\] ", line)
        ]
        if index < 0 or index >= len(todo_indices):
            return f"Error: item index {index} out of range (0-{len(todo_indices) - 1})"
        line_idx = todo_indices[index]
        if done:
            lines[line_idx] = re.sub(r"^- \[ \] ", "- [x] ", lines[line_idx])
        else:
            lines[line_idx] = re.sub(r"^- \[[xX]\] ", "- [ ] ", lines[line_idx])
        filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"Updated item {index} in {filepath.name}"

    def _add(self, filepath: Path, new_item: str) -> str:
        if not new_item:
            return "Error: new_item is required for 'add' action"
        if not filepath.exists():
            return f"Error: file not found: {filepath.name}"
        content = filepath.read_text(encoding="utf-8").rstrip()
        content += f"\n- [ ] {new_item}\n"
        filepath.write_text(content, encoding="utf-8")
        return f"Added item to {filepath.name}"
