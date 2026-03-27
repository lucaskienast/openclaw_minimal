"""Unit tests for structured output validation and retry logic."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from openclaw_lite.schemas import AgentDecision, DecisionType


class TestSchemaEnforcement:
    def test_valid_respond(self) -> None:
        raw = json.dumps({"type": "respond", "reasoning": "done", "content": "hi"})
        d = AgentDecision.model_validate_json(raw)
        assert d.type == DecisionType.RESPOND
        assert d.content == "hi"

    def test_valid_tool(self) -> None:
        raw = json.dumps({
            "type": "tool",
            "reasoning": "need file",
            "tool_name": "read_file",
            "tool_input": {"path": "/tmp/test.txt"},
        })
        d = AgentDecision.model_validate_json(raw)
        assert d.type == DecisionType.TOOL
        assert d.tool_name == "read_file"

    def test_valid_delegate(self) -> None:
        raw = json.dumps({
            "type": "delegate",
            "reasoning": "need research",
            "delegation_target": "research",
            "delegation_prompt": "find info",
        })
        d = AgentDecision.model_validate_json(raw)
        assert d.type == DecisionType.DELEGATE

    def test_invalid_type_rejected(self) -> None:
        raw = json.dumps({"type": "invalid", "reasoning": "test"})
        with pytest.raises(ValidationError):
            AgentDecision.model_validate_json(raw)

    def test_malformed_json_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentDecision.model_validate_json("not json at all")

    def test_extra_fields_ignored(self) -> None:
        raw = json.dumps({
            "type": "respond",
            "reasoning": "test",
            "content": "ok",
            "extra_field": "ignored",
        })
        d = AgentDecision.model_validate_json(raw)
        assert d.content == "ok"


class TestRetryLogic:
    def test_parse_decision_with_retry(self) -> None:
        """Test the retry helper that will be used by providers."""
        from openclaw_lite.providers.output_parser import parse_decision

        # Valid JSON on first try
        result = parse_decision('{"type": "respond", "reasoning": "ok", "content": "hello"}')
        assert result.type == DecisionType.RESPOND

    def test_parse_decision_strips_markdown_fences(self) -> None:
        from openclaw_lite.providers.output_parser import parse_decision

        raw = '```json\n{"type": "respond", "reasoning": "ok", "content": "hello"}\n```'
        result = parse_decision(raw)
        assert result.type == DecisionType.RESPOND

    def test_parse_decision_returns_error_on_failure(self) -> None:
        from openclaw_lite.providers.output_parser import parse_decision

        result = parse_decision("completely invalid")
        assert result.type == DecisionType.RESPOND
        assert "parse" in result.reasoning.lower() or "error" in result.reasoning.lower()
