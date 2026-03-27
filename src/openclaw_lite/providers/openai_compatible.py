"""OpenAI-compatible provider with structured output enforcement."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from openclaw_lite.config import Settings
from openclaw_lite.providers.base import Provider
from openclaw_lite.providers.output_parser import parse_decision
from openclaw_lite.schemas import (
    AgentDecision,
    ChatMessage,
    DecisionType,
    MemoryContext,
    TaskItem,
    ToolSpec,
)

logger = logging.getLogger(__name__)

DECISION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["respond", "tool", "delegate"]},
                "content": {"type": "string"},
                "reasoning": {"type": "string"},
                "tool_name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "tool_input": {"type": "object"},
                "delegation_target": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "delegation_prompt": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed", "failed"],
                            },
                        },
                        "required": ["description", "status"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "type", "content", "reasoning", "tool_name",
                "tool_input", "delegation_target", "delegation_prompt", "tasks",
            ],
            "additionalProperties": False,
        },
    },
}

MAX_RETRIES = 2


class OpenAICompatibleProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def decide(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        memory_context: MemoryContext,
        tool_specs: list[ToolSpec],
        user_message: str,
    ) -> AgentDecision:
        if not self._settings.api_key:
            raise RuntimeError("OPENCLAW_LITE_API_KEY is required")

        messages = self._build_messages(
            system_prompt, history, memory_context, tool_specs, user_message
        )

        for attempt in range(1, MAX_RETRIES + 2):
            raw = self._call_api(messages)

            try:
                data = json.loads(raw)
                decision = self._parse_response(data)
                return decision
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning(
                    "Parse attempt %d/%d failed: %s",
                    attempt, MAX_RETRIES + 1, exc,
                )
                if attempt <= MAX_RETRIES:
                    messages.append({
                        "role": "assistant",
                        "content": raw,
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON matching the "
                            "required schema. Please respond with valid JSON."
                        ),
                    })
                    continue

                return parse_decision(raw)

        return AgentDecision(
            type=DecisionType.RESPOND,
            reasoning="All parse retries exhausted",
            content="I encountered an error processing my response.",
        )

    def _build_messages(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        memory_context: MemoryContext,
        tool_specs: list[ToolSpec],
        user_message: str,
    ) -> list[dict[str, str]]:
        system_parts = [system_prompt]

        if memory_context.session_summary:
            system_parts.append(
                f"Session summary:\n{memory_context.session_summary}"
            )

        if memory_context.long_term:
            lt_text = "\n".join(f"- {f}" for f in memory_context.long_term)
            system_parts.append(f"Long-term memories:\n{lt_text}")

        tool_json = json.dumps(
            [{"name": t.name, "description": t.description} for t in tool_specs]
        )
        system_parts.append(f"Available tools: {tool_json}")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "\n\n".join(system_parts)},
        ]
        role_map = {"tool": "user", "assistant": "assistant", "user": "user"}
        messages.extend(
            {"role": role_map.get(m.role, "user"), "content": m.content}
            for m in history
        )
        messages.append({"role": "user", "content": user_message})
        return messages

    def _call_api(self, messages: list[dict[str, str]]) -> str:
        request_body: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": 0,
            "response_format": DECISION_SCHEMA,
        }
        encoded = json.dumps(request_body).encode()
        req = urllib.request.Request(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")
            if e.code == 400 and "response_format" in err_body:
                # Retry without response_format
                del request_body["response_format"]
                encoded = json.dumps(request_body).encode()
                req = urllib.request.Request(
                    f"{self._settings.base_url.rstrip('/')}/chat/completions",
                    data=encoded,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._settings.api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.loads(resp.read().decode())
            else:
                raise RuntimeError(f"API error {e.code}: {err_body}") from e

        return payload["choices"][0]["message"]["content"]

    def _parse_response(self, data: dict[str, Any]) -> AgentDecision:
        # Handle model putting tool name in type field
        decision_type = data.get("type", "respond")
        if decision_type not in ("respond", "tool", "delegate"):
            data["tool_name"] = data.get("tool_name") or decision_type
            data["type"] = "tool"

        # Convert legacy string tasks to TaskItem format
        raw_tasks = data.get("tasks", [])
        tasks = []
        for t in raw_tasks:
            if isinstance(t, str):
                tasks.append(TaskItem(description=t))
            elif isinstance(t, dict):
                tasks.append(TaskItem(**t))

        return AgentDecision(
            type=data["type"],
            content=data.get("content", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input", {}),
            reasoning=data.get("reasoning", ""),
            delegation_target=data.get("delegation_target"),
            delegation_prompt=data.get("delegation_prompt"),
            tasks=tasks,
        )
