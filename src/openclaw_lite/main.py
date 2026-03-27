"""CLI entry point for openclaw-lite."""
from __future__ import annotations

import argparse
import asyncio
import json
import urllib.request

import uvicorn

from openclaw_lite.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw Lite")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="Run the HTTP gateway")

    chat_parser = sub.add_parser("chat", help="Send one message to the local gateway")
    chat_parser.add_argument("message")
    chat_parser.add_argument("--user-id", default="cli-user")
    chat_parser.add_argument("--session-id", default=None)
    chat_parser.add_argument("--timeout", type=int, default=300)

    sub.add_parser("inspect-tools", help="Print registered tools")

    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run(
            "openclaw_lite.main:_create_asgi_app",
            factory=True,
            host=settings.host,
            port=settings.port,
            reload=False,
        )
        return

    if args.command == "chat":
        _handle_chat(args)
        return

    if args.command == "inspect-tools":
        _handle_inspect_tools()
        return


def _create_asgi_app():
    """Factory function for uvicorn to create the async app."""
    from openclaw_lite.app_factory import build_app

    app = asyncio.run(build_app())
    return app


def _handle_chat(args) -> None:
    """Send a message to the running gateway."""
    base = f"http://{settings.host}:{settings.port}/api/v1"
    user_id = args.user_id
    session_id = args.session_id

    # If no session_id, create one
    if not session_id:
        # Ensure user exists (ignore conflict)
        req = urllib.request.Request(
            f"{base}/users",
            data=json.dumps({"user_id": user_id}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except urllib.error.HTTPError:
            pass  # User may already exist

        # Create session
        req = urllib.request.Request(
            f"{base}/users/{user_id}/sessions",
            data=json.dumps({"title": "CLI Session"}).encode(),
            headers={
                "Content-Type": "application/json",
                "X-User-Id": user_id,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            session_data = json.loads(resp.read().decode())
            session_id = session_data["session_id"]

    # Send message
    req = urllib.request.Request(
        f"{base}/users/{user_id}/sessions/{session_id}/messages",
        data=json.dumps({"content": args.message}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-User-Id": user_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=args.timeout) as resp:
        data = json.loads(resp.read().decode())
        print(json.dumps(data, indent=2))


def _handle_inspect_tools() -> None:
    """Print registered tool specs."""
    from openclaw_lite.app_factory import _build_tool_registry

    registry = _build_tool_registry()
    specs = [
        {"name": s.name, "description": s.description}
        for s in registry.specs()
    ]
    print(json.dumps(specs, indent=2))


if __name__ == "__main__":
    main()
