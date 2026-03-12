from __future__ import annotations

from pathlib import Path

from .base import Tool, ToolContext


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a text file from the workspace."
    input_schema = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}

    def run(self, tool_input: dict, context: ToolContext) -> str:
        target = _safe_path(context.workspace, tool_input["path"])
        try:
            return target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"Error: file not found: {tool_input['path']}"


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write a text file inside the workspace."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }

    def run(self, tool_input: dict, context: ToolContext) -> str:
        target = _safe_path(context.workspace, tool_input["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(tool_input["content"], encoding="utf-8")
        workspace_root = Path(context.workspace).resolve()
        try:
            rel = target.resolve().relative_to(workspace_root)
            return f"Wrote {rel}"
        except ValueError:
            # fallback: don't 500 just because of formatting
            return f"Wrote {target.resolve()}"


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files under the workspace."
    input_schema = {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}

    def run(self, tool_input: dict, context: ToolContext) -> str:
        root = _safe_path(context.workspace, tool_input.get("path", "."))
        if root.is_file():
            return str(root.relative_to(Path(context.workspace).resolve()))
        items = sorted(str(p.relative_to(Path(context.workspace).resolve())) for p in root.rglob("*") if p.is_file())
        return "\n".join(items) if items else "Workspace is empty"


def _safe_path(workspace: str, relative_path: str) -> Path:
    base = Path(workspace).resolve()
    target = (base / relative_path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path escapes workspace")
    return target
