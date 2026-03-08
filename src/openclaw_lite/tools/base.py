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

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())
