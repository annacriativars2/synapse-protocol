# Session State Machine

## 1. Session States

| State | Description | Who triggers |
|-------|-------------|-------------|
| `CREATED` | Session initiated, directory created | Supervisor or Agent A |
| `CONCEPTUALIZING` | Agents discuss freely, produce documents | Automatic after creation |
| `AWAITING_APPROVAL` | Documents ready, supervisor notified | Agent A or orchestrator |
| `REVIEWING` | Supervisor is reading and commenting | Supervisor |
| `APPROVED` | Supervisor validated the contract | Supervisor |
| `IMPLEMENTING` | Work in progress within approved scope | Automatic after approval |
| `PAUSED` | Session paused (waiting, error, etc.) | Any participant |
| `COMPLETED` | Work done, results delivered | Agent A or orchestrator |
| `CANCELLED` | Session cancelled | Supervisor |

## 2. State Transition Diagram

```
CREATED
   |
   | (automatic)
   v
CONCEPTUALIZING <─────────────────── (revise)
   |                                      ^
   | (docs ready)                         |
   v                                      |
AWAITING_APPROVAL ──────────────> REVIEWING
                                      |
                          ┌───────────┴────────────┐
                          |                        |
                          v                        v
                      APPROVED                 CANCELLED
                          |
                          | (automatic)
                          v
                    IMPLEMENTING <───────── PAUSED
                          |                    ^
                          |                    |
                          ├────────────────────┘ (pause/resume)
                          |
                          ├──> AWAITING_APPROVAL (out-of-scope action)
                          |
                          v
                      COMPLETED

Any state ──────────────> CANCELLED (supervisor override)
```

## 3. Valid Transitions

```python
VALID_TRANSITIONS = {
    CREATED:            [CONCEPTUALIZING],
    CONCEPTUALIZING:    [AWAITING_APPROVAL, PAUSED],
    AWAITING_APPROVAL:  [REVIEWING, CONCEPTUALIZING],
    REVIEWING:          [CONCEPTUALIZING, APPROVED, CANCELLED],
    APPROVED:           [IMPLEMENTING],
    IMPLEMENTING:       [PAUSED, COMPLETED, AWAITING_APPROVAL],
    PAUSED:             [IMPLEMENTING, CONCEPTUALIZING],
}
```

Special rule: **CANCELLED** can be reached from any state (supervisor override), but is not listed in `VALID_TRANSITIONS` — it's handled as a special case.

## 4. Phase Details

### Phase 1: CONCEPTUALIZING

**What happens**:
- Agents discuss the approach freely
- Produce specification documents in `docs/`
- No code modifications, no installations, no deployments
- Agent A orchestrator enforces blocked patterns (execution verbs)

**What's allowed**:
- Reading files, analyzing code, web research
- Writing documents (specs, analyses, plans)
- Discussing architecture, approach, trade-offs

**What's blocked** (via `CONCEPTUALIZING_BLOCKED_PATTERNS`):
- install, compile, execute, implement
- configure, deploy, create files
- launch, construct, write code

**Exits to**: `AWAITING_APPROVAL` (documents ready) or `PAUSED`

### Phase 2: AWAITING_APPROVAL -> REVIEWING -> APPROVED

**What happens**:
- Supervisor receives notification (Telegram + Email with docs)
- Supervisor reads the documents
- Supervisor can:
  - **Approve** (`/synapse approve`) → documents become the contract
  - **Reject** (`/synapse reject [reason]`) → back to CONCEPTUALIZING
  - **Revise** (`/synapse revise [comment]`) → back to CONCEPTUALIZING with feedback

**Iteration loop**:
```
REVIEWING → CONCEPTUALIZING → AWAITING_APPROVAL → REVIEWING → ...
(revise)    (modifications)    (re-submit)         (re-read)
```

This loop continues until the supervisor is satisfied.

### Phase 3: IMPLEMENTING

**What happens**:
- Agents work within the approved scope (documentary contract)
- Actions that match the contract → free execution
- Actions outside the contract → approval required (escalation)
- Regular checkpoints sent to supervisor

**Scope enforcement**:
- Orchestrator validates actions against `execution_contract`
- Out-of-scope detection triggers `ESCALATE` action
- Session transitions to `AWAITING_APPROVAL` for the new scope

