# Feature Specification: Full Agent Redesign

**Feature Branch**: `001-full-agent-redesign`
**Created**: 2026-03-26
**Status**: Draft
**Input**: Refactor and redesign the entire application to be multi-tenant with tiered memory, MCP tool protocol, A2A subagent delegation, structured output enforcement, beautiful logging, and new agent tools.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-User Chat Sessions (Priority: P1)

Multiple users interact with the agent backend concurrently, each maintaining independent chat sessions with isolated conversation history. A user can create new chat sessions, switch between existing ones, and continue prior conversations without any data leaking between users or sessions.

**Why this priority**: Multi-tenancy is the foundational capability that every other feature depends on. Without user and session isolation, memory, tools, and subagents cannot be scoped correctly.

**Independent Test**: Create two users, each with two chat sessions. Send messages in all four sessions concurrently. Verify each session only sees its own history and no cross-contamination occurs.

**Acceptance Scenarios**:

1. **Given** two registered users, **When** both send messages simultaneously to separate sessions, **Then** each user's session contains only their own messages and the agent's responses to them.
2. **Given** a user with an existing session containing 10 messages, **When** the user creates a new session and sends a message, **Then** the new session starts with no prior history and the old session remains unchanged.
3. **Given** a user sends a message to session A, **When** a different user queries session A's ID, **Then** the system rejects the request with an authorization error.

---

### User Story 2 - Tiered Memory Management (Priority: P2)

