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

# Run a single test
pytest tests/test_runtime.py::test_write_and_read_cycle -q

# Start the HTTP gateway
openclaw-lite serve

# Send a message (requires gateway running)
openclaw-lite chat "list files"

# Inspect registered tools
openclaw-lite inspect-tools

# Create a scheduled task
openclaw-lite schedule <name> "<prompt>" <interval_seconds>

# Run the scheduler loop
openclaw-lite run-scheduler
```

## Architecture

The system is split across three layers: **Gateway → Runtime → (Memory / Tools / Provider)**. A message flows strictly in one direction — the Gateway is never aware of tools or memory, and the Runtime never knows about HTTP.

### Agent Loop (`runtime.py`)

`AgentRuntime.handle_message()` is the core of the system. Each call:
1. Persists the user message in SQLite
2. Loads last 20 messages + up to 5 memory-search hits for context
3. Loops up to `max_steps` times: asks the Provider what to do → either `respond` (return) or `tool` (execute, append to scratchpad, continue loop)

The scratchpad accumulates tool observations within a single turn and is passed back to the provider on each step. `user_message` is rewritten after each tool call to `"The tool result was: …. Now continue helping the user."`.

### Provider Abstraction (`providers/`)

Providers implement a single method: `decide(system_prompt, history, memories, tool_specs, user_message, scratchpad) → AgentDecision`. The `AgentDecision` dataclass has `type` ("respond" or "tool"), `content`, `tool_name`, `tool_input`, and `reasoning`.

- **`demo`** — pattern-matching with regex; no API key needed; good for tests
- **`openai_compatible`** — calls any OpenAI-format chat completions endpoint; instructs the model to return strict JSON matching the `AgentDecision` shape

### Tool System (`tools/`, `plugins/`)

Tools extend `Tool` (abstract base in `tools/base.py`) and are registered in `ToolRegistry`. All tools receive a `ToolContext(session_id, workspace)` at run time. File tools sandbox paths to the workspace directory.

To add a plugin, drop a `.py` file in `plugins/` that exports `register(registry: ToolRegistry)`. The plugin loader in `plugin_loader.py` imports it automatically on startup.

### Memory (`memory.py`)

`MemoryStore` wraps SQLite with two tables:
- `messages` — per-session conversation history (role: user / assistant / tool)
- `tasks` — scheduler records with `next_run_epoch` for due-task polling

`search()` does a simple SQL `LIKE` match — no vector embeddings by design.

### Configuration (`config.py`)

All settings are read from environment variables with the `OPENCLAW_LITE_` prefix. Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `OPENCLAW_LITE_PROVIDER` | `demo` | `demo` or `openai_compatible` |
| `OPENCLAW_LITE_DB_PATH` | `./data/agent.db` | SQLite path |
| `OPENCLAW_LITE_WORKSPACE` | `./data/workspace` | File tool sandbox root |
| `OPENCLAW_LITE_MAX_STEPS` | `5` | Max agent loop iterations per message |
| `OPENCLAW_LITE_API_KEY` | — | LLM API key (openai_compatible only) |
| `OPENCLAW_LITE_MODEL` | `gpt-4o-mini` | Model name |
| `OPENCLAW_LITE_BASE_URL` | `https://api.openai.com/v1` | API base URL |

`settings.ensure_directories()` must be called before any DB or file I/O; `build_runtime()` in `app_factory.py` handles this for the normal startup path. Tests override `settings.db_path` and `settings.workspace` directly with temp directories.
