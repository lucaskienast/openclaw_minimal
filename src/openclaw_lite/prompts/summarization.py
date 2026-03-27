"""Prompt template for session summarization."""
from __future__ import annotations

SUMMARIZATION_PROMPT = """You are a summarization assistant. Given a list of conversation messages,
produce a concise summary that captures the key points, decisions, and context.

IMPORTANT:
- Focus on factual content and decisions made
- Preserve important details like file paths, code snippets, or specific instructions
- Do not include conversational filler or pleasantries
- Extract the 3-5 most important topics discussed

Respond with valid JSON matching this exact schema:
{
  "summary": "A concise paragraph summarizing the conversation",
  "key_topics": ["topic1", "topic2", "topic3"]
}

Messages to summarize:
"""


def build_summarization_prompt(messages: list[dict]) -> str:
    """Build the full summarization prompt with message content."""
    parts = [SUMMARIZATION_PROMPT]
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        parts.append(f"[{role}]: {content}")
    return "\n".join(parts)
