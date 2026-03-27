"""Prompt template for user fact extraction."""
from __future__ import annotations

EXTRACTION_PROMPT = """You are a fact extraction assistant. Given a user message and assistant response,
extract ONLY key personal facts about the user.

Extract ONLY these types of facts:
- name, nickname
- job_title, role, occupation
- location, city, country
- language preferences
- technical preferences (editor, OS, language)
- other stable personal attributes

Do NOT extract:
- General conversation topics
- Requests or instructions
- Temporary states ("I'm tired", "I need help with X")
- Anything about the assistant

Respond with valid JSON matching this exact schema:
{
  "facts": [
    {"key": "name", "value": "Alice", "confidence": 0.95},
    {"key": "location", "value": "Berlin", "confidence": 0.85}
  ]
}

If no personal facts are present, respond with: {"facts": []}
"""


def build_extraction_prompt(user_message: str, assistant_response: str) -> str:
    """Build the extraction prompt with conversation context."""
    return (
        f"{EXTRACTION_PROMPT}\n\n"
        f"User message: {user_message}\n\n"
        f"Assistant response: {assistant_response}"
    )
