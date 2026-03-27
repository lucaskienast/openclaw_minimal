"""Unit tests for system prompts and ReAct workflow instructions."""
from __future__ import annotations

from openclaw_lite.prompts.system import build_system_prompt


class TestSystemPrompt:
    def test_includes_react_workflow(self) -> None:
        prompt = build_system_prompt(tool_names=["read_file"])
        assert "Reason" in prompt or "reason" in prompt
        assert "Act" in prompt or "act" in prompt
        assert "Observe" in prompt or "observe" in prompt

    def test_includes_task_checklist(self) -> None:
        prompt = build_system_prompt(tool_names=["read_file"])
        assert "task" in prompt.lower()
        assert "checklist" in prompt.lower() or "tasks" in prompt.lower()

    def test_includes_original_message_reread(self) -> None:
        prompt = build_system_prompt(tool_names=["read_file"])
        assert "original" in prompt.lower()

    def test_includes_tool_names(self) -> None:
        prompt = build_system_prompt(tool_names=["read_file", "write_file"])
        assert "read_file" in prompt
        assert "write_file" in prompt

    def test_includes_structured_output_instructions(self) -> None:
        prompt = build_system_prompt(tool_names=[])
        assert "JSON" in prompt or "json" in prompt
        assert "type" in prompt

    def test_includes_delegation_instructions(self) -> None:
        prompt = build_system_prompt(
            tool_names=[],
            subagent_types=["research", "coding", "analysis"],
        )
        assert "delegate" in prompt.lower()
        assert "research" in prompt.lower()
