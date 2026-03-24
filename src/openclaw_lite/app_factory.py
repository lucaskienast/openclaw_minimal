from __future__ import annotations

from pathlib import Path

from .config import settings
from .extraction import MemoryExtractionAgent
from .knowledge_store import KnowledgeStore
from .memory import LongTermMemory, MemoryStore
from .plugin_loader import load_plugins
from .providers.demo import DemoProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .runtime import AgentRuntime
from .tools.base import ToolRegistry
from .tools.files import ListFilesTool, ReadFileTool, WriteFileTool
from .tools.memory_tools import IngestDocumentTool, RecallTool, RememberTool, SearchKnowledgeTool
from .tools.system import SystemInfoTool, TimeTool


def build_runtime() -> AgentRuntime:
    settings.ensure_directories()
    memory = MemoryStore(settings.db_path)
    long_term_memory = LongTermMemory(settings.db_path, settings.knowledge_dir)
    knowledge_store = KnowledgeStore(settings.knowledge_dir)

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListFilesTool())
    registry.register(TimeTool())
    registry.register(SystemInfoTool())
    registry.register(RememberTool(long_term_memory))
    registry.register(RecallTool(long_term_memory))
    registry.register(IngestDocumentTool(knowledge_store))
    registry.register(SearchKnowledgeTool(knowledge_store))

    default_plugins = Path(__file__).resolve().parents[2] / "plugins"
    load_plugins(
        settings.plugins_dir if settings.plugins_dir is not None else default_plugins,
        registry
    )

    print(f"Provider: {settings.provider}")

    if settings.provider == "demo":
        provider = DemoProvider()
    elif settings.provider == "openai_compatible":
        provider = OpenAICompatibleProvider(settings)
    else:
        raise ValueError(f"Unsupported provider: {settings.provider}")

    # Eagerly initialize ChromaDB to avoid background-thread race condition
    # TODO: fix: Access to a protected member _ensure_initialized of a class
    long_term_memory._ensure_initialized()

    extraction_agent = MemoryExtractionAgent(settings, memory, long_term_memory)

    return AgentRuntime(
        settings=settings,
        memory=memory,
        long_term_memory=long_term_memory,
        knowledge_store=knowledge_store,
        provider=provider,
        tools=registry,
        extraction_agent=extraction_agent,
    )
