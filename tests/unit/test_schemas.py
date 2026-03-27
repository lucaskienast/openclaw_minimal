"""Unit tests for Pydantic schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from openclaw_lite.schemas import (
    AgentDecision,
    ChatMessage,
    DecisionType,
    ExtractedFact,
    MemoryExtractionResult,
    MessageRole,
    SummarizationResult,
    TaskItem,
    TaskStatus,
)


class TestAgentDecision:
    def test_respond_decision(self) -> None:
        d = AgentDecision(type=DecisionType.RESPOND, content="Hello!", reasoning="greeting")
        assert d.type == DecisionType.RESPOND
        assert d.content == "Hello!"

    def test_tool_decision(self) -> None:
        d = AgentDecision(
            type=DecisionType.TOOL,
            tool_name="read_file",
            tool_input={"path": "/tmp/test.txt"},
            reasoning="need to read file",
        )
        assert d.type == DecisionType.TOOL
        assert d.tool_name == "read_file"
        assert d.tool_input == {"path": "/tmp/test.txt"}

    def test_delegate_decision(self) -> None:
        d = AgentDecision(
            type=DecisionType.DELEGATE,
            delegation_target="research",
            delegation_prompt="Find information about Python",
            reasoning="need research",
        )
        assert d.type == DecisionType.DELEGATE
        assert d.delegation_target == "research"

    def test_invalid_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentDecision(type="invalid_type", reasoning="test")

    def test_tasks_list(self) -> None:
        d = AgentDecision(
            type=DecisionType.RESPOND,
            content="Done",
            tasks=[
                TaskItem(description="Step 1", status=TaskStatus.COMPLETED),
                TaskItem(description="Step 2", status=TaskStatus.PENDING),
            ],
        )
        assert len(d.tasks) == 2
        assert d.tasks[0].status == TaskStatus.COMPLETED

    def test_from_json(self) -> None:
        raw = '{"type": "respond", "reasoning": "done", "content": "hi"}'
        d = AgentDecision.model_validate_json(raw)
        assert d.type == DecisionType.RESPOND

    def test_invalid_json_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentDecision.model_validate_json('not json at all')


class TestMemoryExtractionResult:
    def test_parse_facts(self) -> None:
        raw = '{"facts": [{"key": "name", "value": "Alice", "confidence": 0.95}]}'
        result = MemoryExtractionResult.model_validate_json(raw)
        assert len(result.facts) == 1
        assert result.facts[0].key == "name"
        assert result.facts[0].confidence == 0.95

    def test_empty_facts(self) -> None:
        result = MemoryExtractionResult(facts=[])
        assert result.facts == []

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedFact(key="test", value="val", confidence=1.5)
        with pytest.raises(ValidationError):
            ExtractedFact(key="test", value="val", confidence=-0.1)


class TestSummarizationResult:
    def test_parse(self) -> None:
        raw = '{"summary": "Discussed Python.", "key_topics": ["python", "coding"]}'
        result = SummarizationResult.model_validate_json(raw)
        assert result.summary == "Discussed Python."
        assert len(result.key_topics) == 2

    def test_missing_summary_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SummarizationResult.model_validate_json('{"key_topics": ["a"]}')


class TestChatMessage:
    def test_valid_roles(self) -> None:
        for role in MessageRole:
            msg = ChatMessage(role=role, content="test")
            assert msg.role == role

    def test_invalid_role_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="test")
