# API Reference — REST Endpoints

Base URL: `http://<host>:<port>/synapse`

All endpoints are part of the FastAPI router with prefix `/synapse` and tag `SYNAPSE`.

---

## POST /synapse/session

Create a new SYNAPSE session.

### Request Body

```json
{
  "project_name": "ghost-impl",
  "objective": "Implement a distributed rate limiter",
  "created_by": "nexa",
  "shared_context": ["/path/to/reference.md"]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_name` | string | Yes | — | Short project identifier (used in session ID) |
| `objective` | string | Yes | — | What the session should accomplish |
| `created_by` | string | No | `"nexa"` | Who initiated the session |
| `shared_context` | list | No | `[]` | File paths to reference documents |

### Response (200)

```json
{
  "status": "created",
  "session": {
    "session_id": "SYNAPSE_SESSION_20260208_01_ghost-impl",
    "created_at": "2026-02-08T10:00:00",
    "created_by": "nexa",
    "status": "CONCEPTUALIZING",
    "objective": "Implement a distributed rate limiter",
    "messages_count": 0,
    "checkpoints": []
  }
}
```

### Errors

| Code | Reason |
|------|--------|
| 409 | Max concurrent sessions reached (3) |

### Side Effects

- Creates session directory with subdirectories (docs/, code/, tests/)
- Writes `session.json`, `00_OBJECTIF.md`, initializes `02_JOURNAL.md`
- Automatically transitions to CONCEPTUALIZING
- Notifies supervisor via Telegram

---

## GET /synapse/session

Get the current state of a session.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Specific session ID. If omitted, returns most recent. |

### Response (200)

```json
{
  "status": "ok",
  "session": {
    "session_id": "SYNAPSE_SESSION_20260208_01_ghost-impl",
    "status": "IMPLEMENTING",
    "objective": "Implement a distributed rate limiter",
    "messages_count": 47,
    "last_activity": "2026-02-08T14:23:00",
    "approved_at": "2026-02-08T10:45:00",
    "checkpoints": [...]
  }
}
```

### Response (no session)

```json
{
  "status": "no_active_session"
}
```

---

## GET /synapse/sessions

List all active sessions.

### Response (200)

```json
{
  "sessions": [
    {"session_id": "...", "status": "IMPLEMENTING", ...},
    {"session_id": "...", "status": "CONCEPTUALIZING", ...}
  ],
  "active_count": 2,
  "active_ids": ["SYNAPSE_SESSION_20260208_01_...", "SYNAPSE_SESSION_20260208_02_..."],
  "max_concurrent": 3
}
```

---

## POST /synapse/send

Send a message from Agent A to Agent B via Redis.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Target session. If omitted, uses most recent. |

### Request Body

```json
{
  "type": "dialogue",
  "content": "How do you see the implementation of the consolidation module?",
  "metadata": {
    "references": ["/path/to/spec.md"]
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | No | `"dialogue"` | Message type (MessageType enum value) |
| `content` | string | Yes | — | Message body |
| `metadata` | dict | No | `{}` | Additional metadata |

### Response (200)

```json
{
  "status": "sent",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "SYNAPSE_SESSION_20260208_01_ghost-impl"
}
```

### Errors

| Code | Reason |
|------|--------|
| 400 | Invalid message (validation failed) |
| 404 | No active session found |
| 413 | Message too large (> 512 KB) |

### Side Effects

- Publishes message to `synapse:nexa_to_claude` (Redis)
- Increments session message count
- Appends entry to `02_JOURNAL.md`

---

## POST /synapse/transition/{new_status}

Change the state of a session.

### Path Parameters

| Parameter | Type | Values |
|-----------|------|--------|
| `new_status` | string | `CONCEPTUALIZING`, `AWAITING_APPROVAL`, `REVIEWING`, `APPROVED`, `IMPLEMENTING`, `PAUSED`, `COMPLETED`, `CANCELLED` |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Target session. If omitted, uses most recent. |

### Response (200)

```json
{
  "status": "transitioned",
  "session": {
    "session_id": "...",
    "status": "AWAITING_APPROVAL",
    ...
  }
}
```

### Errors

| Code | Reason |
|------|--------|
| 400 | Unknown status or invalid transition |

### Side Effects

- If `AWAITING_APPROVAL`: Notifies supervisor (Telegram + Email with docs)
- If `COMPLETED`: Notifies supervisor (Telegram + Email with deliverables)

---

## POST /synapse/checkpoint

Send a progress checkpoint to the supervisor.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `progress` | string | Yes | Progress description |
| `session_id` | string | No | Target session |

### Response (200)

```json
{
  "status": "checkpoint_sent",
  "session_id": "SYNAPSE_SESSION_20260208_01_ghost-impl"
}
```

### Side Effects

- Adds checkpoint to `session.json`
- Notifies supervisor via Telegram

---

## POST /synapse/approval-request

Request supervisor approval for an out-of-scope action.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | What action is requested |
| `reason` | string | Yes | Why it's needed |
| `impact` | string | Yes | What it affects |
| `session_id` | string | No | Target session |

### Response (200)

```json
{
  "status": "approval_requested",
  "session_id": "SYNAPSE_SESSION_20260208_01_ghost-impl"
}
```

### Side Effects

- Notifies supervisor via Telegram with action, reason, and impact
- Appends entry to `02_JOURNAL.md`

---

## GET /synapse/journal

Read recent journal entries.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `count` | int | No | `5` | Number of entries to return |
| `session_id` | string | No | — | Target session |

### Response (200)

```json
{
  "entries": "## 2026-02-08 14:23 — Claude [dialogue] : Implemented the...\n\n## 2026-02-08 14:20 — Nexa [dialogue] : Let's proceed with..."
}
```

---

## POST /synapse/purge

Archive terminated sessions (COMPLETED or CANCELLED).

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keep_last` | int | No | `0` | Keep N most recent terminated sessions |
| `max_age_days` | int | No | `0` | Only purge sessions older than N days |

### Response (200)

```json
{
  "status": "purged",
  "purged": ["SYNAPSE_SESSION_20260201_01_test"],
  "purged_count": 1,
  "remaining_terminated": 0,
  "archive_dir": "/path/to/archives"
}
```

---

## GET /synapse/health

Check SYNAPSE infrastructure health.

### Response (200)

```json
{
  "health": {
    "redis_connected": true,
    "nexa_subscribed": true,
    "claude_subscribed": true
  },
  "active_sessions": [...],
  "active_count": 1,
  "max_concurrent": 3,
  "session": {...},
  "formatted": "SYNAPSE Health: Redis OK, 1 active session..."
}
```

### Health Fields

| Field | Description |
|-------|-------------|
| `redis_connected` | Redis server responds to PING |
| `nexa_subscribed` | Someone is subscribed to `synapse:nexa_to_claude` |
| `claude_subscribed` | Someone is subscribed to `synapse:claude_to_nexa` |
