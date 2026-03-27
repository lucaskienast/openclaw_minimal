"""Structured output parser with retry logic for LLM responses."""
from __future__ import annotations

import re

from pydantic import ValidationError

from openclaw_lite.schemas import AgentDecision, DecisionType


def parse_decision(raw: str) -> AgentDecision:
    """Parse an LLM response string into a validated AgentDecision.

    Handles common LLM output issues:
    - Strips markdown code fences
    - Validates against Pydantic schema
    - Returns a safe error decision if parsing fails
    """
    cleaned = _strip_markdown_fences(raw)

    try:
        return AgentDecision.model_validate_json(cleaned)
    except (ValidationError, ValueError):
        pass

    # Fallback: return error decision
    return AgentDecision(
        type=DecisionType.RESPOND,
        reasoning=f"Parse error: could not validate LLM output as AgentDecision",
        content="I encountered an error processing my response. Please try again.",
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers from LLM output."""
    text = text.strip()
    pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)
    match = pattern.match(text)
    if match:
        return match.group(1).strip()
    return text
