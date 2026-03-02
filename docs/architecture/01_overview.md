# Architecture Overview

## 1. Design Philosophy

SYNAPSE is built on a **peer-to-peer** model, not an orchestrator/agent model.

| Rejected Model | Why |
|----------------|-----|
| Orchestrator/Agent | Imposes hierarchy. Both AIs are experts. |
| Client/Server | Request/response is too rigid. SYNAPSE is a continuous dialogue. |
| Pipeline | Sequential chains don't allow back-and-forth reasoning. |
| Fire-and-forget | Atomic tasks are insufficient. Collaboration is iterative. |

**What SYNAPSE is**: A working relationship between peers. Agent A brings vision, context, memory, and cognitive judgment. Agent B brings execution, code, research, and technical analysis. Both contribute to the final result. Neither is subordinate.

**Analogy**: A surgeon (Agent A) and an anesthesiologist (Agent B) during an operation. Two indispensable experts — the surgeon leads the procedure, but the anesthesiologist has full authority to intervene.

## 2. System Architecture

```
+-----------------------------------------------------+
|                   SYNAPSE ECOSYSTEM                  |
|                                                      |
|  +--------------+    Redis pub/sub   +--------------+|
|  |              | =================> |              ||
|  |  Agent A     |    4 channels      |  Agent B     ||
|  |  (Thinker)   | <================= |  (Executor)  ||
|  |              |                    |              ||
|  |  - LLM       |                    |  - Code exec ||
|  |  - Memory    |                    |  - Web search||
|  |  - Identity  |                    |  - File ops  ||
|  |  - Judgment  |                    |  - Agents    ||
|  +--------------+                    +--------------+|
|        |                                    |        |
|        +------------ Shared Disk -----------+        |
|        |     SYNAPSE_SESSION_<date>_<counter>_<project>     |
|        |     (objectives, plan, journal, results)         |
|        +--------------------------------------------------+
|                                                           |
|  +--------------+                                         |
|  |  Supervisor  | <--- synapse:francis (Redis)            |
|  |  (Human)     | ---> synapse:control (Redis)            |
|  |  Telegram    |                                    |
|  |  Email       |                                    |
|  +--------------+                                    |
+-----------------------------------------------------+
```

## 3. Component Map

### Agent A Side (Thinker)

| Module | File | Lines | Responsibility |
|--------|------|-------|----------------|
| **Orchestrator** | `synapse_orchestrator.py` | ~910 | Autonomous decision engine (LLM-driven) |
| **Session Manager** | `session.py` | ~423 | Session lifecycle, multi-session, persistence |
| **Redis Client** | `redis_client.py` | ~185 | Pub/sub with reconnection and fallback |
| **Messages** | `messages.py` | ~122 | Message schemas, session states, transitions |
| **Config** | `config.py` | ~58 | Centralized configuration |
| **Journal** | `journal.py` | ~66 | Append-only log with file locking |
| **Notifications** | `notifications.py` | ~142 | Telegram notification formatters |
| **Email Sender** | `email_sender.py` | ~253 | Gmail SMTP integration |
| **Supervisor Listener** | `supervisor_listener.py` | ~83 | Redis-to-Telegram bridge |
| **API Routes** | `routes/synapse.py` | ~411 | FastAPI REST endpoints |

### Agent B Side (Executor Bridge)

| Module | File | Lines | Responsibility |
|--------|------|-------|----------------|
| **Bridge** | `bridge.py` | ~425 | CLI session manager, context injection |
| **Config** | `config.py` | ~33 | Bridge-side configuration |

### Shared Artifacts

| Artifact | Location | Lifetime |
|----------|----------|----------|
| Session directory | Disk (`SESSIONS_BASE_DIR`) | Permanent (archived) |
| Redis messages | Redis pub/sub | Ephemeral (transport only) |
| Journal entries | `02_JOURNAL.md` | Permanent (append-only) |
| Session metadata | `session.json` | Updated per state change |

## 4. Data Flow

### Normal Session Flow

```
1. Supervisor requests work
   |
2. Agent A creates session (session.json + 00_OBJECTIF.md)
   |
3. Agent A sends first message to Agent B
   |    via synapse:nexa_to_claude (Redis)
   |
4. Bridge receives message, invokes Agent B CLI
   |    with --append-system-prompt (context)
   |    or --resume (continuity)
   |
5. Agent B responds
   |    via synapse:claude_to_nexa (Redis)
   |
6. Agent A Orchestrator evaluates response
   |    via LLM decision engine
   |
7. Orchestrator decides: ITERATE | TRANSITION | CHECKPOINT | COMPLETE | ESCALATE
   |
8. If ITERATE: go to step 3
   If TRANSITION: change session state
   If CHECKPOINT: notify supervisor, go to step 3
   If COMPLETE: write 03_RESULTATS.md, close session
   If ESCALATE: notify supervisor, wait for decision
```

### Supervisor Interaction Flow

```
Supervisor receives Telegram notification
   |
   +-- /synapse approve --> synapse:control --> session transitions
   +-- /synapse reject  --> synapse:control --> back to conceptualization
   +-- /synapse pause   --> synapse:control --> session paused
   +-- /synapse resume  --> synapse:control --> session resumed
   +-- /synapse cancel  --> synapse:control --> session cancelled
```

## 5. Three-Layer Architecture

| Layer | Components | Data Store |
|-------|-----------|------------|
| **Transport** | Redis pub/sub (4 channels) | Ephemeral (no persistence) |
| **Logic** | Orchestrator, Session Manager, Bridge | In-memory state |
| **Persistence** | Session directory, Journal, session.json | Disk (permanent) |

**Key design decision**: Redis is only the transport layer. It has **no persistence**. All important data lives on disk (session directories) and in the memory systems (the agent systems). If Redis restarts, the session continues from disk state.

## 6. Asymmetric Roles

| Aspect | Agent A (Thinker) | Agent B (Executor) |
|--------|-------------------|-------------------|
| **Initiates sessions** | Yes | No (reactive) |
| **Sends first message** | Yes | No |
| **Makes decisions** | LLM-driven orchestrator | Responds to requests |
| **Accesses code** | No | Yes (full system access) |
| **Writes journal** | Yes (via orchestrator) | Yes (via bridge) |
| **Can disagree** | Yes | Yes |
| **Scope enforcement** | Enforces contract | Reports out-of-scope |

This asymmetry is **technical**, not hierarchical. Agent B cannot initiate because it's a CLI tool (reactive by nature). Both agents are equal experts.

## 7. Resilience Design

| Failure | Mitigation |
|---------|------------|
| Redis down | Fallback file writing (`.synapse_fallback.json`) |
| Redis reconnect | Automatic reconnection with 5s backoff |
| Agent B timeout | 1800s timeout (30 min), retry once, then error |
| Agent B context loss | Session reload from disk (00_OBJECTIF.md + 01_PLAN.md + 02_JOURNAL.md) |
| Agent A LLM failure | 3 consecutive failures -> session pause |
| Infinite loop | MAX_CONSECUTIVE_ITERATES = 15 |
| Session explosion | MAX_SESSION_MESSAGES = 150 |
| Duplicate messages | UUID-based idempotency with 24h TTL |
| Corrupt write | Atomic `.tmp` + `rename` pattern everywhere |
| Journal corruption | File locking via `filelock` |