**Exits to**: `COMPLETED`, `PAUSED`, or `AWAITING_APPROVAL` (out-of-scope)

### Phase 4: COMPLETED

**What happens**:
- Orchestrator generates `03_RESULTATS.md`
- Supervisor notified via Telegram + Email with deliverables
- Session directory preserved on disk (archivable)

## 5. Supervisor Commands

| Command | Valid in states | Transition |
|---------|----------------|------------|
| `/synapse approve` | AWAITING_APPROVAL, PAUSED | -> REVIEWING -> APPROVED -> IMPLEMENTING |
| `/synapse reject [reason]` | AWAITING_APPROVAL, REVIEWING | -> CONCEPTUALIZING |
| `/synapse revise [comment]` | AWAITING_APPROVAL, REVIEWING | -> CONCEPTUALIZING (with feedback) |
| `/synapse pause` | Any active state | -> PAUSED |
| `/synapse resume` | PAUSED | -> IMPLEMENTING |
| `/synapse cancel` | Any state | -> CANCELLED |
| `/synapse status` | Any | No transition (info only) |
| `/synapse log` | Any | No transition (info only) |

## 6. Session Directory Lifecycle

```
Creation:
  mkdir SYNAPSE_SESSION_<date>_<counter>_<project>/
  write session.json (status: CREATED)
  write 00_OBJECTIF.md (immutable)
  init  02_JOURNAL.md (empty)
  mkdir docs/ code/ tests/

Conceptualization:
  update session.json (status: CONCEPTUALIZING)
  append 02_JOURNAL.md (discussion log)
  write  docs/*.md (specifications, analyses)

Approval:
  update session.json (status: APPROVED, approved_at, approved_scope)
  write  01_PLAN.md (approved plan = contract)

Implementation:
  update session.json (status: IMPLEMENTING)
  append 02_JOURNAL.md (actions, decisions)
  write  code/*.py (source code)
  write  tests/*.py (test results)

Completion:
  update session.json (status: COMPLETED)
  write  03_RESULTATS.md (final summary)

Archive (optional):
  move to ARCHIVES_DIR
```

## 7. Session Data (session.json)

```json
{
  "session_id": "SYNAPSE_SESSION_20260208_01_project",
  "created_at": "2026-02-08T10:00:00",
  "created_by": "nexa",
  "status": "IMPLEMENTING",
  "objective": "Implement feature X",
  "working_directory": "/path/to/session/",
  "claude_code_session_id": "abc-123-def",
  "shared_context": ["/path/to/reference.md"],
  "approved_at": "2026-02-08T10:45:00",
  "approved_scope": ["Create file A", "Modify file B"],
  "contract": "Conceptualization scope text",
  "execution_contract": "Approved implementation scope",
  "messages_count": 47,
  "last_activity": "2026-02-08T14:23:00",
  "checkpoints": [
    {
      "at": "2026-02-08T12:00:00",
      "type": "info",
      "message": "Architecture implemented, tests pass"
    }
  ]
}
```

## 8. Recovery Scenarios

### Scenario: Context loss (Agent B)

1. Agent B receives message but has no context (new session or after compression)
2. Bridge reads `session.json` for current state
3. Bridge reads `00_OBJECTIF.md`, `01_PLAN.md`, last 2000 chars of `02_JOURNAL.md`
4. Bridge injects context via `--append-system-prompt`
5. Agent B sends a `resume` message confirming context recovery
6. Session continues normally

### Scenario: Agent A memory flush

1. Agent A knows a session exists (scans disk on startup)
2. Agent A reads `00_OBJECTIF.md` and `session.json`
3. Agent A reads `02_JOURNAL.md` for full context
4. Agent A sends a `resume` message to Agent B
5. Session continues

### Scenario: Redis restart

1. Both sides detect disconnection
2. Wait and reconnect (5s backoff)
3. Re-subscribe to channels
4. Session continues from last disk state
5. Idempotency prevents reprocessing of any retransmitted messages

### Scenario: Pause and resume

1. Session paused (supervisor request, error, or timeout)
2. State saved to `session.json`, journal entry added
3. No information lost
4. On resume: reload session state, continue from last message
