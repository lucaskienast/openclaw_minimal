# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Common Commands

```bash
# Run all tests
pytest -q

# Run unit tests only
pytest tests/unit/ -q

# Run integration tests only
pytest tests/integration/ -q

# Run a single test
pytest tests/unit/test_memory_store.py::test_create_user -q

# Start the HTTP gateway
openclaw-lite serve

# Send a message (requires gateway running, multi-user)
openclaw-lite chat --user-id user123 --session-id sess1 "list files"

# Inspect registered tools
openclaw-lite inspect-tools
```

## Architecture

The system is a multi-tenant async agent backend split across layers: **Gateway → Runtime → (Agents / Memory / Tools / Providers)**.

### Gateway (`gateway.py`)

RESTful API with user-scoped endpoints. All requests require `X-User-Id` header. Key routes:

- `POST /api/v1/users` — create user
- `POST /api/v1/users/{uid}/sessions` — create session
- `POST /api/v1/users/{uid}/sessions/{sid}/messages` — send message (triggers agent loop)
- `GET /api/v1/users/{uid}/memories` — list user-level long-term memories
- `DELETE /api/v1/users/{uid}/sessions/{sid}` — cascade delete session + messages

### Runtime (`runtime.py`)

`AgentRuntime.handle_message(user_id, session_id, user_message)` orchestrates each turn:
1. Loads message history + session/user memories for context
2. Delegates to the agent loop (ReAct cycle with structured output)
3. Persists assistant response
4. Returns `AgentDecision` with reasoning, task checklist, and content

Uses `asyncio.wait_for` with configurable `response_timeout`.

### Agents (`agents/`)

- `BaseAgent` — ReAct loop foundation with structured logging (REASONING, TOOL_CALL, TASK_UPDATE, FINAL_ANSWER)
- `SubagentRegistry` — 3 default subagent types: research, coding, analysis
- Subagents communicate via A2A protocol (`a2a/dispatcher.py`, `a2a/types.py`)

### Provider Abstraction (`providers/`)

Providers implement `decide() → AgentDecision`. All LLM calls enforce structured output via Pydantic schemas and `response_format`.

- **`demo`** — pattern-matching; no API key needed; good for tests
- **`openai_compatible`** — OpenAI-format chat completions with JSON schema enforcement and retry (max 2)

### Tool System (`tools/`)

Built-in tools registered in `app_factory.py`:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents (sandboxed to workspace) |
| `write_file` | Write file (sandboxed) |
| `list_files` | List directory contents |
| `time` | Current date/time |
| `system_info` | OS/platform info |
| `web_fetch` | Fetch URL content |
| `charting` | Create bar/line/pie/scatter PNG charts |
| `todo` | Manage markdown todo lists |
| `calculator` | Safe arithmetic expression evaluator |
| `shell` | Run shell commands in workspace |

MCP support: `MCPToolServer` exposes tools via MCP format; `MCPToolClient` discovers external tools.

Plugin system still available via `plugin_loader.py` for custom tools in `plugins/`.

### Memory (`memory/`)

Multi-tenant async memory backed by aiosqlite:

- **`store.py`** — Core DB with tables: users, sessions, messages (with token_count), session_memories, user_memories
- **`session_memory.py`** — Triggers summarization at 75% context window usage
- **`user_memory.py`** — Extracts personal facts (name, job, preferences) via LLM after each interaction
- **`token_counter.py`** — tiktoken-based token counting

### Prompts (`prompts/`)

- `system.py` — ReAct workflow prompt with task checklist, delegation instructions, original-message re-read
- `summarization.py` — Session summary prompt template
- `extraction.py` — User fact extraction prompt template

### Logging (`logging/`)

Structured logging via structlog with box-drawing formatter. Categories: REASONING, TOOL_CALL, TASK_UPDATE, FINAL_ANSWER, MEMORY, SYSTEM. Correlation IDs via contextvars.

### Configuration (`config.py`)

All settings via environment variables with `OPENCLAW_LITE_` prefix:

| Variable | Default | Purpose |
|---|---|---|
| `OPENCLAW_LITE_PROVIDER` | `demo` | `demo` or `openai_compatible` |
| `OPENCLAW_LITE_DB_PATH` | `./data/agent.db` | SQLite path |
| `OPENCLAW_LITE_WORKSPACE` | `./data/workspace` | File tool sandbox root |
| `OPENCLAW_LITE_MAX_STEPS` | `10` | Max agent loop iterations per message |
| `OPENCLAW_LITE_API_KEY` | — | LLM API key (openai_compatible only) |
| `OPENCLAW_LITE_MODEL` | `gpt-4o-mini` | Model name |
| `OPENCLAW_LITE_BASE_URL` | `https://api.openai.com/v1` | API base URL |
| `OPENCLAW_LITE_CONTEXT_WINDOW` | `128000` | Token context window size |
| `OPENCLAW_LITE_RESPONSE_TIMEOUT` | `120` | Agent loop timeout (seconds) |
| `OPENCLAW_LITE_SUBAGENT_TIMEOUT` | `60` | Subagent dispatch timeout (seconds) |
| `OPENCLAW_LITE_MCP_SERVERS` | — | JSON array of MCP server configs |
| `OPENCLAW_LITE_MEMORY_EXTRACTION` | `true` | Enable user fact extraction |
| `OPENCLAW_LITE_HOST` | `0.0.0.0` | Server bind host |
| `OPENCLAW_LITE_PORT` | `8000` | Server bind port |

## Testing

136 tests across `tests/unit/` and `tests/integration/`. Uses `pytest-asyncio` with `asyncio_mode="auto"`. Tests use temp directories for DB and workspace isolation.

## Active Technologies

- Python 3.11+, FastAPI, uvicorn, aiosqlite, tiktoken, structlog, matplotlib, pydantic
- SQLite via aiosqlite (multi-tenant schema with foreign keys and WAL mode)
- MCP protocol for tool interop
- A2A protocol for subagent communication
