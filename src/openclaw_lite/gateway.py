"""HTTP API gateway — v1 REST endpoints for multi-tenant agent."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openclaw_lite.logging.setup import correlation_id_var
from openclaw_lite.memory.store import MemoryStore


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    user_id: str | None = None


class CreateSessionRequest(BaseModel):
    title: str = ""


class SendMessageRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


def _require_user_id(x_user_id: str | None) -> str:
    if not x_user_id:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "X-User-Id header required"}},
        )
    return x_user_id


def _check_path_user(path_user_id: str, header_user_id: str) -> None:
    if path_user_id != header_user_id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "User does not own this resource"}},
        )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    *,
    store: MemoryStore,
    workspace: Path | None = None,
    runtime: Any | None = None,
) -> FastAPI:
    """Create the FastAPI application with the given dependencies."""
    app = FastAPI(title="OpenClaw Lite")

    # Store deps on app state for access in routes
    app.state.store = store
    app.state.workspace = workspace
    app.state.runtime = runtime

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    @app.post("/api/v1/users", status_code=201)
    async def create_user(body: CreateUserRequest) -> dict[str, Any]:
        try:
            user = await store.create_user(user_id=body.user_id)
        except ValueError:
            return JSONResponse(
                status_code=409,
                content={"error": {"code": "CONFLICT", "message": "User already exists"}},
            )
        return user

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    @app.get("/api/v1/users/{user_id}/sessions")
    async def list_sessions(
        user_id: str,
        x_user_id: str | None = Header(None),
    ) -> dict[str, Any]:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        sessions = await store.list_sessions(user_id)
        return {"sessions": sessions}

    @app.post("/api/v1/users/{user_id}/sessions", status_code=201)
    async def create_session(
        user_id: str,
        body: CreateSessionRequest,
        x_user_id: str | None = Header(None),
    ) -> dict[str, Any]:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        session = await store.create_session(user_id, title=body.title)
        return session

    @app.delete("/api/v1/users/{user_id}/sessions/{session_id}", status_code=204)
    async def delete_session(
        user_id: str,
        session_id: str,
        x_user_id: str | None = Header(None),
    ) -> None:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        try:
            await store.delete_session(session_id, user_id)
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "FORBIDDEN", "message": "User does not own this session"}},
            )
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": "Session not found"}},
            )

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    @app.get("/api/v1/users/{user_id}/sessions/{session_id}/messages")
    async def get_messages(
        user_id: str,
        session_id: str,
        x_user_id: str | None = Header(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        # Verify session ownership
        owner = await store.get_session_owner(session_id)
        if owner is not None and owner != uid:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "FORBIDDEN", "message": "User does not own this session"}},
            )
        messages = await store.get_messages(session_id, user_id, limit=limit, offset=offset)
        total = await store.get_message_count(session_id, user_id)
        return {"messages": messages, "total": total}

    @app.post("/api/v1/users/{user_id}/sessions/{session_id}/messages")
    async def send_message(
        user_id: str,
        session_id: str,
        body: SendMessageRequest,
        x_user_id: str | None = Header(None),
    ) -> dict[str, Any]:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        # Verify session ownership
        owner = await store.get_session_owner(session_id)
        if owner is not None and owner != uid:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "FORBIDDEN", "message": "User does not own this session"}},
            )
        # Generate correlation ID for this request
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)

        # Store user message
        await store.add_message(session_id, user_id, "user", body.content)

        # If runtime is wired, run the agent loop
        rt = app.state.runtime
        if rt is not None:
            result = await rt.handle_message(
                user_id=user_id,
                session_id=session_id,
                user_message=body.content,
            )
            result["correlation_id"] = cid
            return result

        # Fallback: echo-style response when no runtime wired (for testing)
        return {
            "response": f"Echo: {body.content}",
            "session_id": session_id,
            "correlation_id": cid,
        }

    # ------------------------------------------------------------------
    # User Memories (placeholder for US2)
    # ------------------------------------------------------------------

    @app.get("/api/v1/users/{user_id}/memories")
    async def get_user_memories(
        user_id: str,
        x_user_id: str | None = Header(None),
    ) -> dict[str, Any]:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        memories = await store.get_user_memories(user_id)
        return {"memories": memories}

    @app.delete("/api/v1/users/{user_id}/memories/{key}", status_code=204)
    async def delete_user_memory(
        user_id: str,
        key: str,
        x_user_id: str | None = Header(None),
    ) -> None:
        uid = _require_user_id(x_user_id)
        _check_path_user(user_id, uid)
        await store.delete_user_memory(user_id, key)

    return app
