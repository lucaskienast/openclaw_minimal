"""Application configuration loaded from environment variables."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_mcp_servers(raw: str | None) -> list[dict[str, list[str]]]:
    """Parse MCP_SERVERS JSON config.

    Expected format: [{"command": "python", "args": ["-m", "my_server"]}]
    """
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


@dataclass(slots=True)
class Settings:
    # Provider
    provider: str = os.getenv("OPENCLAW_LITE_PROVIDER", "demo")
    api_key: str | None = os.getenv("OPENCLAW_LITE_API_KEY")
    model: str = os.getenv("OPENCLAW_LITE_MODEL", "gpt-4o-mini")
    base_url: str = os.getenv("OPENCLAW_LITE_BASE_URL", "https://api.openai.com/v1")

    # Storage
    db_path: Path = Path(os.getenv("OPENCLAW_LITE_DB_PATH", "./data/agent.db"))
    workspace: Path = Path(os.getenv("OPENCLAW_LITE_WORKSPACE", "./data/workspace"))

    # Server
    host: str = os.getenv("OPENCLAW_LITE_HOST", "0.0.0.0")
    port: int = int(os.getenv("OPENCLAW_LITE_PORT", "8000"))

    # Agent loop
    max_steps: int = int(os.getenv("OPENCLAW_LITE_MAX_STEPS", "10"))
    context_window: int = int(os.getenv("OPENCLAW_LITE_CONTEXT_WINDOW", "128000"))
    response_timeout: int = int(os.getenv("OPENCLAW_LITE_RESPONSE_TIMEOUT", "120"))
    subagent_timeout: int = int(os.getenv("OPENCLAW_LITE_SUBAGENT_TIMEOUT", "60"))

    # MCP
    mcp_servers: list[dict[str, list[str]]] = field(
        default_factory=lambda: _parse_mcp_servers(
            os.getenv("OPENCLAW_LITE_MCP_SERVERS")
        )
    )

    # Memory
    memory_extraction: bool = (
        os.getenv("OPENCLAW_LITE_MEMORY_EXTRACTION", "true").lower() == "true"
    )
    extraction_model: str | None = os.getenv("OPENCLAW_LITE_EXTRACTION_MODEL")

    # Plugins (legacy)
    plugins_dir: Path | None = (
        Path(v) if (v := os.getenv("OPENCLAW_LITE_PLUGINS_DIR")) else None
    )

    def ensure_directories(self) -> None:
        """Create required data directories if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)


settings = Settings()
