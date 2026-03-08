from __future__ import annotations

import logging
import time

from .app_factory import build_runtime
from .config import settings
from .memory import MemoryStore

logger = logging.getLogger(__name__)


def run_scheduler(poll_seconds: int = 2) -> None:
    runtime = build_runtime()
    memory = MemoryStore(settings.db_path)
    logger.info("Scheduler started")
    while True:
        now = int(time.time())
        for task in memory.due_tasks(now):
            logger.info("Running task id=%s name=%s", task["id"], task["name"])
            runtime.handle_message(task["session_id"], f"[Scheduled task: {task['name']}] {task['prompt']}")
            memory.reschedule_task(task["id"], now + int(task["interval_seconds"]))
        time.sleep(poll_seconds)
