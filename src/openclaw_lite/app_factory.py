"""Application factory — wires up all dependencies."""
from __future__ import annotations

from fastapi import FastAPI

from openclaw_lite.config import settings
from openclaw_lite.gateway import create_app
from openclaw_lite.logging.setup import configure_logging
from openclaw_lite.memory.store import MemoryStore
from openclaw_lite.providers.demo import DemoProvider
from openclaw_lite.providers.openai_compatible import OpenAICompatibleProvider
from openclaw_lite.runtime import AgentRuntime
from openclaw_lite.tools.base import ToolRegistry
from openclaw_lite.tools.calculator import CalculatorTool
from openclaw_lite.tools.charting import ChartingTool
from openclaw_lite.tools.files import ListFilesTool, ReadFileTool, WriteFileTool
from openclaw_lite.tools.shell import ShellTool
from openclaw_lite.tools.system import SystemInfoTool, TimeTool
from openclaw_lite.tools.todo import TodoTool
from openclaw_lite.tools.web_fetch import WebFetchTool


def _build_provider(s=settings):
    if s.provider == "demo":
        return DemoProvider()
    if s.provider == "openai_compatible":
        return OpenAICompatibleProvider(s)
    raise ValueError(f"Unsupported provider: {s.provider}")


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListFilesTool())
    registry.register(TimeTool())
    registry.register(SystemInfoTool())
    registry.register(WebFetchTool())
    registry.register(ChartingTool())
    registry.register(TodoTool())
    registry.register(CalculatorTool())
    registry.register(ShellTool())
    return registry


async def build_app() -> FastAPI:
    """Create and wire the full application.

    Call this at startup (e.g. via lifespan or manual init).
    """
    configure_logging()
    settings.ensure_directories()

    store = MemoryStore(settings.db_path)
    await store.initialize()

    provider = _build_provider()
    tools = _build_tool_registry()

    runtime = AgentRuntime(
        settings=settings,
        store=store,
        provider=provider,
        tools=tools,
    )

    app = create_app(
        store=store,
        workspace=settings.workspace,
        runtime=runtime,
    )

    # Attach store for shutdown cleanup
    app.state.store = store

    return app
