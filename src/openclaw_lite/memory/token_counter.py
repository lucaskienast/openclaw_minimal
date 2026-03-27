"""Token counting utilities using tiktoken."""
from __future__ import annotations

import tiktoken

# Cache encodings to avoid repeated model lookups
_encoding_cache: dict[str, tiktoken.Encoding] = {}


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return a cached tiktoken encoding for the given model."""
    if model not in _encoding_cache:
        try:
            _encoding_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base for unknown models
            _encoding_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoding_cache[model]


class TokenCounter:
    """Count tokens for strings and message lists using tiktoken."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self._model = model
        self._encoding = _get_encoding(model)

    @property
    def model(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self._encoding.encode(text))

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        """Count total tokens across a list of chat messages.

        Each message is expected to have ``role`` and ``content`` keys.
        Uses the OpenAI message token overhead formula:
        each message adds ~4 tokens of framing (role, delimiters).
        """
        total = 0
        for msg in messages:
            # 4 tokens per message for framing overhead
            total += 4
            total += self.count_tokens(msg.get("role", ""))
            total += self.count_tokens(msg.get("content", ""))
        # Every reply is primed with <|start|>assistant<|message|>
        total += 3
        return total

    def encode(self, text: str) -> list[int]:
        """Return the token IDs for a text string."""
        return self._encoding.encode(text)
