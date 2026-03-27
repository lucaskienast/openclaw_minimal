# Implementation Plan: Full Agent Redesign

**Branch**: `001-full-agent-redesign` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-full-agent-redesign/spec.md`

## Summary

Refactor the entire OpenClaw Lite application from a single-session prototype into a multi-tenant agent backend with tiered memory management, MCP-based tool protocol, A2A subagent delegation, structured output enforcement on all LLM calls, beautiful formatted logging, and new agent tools (charting, todo). The architecture stays framework-free (no LangChain/etc.) per constitution, using direct API integrations with `mcp` SDK for tool protocol, `aiosqlite` for async multi-tenant storage, `tiktoken` for token counting, `structlog` for correlation-ID-based logging, and `matplotlib` for charting.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, uvicorn, mcp (MCP SDK), aiosqlite, tiktoken, structlog, matplotlib, pydantic
**Storage**: SQLite via aiosqlite (PostgreSQL-migration-ready schema design)
**Testing**: pytest, pytest-asyncio, httpx (for async FastAPI test client)
**Target Platform**: Linux/macOS server
**Project Type**: Web service (backend API)
**Performance Goals**: <120s end-to-end per interaction; concurrent multi-user support
**Constraints**: Single server instance; stdio-only MCP transport; in-process subagents
**Scale/Scope**: Multiple concurrent users with multiple sessions each; single-instance deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clean Code | PASS | Refactor cleans up existing code; type annotations on all public interfaces |
| II. Framework-Free Architecture | PASS | No LangChain/etc. Using `mcp` SDK (protocol library, not orchestration framework). Direct `aiosqlite` instead of ORM. |
| III. Standard Agent Protocols | PASS | MCP for tools (stdio transport), A2A for subagent delegation |
| IV. Structured Observability | PASS | structlog + custom formatter with box-drawing, correlation IDs, log categories |
| V. Cognitive Agent Capabilities | PASS | ReAct loop with reasoning, planning, tool calling, task checklist, subagent delegation |
| VI. Effective Memory Management | PASS | Two-tier: session summaries (short-term) + cross-session user facts (long-term); LLM extraction; tiktoken threshold |
| VII. Multi-Tenant Backend | PASS | user_id on all tables, session isolation, ownership checks, cascade deletes |
| VIII. Comprehensive Testing | PASS | Unit tests per module + integration tests for cross-layer interactions |

**Post-design re-check**: All gates still pass. `structlog` dependency justified for correlation ID propagation (principle II allows minimal justified dependencies). `mcp` SDK is a protocol library, not an orchestration framework.

## Project Structure

### Documentation (this feature)

```text
specs/001-full-agent-redesign/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-api.md
│   └── agent-decision-schema.md
└── tasks.md
```

### Source Code (repository root)

```text
src/openclaw_lite/
├── __init__.py
├── main.py                    # CLI entry point (serve, chat, inspect-tools)
├── config.py                  # Settings from env vars
├── app_factory.py             # Builds runtime with all components
├── gateway.py                 # FastAPI HTTP gateway (v1 API routes)
├── runtime.py                 # AgentRuntime: ReAct agent loop
├── schemas.py                 # Pydantic models: AgentDecision, MemoryExtractionResult, etc.
├── memory/
│   ├── __init__.py
│   ├── store.py               # Database operations (aiosqlite)
│   ├── session_memory.py      # Session-scoped summarization logic
│   ├── user_memory.py         # Cross-session user fact extraction
│   └── token_counter.py       # tiktoken-based token counting
├── tools/
│   ├── __init__.py
│   ├── base.py                # Tool base class + ToolRegistry
│   ├── mcp_server.py          # Built-in MCP server (exposes tools via stdio)
│   ├── mcp_client.py          # MCP client for consuming external tools
│   ├── files.py               # File read/write/list tools
│   ├── system.py              # Time, system info tools
│   ├── charting.py            # Chart generation tool (matplotlib)
│   ├── todo.py                # Todo list management tool
│   ├── web_fetch.py           # HTTP fetch tool
│   ├── calculator.py          # Calculator tool (migrated from plugin)
│   └── shell.py               # Shell command tool (migrated from plugin)
├── agents/
│   ├── __init__.py
│   ├── base.py                # Base agent class with ReAct loop
│   ├── main_agent.py          # Main orchestrating agent
│   ├── subagent.py            # Subagent runner (research, coding, analysis)
│   └── registry.py            # SubagentRegistry with AgentCards
├── a2a/
│   ├── __init__.py
│   ├── types.py               # A2A data types: AgentCard, A2ATask, A2AMessage
│   └── dispatcher.py          # Task dispatch and lifecycle management
├── providers/
│   ├── __init__.py
│   ├── base.py                # Provider ABC
│   ├── openai_compatible.py   # OpenAI-compatible provider with structured output
│   └── demo.py                # Demo provider for testing
├── logging/
│   ├── __init__.py
│   ├── formatter.py           # Box-drawing, color-coded log formatter
│   ├── categories.py          # Log category definitions (REASONING, TOOL_CALL, etc.)
│   └── setup.py               # Logging configuration and structlog setup
└── prompts/
    ├── __init__.py
    ├── system.py              # System prompt templates (ReAct workflow)
    ├── extraction.py          # User memory extraction prompt
    └── summarization.py       # Session summarization prompt

plugins/                       # Dynamic plugins (loaded at startup)
├── echo_plugin.py
├── calculator_plugin.py
├── shell_plugin.py
└── web_fetch_plugin.py

tests/
├── unit/
│   ├── test_schemas.py
│   ├── test_token_counter.py
│   ├── test_session_memory.py
│   ├── test_user_memory.py
│   ├── test_a2a_types.py
│   ├── test_a2a_dispatcher.py
│   ├── test_mcp_server.py
│   ├── test_mcp_client.py
│   ├── test_charting_tool.py
│   ├── test_todo_tool.py
│   ├── test_log_formatter.py
│   ├── test_prompts.py
│   └── test_agent_decision.py
├── integration/
│   ├── test_gateway.py
│   ├── test_runtime_loop.py
│   ├── test_memory_store.py
│   ├── test_multi_tenant.py
│   ├── test_subagent_delegation.py
│   └── test_mcp_integration.py
└── conftest.py                # Shared fixtures (temp DB, test users, mock provider)
```

**Structure Decision**: Single project layout, evolving the existing `src/openclaw_lite/` package. New subdirectories (`memory/`, `agents/`, `a2a/`, `logging/`, `prompts/`) organize the expanded functionality by domain. Tests split into `unit/` and `integration/` per constitution principle VIII.

## Complexity Tracking

> No constitution violations requiring justification. All dependencies are minimal and justified:

| Dependency | Justification |
|------------|---------------|
| `mcp` | Required by constitution principle III for MCP protocol compliance |
| `aiosqlite` | Required for async DB access in async FastAPI handlers |
| `tiktoken` | Required for accurate token counting (summarization threshold) |
| `structlog` | Required for correlation ID propagation (principle IV) |
| `matplotlib` | Required for charting tool (FR-013) |
| `pydantic` | Required for structured output schema enforcement (FR-009) |
