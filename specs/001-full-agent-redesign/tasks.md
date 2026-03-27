# Tasks: Full Agent Redesign

**Input**: Design documents from `/specs/001-full-agent-redesign/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — FR-016 and constitution principle VIII require unit and integration tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/openclaw_lite/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project restructuring, dependency installation, and new package scaffolding

- [x] T001 Update requirements.txt and pyproject.toml: add new dependencies (aiosqlite, tiktoken, structlog, matplotlib, pydantic, mcp, pytest-asyncio, httpx), remove chromadb (replaced by SQLite-based user_memories table)
- [x] T002 Create new package directories: src/openclaw_lite/memory/, src/openclaw_lite/agents/, src/openclaw_lite/a2a/, src/openclaw_lite/logging/, src/openclaw_lite/prompts/ — each with __init__.py
- [x] T003 [P] Create test directory structure: tests/unit/, tests/integration/ with __init__.py files
- [x] T004 [P] Create tests/conftest.py with shared fixtures: temp DB path, temp workspace, test user IDs, mock provider factory
- [x] T005 Update src/openclaw_lite/config.py to add new settings: CONTEXT_WINDOW (default 128000), SUBAGENT_TIMEOUT (default 60), RESPONSE_TIMEOUT (default 120), MCP_SERVERS (JSON config)

**Checkpoint**: Project compiles, new packages importable, pytest discovers test directories

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can begin

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Define Pydantic schemas in src/openclaw_lite/schemas.py: AgentDecision (type: respond/tool/delegate, reasoning, content, tool_name, tool_input, delegation_target, delegation_prompt, tasks list), MemoryExtractionResult (facts: list of key/value/confidence), SummarizationResult (summary, key_topics), ChatMessage, ToolSpec, MemoryContext
- [x] T007 [P] Implement token counter in src/openclaw_lite/memory/token_counter.py: TokenCounter class wrapping tiktoken with encode/count_tokens/count_messages methods, model-aware encoding selection
- [x] T008 [P] Implement log category definitions in src/openclaw_lite/logging/categories.py: LogCategory enum (REASONING, TOOL_CALL, TASK_UPDATE, FINAL_ANSWER, MEMORY, SYSTEM) with box-drawing styles and header emojis per category
- [x] T009 [P] Implement box-drawing log formatter in src/openclaw_lite/logging/formatter.py: custom structlog processor that wraps log messages in category-specific box-drawn sections with timestamps, correlation IDs, module names, and color-coded levels
- [x] T010 Implement logging setup in src/openclaw_lite/logging/setup.py: configure_logging() function that initializes structlog with context vars for correlation IDs, registers custom formatter, sets up sensitive data filter, integrates with Python stdlib logging
- [x] T011 [P] Write unit test for token counter in tests/unit/test_token_counter.py: test count_tokens with known strings, test count_messages with message list, test model encoding selection
- [x] T012 [P] Write unit test for schemas in tests/unit/test_schemas.py: test AgentDecision validation for respond/tool/delegate types, test MemoryExtractionResult parsing, test SummarizationResult parsing, test invalid inputs rejected
- [x] T013 [P] Write unit test for log formatter in tests/unit/test_log_formatter.py: test box-drawing output format, test each log category produces distinct visual output, test correlation ID inclusion, test sensitive data filtering

**Checkpoint**: Foundation ready — schemas validate, token counting works, logging produces formatted output. User story implementation can now begin.

---

## Phase 3: User Story 1 — Multi-User Chat Sessions (Priority: P1)

**Goal**: Multiple users with isolated sessions and conversation history. Full CRUD API for users, sessions, messages.

**Independent Test**: Create two users, each with two sessions. Send messages in all four concurrently. Verify isolation.

### Tests for User Story 1

- [x] T014 [P] [US1] Write unit test for memory store in tests/unit/test_memory_store.py: test create_user, create_session, add_message, get_messages, delete_session (cascade), test user_id isolation on all queries
- [x] T015 [P] [US1] Write integration test for gateway in tests/integration/test_gateway.py: test all HTTP endpoints (POST /users, POST /sessions, POST /messages, GET /messages, DELETE /sessions, GET /health), test X-User-Id ownership enforcement, test 403 on cross-user access

### Implementation for User Story 1

- [x] T016 [US1] Implement async database store in src/openclaw_lite/memory/store.py: MemoryStore class with aiosqlite, schema creation (users, sessions, messages tables per data-model.md), methods: create_user (also creates {workspace}/{user_id}/ directory), create_session, list_sessions, delete_session (cascade), add_message, get_messages (with limit/offset), get_session_token_count. All queries scoped by user_id. Per-user workspace directories created under {OPENCLAW_LITE_WORKSPACE}/{user_id}/.
- [x] T017 [US1] Refactor src/openclaw_lite/gateway.py: replace single /message endpoint with full v1 API per contracts/http-api.md — POST /users, GET/POST/DELETE /users/{user_id}/sessions, POST /GET /users/{user_id}/sessions/{session_id}/messages, GET /health. Add X-User-Id header extraction and ownership validation middleware. Add error response format (code + message JSON).
- [x] T018 [US1] Refactor src/openclaw_lite/runtime.py: update AgentRuntime.handle_message() to accept user_id and session_id parameters, pass them through to memory store, add 120-second timeout wrapper via asyncio.wait_for
- [x] T019 [US1] Update src/openclaw_lite/app_factory.py: replace old build_runtime() with async build_runtime() that initializes new MemoryStore (aiosqlite), wires gateway routes, configures logging via configure_logging()
- [x] T020 [US1] Update src/openclaw_lite/main.py: update serve command to use new async app factory, update chat command to accept --user-id and --session-id arguments
- [x] T021 [US1] Write integration test for multi-tenant isolation in tests/integration/test_multi_tenant.py: test two users with two sessions each sending concurrent messages (asyncio.gather), verify zero data leakage across users and sessions

**Checkpoint**: Multi-user API functional. Two users can chat in isolated sessions. All US1 acceptance scenarios pass.

---

## Phase 4: User Story 2 — Tiered Memory Management (Priority: P2)

**Goal**: Session-scoped summaries triggered by token threshold + cross-session user fact extraction via LLM.

**Independent Test**: Exceed token threshold in a session and verify summary. Start new session and verify user facts recalled but not conversation details.

### Tests for User Story 2

- [x] T022 [P] [US2] Write unit test for session memory in tests/unit/test_session_memory.py: test summarization trigger at 75% threshold, test no trigger below threshold, test summary stored correctly, test exact-threshold boundary (no premature trigger)
- [x] T023 [P] [US2] Write unit test for user memory extraction in tests/unit/test_user_memory.py: test LLM extraction result parsing, test upsert-on-conflict for duplicate keys, test confidence scoring, test only personal facts stored (mock LLM)

### Implementation for User Story 2

- [x] T024 [US2] Add session_memories and user_memories tables to src/openclaw_lite/memory/store.py: schema per data-model.md, methods: add_session_memory, get_session_memories, add_or_update_user_memory, get_user_memories, delete_user_memory. UNIQUE(user_id, key) constraint on user_memories.
- [x] T025 [US2] Implement session memory manager in src/openclaw_lite/memory/session_memory.py: SessionMemoryManager class that checks token count against threshold (75% of configured context window), triggers LLM-based summarization of oldest messages when exceeded, stores SessionMemory record, returns compressed context (summaries + recent messages)
- [x] T026 [US2] Implement summarization prompt in src/openclaw_lite/prompts/summarization.py: prompt template that instructs LLM to produce SummarizationResult JSON from a list of messages, emphasizing compression and key topic extraction
- [x] T027 [US2] Implement user memory extractor in src/openclaw_lite/memory/user_memory.py: UserMemoryExtractor class with extract_after_interaction() method that makes a dedicated LLM call using the extraction prompt, parses MemoryExtractionResult, upserts facts into user_memories table
- [x] T028 [US2] Implement extraction prompt in src/openclaw_lite/prompts/extraction.py: prompt template that instructs LLM to extract ONLY key personal facts (name, role, location, preferences) from a user+assistant exchange, produce MemoryExtractionResult JSON, ignore general conversational content
- [x] T029 [US2] Integrate memory into runtime: update src/openclaw_lite/runtime.py handle_message() to call SessionMemoryManager before building context, call UserMemoryExtractor after each interaction, include user memories in provider context
- [x] T030 [US2] Add user memory API endpoints to src/openclaw_lite/gateway.py: GET /users/{user_id}/memories, DELETE /users/{user_id}/memories/{key} per contracts/http-api.md
- [x] T031 [US2] Write integration test for memory in tests/integration/test_memory_store.py: test full flow — send messages until threshold exceeded, verify session summary created, start new session, verify user facts available but conversation content not present

**Checkpoint**: Memory system operational. Summarization triggers correctly. Cross-session user facts persist. US2 acceptance scenarios pass.

---

## Phase 5: User Story 3 — MCP Tool Protocol (Priority: P3)

**Goal**: All tools exposed via MCP (stdio transport). Agent consumes tools as MCP client. External MCP server connectivity.

**Independent Test**: Register a tool via MCP, invoke it, verify MCP schema conformance. Connect to external MCP server.

### Tests for User Story 3

- [x] T032 [P] [US3] Write unit test for MCP server in tests/unit/test_mcp_server.py: test tool registration produces valid MCP tool schema, test tool invocation via MCP protocol returns valid result, test error handling for failed tools
- [x] T033 [P] [US3] Write unit test for MCP client in tests/unit/test_mcp_client.py: test connecting to a mock MCP server via stdio, test tool discovery (list_tools), test tool invocation and result parsing

### Implementation for User Story 3

- [x] T034 [US3] Implement built-in MCP server in src/openclaw_lite/tools/mcp_server.py: MCPToolServer class that wraps ToolRegistry, exposes all registered tools via mcp.server.Server with stdio_server() transport, maps Tool.input_schema to MCP tool definitions, handles tool invocations by delegating to Tool.run()
- [x] T035 [US3] Implement MCP client in src/openclaw_lite/tools/mcp_client.py: MCPToolClient class that connects to external MCP servers via stdio_client(), discovers tools (list_tools), invokes tools (call_tool), returns results as structured data. Manage child process lifecycle.
- [x] T036 [US3] Refactor src/openclaw_lite/tools/base.py: change Tool.run() signature to async def run() (all I/O must be async per constitution). Update ToolRegistry to support both local tools and MCP-discovered external tools. Add get_all_tool_specs() that merges local + external tool definitions. ToolContext.workspace MUST resolve to {base_workspace}/{user_id}/ — tools MUST NOT access paths outside this directory.
- [x] T037 [US3] Migrate existing tools to MCP-compatible async format: update src/openclaw_lite/tools/files.py, src/openclaw_lite/tools/system.py, src/openclaw_lite/tools/web_fetch.py (move from plugins/) — convert all run() methods to async def run(), ensure input_schema conforms to MCP tool call/result format
- [x] T038 [US3] Update src/openclaw_lite/runtime.py: replace direct tool.run() calls with MCP client tool invocation. Tool results now flow through MCP protocol. Add MCP schema validation on every tool call and result.
- [x] T039 [US3] Update src/openclaw_lite/config.py and app_factory.py: add MCP_SERVERS config for external server definitions (list of command+args), initialize MCPToolClient connections at startup, register external tools in ToolRegistry
- [x] T040 [US3] Write integration test for MCP in tests/integration/test_mcp_integration.py: test full roundtrip — register tool, invoke via MCP protocol, verify schema conformance. Test external MCP server connection with a test server subprocess.

**Checkpoint**: All tools available via MCP. External MCP servers connectable. Schema validation on all tool calls. US3 acceptance scenarios pass.

---

## Phase 6: User Story 4 — Subagent Delegation via A2A (Priority: P4)

**Goal**: Main agent can delegate to research/coding/analysis subagents via A2A protocol. Concurrent execution with timeout.

**Independent Test**: Send request requiring two subtasks. Verify subagents complete and main agent synthesizes results.

### Tests for User Story 4

- [x] T041 [P] [US4] Write unit test for A2A types in tests/unit/test_a2a_types.py: test AgentCard creation, test A2ATask status transitions (submitted→working→completed, submitted→working→failed), test A2AMessage serialization
- [x] T042 [P] [US4] Write unit test for A2A dispatcher in tests/unit/test_a2a_dispatcher.py: test task dispatch to correct subagent type, test timeout enforcement, test concurrent task execution, test failure handling

### Implementation for User Story 4

- [x] T043 [US4] Implement A2A data types in src/openclaw_lite/a2a/types.py: AgentCard dataclass (agent_type, name, description, skills, tool_names), A2ATask dataclass (task_id, status enum, agent_type, input_msg, output, artifacts, created_at, timeout_s), A2AMessage dataclass (role, parts), TextPart/DataPart/FilePart
- [x] T044 [US4] Implement subagent registry in src/openclaw_lite/agents/registry.py: SubagentRegistry class with register_agent(AgentCard), get_agent(agent_type), list_agents(). Pre-register three default agents: research (web_fetch tools), coding (file read/write/list, shell tools), analysis (charting, calculator tools)
- [x] T045 [US4] Extend base agent class in src/openclaw_lite/agents/base.py: add subagent-specific run(prompt, tools, provider) → A2ATask method that reuses the ReAct loop from T052b with a subagent-scoped system prompt and tool subset.
- [x] T046 [US4] Implement subagent runner in src/openclaw_lite/agents/subagent.py: SubagentRunner class that instantiates BaseAgent with the correct tool subset and system prompt based on agent_type. Handles timeout via asyncio.wait_for(). Returns completed/failed A2ATask.
- [x] T047 [US4] Implement A2A dispatcher in src/openclaw_lite/a2a/dispatcher.py: A2ADispatcher class with dispatch(task: A2ATask) → A2ATask method. Routes to correct SubagentRunner, manages task lifecycle (submitted→working→completed/failed), supports concurrent dispatch via asyncio.gather for independent tasks.
- [x] T048 [US4] Implement main agent in src/openclaw_lite/agents/main_agent.py: MainAgent class extending BaseAgent. Handles "delegate" decision type by creating A2ATask, dispatching via A2ADispatcher, incorporating subagent output into scratchpad, continuing ReAct loop.
- [x] T049 [US4] Integrate delegation into runtime: update src/openclaw_lite/runtime.py to use MainAgent instead of direct provider calls. Wire A2ADispatcher and SubagentRegistry into app_factory.py initialization.
- [x] T050 [US4] Write integration test for subagent delegation in tests/integration/test_subagent_delegation.py: test end-to-end delegation with mock provider, test concurrent subagent execution, test timeout handling, test failure recovery

**Checkpoint**: Main agent delegates to subagents. Research/coding/analysis subagents operational. A2A lifecycle managed. US4 acceptance scenarios pass.

---

## Phase 7: User Story 5 — Structured Output and ReAct Prompting (Priority: P5)

**Goal**: Enforced structured output on every LLM call. ReAct workflow with task checklist and original-message re-read.

**Independent Test**: Send message triggering tool use. Verify all LLM responses validate against schema. Verify checklist and re-read behavior.

### Tests for User Story 5

- [x] T051 [P] [US5] Write unit test for agent decision validation in tests/unit/test_agent_decision.py: test schema enforcement rejects invalid JSON, test retry logic on malformed response (up to 2 retries), test fallback error response after retries exhausted
- [x] T052 [P] [US5] Write unit test for prompts in tests/unit/test_prompts.py: test system prompt includes ReAct workflow instructions, test prompt includes task checklist placeholder, test prompt includes original-message re-read instruction

### Implementation for User Story 5

- [x] T052b [US5] Create base agent class in src/openclaw_lite/agents/base.py: BaseAgent class with ReAct loop (reason → plan → act → observe), structured output validation via Pydantic on every LLM call, task checklist tracking, original-message re-read before final response. This is the foundation that both MainAgent and subagents extend.
- [x] T053 [US5] Implement system prompt template in src/openclaw_lite/prompts/system.py (used by BaseAgent from T052b): ReAct workflow prompt with sections for: reasoning step, tool/delegation selection, task checklist tracking, original message re-read before final response. Include structured output format instructions referencing AgentDecision schema.
- [x] T054 [US5] Update src/openclaw_lite/providers/openai_compatible.py: add response_format parameter with json_schema type on every API call. Pass AgentDecision/MemoryExtractionResult/SummarizationResult schemas as appropriate. Add retry logic: on JSON parse failure, retry up to 2 times with corrective system message, then return error AgentDecision.
- [x] T055 [US5] Update src/openclaw_lite/providers/demo.py: update DemoProvider to return valid AgentDecision JSON matching the Pydantic schema for all test patterns. Add delegation pattern support.
- [x] T056 [US5] Update agent loop in src/openclaw_lite/agents/base.py: after each LLM call, validate response against AgentDecision schema via Pydantic. On final response, inject original user message into prompt for re-read verification. Track task checklist across loop iterations — include completed/pending status in each LLM call context.
- [x] T057 [US5] Write integration test for structured output in tests/integration/test_runtime_loop.py: test full agent loop with mock provider, verify every LLM call produces valid AgentDecision, verify task checklist progression, verify original message re-read on final response

**Checkpoint**: All LLM calls produce validated structured output. ReAct workflow enforced. Retry logic operational. US5 acceptance scenarios pass.

---

## Phase 8: User Story 6 — Beautiful Structured Logging (Priority: P6)

**Goal**: All agent operations produce visually formatted, category-specific log output with correlation IDs.

**Independent Test**: Process a message and verify log output has distinct visual sections for reasoning, tool calls, task updates, final answer.

### Tests for User Story 6

- [x] T058 [P] [US6] Write unit test for log categories in tests/unit/test_log_formatter.py (extend T013): test each category (REASONING, TOOL_CALL, TASK_UPDATE, FINAL_ANSWER, MEMORY, SYSTEM) produces correctly formatted box-drawn output with category-specific emoji headers

### Implementation for User Story 6

- [x] T059 [US6] Add structured log calls throughout src/openclaw_lite/agents/base.py: log REASONING category when agent produces chain-of-thought, log TOOL_CALL with tool name/input/output/duration, log TASK_UPDATE when checklist changes, log FINAL_ANSWER when agent responds
- [x] T060 [US6] Add structured log calls to src/openclaw_lite/memory/session_memory.py and src/openclaw_lite/memory/user_memory.py: log MEMORY category for summarization triggers, summary creation, user fact extraction/upsert
- [x] T061 [US6] Add structured log calls to src/openclaw_lite/a2a/dispatcher.py: log SYSTEM category for subagent dispatch, status transitions, timeout events
- [x] T062 [US6] Add correlation ID generation in src/openclaw_lite/gateway.py: generate UUID correlation_id per request, bind to structlog context vars, pass through to runtime and all downstream components. Return correlation_id in API response.
- [x] T063 [US6] Verify log output end-to-end: manually test (or add to tests/integration/test_runtime_loop.py) that a single interaction produces visually distinct log sections with shared correlation ID

**Checkpoint**: All log output is visually formatted with box-drawing. Each category visually distinct. Correlation IDs propagate. US6 acceptance scenarios pass.

---

## Phase 9: User Story 7 — New Agent Tools (Priority: P7)

**Goal**: Charting tool (matplotlib, PNG output) and todo list tool (markdown checkboxes). Both exposed via MCP.

**Independent Test**: Create a bar chart and verify PNG saved. Create/update a todo list and verify file content.

### Tests for User Story 7

- [x] T064 [P] [US7] Write unit test for charting tool in tests/unit/test_charting_tool.py: test bar/line/pie chart generation produces valid PNG file, test data validation (empty data, missing labels), test file saved to correct workspace path
- [x] T065 [P] [US7] Write unit test for todo tool in tests/unit/test_todo_tool.py: test create todo file with markdown checkboxes, test read existing file, test mark item as done (checkbox toggle), test add item to existing list

### Implementation for User Story 7

- [x] T066 [US7] Implement charting tool in src/openclaw_lite/tools/charting.py: ChartingTool class with input_schema accepting data (dict), chart_type (bar/line/pie/scatter), title, filename. Uses matplotlib to generate chart and save as PNG to user workspace. Returns file path confirmation.
- [x] T067 [US7] Implement todo tool in src/openclaw_lite/tools/todo.py: TodoTool class with input_schema accepting action (create/read/update/add), filename, items (for create), item_index + done status (for update), new_item (for add). Manages markdown checkbox files (- [ ] / - [x] format) in user workspace.
- [x] T068 [US7] Register new tools in src/openclaw_lite/app_factory.py: add ChartingTool and TodoTool to ToolRegistry, ensure they appear in MCP tool listing
- [x] T069 [US7] Verify tools work end-to-end: add test cases to tests/integration/test_runtime_loop.py that trigger charting and todo tools via agent interaction with mock provider

**Checkpoint**: Both tools operational, produce correct output files, accessible via MCP. US7 acceptance scenarios pass.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Code cleanup, plugin migration, encapsulation fixes, final validation

- [ ] T070 [P] Remove old code: delete src/openclaw_lite/extraction.py (replaced by memory/user_memory.py), delete src/openclaw_lite/knowledge_store.py (replaced by memory/store.py), delete src/openclaw_lite/logging_utils.py (replaced by logging/), delete src/openclaw_lite/scheduler.py (superseded by task management in agents)
- [ ] T071 [P] Migrate plugins to built-in tools: move plugins/web_fetch_plugin.py logic into src/openclaw_lite/tools/web_fetch.py, move plugins/calculator_plugin.py into src/openclaw_lite/tools/calculator.py, move plugins/shell_plugin.py into src/openclaw_lite/tools/shell.py, remove plugins/echo_plugin.py (trivial; not needed as a tool). Update plugin_loader.py to support both legacy plugins/ and new tools/ registration.
- [ ] T072 [P] Clean up __pycache__ directories: add **/__pycache__/ to .gitignore, remove all tracked .pyc files from git
- [ ] T073 Run static analysis: fix all code warnings, ensure no private method access from outside classes, verify type annotations on all public interfaces (FR-015)
- [ ] T074 Update CLAUDE.md: document new CLI arguments (--user-id, --session-id), new environment variables (CONTEXT_WINDOW, SUBAGENT_TIMEOUT, RESPONSE_TIMEOUT, MCP_SERVERS), new API endpoints
- [ ] T075 Run full test suite: execute pytest -q across all tests/unit/ and tests/integration/, verify all pass, fix any failures
- [ ] T076 Run quickstart validation: follow specs/001-full-agent-redesign/quickstart.md end-to-end, verify all commands work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — foundational for all other stories
- **US2 (Phase 4)**: Depends on US1 (needs multi-tenant store)
- **US3 (Phase 5)**: Depends on US1 (needs tool registry with user context)
- **US4 (Phase 6)**: Depends on US3 (subagents need MCP tools) and US5 (structured output)
- **US5 (Phase 7)**: Depends on US1 (needs runtime loop)
- **US6 (Phase 8)**: Can start after Phase 2 (logging is cross-cutting) but full value after US1-US5
- **US7 (Phase 9)**: Depends on US3 (tools need MCP registration)
- **Polish (Phase 10)**: Depends on all user stories complete

### Recommended Execution Order

```
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 7 (US5) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 8 (US6) → Phase 9 (US7) → Phase 10
```

Note: US5 (structured output) is moved before US2-US4 because the ReAct loop and schema enforcement should be in place before building memory and MCP on top of it.

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel. Across phases:

- US6 (logging) can be partially started in parallel with US2-US5 since it's cross-cutting
- US7 (new tools) can be partially started once US3 (MCP) is in progress
- All unit tests within a phase are parallelizable with each other

### Within Each User Story

- Tests MUST be written first and FAIL before implementation
- Store/model tasks before service/logic tasks
- Core implementation before integration with other stories
- Story complete before moving to next priority

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (multi-tenant)
4. **STOP and VALIDATE**: Two users can chat in isolated sessions
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Multi-tenant chat sessions (MVP!)
3. Add US5 → Structured output + ReAct loop
4. Add US2 → Tiered memory management
5. Add US3 → MCP tool protocol
6. Add US4 → Subagent delegation
7. Add US6 → Beautiful logging
8. Add US7 → New tools (charting, todo)
9. Polish → Cleanup, validation, documentation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
