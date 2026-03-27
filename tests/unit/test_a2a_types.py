"""Unit tests for A2A data types and task lifecycle."""
from __future__ import annotations

from openclaw_lite.a2a.types import A2AMessage, A2ATask, A2ATaskStatus, AgentCard


class TestAgentCard:
    def test_create_agent_card(self) -> None:
        card = AgentCard(
            agent_type="research",
            name="Research Agent",
            description="Searches for information",
            skills=["web search", "summarization"],
            tool_names=["web_fetch"],
        )
        assert card.agent_type == "research"
        assert len(card.skills) == 2
        assert "web_fetch" in card.tool_names


class TestA2ATask:
    def test_lifecycle_submitted_to_completed(self) -> None:
        task = A2ATask(agent_type="research", input_msg="find info")
        assert task.status == A2ATaskStatus.SUBMITTED
        task.start()
        assert task.status == A2ATaskStatus.WORKING
        task.complete("Found the information")
        assert task.status == A2ATaskStatus.COMPLETED
        assert task.output == "Found the information"

    def test_lifecycle_submitted_to_failed(self) -> None:
        task = A2ATask(agent_type="coding", input_msg="write code")
        task.start()
        task.fail("timeout")
        assert task.status == A2ATaskStatus.FAILED
        assert "timeout" in task.output

    def test_task_has_unique_id(self) -> None:
        t1 = A2ATask()
        t2 = A2ATask()
        assert t1.task_id != t2.task_id

    def test_task_has_timestamp(self) -> None:
        task = A2ATask()
        assert task.created_at > 0

    def test_complete_with_artifacts(self) -> None:
        task = A2ATask()
        task.start()
        task.complete("done", artifacts=[{"type": "file", "path": "/tmp/out.png"}])
        assert len(task.artifacts) == 1


class TestA2AMessage:
    def test_text_message(self) -> None:
        msg = A2AMessage.text("user", "hello")
        assert msg.role == "user"
        assert msg.parts[0]["type"] == "text"
        assert msg.parts[0]["text"] == "hello"
