# Research: Full Agent Redesign

**Date**: 2026-03-26
**Branch**: `001-full-agent-redesign`

## R1: MCP Python SDK for Stdio Transport

**Decision**: Use the `mcp` Python SDK (official Anthropic MCP SDK) for both server and client roles over stdio transport.

**Rationale**: The official `mcp` package provides first-class support for stdio transport, server/client abstractions, and tool schema definitions that conform to the MCP specification. It is actively maintained and is the de facto standard for Python MCP implementations.

**Alternatives considered**:
- Custom MCP implementation from scratch — rejected because the protocol has non-trivial JSON-RPC framing and capability negotiation that the SDK handles correctly.
- `fastmcp` — rejected because it adds unnecessary abstraction on top of the official SDK and is less stable.

**Key details**:
- Package: `mcp` (PyPI)
- Server: Expose tools via `mcp.server.Server` with `stdio_server()` transport
- Client: Connect to external MCP servers via `mcp.client.stdio.stdio_client()`
- Tool schemas map directly to JSON Schema — compatible with existing `ToolSpec` definitions
- Built-in tools will be wrapped in an in-process MCP server; the agent loop acts as an MCP client

## R2: A2A Protocol for In-Process Subagents

**Decision**: Implement A2A protocol semantics (agent cards, task lifecycle, message parts) in-process using Python async. No HTTP transport needed for this iteration.

**Rationale**: The A2A specification defines agent cards (capabilities), task objects (with status lifecycle: submitted → working → completed/failed), and structured message exchange. For in-process subagents, we implement the data model and lifecycle without the HTTP transport layer. This keeps the architecture aligned with A2A so that future network-based delegation requires only adding the transport.

**Alternatives considered**:
- Full A2A HTTP server/client — rejected because subagents are in-process per spec assumptions. Would add unnecessary latency and complexity.
- Custom ad-hoc delegation — rejected because it would diverge from A2A and require rewriting when external agents are added later.

**Key details**:
- `AgentCard` dataclass: name, description, skills, tools available
- `A2ATask` dataclass: id, status (submitted/working/completed/failed), messages, artifacts
- `A2AMessage`: role (user/agent), parts list (TextPart, DataPart, FilePart)
- `SubagentRegistry`: maps specialization types to agent cards
- Three default subagent types: research, coding, analysis — each with distinct tool sets and system prompts
- Parent agent creates A2ATask, dispatches to subagent, polls/awaits completion
- Timeout enforcement per task (configurable, default 60s per subagent, 120s total)

## R3: Structured Output Enforcement

**Decision**: Use OpenAI-compatible `response_format` with `json_schema` type for all LLM calls. Define Pydantic models for all output schemas and validate every response.

**Rationale**: OpenAI-compatible APIs support `response_format: { type: "json_schema", json_schema: {...} }` which forces the model to produce valid JSON matching the schema. Combined with Pydantic validation on the client side, this provides double enforcement. This is the industry standard approach.

**Alternatives considered**:
- Prompt-only enforcement (ask model to output JSON) — rejected because it's unreliable; models frequently produce invalid JSON without schema enforcement.
- Function calling for structured output — rejected because function calling is semantically for tool use, not for structuring all agent responses.

**Key details**:
- `AgentDecision` Pydantic model: type (respond/tool/delegate), content, reasoning, tool_name, tool_input, tasks, delegation_target
- `MemoryExtractionResult` Pydantic model: facts list with key/value/confidence
- `SummarizationResult` Pydantic model: summary text, key topics
- All schemas registered with the provider and passed as `response_format` on every call
- On parse failure: retry up to 2 times with corrective system message, then error fallback

## R4: Token Counting and Summarization Strategy

**Decision**: Use `tiktoken` for token counting with model-appropriate encoding. Trigger summarization at 75% of the configured context window. Use an LLM call to generate summaries.

**Rationale**: `tiktoken` is the standard token counting library for OpenAI-compatible models. The 75% threshold leaves room for the system prompt, tool definitions, memory context, and the user's new message. LLM-based summarization produces higher quality summaries than extractive methods.

