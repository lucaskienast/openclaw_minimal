# Data Model: Full Agent Redesign

**Date**: 2026-03-26
**Branch**: `001-full-agent-redesign`

## Entities

### User

| Field      | Type   | Constraints                    |
|------------|--------|--------------------------------|
| user_id    | string | Primary key, UUID              |
| created_at | string | ISO 8601 timestamp, NOT NULL   |

**Relationships**: Owns many ChatSessions, owns many UserMemories.

---

### ChatSession

| Field      | Type   | Constraints                              |
|------------|--------|------------------------------------------|
| session_id | string | Primary key, UUID                        |
| user_id    | string | Foreign key → User, NOT NULL             |
| title      | string | Optional, auto-generated from first msg  |
| created_at | string | ISO 8601 timestamp, NOT NULL             |

**Relationships**: Belongs to one User. Contains many Messages, many SessionMemories.
**Lifecycle**: Created on first message or explicit creation. Retained indefinitely. Deleted by owning user (cascade-deletes Messages and SessionMemories).

---

### Message

| Field       | Type    | Constraints                                |
|-------------|---------|--------------------------------------------|
| message_id  | string  | Primary key, UUID                          |
| session_id  | string  | Foreign key → ChatSession, NOT NULL        |
| role        | string  | Enum: "user", "assistant", "tool"          |
| content     | string  | NOT NULL                                   |
| token_count | integer | NOT NULL, computed on insert               |
| created_at  | string  | ISO 8601 timestamp, NOT NULL               |

**Relationships**: Belongs to one ChatSession.
**Notes**: `token_count` is computed via tiktoken on insert and used for summarization threshold tracking.

---

### SessionMemory

| Field             | Type   | Constraints                              |
|-------------------|--------|------------------------------------------|
| memory_id         | string | Primary key, UUID                        |
| session_id        | string | Foreign key → ChatSession, NOT NULL      |
| summary           | string | NOT NULL, LLM-generated summary text     |
| messages_covered  | integer| Count of messages summarized             |
| created_at        | string | ISO 8601 timestamp, NOT NULL             |

**Relationships**: Belongs to one ChatSession.
**Lifecycle**: Created when session token count exceeds 75% of context window. Multiple summaries can exist per session (incremental summarization).

---

### UserMemory

| Field      | Type   | Constraints                                      |
|------------|--------|--------------------------------------------------|
| memory_id  | string | Primary key, UUID                                |
| user_id    | string | Foreign key → User, NOT NULL                     |
| key        | string | NOT NULL, e.g. "name", "job_title", "location"   |
| value      | string | NOT NULL, the extracted fact                      |
| confidence | float  | 0.0–1.0, extraction confidence from LLM          |
| updated_at | string | ISO 8601 timestamp, NOT NULL                     |

**Relationships**: Belongs to one User.
**Uniqueness**: UNIQUE(user_id, key) — upsert on conflict (update value and confidence).
**Lifecycle**: Created/updated by dedicated LLM extraction call after each interaction. Only key personal facts stored (name, role, preferences, location, etc.).

---

### AgentCard (in-memory, not persisted)

| Field       | Type        | Constraints                              |
|-------------|-------------|------------------------------------------|
| agent_type  | string      | Enum: "main", "research", "coding", "analysis" |
| name        | string      | Human-readable agent name                |
| description | string      | What this agent specializes in           |
| skills      | list[str]   | Capability descriptions                  |
| tool_names  | list[str]   | MCP tool names available to this agent   |

**Notes**: Follows A2A AgentCard semantics. Stored in SubagentRegistry at startup.

---

### A2ATask (in-memory, transient per request)

| Field      | Type        | Constraints                                        |
|------------|-------------|----------------------------------------------------|
| task_id    | string      | UUID, unique per delegation                        |
| status     | string      | Enum: "submitted", "working", "completed", "failed"|
| agent_type | string      | Target subagent type                               |
| input_msg  | string      | The delegated prompt/instruction                   |
| output     | string      | Subagent's response (when completed)               |
| artifacts  | list[dict]  | Any files or data produced                         |
| created_at | float       | Unix timestamp                                     |
| timeout_s  | float       | Per-task timeout in seconds (default 60)           |

**Lifecycle**: submitted → working → completed | failed. Transient — not persisted to database.

---

## State Transitions

### A2ATask Status

```
submitted ──→ working ──→ completed
                  │
                  └──→ failed (error or timeout)
```

### Session Summarization

```
normal (total tokens < 75% window)
  │
  ├── message added, tokens recalculated
  │
  └── tokens exceed threshold ──→ summarize oldest messages
                                    │
                                    ├── create SessionMemory record
                                    ├── mark summarized messages
                                    └── return to normal (reduced token count)
```

## Indexes

- `messages`: INDEX on (session_id, created_at) for ordered retrieval
- `sessions`: INDEX on (user_id) for listing user's sessions
- `user_memories`: UNIQUE INDEX on (user_id, key) for upsert
- `session_memories`: INDEX on (session_id) for summary retrieval
