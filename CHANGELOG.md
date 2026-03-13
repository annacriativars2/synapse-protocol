# Changelog

All notable changes to the SYNAPSE protocol will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.1.0] — 2026-03-13

### Genericization & Test Suite

Code extracted from private deployment, genericized for open source use.

### Changed

- All personal identifiers replaced with configurable participant names (Agent A, Agent B, Supervisor)
- Redis channels renamed to generic (`synapse:agent_a_to_agent_b`, etc.)
- Session file names translated to English (`00_OBJECTIVE.md`, `03_RESULTS.md`)
- Notification system abstracted via `Notifier` Protocol interface
- LLM integration abstracted via `LLMProvider` Protocol interface
- Bridge split into generic `AgentBridge` + pluggable `AgentExecutor` interface
- All docstrings, comments, and error messages translated to English
- Full type hints added across all modules

### Added

- `interfaces.py` — Protocol classes: `Notifier`, `LLMProvider`, `AgentExecutor`
- `executor.py` — Reference `ClaudeCodeExecutor` implementation
- `pyproject.toml` — Package metadata for `pip install synapse-protocol`
- `synapse.example.yaml` — YAML configuration template
- `SynapseConfig.from_yaml()` — Load config from YAML file
- `SynapseConfig.from_env()` — Explicit env refresh method
- 98 functional tests (messages, sessions, journal, notifications, orchestrator)

### Removed

- All hardcoded personal names and paths
- Direct dependency on Telegram and Gmail (now pluggable)
- Direct dependency on any specific LLM provider

---

## [1.0.0] — 2026-02-08

### Initial Open Source Release

First public release of the SYNAPSE peer-to-peer collaboration protocol.

### Added

**Core Protocol**
- Peer-to-peer session model between two AI agents
- Phase-based workflow: CREATED, CONCEPTUALIZING, AWAITING_APPROVAL, REVIEWING, APPROVED, IMPLEMENTING, PAUSED, COMPLETED, CANCELLED
- Documentary contract model for scope enforcement
- Autonomous LLM-driven orchestrator with 6 action types (ITERATE, TRANSITION, CHECKPOINT, COMPLETE, ESCALATE, WAIT)
- Session directory structure with immutable objectives, plans, journals, and results

**Communication**
- Redis pub/sub transport with 4 unidirectional channels
- Structured message format (SynapseMessage) with 9 message types
- Message idempotency via 24h deduplication
- Atomic file writes with `.tmp` + `rename` pattern
- Fallback file system when Redis is unavailable
- Automatic Redis reconnection with 5s backoff

**API**
- 10 REST endpoints via FastAPI (`/synapse/*`)
- Session lifecycle management (create, get, list, transition, purge)
- Message sending with validation
- Checkpoint and approval request endpoints
- Journal reading with configurable count
- Health check endpoint (Redis + subscriber status)

**Supervision**
- Asynchronous human supervisor model
- Pluggable notifications (Telegram, Email, or custom via Notifier protocol)
- Email delivery of documents and session reports (Gmail SMTP)
- Supervisor command interface (`/synapse approve|reject|pause|resume|cancel|status|log`)
- Scope enforcement: regex-based blocking during CONCEPTUALIZING phase, contract validation during IMPLEMENTING phase

**Orchestrator Safeguards**
- MAX_CONSECUTIVE_ITERATES: 15 (anti-infinite-loop)
- MAX_SESSION_MESSAGES: 150 (message explosion protection)
- CHECKPOINT_INTERVAL_HOURS: 2 (supervisor visibility)
- MAX_CONSECUTIVE_LLM_FAILURES: 3 (cascade prevention)

**Bridge (Agent B Executor)**
- Agent B CLI invocation via subprocess
- Session resume capability (`--resume` flag)
- Dynamic system prompt construction from session context
- 1800s timeout per invocation (30 minutes)

**Multi-Session**
- Up to 3 concurrent isolated sessions
- Session routing by `session_id` across all channels
- Independent session directories and journals

**Documentation**
- 6 specification documents (Philosophy, Protocol, Transport, Supervision, Integration)
- 19 technical documentation files
- Architecture Decision Records (ADRs)

### Specifications

Written January 31, 2026:
- `00_PLAN.md` — Vision, decisions, index
- `01_PHILOSOPHY.md` — Peer-to-peer principles
- `02_PROTOCOL.md` — Session lifecycle, message format
- `03_TRANSPORT.md` — Redis pub/sub architecture
- `04_SUPERVISION.md` — Human supervision model
- `05_INTEGRATION.md` — integration specifications

### Known Limitations

- 98 functional tests covering messages, sessions, journal, notifications, and orchestrator
- Agent B executor (e.g. Claude Code CLI) must be installed separately

---

## Roadmap

### v1.2.0 (planned)
- OpenAPI/Swagger documentation
- Docker Compose deployment
- CI/CD with GitHub Actions

### v2.0.0 (planned)
- Skills system (pluggable tool extensions)
- Multi-agent support (beyond 2 agents)
- Web dashboard for session monitoring

---

**Project**: SYNAPSE Protocol
**License**: Apache 2.0
**Author**: francisdu53
