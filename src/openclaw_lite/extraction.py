from __future__ import annotations

import json
import logging
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import Settings
from .memory import LongTermMemory, MemoryStore

logger = logging.getLogger(__name__)


EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "extraction_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "memories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content":    {"type": "string"},
                            "importance": {"type": "number"},
                            "tags":       {"type": "string"},
                        },
                        "required": ["content", "importance", "tags"],
                        "additionalProperties": False,
                    },
                },
                "updated_summary": {"type": "string"},
            },
            "required": ["memories", "updated_summary"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class ExtractionResult:
    memories: list[dict] = field(default_factory=list)  # {"content", "importance", "tags"}
    updated_summary: str = ""


class HeuristicExtractor:
    _PREFERENCE_PATTERNS = re.compile(
        r"\b(I prefer|I like|I always|I never|my favourite|my favorite|I hate|I love)\b",
        re.IGNORECASE,
    )
    _ENTITY_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")

    def extract(self, user_msg: str, assistant_msg: str, current_summary: str) -> ExtractionResult:
        memories: list[dict] = []

        # Preference memories
        for match in self._PREFERENCE_PATTERNS.finditer(user_msg):
            start = match.start()
            sentence_end = user_msg.find(".", start)
            snippet = user_msg[start: sentence_end + 1 if sentence_end != -1 else start + 120].strip()
            if snippet:
                memories.append({"content": snippet, "importance": 0.8, "tags": "preference,auto-extracted"})

        # Named entity memories
        seen: set[str] = set()
        for match in self._ENTITY_PATTERN.finditer(user_msg):
            entity = match.group(0)
            if entity not in seen:
                seen.add(entity)
                memories.append({"content": f"Entity mentioned: {entity}", "importance": 0.6, "tags": "entity,auto-extracted"})

        # Rolling summary: append first sentence of user message, cap at 600 chars
        first_sentence = user_msg.split(".")[0].strip()
        updated = (current_summary + "\n" + first_sentence).strip()
        updated = updated[-600:] if len(updated) > 600 else updated

        return ExtractionResult(memories=memories, updated_summary=updated)


class LLMExtractor:
    _PROMPT_TEMPLATE = """\
You are a memory extraction assistant. Given a conversation turn, extract:
1. Named entities (people, orgs, places, dates, topics) → tag "entity"
2. User preferences/habits/values explicitly or implicitly stated → tag "preference"
3. Important facts that should persist across sessions → tag "fact"
4. An updated rolling session summary (≤250 words, most recent events prioritized).

USER: {user_message}
ASSISTANT: {assistant_response}

Current summary: {current_summary}"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # TODO: only extract important preferences and details about the user for cross chat info (name, job, location, etc - but not every request made or other conversational things)
    # TODO: still keep summary of current chat for individual chats (here keep conversational summary)
    def extract(self, user_msg: str, assistant_msg: str, current_summary: str) -> ExtractionResult:
        model = self.settings.extraction_model or self.settings.model
        prompt = self._PROMPT_TEMPLATE.format(
            user_message=user_msg,
            assistant_response=assistant_msg,
            current_summary=current_summary or "(none yet)",
        )

        def _make_request(include_response_format: bool) -> dict:
            body: dict = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            if include_response_format:
                body["response_format"] = EXTRACTION_SCHEMA
            req = urllib.request.Request(
                f"{self.settings.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            payload = _make_request(include_response_format=True)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 400 and "response_format" in err_body:
                try:
                    payload = _make_request(include_response_format=False)
                except Exception as exc:
                    logger.warning("LLMExtractor fallback request failed: %s", exc)
                    return ExtractionResult(memories=[], updated_summary=current_summary)
            else:
                logger.warning("LLMExtractor HTTP error %d: %s", e.code, err_body[:200])
                return ExtractionResult(memories=[], updated_summary=current_summary)
        except Exception as exc:
            logger.warning("LLMExtractor request failed (non-HTTP): %s", exc)
            return ExtractionResult(memories=[], updated_summary=current_summary)

        try:
            raw = payload["choices"][0]["message"]["content"]
            data = json.loads(raw)
            return ExtractionResult(
                memories=data.get("memories", []),
                updated_summary=data.get("updated_summary", current_summary),
            )
        except Exception as exc:
            logger.warning("LLMExtractor failed to parse response: %s", exc)
            return ExtractionResult(memories=[], updated_summary=current_summary)


class MemoryExtractionAgent:
    def __init__(self, settings: Settings, memory: MemoryStore, long_term: LongTermMemory) -> None:
        self.settings = settings
        self.memory = memory
        self.long_term = long_term
        if settings.provider == "demo":
            self._extractor: HeuristicExtractor | LLMExtractor = HeuristicExtractor()
        else:
            self._extractor = LLMExtractor(settings)

    def run_async(self, session_id: str, user_message: str, assistant_response: str) -> None:
        if not self.settings.memory_extraction:
            return
        t = threading.Thread(
            target=self._run,
            args=(session_id, user_message, assistant_response),
            daemon=True,
        )
        t.start()

    def _run(self, session_id: str, user_message: str, assistant_response: str) -> None:
        try:
            current_summary = self.memory.get_session_summary(session_id)
            result = self._extractor.extract(user_message, assistant_response, current_summary)
            logger.info("Extraction complete: %d memories, summary_len=%d",
                        len(result.memories), len(result.updated_summary))
            logger.info("Memories: %s", result.memories)
            logger.info("Updated summary: %s", result.updated_summary)
            for mem in result.memories:
                self.long_term.store(
                    content=mem["content"],
                    importance=float(mem.get("importance", 0.7)),
                    tags=mem.get("tags", "auto-extracted"),
                )
            self.memory.upsert_session_summary(session_id, result.updated_summary)
        except Exception as exc:
            logger.warning("Memory extraction failed: %s", exc)
