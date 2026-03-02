# Architecture Decision Records (ADR)

## ADR-001: Redis Pub/Sub over Alternatives

**Status**: Accepted
**Date**: January 31, 2026

### Context

SYNAPSE needs a real-time messaging layer between two processes on the same machine. The previous system used 10 JSON files with 500ms polling and had race conditions.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Redis pub/sub | Already installed, single-threaded, real-time, simple API | No persistence, no message acknowledgment |
| WebSocket | Bidirectional, standard | Overkill for 2 participants on same machine |
| HTTP polling | Simple, well-understood | Latency, race conditions (already proven problematic) |
| gRPC | Typed, efficient | Complex setup, overkill |
| RabbitMQ/Kafka | Reliable delivery, persistence | Overkill infrastructure for 2 participants |

### Decision

Use Redis pub/sub. Redis is already running on the server, provides real-time delivery, and its single-threaded model eliminates race conditions.

### Consequences

- No built-in message persistence (mitigated by disk-based session directories)
- No delivery acknowledgment (mitigated by idempotency and fallback files)
- Simple deployment (no new infrastructure)

---

## ADR-002: Peer-to-Peer over Orchestrator/Agent

**Status**: Accepted
**Date**: January 31, 2026

### Context

Need to define the relationship between the two AI agents.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Orchestrator/Agent | Clear authority chain | Imposes hierarchy, limits Agent B's ability to disagree |
| Client/Server | Familiar pattern | Too rigid for iterative dialogue |
| Peer-to-peer | Both contribute equally, disagreement possible | More complex coordination |

### Decision

Peer-to-peer with functional asymmetry. Agent A initiates (technical constraint) but both are equal experts.

### Consequences

- Disagreement resolution protocol needed
- Orchestrator must handle both agents' inputs fairly
- More complex than simple command/execute pattern
- Better outcomes from genuine collaboration

---

## ADR-003: Documentary Contract for Supervision

**Status**: Accepted
**Date**: January 31, 2026

### Context

The human supervisor needs to maintain control without becoming a bottleneck.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Approve every action | Full control | Bottleneck, supervisor fatigue |
| No approval | Maximum autonomy | No control, risky |
| Documentary contract | Control at plan level, freedom at execution | Requires scope enforcement |

### Decision

Documentary contract: supervisor approves a plan (documents), agents work freely within the approved scope. Out-of-scope actions require explicit approval.

### Consequences

- Scope enforcement needed in orchestrator
- Blocked patterns for conceptualization phase
- Out-of-scope detection and escalation mechanism

---

## ADR-004: Disk as Primary Storage (Not Redis)

**Status**: Accepted
**Date**: January 31, 2026

### Context

Session data needs to survive restarts, memory flushes, and context compression.

### Decision

Redis is transport only (ephemeral). All important data lives on disk:
- `session.json` for metadata
- `00_OBJECTIF.md` through `03_RESULTATS.md` for documentation
- `02_JOURNAL.md` for audit trail

### Consequences

- Redis can restart without data loss
- Session recovery is straightforward (read from disk)
- Atomic writes needed everywhere (`.tmp` + `rename` pattern)
- File locking needed for journal (concurrent writers)

---

## ADR-005: Append-Only Journal

**Status**: Accepted
**Date**: January 31, 2026

### Context

Need a collaboration audit trail.

### Decision

`02_JOURNAL.md` is append-only with file locking. Entries are never modified or deleted.

### Consequences

- Complete audit trail
- File can grow large in long sessions (mitigated by `read_last_entries()`)
- File locking adds slight overhead
- Journal survives any failure mode

---

## ADR-006: LLM-Driven Orchestration

**Status**: Accepted
**Date**: February 2026

### Context

Agent A needs to decide what to do after each Agent B response.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Rule-based | Predictable, fast | Cannot handle nuanced situations |
| LLM-driven | Context-aware, flexible | Depends on LLM availability, potential failures |
| Hybrid | Best of both | More complex |

### Decision

LLM-driven with hard safeguards. The orchestrator uses Agent A's LLM for contextual decisions, but hard limits override any LLM decision.

### Consequences

- Safeguards: max 15 iterates, max 150 messages, 2h checkpoint, 3 LLM failures
- Graceful degradation if LLM unavailable (session pauses)
- More intelligent routing than rules alone

---

## ADR-007: Multi-Session Support

**Status**: Accepted
**Date**: February 2026

### Context

Should SYNAPSE support concurrent sessions?

### Decision

Yes, up to 3 concurrent sessions. Each session is isolated by directory and tracked by `session_id` in messages.

### Consequences

- Message routing by `session_id` in Redis callbacks
- Per-session orchestrator context
- Backward-compatible `.active` property for single-session usage
- Session directory naming includes counter: `SYNAPSE_SESSION_<date>_<counter>_<project>`

---

## ADR-008: Session Continuity via CLI Resume

**Status**: Accepted
**Date**: February 2026

### Context

Agent B (Claude Code CLI) loses context between invocations.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| New session every call | Simple | Context loss, expensive |
| `--resume` flag | Preserves full context | May fail if session expired |
| Context re-injection | Always works | Less context than full resume |

### Decision

Two-level approach:
- **Level 1**: Use `--resume <session_id>` to preserve full CLI context
- **Level 2**: If resume fails, fall back to new session with context re-injection from disk (objective + plan + journal)

### Consequences

- Bridge saves `claude_code_session_id` in `session.json`
- Automatic fallback keeps sessions running
- Context may degrade on fallback (last 2000 chars of journal vs full context)
