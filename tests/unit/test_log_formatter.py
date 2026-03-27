"""Unit tests for box-drawing log formatter."""
from __future__ import annotations

from openclaw_lite.logging.categories import RESET, LogCategory
from openclaw_lite.logging.formatter import box_format


class TestBoxFormat:
    def test_basic_output_has_box_characters(self) -> None:
        output = box_format(LogCategory.REASONING, "test message")
        assert "\u250f" in output  # top-left corner ┏
        assert "\u2517" in output  # bottom-left corner ┗
        assert "\u2503" in output  # vertical bar ┃

    def test_header_contains_category_label(self) -> None:
        output = box_format(LogCategory.TOOL_CALL, "calling tool")
        assert "TOOL CALL" in output

    def test_header_contains_emoji(self) -> None:
        output = box_format(LogCategory.REASONING, "thinking")
        assert LogCategory.REASONING.style.emoji in output

    def test_correlation_id_included(self) -> None:
        output = box_format(
            LogCategory.SYSTEM,
            "test",
            correlation_id="abcdef12-3456-7890-abcd-ef1234567890",
        )
        assert "abcdef12" in output

    def test_module_name_included(self) -> None:
        output = box_format(LogCategory.MEMORY, "test", module="memory.store")
        assert "memory.store" in output

    def test_level_included(self) -> None:
        output = box_format(LogCategory.SYSTEM, "test", level="WARNING")
        assert "WARNING" in output

    def test_extra_fields_rendered(self) -> None:
        output = box_format(
            LogCategory.TOOL_CALL,
            "called read_file",
            extra={"duration_ms": 42, "tool": "read_file"},
        )
        assert "duration_ms: 42" in output
        assert "tool: read_file" in output

    def test_sensitive_data_redacted(self) -> None:
        output = box_format(
            LogCategory.SYSTEM,
            "api_key = sk-abc123456789012345678901234567890",
        )
        assert "sk-abc" not in output
        assert "[REDACTED]" in output

    def test_bearer_token_redacted(self) -> None:
        output = box_format(
            LogCategory.SYSTEM,
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test",
        )
        assert "eyJhbGci" not in output
        assert "[REDACTED]" in output

    def test_each_category_produces_distinct_output(self) -> None:
        outputs = {}
        for cat in LogCategory:
            outputs[cat.name] = box_format(cat, "test message")

        # Each category should have its own label
        assert "REASONING" in outputs["REASONING"]
        assert "TOOL CALL" in outputs["TOOL_CALL"]
        assert "TASK UPDATE" in outputs["TASK_UPDATE"]
        assert "FINAL ANSWER" in outputs["FINAL_ANSWER"]
        assert "MEMORY" in outputs["MEMORY"]
        assert "SYSTEM" in outputs["SYSTEM"]

    def test_multiline_message(self) -> None:
        output = box_format(LogCategory.REASONING, "line 1\nline 2\nline 3")
        lines = output.split("\n")
        # Should have: top border, header, separator, 3 message lines, bottom border = 7
        assert len(lines) >= 7

    def test_color_reset_present(self) -> None:
        output = box_format(LogCategory.REASONING, "test")
        assert RESET in output