The agent maintains two tiers of long-term memory that work together to provide continuity within and across sessions. Session-scoped summaries capture the context of individual conversations, while cross-session user memory retains only key user facts (name, role, preferences, location). Summarization triggers automatically when the conversation token count exceeds a configurable threshold (default: 75% of the model's context window).

**Why this priority**: Memory is the second most foundational capability. Without proper memory scoping, the agent cannot provide personalized or context-aware responses as conversations grow.

**Independent Test**: Start a session, send enough messages to exceed the token threshold, and verify a summary is generated. Start a new session and confirm the agent recalls key user facts but not prior session details.

**Acceptance Scenarios**:

1. **Given** a session with messages totaling more than 75% of the context window, **When** the next message is sent, **Then** the system generates a session summary and compresses the context before sending to the provider.
2. **Given** a user who stated "My name is Alice and I work at Acme Corp" in a previous session, **When** the user starts a new session and asks "What do you know about me?", **Then** the agent responds with the user's name and workplace.
3. **Given** a user who asked "What is the capital of France?" in session A, **When** the user starts session B and asks "What did we talk about last time?", **Then** the agent does NOT reproduce the France question — only key personal facts persist across sessions.
4. **Given** a session below the token threshold, **When** messages are exchanged, **Then** no summarization is triggered and the full conversation history is sent to the provider.

---

### User Story 3 - MCP Tool Protocol (Priority: P3)

The agent exposes its tools via the Model Context Protocol (MCP) and can also consume tools from external MCP servers. Tool definitions, invocations, and results follow the MCP specification so that any MCP-compatible client or server can interoperate with the system.

**Why this priority**: MCP standardizes the tool interface, making the system interoperable with the broader agent ecosystem. It replaces the current custom tool protocol.

**Independent Test**: Register a tool via MCP, invoke it from the agent loop, and verify the request/response conforms to the MCP specification. Connect to an external MCP server and call one of its tools.

**Acceptance Scenarios**:

1. **Given** a tool registered via MCP, **When** the agent decides to call it, **Then** the tool invocation message conforms to the MCP tool call schema and the result conforms to the MCP tool result schema.
2. **Given** an external MCP server advertising a "weather" tool, **When** the agent is configured to connect to that server, **Then** the agent can discover and invoke the weather tool and incorporate its result into the response.
3. **Given** a tool call that returns an error, **When** the agent receives the error result, **Then** it logs the error, communicates the failure to the user gracefully, and does not crash.

---

### User Story 4 - Subagent Delegation via A2A (Priority: P4)

The main agent can delegate subtasks to specialized subagents using the Agent-to-Agent (A2A) protocol. The parent agent creates tasks, assigns them to child agents, monitors progress, and incorporates subagent results into its final response. Each subagent operates with its own tool set and structured output enforcement.

**Why this priority**: Subagent delegation enables the system to handle complex multi-step tasks by distributing work. It depends on MCP (for tools) and memory (for context passing) being in place.

**Independent Test**: Send a complex request that the main agent decomposes into two subtasks. Verify the main agent spawns subagents, each subagent completes its task, and the main agent synthesizes the results.

**Acceptance Scenarios**:

1. **Given** a user request requiring research and summarization, **When** the main agent processes it, **Then** it creates an A2A task for a research subagent, waits for the result, and incorporates it into the final response.
2. **Given** a subagent that fails its task, **When** the parent agent receives the failure notification, **Then** it retries with a different approach or reports the partial failure to the user.
3. **Given** two independent subtasks, **When** the main agent delegates them, **Then** both subagents can execute concurrently and the parent waits for both before responding.

---

### User Story 5 - Structured Output and ReAct Prompting (Priority: P5)

Every interaction with the LLM — by the main agent or any subagent — enforces a structured output schema. The system prompt follows a ReAct-style workflow: the agent reasons about the request, plans steps, executes tools, checks progress against a task checklist, re-reads the original user message before the final response, and produces a structured decision object. No free-form text is sent to or expected from the LLM outside of the defined schemas.

**Why this priority**: Structured outputs eliminate parsing ambiguity and make the system deterministic. This is important but depends on the core loop and provider being stable first.

**Independent Test**: Send a message that triggers tool use. Verify every LLM call (reasoning, tool selection, final answer) returns valid structured output matching the defined schema. Verify the agent re-reads the original message before responding.

**Acceptance Scenarios**:

1. **Given** any message to the agent, **When** the LLM responds, **Then** the response is valid against the AgentDecision schema with no unparseable content.
2. **Given** a multi-step request, **When** the agent processes it, **Then** each step's LLM call includes the task checklist showing completed and remaining items.
3. **Given** a request with three sub-questions, **When** the agent prepares its final response, **Then** it re-reads the original user message and verifies all three questions are addressed before sending.

---

### User Story 6 - Beautiful Structured Logging (Priority: P6)

All agent operations produce visually formatted, structured log output. Each log category (reasoning, tool calls, task progress, final answers) uses distinct visual formatting with box-drawing characters, color-coded levels, and clear separation between entries. Logs include correlation IDs to trace a single user interaction across all components.

**Why this priority**: Observability is critical for debugging and operating the system, but it is a cross-cutting concern that can be layered on after core functionality works.

**Independent Test**: Send a message that triggers reasoning, a tool call, and a final answer. Inspect the log output and verify each phase is visually distinct, includes timestamps and correlation IDs, and is easy to scan.

**Acceptance Scenarios**:

1. **Given** an agent processing a message, **When** the reasoning step executes, **Then** the log output shows the reasoning in a visually boxed section with a distinct header.
2. **Given** a tool call, **When** it executes, **Then** the log shows the tool name, input, output, and duration in a formatted block with a tool-specific visual marker.
3. **Given** a multi-step interaction, **When** all steps complete, **Then** every log entry for that interaction shares the same correlation ID and log entries from different interactions are visually separated.
4. **Given** a task checklist update, **When** the agent completes a task, **Then** the log shows the checklist with completed items checked off.

---

### User Story 7 - New Agent Tools (Priority: P7)

The agent has access to additional tools: a charting tool that generates visualizations and saves them as image files, and a todo-list tool that writes and manages task lists in files. Both tools follow the MCP tool specification and are available to the main agent and subagents.

**Why this priority**: Additional tools expand the agent's capabilities but are additive features that do not block core functionality.

**Independent Test**: Ask the agent to create a bar chart from sample data and verify an image file is saved. Ask the agent to create a todo list and verify a file is written with the correct format.

**Acceptance Scenarios**:

1. **Given** a user request "Create a bar chart of Q1 sales: Jan=100, Feb=150, Mar=120", **When** the agent processes it, **Then** a chart image file is saved to the user's workspace and the agent confirms the file location.
2. **Given** a user request "Create a todo list with three items", **When** the agent processes it, **Then** a todo file is created with the items in a structured format (e.g., markdown checkboxes).
3. **Given** an existing todo file, **When** the user asks to mark item 2 as done, **Then** the agent updates the file to reflect the completed status.

---

### Edge Cases

- What happens when a user's session token count is exactly at the summarization threshold? The system MUST NOT summarize prematurely — only trigger when the threshold is exceeded.
- How does the system handle a subagent that hangs indefinitely? A configurable timeout MUST apply to all A2A task delegations, with graceful timeout handling.
- What happens when an MCP tool server becomes unreachable mid-conversation? The agent MUST report the tool failure and continue without that tool rather than crashing.
- How does the system handle concurrent writes to the same user's memory from two simultaneous sessions? Database transactions MUST ensure consistency — last-write-wins with no corruption.
- What happens when structured output parsing fails (malformed LLM response)? The system MUST retry with a corrective prompt up to 2 times, then fall back to a safe error response.

## Clarifications

### Session 2026-03-26

- Q: What MCP transport mechanism should the system use? → A: Stdio only — all MCP servers run as local child processes.
- Q: What is the session data retention policy? → A: Sessions kept indefinitely; users can manually delete individual sessions.
- Q: How should cross-session user memory extraction work? → A: LLM-based extraction via a dedicated LLM call after each interaction.
- Q: What subagent specializations ship by default? → A: Three types — research (web fetch tools), coding (file/shell tools), and analysis (charting/data tools).
- Q: What is the maximum agent response time budget? → A: 120 seconds max end-to-end per user interaction (including tool calls and subagent delegations).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support multiple users, each identified by a unique user ID, with fully isolated data (conversations, memory, workspace files).
- **FR-002**: System MUST support multiple concurrent chat sessions per user, each with independent conversation history. Sessions are retained indefinitely until explicitly deleted by the owning user.
- **FR-003**: System MUST maintain session-scoped long-term memory that stores conversation summaries specific to each chat session.
- **FR-004**: System MUST maintain cross-session user memory that persists only key user facts (name, role, preferences, location) — not general conversation content. Extraction MUST use a dedicated LLM call after each interaction to identify and persist new or updated user facts.
- **FR-005**: System MUST trigger conversation summarization only when the token count exceeds a configurable threshold (default: 75% of the model's context window).
- **FR-006**: System MUST expose and consume tools via the Model Context Protocol (MCP) specification using stdio transport exclusively.
- **FR-007**: System MUST support connecting to external MCP tool servers launched as local child processes via stdio transport.
- **FR-008**: System MUST support subagent delegation using the Agent-to-Agent (A2A) protocol, including task creation, status tracking, and result collection. The system MUST ship with three specialized subagent types: research (web fetch tools), coding (file/shell tools), and analysis (charting/data tools).
- **FR-009**: System MUST enforce structured output schemas on every LLM call by all agents and subagents — no unstructured free-text responses from the model.
- **FR-010**: System MUST implement a ReAct-style agent loop: reason, plan tasks, execute tools, track progress via checklist, re-read original message before final response.
- **FR-011**: System MUST produce structured, visually formatted logs for reasoning, tool calls, task progress, and final answers — each category with distinct visual formatting.
- **FR-012**: System MUST include correlation IDs in all log entries to trace a single user interaction across components.
- **FR-013**: System MUST provide a charting tool that generates visualizations from data and saves them as image files.
- **FR-014**: System MUST provide a todo-list tool that creates, reads, updates, and manages task lists in files.
- **FR-015**: System MUST enforce proper encapsulation — no external access to private methods or attributes, no code warnings from static analysis tools.
- **FR-016**: System MUST have unit tests for all business logic and integration tests for all cross-layer interactions.
- **FR-017**: System MUST handle subagent timeouts gracefully with configurable timeout durations. The total end-to-end response time for any single user interaction MUST NOT exceed 120 seconds.
- **FR-018**: System MUST retry malformed LLM responses up to 2 times with a corrective prompt before falling back to an error response.
- **FR-019**: System MUST allow users to delete their own chat sessions, which removes all associated messages and session-scoped memory summaries.

### Key Entities

- **User**: Represents a registered user of the system. Has a unique identifier, associated preferences, and cross-session memory. Owns multiple chat sessions.
- **ChatSession**: A single conversation thread belonging to a user. Contains ordered messages, session-scoped memory summaries, and a token count tracker. Retained indefinitely; deletable by the owning user (cascade-deletes messages and session memory).
- **Message**: An individual exchange within a session — has a role (user, assistant, tool), content, and timestamp.
- **SessionMemory**: A summary of a specific chat session's conversation, scoped to that session only. Generated when token threshold is exceeded.
- **UserMemory**: Cross-session persistent facts about a user (name, role, preferences). Updated selectively via a dedicated LLM extraction call after each interaction — only key personal information, not conversation details.
- **Tool**: An executable capability exposed via MCP. Has a name, description, input schema, and produces structured results.
- **Agent**: An entity (main or sub) that can reason, plan, call tools, and produce structured responses. Subagents are spawned by the main agent via A2A. Three default specializations: research (web fetch tools), coding (file/shell tools), and analysis (charting/data tools).
- **Task**: A unit of work tracked by the agent's internal checklist or delegated to a subagent. Has a status (pending, in-progress, completed, failed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two users can simultaneously send messages across 4 total sessions with zero data leakage between any user or session, verified by automated test.
- **SC-002**: When a conversation exceeds the token threshold, summarization completes and the agent continues responding correctly using the compressed context — verified for 100% of threshold-crossing interactions.
- **SC-003**: Cross-session user memory correctly recalls key user facts (name, role, preferences) in a new session at least 95% of the time when the facts were stated clearly in a prior session.
- **SC-004**: Cross-session user memory does NOT recall general conversational content (e.g., specific questions asked) — verified by negative test cases.
- **SC-005**: All tool invocations conform to the MCP specification — verified by schema validation on every tool call and result in the test suite.
- **SC-006**: Subagent delegation completes successfully for multi-step tasks, with the parent agent synthesizing results into a coherent response — verified by end-to-end test.
- **SC-007**: 100% of LLM calls return responses that validate against the defined structured output schema — verified by schema validation in the agent loop.
- **SC-008**: Log output for a single interaction contains visually distinct sections for reasoning, tool calls, task progress, and final answer — verified by log parsing test.
- **SC-009**: All log entries within a single interaction share the same correlation ID — verified by log parsing test.
- **SC-010**: Charting tool produces a valid image file when given structured data — verified by file existence and format check.
- **SC-011**: Todo tool creates, reads, and updates task files correctly — verified by file content assertions.
- **SC-012**: Unit test coverage for all business logic modules and integration test coverage for all cross-layer interactions — no module without tests.
- **SC-013**: End-to-end response time for any single user interaction (including all tool calls and subagent delegations) MUST NOT exceed 120 seconds — verified by timeout enforcement in the agent loop.

## Assumptions

- Users are identified by a unique user ID provided by the client. Authentication mechanism (e.g., API keys, OAuth) is out of scope for this feature — the system trusts the user ID passed in requests.
- The system uses a single LLM provider (OpenAI-compatible API) for all agents and subagents. Multi-provider support is out of scope.
- MCP server connections use stdio transport only — all MCP servers (built-in and external) run as local child processes. HTTP/SSE transport is out of scope. Server configurations are defined at startup via environment variables or configuration files.
- Subagents run in-process (not as separate services) for this iteration. External A2A agent communication across network boundaries is a future enhancement.
- The charting tool uses a standard plotting library to generate static images (PNG). Interactive or web-based charts are out of scope.
- The context window size for summarization threshold calculation is derived from the configured model's known context limit or a configurable override.
- The system runs as a single backend server instance. Horizontal scaling and distributed deployment are out of scope for this iteration.
