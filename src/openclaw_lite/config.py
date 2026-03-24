from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

@dataclass(slots=True)
class Settings:
    provider: str = os.getenv("OPENCLAW_LITE_PROVIDER", "demo")
    db_path: Path = Path(os.getenv("OPENCLAW_LITE_DB_PATH", "./data/agent.db"))
    workspace: Path = Path(os.getenv("OPENCLAW_LITE_WORKSPACE", "./data/workspace"))
    host: str = os.getenv("OPENCLAW_LITE_HOST", "127.0.0.1")
    port: int = int(os.getenv("OPENCLAW_LITE_PORT", "8765"))
    max_steps: int = int(os.getenv("OPENCLAW_LITE_MAX_STEPS", "20"))
    api_key: str | None = os.getenv("OPENCLAW_LITE_API_KEY")
    model: str = os.getenv("OPENCLAW_LITE_MODEL", "gpt-4o-mini")
    base_url: str = os.getenv("OPENCLAW_LITE_BASE_URL", "https://api.openai.com/v1")
    plugins_dir: Path | None = (Path(v) if (v := os.getenv("OPENCLAW_LITE_PLUGINS_DIR")) else None)
    knowledge_dir: Path = Path(os.getenv("OPENCLAW_LITE_KNOWLEDGE_DIR", "./data/knowledge"))
    memory_extraction: bool = os.getenv("OPENCLAW_LITE_MEMORY_EXTRACTION", "true").lower() == "true"
    extraction_model: str | None = os.getenv("OPENCLAW_LITE_EXTRACTION_MODEL")

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
