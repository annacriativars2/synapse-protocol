# Communication Protocol

## 1. Transport Layer: Redis Pub/Sub

SYNAPSE uses Redis pub/sub as its transport layer. Redis was chosen over alternatives for these reasons:

| Alternative | Why rejected |
|-------------|-------------|
| WebSocket | Overkill for 2 participants on same machine |
| HTTP polling | Latency, race conditions (was the old system) |
| File-based | Already tried, had 10 JSON files with race conditions |
| gRPC | Too complex for the use case |
| RabbitMQ/Kafka | Overkill for 2 participants |

**Redis advantages**: Already installed, single-threaded (no race conditions), real-time delivery, simple API, zero config.

**Key design decision**: Redis has **no persistence** in SYNAPSE. It is purely a transport pipe. All important data lives on disk (session directories).

## 2. Channel Architecture

```
+------------+                                    +------------+
|            |  synapse:nexa_to_claude            |            |
|  Agent A   | --------------------------------> |  Agent B   |
|  (Nexa)    |                                    |  (Bridge)  |
|            |  synapse:claude_to_nexa            |            |
|            | <-------------------------------- |            |
+-----+------+                                    +------------+
      |
      |  synapse:francis
      | --------------------------------> Supervisor (Telegram)
      |
      |  synapse:control
      | <-------------------------------- Supervisor (Telegram)
```

### Channel Specifications

| Channel | Direction | Publisher | Subscriber | Content |
|---------|-----------|-----------|------------|---------|
| `synapse:nexa_to_claude` | A -> B | Agent A (Orchestrator) | Bridge | Work messages, iterations |
| `synapse:claude_to_nexa` | B -> A | Bridge | Agent A (Redis callback) | Responses, proposals |
| `synapse:francis` | System -> Supervisor | Agent A (notifications) | Supervisor Listener -> Telegram | Notifications, checkpoints |
| `synapse:control` | Supervisor -> System | Telegram bot | Agent A + Bridge | Commands: approve, reject, pause |

### Channel Rules

- Each channel is **unidirectional** (one publisher, one or two subscribers)
- Messages are **JSON** encoded (`SynapseMessage.to_json()`)
- Maximum message size: **512 KB** (`MAX_MESSAGE_SIZE`)
- For larger content, reference a file on disk in `metadata.references`

## 3. Message Format

### SynapseMessage Schema

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "SYNAPSE_SESSION_20260208_01_project",
  "timestamp": "2026-02-08T14:30:00.000Z",
  "sender": "nexa",
  "type": "dialogue",
  "content": "Message text content here...",
  "metadata": {
    "references": ["/path/to/file.md"],
    "in_reply_to": "uuid-of-previous-message",
    "files_modified": ["/path/to/modified/file.py"]
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID v4 | Unique identifier, serves as idempotency key |
| `session_id` | string | Reference to the active session |
| `timestamp` | ISO 8601 | UTC timestamp |
| `sender` | `"nexa"` or `"claude"` | Message author |
| `type` | MessageType enum | Message category |
| `content` | string | Message body |

### Optional Metadata

| Field | Type | Description |
|-------|------|-------------|
| `metadata.references` | string[] | Referenced files |
| `metadata.in_reply_to` | UUID | Previous message being responded to |
| `metadata.files_modified` | string[] | Files created or modified |
| `metadata.approval_scope` | string | What needs approval |
| `metadata.approval_reason` | string | Why approval is needed |

### Message Types (MessageType enum)

| Type | Usage | Example |
|------|-------|---------|
| `dialogue` | Normal working exchange | "How do you see the implementation of X?" |
| `proposal` | Formal proposal to discuss | "I propose this architecture: ..." |
| `decision` | Decision taken and logged | "We go with approach B" |
| `action` | Action executed | "Created reflection.py (245 lines)" |
| `checkpoint` | Progress update for supervisor | "Module 3 coded and tested" |
| `approval_request` | Out-of-scope request | "Need to modify api.py, not in plan" |
| `disagreement` | Argued disagreement | "I disagree because..." |
| `resume` | Context summary after restart | "Resuming session. Current state: ..." |
| `delivery` | Final deliverables | "Session complete. 9 files produced." |

## 4. Reliability Mechanisms

### 4.1 Idempotency

Both Agent A and Bridge maintain an in-memory set of processed message IDs with a 24-hour TTL.

```
Message arrives -> Check if ID in processed_ids ->
  If yes: skip (duplicate)
  If no: process, add to processed_ids
```

Old IDs are cleaned up on each check to prevent memory growth.

### 4.2 Redis Reconnection

If Redis disconnects, both sides:
1. Log the error
2. Wait `REDIS_RECONNECT_DELAY` (5 seconds)
3. Attempt reconnection
4. Re-subscribe to channels
5. Resume normal operation

The session state on disk is unaffected by Redis disconnection.

### 4.3 Fallback File

If a message cannot be published to Redis:

```python
# Atomic write: write to .tmp, then rename
temp_file = fallback_path + ".tmp"
with open(temp_file, "w") as f:
    json.dump(message, f)
os.rename(temp_file, fallback_path)
```

This ensures no partial writes. The fallback file can be replayed when Redis recovers.

### 4.4 Atomic Writes

All disk writes in SYNAPSE use the `.tmp` + `rename` pattern:

```python
temp = filepath + ".tmp"
with open(temp, "w") as f:
    f.write(content)
os.rename(temp, filepath)  # Atomic on same filesystem
```

This prevents:
- Partial writes from crashes
- Corrupt session.json files
- Incomplete journal entries

### 4.5 Journal Locking

Journal writes use `filelock.FileLock` to prevent concurrent corruption when both Agent A's orchestrator and the Redis callback write simultaneously.

```python
lock = filelock.FileLock("/tmp/synapse_journal.lock")
with lock:
    with open(journal_path, "a") as f:
        f.write(entry)
```

## 5. Scope Header Protocol

Every message from Agent A to Agent B includes a scope header:

```
[SYNAPSE:CONCEPTUALIZING] [SOURCE:orchestrator_iterate] [SCOPE:Implement GHOST Module 3]
```

This header:
- Tells Agent B the current phase
- Identifies the source of the message
- Reminds Agent B of the scope boundaries
- Is injected by the orchestrator before publishing

## 6. Delivery Notifications

When a session produces deliverables, a `delivery` message is sent with structured metadata:

```json
{
  "type": "delivery",
  "content": "Session GHOST_IMPL complete. 9 files produced.",
  "metadata": {
    "delivery": {
      "session_dir": "/path/to/session/",
      "files": [
        {"path": "/path/to/file.py", "description": "Module 3", "lines": 312}
      ],
      "channels": ["telegram", "email"]
    }
  }
}
```

The supervisor receives notifications via Telegram (real-time) and email (with attachments).
