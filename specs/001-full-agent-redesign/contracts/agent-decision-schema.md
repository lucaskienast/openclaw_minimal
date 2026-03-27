# Agent Decision Schema Contract

**Date**: 2026-03-26
**Branch**: `001-full-agent-redesign`

## AgentDecision (Primary LLM Output Schema)

Every LLM call by any agent (main or subagent) MUST return JSON conforming to this schema.

```json
{
  "type": "object",
  "required": ["type", "reasoning"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["respond", "tool", "delegate"]
    },
    "reasoning": {
      "type": "string",
      "description": "Chain-of-thought reasoning for this decision"
    },
    "content": {
      "type": "string",
      "description": "Final response text (when type=respond)"
    },
    "tool_name": {
      "type": "string",
      "description": "MCP tool name to invoke (when type=tool)"
    },
    "tool_input": {
      "type": "object",
      "description": "Tool input arguments (when type=tool)"
    },
    "delegation_target": {
      "type": "string",
      "enum": ["research", "coding", "analysis"],
      "description": "Subagent type to delegate to (when type=delegate)"
    },
    "delegation_prompt": {
      "type": "string",
      "description": "Instructions for the subagent (when type=delegate)"
    },
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": { "type": "string" },
          "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed", "failed"]
          }
        }
      },
      "description": "Current task checklist with status"
    }
  }
}
```

## MemoryExtractionResult (Post-Interaction User Fact Extraction)

```json
{
  "type": "object",
  "required": ["facts"],
  "properties": {
    "facts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["key", "value", "confidence"],
        "properties": {
          "key": {
            "type": "string",
            "description": "Fact category, e.g. name, job_title, location"
          },
          "value": {
            "type": "string",
            "description": "The extracted fact value"
          },
          "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Extraction confidence score"
          }
        }
      }
    }
  }
}
```

## SummarizationResult (Session Context Compression)

```json
{
  "type": "object",
  "required": ["summary", "key_topics"],
  "properties": {
    "summary": {
      "type": "string",
      "description": "Compressed conversation summary"
    },
    "key_topics": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Main topics discussed in summarized messages"
    }
  }
}
```
