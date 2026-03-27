"""Unit tests for TokenCounter."""
from __future__ import annotations

from openclaw_lite.memory.token_counter import TokenCounter


class TestTokenCounter:
    def test_count_tokens_empty_string(self) -> None:
        counter = TokenCounter()
        assert counter.count_tokens("") == 0

    def test_count_tokens_known_string(self) -> None:
        counter = TokenCounter()
        # "hello world" is 2 tokens in cl100k_base
        result = counter.count_tokens("hello world")
        assert result > 0
        assert isinstance(result, int)

    def test_count_tokens_longer_text(self) -> None:
        counter = TokenCounter()
        short = counter.count_tokens("hi")
        long = counter.count_tokens("This is a much longer sentence with many words.")
        assert long > short

    def test_count_messages_single(self) -> None:
        counter = TokenCounter()
        messages = [{"role": "user", "content": "hello"}]
        result = counter.count_messages(messages)
        # At least: 4 (framing) + role tokens + content tokens + 3 (reply primer)
        assert result > 0

    def test_count_messages_multiple(self) -> None:
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        single = counter.count_messages(messages[:1])
        double = counter.count_messages(messages)
        assert double > single

    def test_count_messages_empty_list(self) -> None:
        counter = TokenCounter()
        # Only the reply primer (3 tokens)
        result = counter.count_messages([])
        assert result == 3

    def test_model_property(self) -> None:
        counter = TokenCounter(model="gpt-4o")
        assert counter.model == "gpt-4o"

    def test_fallback_encoding_for_unknown_model(self) -> None:
        counter = TokenCounter(model="unknown-model-xyz")
        # Should fall back to cl100k_base and still work
        result = counter.count_tokens("test")
        assert result > 0

    def test_encode_returns_ints(self) -> None:
        counter = TokenCounter()
        tokens = counter.encode("hello world")
        assert isinstance(tokens, list)
        assert all(isinstance(t, int) for t in tokens)
