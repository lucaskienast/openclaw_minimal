# Quickstart: Full Agent Redesign

**Branch**: `001-full-agent-redesign`

## Prerequisites

- Python 3.11+
- An OpenAI-compatible API key

## Setup

```bash
# Clone and checkout feature branch
git checkout 001-full-agent-redesign

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## Configuration

```bash
# Required
export OPENCLAW_LITE_API_KEY="your-api-key"
export OPENCLAW_LITE_PROVIDER="openai_compatible"

# Optional (defaults shown)
export OPENCLAW_LITE_MODEL="gpt-4o-mini"
export OPENCLAW_LITE_BASE_URL="https://api.openai.com/v1"
export OPENCLAW_LITE_DB_PATH="./data/agent.db"
export OPENCLAW_LITE_WORKSPACE="./data/workspace"
export OPENCLAW_LITE_HOST="0.0.0.0"
export OPENCLAW_LITE_PORT="8000"
export OPENCLAW_LITE_MAX_STEPS="10"
export OPENCLAW_LITE_CONTEXT_WINDOW="128000"
```

## Start the Server

```bash
openclaw-lite serve
```

Server starts at `http://localhost:8000`.

## Basic Usage

### Create a user and session

```bash
# Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{}'

# Create session (use user_id from above)
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{"title": "My first chat"}'
```

### Send a message

```bash
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions/{session_id}/messages \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! My name is Alice and I am a data scientist."}'
```

### Verify cross-session memory

```bash
# Create a new session
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{}'

# Ask about remembered facts in the new session
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions/{new_session_id}/messages \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{"content": "What do you know about me?"}'
# Expected: Agent recalls name and role from previous session
```

### Use tools

```bash
# Ask agent to create a chart
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions/{session_id}/messages \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Create a bar chart showing: Jan=100, Feb=150, Mar=120"}'

# Ask agent to manage todos
curl -X POST http://localhost:8000/api/v1/users/{user_id}/sessions/{session_id}/messages \
  -H "X-User-Id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Create a todo list: Buy groceries, Walk the dog, Read a book"}'
```

## Run Tests

```bash
# All tests
pytest -q

# Unit tests only
pytest tests/unit/ -q

# Integration tests only
pytest tests/integration/ -q
```

## Verify Setup

After starting the server, run:

```bash
# Health check
curl http://localhost:8000/health

# Inspect available MCP tools
openclaw-lite inspect-tools
```

Both should return without errors.
