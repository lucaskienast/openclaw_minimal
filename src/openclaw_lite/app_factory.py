from __future__ import annotations

from pathlib import Path

from .config import settings
from .memory import MemoryStore
from .plugin_loader import load_plugins
from .providers.demo import DemoProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .runtime import AgentRuntime
from .tools.base import ToolRegistry
from .tools.files import ListFilesTool, ReadFileTool, WriteFileTool
from .tools.system import SystemInfoTool, TimeTool


def build_runtime() -> AgentRuntime:
    settings.ensure_directories()
    memory = MemoryStore(settings.db_path)
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListFilesTool())
    registry.register(TimeTool())
    registry.register(SystemInfoTool())
    default_plugins = Path(__file__).resolve().parents[2] / "plugins"
    load_plugins(settings.plugins_dir if settings.plugins_dir is not None else default_plugins, registry)

    print(f"Provider: {settings.provider}")

    if settings.provider == "demo":
        provider = DemoProvider()
    elif settings.provider == "openai_compatible":
        provider = OpenAICompatibleProvider(settings)
    else:
        raise ValueError(f"Unsupported provider: {settings.provider}")

    return AgentRuntime(settings=settings,
                        memory=memory,
                        provider=provider,
                        tools=registry)
