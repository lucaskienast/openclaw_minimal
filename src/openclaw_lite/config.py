from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    provider: str = os.getenv("OPENCLAW_LITE_PROVIDER", "demo")
    db_path: Path = Path(os.getenv("OPENCLAW_LITE_DB_PATH", "./data/agent.db"))
    workspace: Path = Path(os.getenv("OPENCLAW_LITE_WORKSPACE", "./data/workspace"))
    host: str = os.getenv("OPENCLAW_LITE_HOST", "127.0.0.1")
    port: int = int(os.getenv("OPENCLAW_LITE_PORT", "8765"))
    max_steps: int = int(os.getenv("OPENCLAW_LITE_MAX_STEPS", "5"))
    api_key: str | None = os.getenv("OPENCLAW_LITE_API_KEY")
    model: str = os.getenv("OPENCLAW_LITE_MODEL", "gpt-4o-mini")
    base_url: str = os.getenv("OPENCLAW_LITE_BASE_URL", "https://api.openai.com/v1")

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)


settings = Settings()
