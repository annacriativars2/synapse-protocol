# API Reference — Redis Events

## 1. Channel Overview

SYNAPSE uses 4 Redis pub/sub channels:

| Channel | Direction | Publisher | Subscriber |
|---------|-----------|-----------|------------|
| `synapse:nexa_to_claude` | A -> B | Agent A | Bridge |
| `synapse:claude_to_nexa` | B -> A | Bridge | Agent A |
| `synapse:francis` | System -> Supervisor | Agent A | Supervisor Listener |
| `synapse:control` | Supervisor -> System | Telegram bot | Agent A + Bridge |

## 2. Event Payloads

### synapse:nexa_to_claude

Messages from Agent A to Agent B. Always a `SynapseMessage`:

```json
{
  "id": "uuid",
  "session_id": "SYNAPSE_SESSION_...",
  "timestamp": "2026-02-08T14:30:00Z",
  "sender": "nexa",
  "type": "dialogue",
  "content": "[SYNAPSE:IMPLEMENTING] [SOURCE:orchestrator_iterate] [SCOPE:...]\n\nActual message content here...",
  "metadata": {}
}
```

**Note**: The orchestrator injects a scope header at the beginning of the content field.

### synapse:claude_to_nexa

Responses from Agent B to Agent A:

```json
{
  "id": "uuid",
  "session_id": "SYNAPSE_SESSION_...",
  "timestamp": "2026-02-08T14:30:15Z",
  "sender": "claude",
  "type": "dialogue",
  "content": "Response from Agent B...",
  "metadata": {
    "files_modified": ["/path/to/file.py"]
  }
}
```

### synapse:francis

Notifications for the supervisor:

```json
{
  "id": "uuid",
  "session_id": "SYNAPSE_SESSION_...",
  "timestamp": "2026-02-08T14:30:00Z",
  "sender": "synapse",
  "type": "session_created",
  "content": "Formatted notification text for Telegram..."
}
```

**Notification types**:

| Type | Trigger |
|------|---------|
| `session_created` | New session started |
| `docs_ready` | Documents ready for review |
| `checkpoint` | Progress update |
| `approval_needed` | Out-of-scope action request |
| `disagreement` | Agent disagreement |
| `session_completed` | Session finished |
| `session_error` | Critical error |
| `notification` | Generic notification (from bridge) |

### synapse:control

Commands from the supervisor:

```json
{
  "id": "uuid",
  "session_id": "SYNAPSE_SESSION_...",
  "timestamp": "2026-02-08T14:30:00Z",
  "sender": "francis",
  "type": "control",
  "content": "approve",
  "metadata": {
    "reason": "optional reason text",
    "comment": "optional revision comment"
  }
}
```

**Control commands**:

| Command | Metadata | Effect |
|---------|----------|--------|
| `approve` | — | Approve plan or out-of-scope action |
| `reject` | `reason` | Reject with explanation |
| `revise` | `comment` | Request modifications |
| `pause` | — | Pause session |
| `resume` | — | Resume session |
| `cancel` | — | Cancel session |

## 3. Subscribing to Events

### Python Example (Agent A side)

```python
from synapse.redis_client import SynapseRedisClient
from synapse.messages import SynapseMessage

client = SynapseRedisClient()

def on_message(channel: str, message: SynapseMessage):
    print(f"[{channel}] {message.sender}: {message.content[:100]}")

client.subscribe(
    channels=["synapse:claude_to_nexa", "synapse:control"],
    callback=on_message,
)
```

### Python Example (Bridge side)

```python
import redis
import json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe("synapse:nexa_to_claude", "synapse:control")

for raw in pubsub.listen():
    if raw["type"] != "message":
        continue
    message = json.loads(raw["data"])
    print(f"Received: {message['type']} from {message['sender']}")
```

## 4. Publishing Events

### Agent A to Agent B

```python
from synapse.messages import SynapseMessage, MessageType

message = SynapseMessage(
    session_id="SYNAPSE_SESSION_...",
    sender="nexa",
    type=MessageType.DIALOGUE,
    content="Your message here",
)
client.publish_to_claude(message)
```

### Notify Supervisor

```python
client.notify_francis(
    session_id="SYNAPSE_SESSION_...",
    notification_type="checkpoint",
    content="Progress: Module 3 implementation complete",
)
```

### Supervisor Command

```python
client.publish_control(
    command="approve",
    session_id="SYNAPSE_SESSION_...",
)
```

## 5. Event Processing Rules

### Idempotency

Every subscriber maintains a set of processed message IDs:
- New message: process and add ID to set
- Duplicate message: skip silently
- IDs older than 24 hours: removed from set

### Ordering

Redis pub/sub delivers messages in order within a single channel. Cross-channel ordering is not guaranteed but is typically consistent on a single Redis instance.

### Error Handling

If a subscriber fails to process a message:
1. Error is logged
2. Message is NOT retried (pub/sub has no ack mechanism)
3. The session state on disk remains the source of truth
4. On reconnection, both sides reload from disk

### Fallback

If Redis is unavailable:
1. Message is written to `.synapse_fallback.json` (atomic write)
2. Error is logged
3. On Redis recovery, the fallback file can be replayed manually

## 6. Monitoring

### Check channel subscribers

```bash
redis-cli pubsub numsub synapse:nexa_to_claude synapse:claude_to_nexa
```

### Monitor all SYNAPSE traffic

```bash
redis-cli psubscribe "synapse:*"
```

### Check Redis health

```bash
redis-cli ping
# Expected: PONG
```

### SYNAPSE health endpoint

```bash
curl http://localhost:8000/synapse/health
```
