# Component Detail

## 1. Orchestrator (`synapse_orchestrator.py`)

The orchestrator is the autonomous decision engine on Agent A's side. It receives every response from Agent B and decides what to do next.

### Class: `SynapseOrchestrator`

**Constructor dependencies**:
- `session_manager` (SynapseSession) — Session lifecycle
- `redis_client` (SynapseRedisClient) — Message publishing
- `telegram_notifier` — Telegram notifications
- `email_sender` (SynapseEmailSender) — Email delivery

### Entry Point: `handle_claude_response(message, session_id)`

Called by the Redis callback when Agent B publishes a response. Flow:

```
1. Forward response to supervisor (Telegram)
2. Load session context
3. Check safeguards (message count, iterate count, LLM failures)
4. Call LLM to evaluate response and decide next action
5. Execute decided action
6. Log to journal
```

### Decision Actions (OrchestratorAction enum)

| Action | When | What happens |
|--------|------|-------------|
| `ITERATE` | Normal flow | Sends next message to Agent B with scope header |
| `TRANSITION` | Phase change needed | Validates and executes session state transition |
| `CHECKPOINT` | Time or milestone | Sends progress update to supervisor |
| `COMPLETE` | Work done | Generates 03_RESULTATS.md, closes session |
| `ESCALATE` | Out-of-scope detected | Notifies supervisor for decision |
| `WAIT` | Session paused/waiting | Does nothing (waits for external event) |

### Scope Enforcement

During **CONCEPTUALIZING** phase, the orchestrator blocks execution verbs via regex:

```python
CONCEPTUALIZING_BLOCKED_PATTERNS = [
    r"\binstall(?:e[rsz]?|er|ation)\b",
    r"\bcompil(?:e[rsz]?|er|ation)\b",
    r"\bex[eé]cut(?:e[rsz]?|er|ion)\b",
    r"\bimpl[eé]ment(?:e[rsz]?|er|ation)\b",
    r"\bconfigur(?:e[rsz]?|er|ation)\b",
    r"\bd[eé]ploy(?:e[rsz]?|er|ment)\b",
    r"\bcr[eé](?:e[rsz]?|er).*files?\b",
    r"\blanc(?:e[rsz]?|er)\b",
    r"\bconstru(?:i[rstz]?|ire|ction)\b",
    r"\b[eé]cri(?:re|s|t|ture).*code\b",
]
```

During **IMPLEMENTING** phase, actions are validated against the execution contract (approved scope).

### Message Header Injection

Every message to Agent B includes a scope header:

```
[SYNAPSE:<status>] [SOURCE:<source>] [SCOPE:<objective>]
```

This ensures Agent B always knows the current session context.

---

## 2. Session Manager (`session.py`)

### Class: `SynapseSession`

Manages the lifecycle of collaboration sessions.

### Multi-Session Support

- Maximum `MAX_CONCURRENT_SESSIONS = 3` active sessions
- Each session is identified by a unique `session_id`
- Sessions are isolated by directory
- Backward-compatible `.active` property returns most recent session

### Core Methods

| Method | Purpose |
|--------|---------|
| `create(project_name, objective, ...)` | Creates session directory and metadata |
| `transition(new_status, reason, session_id)` | Validates and executes state transition |
| `get(session_id)` | Retrieves session by ID |
| `increment_messages(session_id)` | Tracks message count |
| `add_checkpoint(type, message, session_id)` | Adds progress marker |
| `set_contract(contract, session_id)` | Sets conceptualization scope |
| `set_execution_contract(contract, session_id)` | Sets implementation scope |
| `purge_sessions(keep_last, max_age_days)` | Archives terminated sessions |

### Persistence

- **Atomic writes**: Uses `.tmp` + `os.rename()` pattern for `session.json`
- **Startup load**: Scans `SESSIONS_BASE_DIR` for active sessions on restart
- **Immutable objective**: `00_OBJECTIF.md` is written once at creation

### State Transition Validation

Transitions are validated against `VALID_TRANSITIONS` map. Invalid transitions raise `ValueError`.

---

## 3. Redis Client (`redis_client.py`)

### Class: `SynapseRedisClient`

### Publication Methods

| Method | Channel | Purpose |
|--------|---------|---------|
| `publish_to_claude(message)` | `synapse:nexa_to_claude` | Send to Agent B |
| `publish_to_nexa(message)` | `synapse:claude_to_nexa` | Bridge utility |
| `notify_francis(session_id, type, content)` | `synapse:francis` | Supervisor notification |
| `publish_control(command, session_id, data)` | `synapse:control` | Supervisor command |

### Subscription

`subscribe(channels, callback)` creates a daemon thread that:
1. Listens on specified channels
2. Deserializes JSON messages into `SynapseMessage` objects
3. Checks idempotency (24h dedup)
4. Calls the callback with `(channel, message)`
5. Auto-reconnects on Redis disconnection

### Idempotency

- Tracks processed message IDs in memory
- TTL: 24 hours (`IDEMPOTENCY_TTL`)
- Cleanup runs on each check

### Fallback

If Redis is unavailable, messages are written atomically to `.synapse_fallback.json`.

### Health Check

`health()` returns Redis connectivity status and channel subscriber counts.

---

## 4. Messages (`messages.py`)

### Enums

**MessageType**:
`DIALOGUE`, `PROPOSAL`, `DECISION`, `ACTION`, `CHECKPOINT`, `APPROVAL_REQUEST`, `DISAGREEMENT`, `RESUME`, `DELIVERY`

