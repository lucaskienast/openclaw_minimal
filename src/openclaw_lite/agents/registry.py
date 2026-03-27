"""Subagent registry — manages available subagent types."""
from __future__ import annotations

from openclaw_lite.a2a.types import AgentCard


class SubagentRegistry:
    """Registry of available subagent types and their capabilities."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentCard] = {}

    def register_agent(self, card: AgentCard) -> None:
        self._agents[card.agent_type] = card

    def get_agent(self, agent_type: str) -> AgentCard:
        if agent_type not in self._agents:
            raise KeyError(f"Unknown agent type: {agent_type}")
        return self._agents[agent_type]

    def list_agents(self) -> list[AgentCard]:
        return list(self._agents.values())

    def agent_types(self) -> list[str]:
        return list(self._agents.keys())


def create_default_registry() -> SubagentRegistry:
    """Create a registry with the three default subagent types."""
    registry = SubagentRegistry()
    registry.register_agent(AgentCard(
        agent_type="research",
        name="Research Agent",
        description="Searches the web and summarizes information",
        skills=["web search", "information retrieval", "summarization"],
        tool_names=["web_fetch"],
    ))
    registry.register_agent(AgentCard(
        agent_type="coding",
        name="Coding Agent",
        description="Reads, writes, and modifies code files",
        skills=["file operations", "code generation", "code review"],
        tool_names=["read_file", "write_file", "list_files"],
    ))
    registry.register_agent(AgentCard(
        agent_type="analysis",
        name="Analysis Agent",
        description="Creates charts, performs calculations, and analyzes data",
        skills=["data analysis", "charting", "calculations"],
        tool_names=["charting", "calculator"],
    ))
    return registry