**Alternatives considered**:
- Character-based estimation — rejected because it's inaccurate across models with different tokenizers.
- Fixed message count cutoff — rejected because message length varies wildly; a token-based approach is more precise.
- 50% threshold — rejected because it's too aggressive and would trigger summarization too frequently.

**Key details**:
- Default context window: configurable via `OPENCLAW_LITE_CONTEXT_WINDOW` (default: 128000 for GPT-4o)
- Summarization threshold: 75% = 96000 tokens by default
- On threshold breach: summarize oldest messages into a compact summary, keep recent N messages raw
- Session summaries stored in `session_memories` table, scoped to session_id
- Cross-session user fact extraction runs as a separate async LLM call after each interaction

## R5: Multi-Tenant Database Schema Design

**Decision**: Extend SQLite schema with explicit `user_id` foreign keys on all tables. Use `aiosqlite` for async database access. Design schema to be PostgreSQL-migration-ready.

**Rationale**: The existing schema uses `session_id` but has no user concept. Adding `user_id` as a first-class column with foreign key constraints enables multi-tenancy. `aiosqlite` provides async SQLite access needed for the FastAPI async handlers. Using standard SQL (no SQLite-specific extensions) ensures PostgreSQL compatibility.

**Alternatives considered**:
- SQLAlchemy ORM — rejected per constitution principle II (framework-free). Direct SQL with `aiosqlite` is simpler and more auditable.
- Separate database per user — rejected because it complicates connection management and doesn't scale well with many users.

**Key details**:
- Tables: `users`, `sessions`, `messages`, `session_memories`, `user_memories`, `tasks`
- All tables have `user_id` column (except `users` itself)
- `sessions` table: user_id, session_id (UUID), created_at, title
- `messages` table: session_id FK, role, content, timestamp, token_count
- `session_memories` table: session_id FK, summary, created_at
- `user_memories` table: user_id FK, key, value, confidence, updated_at (deduplication by key)
- Cascade deletes: deleting a session removes its messages and session_memories

## R6: Logging Architecture

**Decision**: Use Python's built-in `logging` module with a custom `Formatter` that produces box-drawn, color-coded output. Use `structlog` for structured field attachment (correlation IDs, timing).

**Rationale**: The built-in logging module is universally supported and integrates with all Python libraries. A custom formatter can produce the visually distinct output required (box characters, section headers) without adding framework dependencies. `structlog` is lightweight and adds structured context (correlation IDs) cleanly.

**Alternatives considered**:
- `loguru` — rejected because it replaces the standard logging infrastructure and doesn't integrate well with library logging.
- Pure `logging` without `structlog` — rejected because manually threading correlation IDs through every call is error-prone. `structlog`'s context vars handle this cleanly.

**Key details**:
- Categories: REASONING, TOOL_CALL, TASK_UPDATE, FINAL_ANSWER, MEMORY, SYSTEM
- Each category gets a distinct box style and header emoji
- Correlation ID generated per request, bound to `structlog` context vars
- Log format: `[timestamp] [level] [correlation_id] [module] message`
- Visual separators between log categories using box-drawing characters (━, ┃, ┏, ┗)
- Sensitive data filtering via custom log filter

## R7: Charting and Todo Tools

**Decision**: Use `matplotlib` for charting (PNG output). Todo tool manages markdown checkbox files.

**Rationale**: `matplotlib` is the most widely used Python charting library, produces high-quality static images, and has no system dependencies beyond Python. Markdown checkboxes are a universally understood format for todo lists.

**Alternatives considered**:
- `plotly` — rejected because it's primarily for interactive/HTML charts; PNG export requires `kaleido` which adds binary dependencies.
- `seaborn` — considered as an addition on top of matplotlib for statistical charts, but unnecessary for the initial tool set.
- JSON/YAML for todo format — rejected because markdown checkboxes are more human-readable and the user explicitly requested file-based todos.

**Key details**:
- Charting tool: accepts data dict + chart type (bar, line, pie, scatter) + title → saves PNG to workspace
- Todo tool: CRUD operations on markdown files with `- [ ]` / `- [x]` format
- Both tools sandboxed to user's workspace directory
- Both exposed as MCP tools via the built-in MCP server
