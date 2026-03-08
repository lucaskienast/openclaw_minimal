from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from .tools.base import ToolRegistry

logger = logging.getLogger(__name__)


def load_plugins(plugin_dir: Path, registry: ToolRegistry) -> None:
    if not plugin_dir.exists():
        return
    for path in plugin_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "register"):
            module.register(registry)
            logger.info("Loaded plugin: %s", path.name)
