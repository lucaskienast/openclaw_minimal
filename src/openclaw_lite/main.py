from __future__ import annotations

import argparse
import json
import time
import urllib.request
from dataclasses import is_dataclass, asdict

import uvicorn

from .app_factory import build_runtime
from .config import settings
from .logging_utils import configure_logging
from .memory import MemoryStore
from .scheduler import run_scheduler


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="OpenClaw Lite")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="Run the HTTP gateway")

    chat_parser = sub.add_parser("chat", help="Send one message to the local gateway")
    chat_parser.add_argument("message")
    chat_parser.add_argument("--session", default="main")

    sched_parser = sub.add_parser("schedule", help="Create a recurring scheduled prompt")
    sched_parser.add_argument("name")
    sched_parser.add_argument("prompt")
    sched_parser.add_argument("interval_seconds", type=int)
    sched_parser.add_argument("--session", default="main")

    sub.add_parser("run-scheduler", help="Run the scheduler loop")
    sub.add_parser("inspect-tools", help="Print registered tools")

    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run("openclaw_lite.gateway:app", host=settings.host, port=settings.port, reload=False)
        return

    if args.command == "chat":
        req = urllib.request.Request(
            f"http://{settings.host}:{settings.port}/message",
            data=json.dumps({"session_id": args.session, "message": args.message}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(resp.read().decode("utf-8"))
        return

    # TODO: use in an example
    if args.command == "schedule":
        settings.ensure_directories()
        memory = MemoryStore(settings.db_path)
        task_id = memory.add_task(
            session_id=args.session,
            name=args.name,
            prompt=args.prompt,
            interval_seconds=args.interval_seconds,
            next_run_epoch=int(time.time()) + args.interval_seconds,
        )
        print(f"Created task {task_id}")
        return

    if args.command == "run-scheduler":
        run_scheduler()
        return

    if args.command == "inspect-tools":
        runtime = build_runtime()

        def to_jsonable(x):
            if is_dataclass(x):
                return asdict(x)
            # fallback for non-dataclass objects
            return {k: getattr(x, k) for k in dir(x)
                    if not k.startswith("_") and isinstance(getattr(x, k),
                                                            (str, int, float, bool, list, dict, type(None)))}

        print(json.dumps([to_jsonable(tool) for tool in runtime.tools.specs()], indent=2))
        return


if __name__ == "__main__":
    main()