**SessionStatus**:
`CREATED`, `CONCEPTUALIZING`, `AWAITING_APPROVAL`, `REVIEWING`, `APPROVED`, `IMPLEMENTING`, `PAUSED`, `COMPLETED`, `CANCELLED`

### Classes

**SynapseMessage**: Transport wrapper with validation
- `id` (UUID v4, auto-generated)
- `session_id` (string)
- `sender` ("nexa" | "claude")
- `type` (MessageType)
- `content` (string)
- `timestamp` (ISO 8601)
- `metadata` (dict)
- `validate()` — Checks required fields
- `to_json()` / `from_json()` — Serialization

**SessionData**: Session metadata for persistence
- All session fields (see session.json format)
- `to_dict()` / `from_dict()` — Serialization

### State Transitions Map

```
CREATED           -> [CONCEPTUALIZING]
CONCEPTUALIZING   -> [AWAITING_APPROVAL, PAUSED]
AWAITING_APPROVAL -> [REVIEWING, CONCEPTUALIZING]
REVIEWING         -> [CONCEPTUALIZING, APPROVED, CANCELLED]
APPROVED          -> [IMPLEMENTING]
IMPLEMENTING      -> [PAUSED, COMPLETED, AWAITING_APPROVAL]
PAUSED            -> [IMPLEMENTING, CONCEPTUALIZING]
```

---

## 5. Journal (`journal.py`)

### Functions

| Function | Purpose |
|----------|---------|
| `append_to_journal(session_dir, entry)` | Add timestamped entry with file locking |
| `append_raw(session_dir, raw_text)` | Add raw text (for sub-entries) |
| `read_last_entries(session_dir, count)` | Read last N journal sections |

### Design

- **Append-only**: Never modify previous entries
- **File locking**: Uses `filelock.FileLock` to prevent concurrent corruption
- **Format**: `## YYYY-MM-DD HH:MM — <entry text>`
- **Purpose**: Black box of the collaboration (audit trail)

---

## 6. Notifications (`notifications.py`)

Formats messages for the human supervisor via Telegram.

| Formatter | Trigger |
|-----------|---------|
| `format_session_created(session)` | New session started |
| `format_docs_ready(session)` | Documents ready for review |
| `format_checkpoint(session, progress)` | Progress update |
| `format_approval_needed(session, action, reason, impact)` | Out-of-scope request |
| `format_disagreement(session, nexa_pos, claude_pos)` | Agent disagreement |
| `format_session_completed(session)` | Session finished |
| `format_session_error(session, error)` | Critical error |
| `format_health(health, session)` | Health check output |

---

## 7. Email Sender (`email_sender.py`)

### Class: `SynapseEmailSender`

Sends documents to the supervisor via Gmail SMTP.

| Method | Purpose |
|--------|---------|
| `send_docs_for_review(session_id, session_dir, summary)` | Send conceptualization docs |
| `send_session_report(session_id, session_dir, report)` | Send final deliverables |
| `send_custom(subject, body, attachments)` | Generic email |

### Auto-Discovery

- `_discover_docs()` — Finds `00_OBJECTIF.md`, `01_PLAN.md`, `02_JOURNAL.md` + `docs/` contents
- `_discover_deliverables()` — Finds `03_RESULTATS.md` + `code/` + `tests/` + `docs/`

### Constraints

- Max 10 MB per attachment
- TLS via smtp.gmail.com:587
- Requires Gmail app password (2FA)

---

## 8. Supervisor Listener (`supervisor_listener.py`)

### Class: `FrancisListener`

Background daemon thread that:
1. Subscribes to `synapse:francis` Redis channel
2. Parses incoming JSON messages
3. Forwards to supervisor via Telegram
4. Auto-reconnects on Redis failure

---

## 9. Bridge (`bridge.py`)

The bridge connects Agent B (Claude Code CLI) to the SYNAPSE Redis network.

### Main Loop

```
1. Connect to Redis
2. Find active session on disk
3. Load claude_code_session_id for --resume
4. Subscribe to synapse:nexa_to_claude + synapse:control
5. For each message:
   a. Check idempotency
   b. Load/reload session data
   c. Build system prompt (objectives + plan + journal)
   d. Call Claude Code CLI (--resume or --append-system-prompt)
   e. Parse JSON response
   f. Publish response to synapse:claude_to_nexa
   g. Save claude_code_session_id for next call
```

### Context Injection

The bridge builds a dynamic system prompt from:
- `00_OBJECTIF.md` (immutable objective)
- `01_PLAN.md` (approved plan, if exists)
- `02_JOURNAL.md` (last 2000 characters)
- Current session status
- Rule: all documents must go in `docs/` directory

### Session Continuity

- Level 1: `--resume <session_id>` (preserves full CLI context)
- Level 2: If resume fails, new session with context reinjection from disk

---

## 10. API Routes (`routes/synapse.py`)

FastAPI router with prefix `/synapse`.

### Initialization

`init_synapse()` is called at app startup. It:
1. Creates `SynapseRedisClient`
2. Creates `SynapseSession`
3. Creates `SynapseOrchestrator`
4. Subscribes to Redis channels
5. Starts `FrancisListener`

### Message Routing

Incoming messages are routed by `session_id` to the correct session context, supporting multi-session operation.

### Control Commands

Francis commands (`approve`, `reject`, `revise`, `pause`, `resume`, `cancel`) are routed via `_handle_control_command()` which validates transitions and triggers orchestrator actions.
