<!--
  Sync Impact Report
  ==================
  Version change: (none) → 1.0.0
  Modified principles: N/A (initial adoption)
  Added sections:
    - Core Principles (8 principles)
    - Architecture Constraints
    - Development Workflow
    - Governance
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ compatible (Constitution Check section is generic)
    - .specify/templates/spec-template.md — ✅ compatible (testing requirements align with Principle VII/VIII)
    - .specify/templates/tasks-template.md — ✅ compatible (phase structure supports testing-first, logging tasks)
  Follow-up TODOs: None
-->

# OpenClaw Constitution

## Core Principles

### I. Clean Code

All code MUST follow software development best practices for
readability, maintainability, and clarity. Functions MUST do one thing.
Names MUST be descriptive and self-documenting. Files MUST be
cohesive — one module, one responsibility. Dead code, commented-out
blocks, and unused imports MUST be removed. Code duplication MUST
be eliminated only when three or more occurrences exist; premature
abstraction is prohibited. Every public interface MUST have clear
type annotations.

### II. Framework-Free Agentic Architecture

The agent architecture MUST be built from first principles using
standard Python libraries and direct API integrations — no
orchestration frameworks (LangChain, LlamaIndex, CrewAI, AutoGen,
etc.). The core agent loop (reason → plan → act → observe) MUST
be explicitly implemented and fully auditable. Each architectural
layer (Gateway, Runtime, Memory, Tools, Provider) MUST have clear
boundaries with well-defined interfaces. Dependencies MUST be
minimal and each one MUST be justified.

### III. Standard Agent Protocols

The system MUST implement industry-standard agent communication
protocols:

- **MCP (Model Context Protocol)**: Tool exposure and consumption
  MUST conform to the MCP specification. The agent MUST be able to
  both serve tools as an MCP server and consume tools from external
  MCP servers.
- **A2A (Agent-to-Agent)**: Inter-agent communication for subagent
  delegation MUST follow the A2A protocol. Agent cards, task
  lifecycle, and message exchange MUST conform to the A2A
  specification.

### IV. Structured Observability

All modules MUST use structured logging with consistent formatting.
Log output MUST be visually scannable: each log entry MUST include
timestamp, level, module name, and a human-readable message. Log
entries from different operations MUST be clearly separated with
visual delimiters or contextual grouping. Log levels MUST be used
correctly: DEBUG for internal state, INFO for lifecycle events,
WARNING for recoverable issues, ERROR for failures requiring
attention. Request-scoped correlation IDs MUST propagate across
all log entries within a single user interaction. Sensitive data
(API keys, tokens, user PII) MUST NEVER appear in logs.

### V. Cognitive Agent Capabilities

The agent MUST support the full cognitive loop:

- **Reasoning**: The agent MUST produce explicit chain-of-thought
  reasoning before taking actions.
- **Planning**: The agent MUST decompose complex requests into
  ordered sub-steps and track progress against the plan.
- **Tool Calling**: The agent MUST discover, validate, and invoke
  tools with structured input/output. Tool errors MUST be handled
  gracefully with retry or fallback logic.
- **Task Management**: The agent MUST create, track, and complete
  tasks. Long-running tasks MUST report progress.
- **Subagent Delegation**: The agent MUST be able to spawn subagents
  for parallel or specialized work, with clear parent-child
  lifecycle management.

### VI. Effective Memory Management

The system MUST implement both short-term and long-term memory:

- **Short-term (session) memory**: Conversation history within a
  chat session. MUST support configurable context window management
  with summarization or truncation strategies.
- **Long-term (cross-session) memory**: Persistent knowledge that
  survives across sessions. MUST support semantic search and
  retrieval. MUST be scoped per user.
- Memory retrieval MUST be automatic and context-aware — the agent
  MUST surface relevant memories without explicit user requests.
- Memory writes MUST be selective — only non-obvious, reusable
  knowledge is persisted.

### VII. Multi-Tenant Backend

The application MUST be a backend server capable of handling
multiple concurrent users across multiple chat sessions. Each user
MUST have isolated data (conversations, memory, workspace). Session
state MUST NOT leak between users. The API MUST support
authentication and session management. The system MUST handle
concurrent requests without data corruption. Database operations
MUST use proper transaction isolation.

### VIII. Comprehensive Testing

Every feature MUST have both unit tests and integration tests:

- **Unit tests**: All business logic, utilities, and individual
  components MUST have unit tests. Tests MUST be fast, isolated,
  and deterministic. External dependencies MUST be mocked at
  module boundaries.
- **Integration tests**: All cross-layer interactions (Gateway →
  Runtime → Provider, Runtime → Memory, Runtime → Tools) MUST have
  integration tests using real (in-memory or temp) databases and
  actual HTTP calls where feasible.
- Test coverage MUST NOT decrease with new changes. Critical paths
  (agent loop, tool execution, memory retrieval) MUST have explicit
  test coverage.

## Architecture Constraints

- **Language**: Python 3.11+.
- **HTTP Framework**: FastAPI or equivalent async-capable framework.
- **Database**: SQLite for development; design MUST allow migration
  to PostgreSQL for production multi-tenant deployments.
- **Async**: All I/O-bound operations (LLM calls, database queries,
  HTTP requests) MUST be async.
- **Configuration**: All settings MUST be driven by environment
  variables with sensible defaults. No hardcoded secrets.
- **Project Structure**: Maintain the existing layered architecture
  (Gateway → Runtime → Memory / Tools / Provider). New capabilities
  MUST integrate into the existing layer boundaries rather than
  creating parallel hierarchies.

## Development Workflow

- **Branch Strategy**: Feature branches off `main`. PRs MUST pass
  all tests before merge.
- **Commit Discipline**: Each commit MUST represent a single logical
  change. Commit messages MUST describe the "why."
- **Code Review**: All changes MUST be reviewed for compliance with
  this constitution before merge.
- **Test-First Encouraged**: For complex features, write failing
  tests first, then implement. For straightforward additions,
  tests MAY be written alongside implementation.
- **Logging Validation**: Every new module or significant code path
  MUST include appropriate structured log statements before the PR
  is considered complete.

## Governance

This constitution is the authoritative source of project standards.
All code contributions, reviews, and architectural decisions MUST
comply with the principles defined herein.

- **Amendments**: Any change to this constitution MUST be documented
  with a version bump, rationale, and migration plan for affected
  code.
- **Versioning**: Constitution versions follow semantic versioning
  (MAJOR.MINOR.PATCH). Principle removals or redefinitions require
  a MAJOR bump. New principles or material expansions require MINOR.
  Clarifications and wording fixes require PATCH.
- **Compliance Review**: PRs MUST include a constitution compliance
  check. Violations MUST be justified in the PR description with a
  reference to the specific principle being exempted and why.
- **Runtime Guidance**: Use `CLAUDE.md` for development environment
  setup and runtime command reference. This constitution governs
  design and quality standards.

**Version**: 1.0.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-03-26
