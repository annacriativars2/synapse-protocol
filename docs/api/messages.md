# API Reference — Message Schemas

## 1. SynapseMessage

The fundamental unit of communication in SYNAPSE.

### Schema

```json
{
  "id": "string (UUID v4)",
  "session_id": "string",
  "timestamp": "string (ISO 8601)",
  "sender": "string (nexa|claude)",
  "type": "string (MessageType)",
  "content": "string",
  "metadata": "object (optional)"
}
```

### Fields

| Field | Type | Required | Auto-generated | Description |
|-------|------|----------|----------------|-------------|
| `id` | UUID v4 | Yes | Yes (on creation) | Unique identifier, idempotency key |
| `session_id` | string | Yes | No | Session this message belongs to |
| `timestamp` | ISO 8601 | Yes | Yes (on creation) | UTC creation time |
| `sender` | string | Yes | No | `"nexa"` or `"claude"` |
| `type` | MessageType | Yes | No | Message category |
| `content` | string | Yes | No | Message body (max 512 KB) |
| `metadata` | object | No | No | Additional context |

### Validation Rules

- `id` must be a valid UUID v4
- `session_id` must not be empty
- `sender` must be `"nexa"` or `"claude"`
- `type` must be a valid MessageType value
- `content` must not be empty
- Total serialized size must not exceed `MAX_MESSAGE_SIZE` (512 KB)

---

## 2. MessageType Enum

| Value | Purpose | Typical Sender |
|-------|---------|----------------|
| `dialogue` | Normal working exchange | Either |
| `proposal` | Formal proposal to discuss | Either |
| `decision` | Decision taken and logged | Either |
| `action` | Action executed and reported | Agent B |
| `checkpoint` | Progress update for supervisor | Agent A |
| `approval_request` | Request for out-of-scope action | Either |
| `disagreement` | Argued disagreement | Either |
| `resume` | Context recovery after restart | Either |
| `delivery` | Final deliverables notification | Agent A |

### Usage Guidelines

| Scenario | Use type |
|----------|----------|
| "How should we implement X?" | `dialogue` |
| "I propose this architecture..." | `proposal` |
| "We go with approach B" | `decision` |
| "Created file.py (245 lines)" | `action` |
| "Module 3 coded and tested" | `checkpoint` |
| "Need to modify api.py, not in plan" | `approval_request` |
| "I disagree because..." | `disagreement` |
| "Resuming session. Current state..." | `resume` |
| "Session complete. 9 files produced." | `delivery` |

---

## 3. Metadata Fields

### Standard Metadata

| Field | Type | When used |
|-------|------|-----------|
| `references` | string[] | Files referenced in the message |
| `in_reply_to` | UUID | Responding to a specific message |
| `files_modified` | string[] | Files created or modified by an action |

### Approval Metadata

| Field | Type | When used |
|-------|------|-----------|
| `approval_scope` | string | Description of what needs approval |
| `approval_reason` | string | Why the action is needed (required for approval_request) |

### Delivery Metadata

| Field | Type | When used |
|-------|------|-----------|
| `delivery.session_dir` | string | Path to session directory |
| `delivery.files` | array | List of deliverable files |
| `delivery.files[].path` | string | File path |
| `delivery.files[].description` | string | File description |
| `delivery.files[].lines` | int | Line count |
| `delivery.channels` | string[] | Notification channels ("telegram", "email") |

### Control Metadata (supervisor commands)

| Field | Type | When used |
|-------|------|-----------|
| `reason` | string | Reason for rejection |
| `comment` | string | Revision feedback |

---

## 4. SessionStatus Enum

| Value | Description |
|-------|-------------|
| `CREATED` | Session initiated, directory created |
| `CONCEPTUALIZING` | Agents discuss freely, produce documents |
| `AWAITING_APPROVAL` | Documents ready, supervisor notified |
| `REVIEWING` | Supervisor is reading and commenting |
| `APPROVED` | Supervisor validated the contract |
| `IMPLEMENTING` | Work in progress within approved scope |
| `PAUSED` | Session paused |
| `COMPLETED` | Work done, results delivered |
| `CANCELLED` | Session cancelled |

---

## 5. SessionData

Session metadata stored in `session.json`.

### Schema

```json
{
  "session_id": "string",
  "created_at": "string (ISO 8601)",
  "created_by": "string",
  "status": "string (SessionStatus)",
  "objective": "string",
  "working_directory": "string",
  "claude_code_session_id": "string (nullable)",
  "shared_context": ["string"],
  "approved_at": "string (ISO 8601, nullable)",
  "approved_scope": ["string"],
  "contract": "string (nullable)",
  "execution_contract": "string (nullable)",
  "messages_count": "integer",
  "last_activity": "string (ISO 8601)",
  "checkpoints": [
    {
      "at": "string (ISO 8601)",
      "type": "string (info|safeguard|time)",
      "message": "string"
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `created_at` | ISO 8601 | Creation timestamp |
| `created_by` | string | Who initiated (nexa, francis) |
| `status` | SessionStatus | Current state |
| `objective` | string | Session objective |
| `working_directory` | string | Session directory path |
| `claude_code_session_id` | string? | Agent B CLI session ID for --resume |
| `shared_context` | string[] | Reference file paths |
| `approved_at` | ISO 8601? | When supervisor approved |
| `approved_scope` | string[] | What actions are authorized |
| `contract` | string? | Conceptualization scope text |
| `execution_contract` | string? | Implementation scope text |
| `messages_count` | int | Total messages exchanged |
| `last_activity` | ISO 8601 | Last message timestamp |
| `checkpoints` | array | Progress markers |

---

## 6. Serialization

### SynapseMessage

```python
# Serialize
message = SynapseMessage(
    session_id="SYNAPSE_SESSION_20260208_01_test",
    sender="nexa",
    type=MessageType.DIALOGUE,
    content="Hello Claude",
)
json_str = message.to_json()

# Deserialize
message = SynapseMessage.from_json(json_str)
```

### SessionData

```python
# Serialize
data = session.to_dict()
json.dump(data, file)

# Deserialize
data = json.load(file)
session = SessionData.from_dict(data)
```

---

## 7. State Transition Validation

Transitions are validated against the `VALID_TRANSITIONS` map:

```python
VALID_TRANSITIONS = {
    SessionStatus.CREATED:            [SessionStatus.CONCEPTUALIZING],
    SessionStatus.CONCEPTUALIZING:    [SessionStatus.AWAITING_APPROVAL, SessionStatus.PAUSED],
    SessionStatus.AWAITING_APPROVAL:  [SessionStatus.REVIEWING, SessionStatus.CONCEPTUALIZING],
    SessionStatus.REVIEWING:          [SessionStatus.CONCEPTUALIZING, SessionStatus.APPROVED, SessionStatus.CANCELLED],
    SessionStatus.APPROVED:           [SessionStatus.IMPLEMENTING],
    SessionStatus.IMPLEMENTING:       [SessionStatus.PAUSED, SessionStatus.COMPLETED, SessionStatus.AWAITING_APPROVAL],
    SessionStatus.PAUSED:             [SessionStatus.IMPLEMENTING, SessionStatus.CONCEPTUALIZING],
}
```

Invalid transitions raise `ValueError`. CANCELLED is a special case reachable from any state.
