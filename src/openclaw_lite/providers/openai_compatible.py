from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..config import Settings
from ..schemas import AgentDecision, ChatMessage, MemoryContext, ToolSpec
from .base import Provider
from ..utils import to_jsonable


DECISION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "type":       {"type": "string", "enum": ["respond", "tool"]},
                "content":    {"type": "string"},
                "tool_name":  {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "tool_input": {"type": "object"},
                "reasoning":  {"type": "string"},
                "tasks":      {"type": "array", "items": {"type": "string"}},
            },
            "required": ["type", "content", "tool_name", "tool_input", "reasoning", "tasks"],
            "additionalProperties": False,
        },
    },
}


class OpenAICompatibleProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def decide(self,
               system_prompt: str,
               history: list[ChatMessage],
               memory_context: MemoryContext,
               tool_specs: list[ToolSpec],
               user_message: str,
               ) -> AgentDecision:
        if not self.settings.api_key:
            raise RuntimeError("OPENCLAW_LITE_API_KEY is required for openai_compatible provider")

        system_parts = [system_prompt]

        if memory_context.session_summary:
            system_parts.append(
                f"Session summary (high priority — what has been discussed so far):\n{memory_context.session_summary}"
            )

        if memory_context.long_term:
            lt_text = "\n".join(f"- {f}" for f in memory_context.long_term)
            system_parts.append(f"Relevant long-term memories (includes recency and importance):\n{lt_text}")

        if memory_context.knowledge:
            k_text = "\n\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(memory_context.knowledge))
            system_parts.append(f"Relevant knowledge from document store:\n{k_text}")

        system_parts.append(
            "Note: knowledge retrieval is automatic. Only call search_knowledge if the above "
            "context is insufficient or you need a more specific query.\n\n"
            "Respond with a single JSON object. ALWAYS include the `tasks` field.\n\n"
            '  Intermediate: {"type":"respond","content":"...","tasks":["remaining task 1","remaining task 2"]}\n'
            '  Use tool:     {"type":"tool","tool_name":"<name>","tool_input":{...},"reasoning":"...","tasks":["remaining"]}\n'
            '  Final:        {"type":"respond","content":"...","tasks":[]}\n\n'
            'IMPORTANT:\n'
            '- "type" must be "respond" or "tool". Never put a tool name in "type".\n'
            '- "tasks" is REQUIRED in every response. On your first decision, list ALL work items.\n'
            '  Remove items as you complete them. Only set tasks=[] when ALL work is done.\n\n'
            f"Available tools: {json.dumps([to_jsonable(tool) for tool in tool_specs])}"
        )

        messages = [
            {"role": "system", "content": "\n\n".join(system_parts)},
        ]
        ROLE_MAP = {"tool": "user", "assistant": "assistant", "user": "user"}
        messages.extend(
            {"role": ROLE_MAP.get(m.role, "user"), "content": m.content}
            for m in history
        )
        messages.append({"role": "user", "content": user_message})

        def _make_request(include_response_format: bool) -> dict:
            request_body: dict[str, Any] = {"model": self.settings.model, "messages": messages, "temperature": 0}
            if include_response_format:
                request_body["response_format"] = DECISION_SCHEMA
            encoded = json.dumps(request_body).encode("utf-8")
            req = urllib.request.Request(
                f"{self.settings.base_url.rstrip('/')}/chat/completions",
                data=encoded,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            payload = _make_request(include_response_format=True)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 400 and "response_format" in err_body:
                try:
                    payload = _make_request(include_response_format=False)
                except urllib.error.HTTPError as e2:
                    raise RuntimeError(f"API request failed {e2.code}: {e2.read().decode('utf-8', errors='replace')}") from e2
            else:
                raise RuntimeError(f"API request failed {e.code}: {err_body}") from e

        raw = payload["choices"][0]["message"]["content"]
        data = json.loads(raw)

        # Fallback: model used tool name as "type" (e.g. {"type":"write_file",...})
        decision_type = data.get("type")
        if decision_type not in ("respond", "tool"):
            if decision_type:  # model put a tool name in the "type" field
                data["tool_name"] = data.get("tool_name") or decision_type
                data["type"] = "tool"
            else:              # "type" key is missing entirely — safe default
                data["type"] = "respond"

        return AgentDecision(
            type=data["type"],
            content=data.get("content", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input", {}),
            reasoning=data.get("reasoning", ""),
            tasks=data.get("tasks"),
        )
