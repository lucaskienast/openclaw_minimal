from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .app_factory import build_runtime

runtime = build_runtime()
app = FastAPI(title="OpenClaw Lite")


class MessageRequest(BaseModel):
    session_id: str = "main"
    message: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/message")
def message(request: MessageRequest) -> dict:
    return runtime.handle_message(session_id=request.session_id, user_message=request.message)
