from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..schemas import ToolSpec


@dataclass(slots=True)
class ToolContext:
    session_id: str
    workspace: str


class Tool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any]

    @abstractmethod
    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        raise NotImplementedError

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._external_specs: list[ToolSpec] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_external_spec(self, spec: ToolSpec) -> None:
        """Register a tool spec from an external MCP server."""
        self._external_specs.append(spec)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def specs(self) -> list[ToolSpec]:
        """Return specs for all tools (local + external)."""
        local = [tool.spec() for tool in self._tools.values()]
        return local + self._external_specs

    def get_all_tool_specs(self) -> list[ToolSpec]:
        """Alias for specs() — returns merged local + external definitions."""
        return self.specs()

    def names(self) -> list[str]:
        local = list(self._tools.keys())
        external = [s.name for s in self._external_specs]
        return local + external
