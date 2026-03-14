from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import Settings
from ..schemas import AgentDecision, ChatMessage, ToolSpec
from .base import Provider
from ..utils import to_jsonable


class OpenAICompatibleProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def decide(self,
               system_prompt: str,
               history: list[ChatMessage],
               memories: list[ChatMessage],
               tool_specs: list[ToolSpec],
               user_message: str,
               ) -> AgentDecision:
        if not self.settings.api_key:
            raise RuntimeError("OPENCLAW_LITE_API_KEY is required for openai_compatible provider")

        system_parts = [system_prompt]

        if memories:
            system_parts.append("Relevant memory:\n" + "\n".join(m.content for m in memories))

        system_parts.append(
            "You must answer in strict JSON with one of these shapes:\n"
            '{"type":"respond","content":"..."}\n'
            '{"type":"tool","tool_name":"...","tool_input":{...},"reasoning":"..."}\n'
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

        body = json.dumps({"model": self.settings.model, "messages": messages, "temperature": 0}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"API request failed {e.code}: {body}") from e
        raw = payload["choices"][0]["message"]["content"]
        data = json.loads(raw)
        return AgentDecision(
            type=data["type"],
            content=data.get("content", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input", {}),
            reasoning=data.get("reasoning", ""),
        )
