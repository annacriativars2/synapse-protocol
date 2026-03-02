# Quickstart Guide

## Complete Session Walkthrough

This guide walks through a complete SYNAPSE session from creation to completion.

### Prerequisites

- Redis running on localhost:6379
- Agent A API running on localhost:8000
- Bridge running (synapse/bridge.py)

---

## Step 1: Create a Session

```bash
curl -X POST http://localhost:8000/synapse/session \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "hello-synapse",
    "objective": "Write a Python utility that validates email addresses",
    "created_by": "admin"
  }'
```

**What happens**:
- Session directory created: `SYNAPSE_SESSION_<date>_01_hello-synapse/`
- `00_OBJECTIF.md` written with the objective
- `02_JOURNAL.md` initialized
- Status auto-transitions to CONCEPTUALIZING
- Supervisor notified via Telegram

**Response**:
```json
{
  "status": "created",
  "session": {
    "session_id": "SYNAPSE_SESSION_20260208_01_hello-synapse",
    "status": "CONCEPTUALIZING"
  }
}
```

## Step 2: Conceptualization Phase

Send messages between Agent A and Agent B to discuss the approach:

```bash
# Agent A sends first message to Agent B
curl -X POST http://localhost:8000/synapse/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "dialogue",
    "content": "We need to create an email validator. What approach do you recommend? Consider RFC 5322 compliance and common edge cases."
  }'
```

Agent B receives the message via Redis, processes it, and responds. The orchestrator then decides the next action.

This back-and-forth continues until the agents have a plan.

## Step 3: Submit for Approval

When the plan is ready:

```bash
curl -X POST http://localhost:8000/synapse/transition/AWAITING_APPROVAL
```

**What happens**:
- Supervisor receives Telegram notification with document summary
- Supervisor receives email with docs attached
- Session pauses until supervisor responds

## Step 4: Supervisor Review

Supervisor reads the documents and decides:

```bash
# Option A: Approve
/synapse approve

# Option B: Request changes
/synapse revise "Add support for international email addresses"

# Option C: Reject
/synapse reject "Not the right approach"
```

If approved, session auto-transitions: REVIEWING -> APPROVED -> IMPLEMENTING.

## Step 5: Implementation Phase

The orchestrator sends the first implementation message to Agent B. Agent B begins coding within the approved scope.

Monitor progress:

```bash
# Check session status
curl http://localhost:8000/synapse/session

# Read journal
curl "http://localhost:8000/synapse/journal?count=10"
```

Checkpoints are sent to the supervisor automatically.

## Step 6: Completion

When the work is done, the orchestrator generates results:

```bash
curl -X POST http://localhost:8000/synapse/transition/COMPLETED
```

**What happens**:
- `03_RESULTATS.md` written with summary and deliverables
- Supervisor notified via Telegram
- Supervisor receives email with final files
- Session archived

## Step 7: Verify Results

```bash
# List session files
ls SYNAPSE_SESSION_20260208_01_hello-synapse/

# Read results
cat SYNAPSE_SESSION_20260208_01_hello-synapse/03_RESULTATS.md

# Check code
ls SYNAPSE_SESSION_20260208_01_hello-synapse/code/
```

---

## Monitoring During a Session

### Health check

```bash
curl http://localhost:8000/synapse/health
```

### Redis traffic

```bash
redis-cli psubscribe "synapse:*"
```

### Journal

```bash
curl "http://localhost:8000/synapse/journal?count=5"
```

### Session status

```bash
curl http://localhost:8000/synapse/session
```

---

## Common Workflows

### Pause and Resume

```bash
# Supervisor pauses
/synapse pause

# Later, supervisor resumes
/synapse resume
```

### Out-of-Scope Action

During implementation, if Agent B needs to do something outside the plan:

1. Orchestrator detects the out-of-scope action
2. Sends approval request to supervisor
3. Session waits for supervisor decision

```bash
# Supervisor approves the additional action
/synapse approve
```

### Multiple Sessions

Create up to 3 concurrent sessions:

```bash
# Session 1
curl -X POST http://localhost:8000/synapse/session \
  -d '{"project_name": "feature-a", "objective": "..."}'

# Session 2
curl -X POST http://localhost:8000/synapse/session \
  -d '{"project_name": "feature-b", "objective": "..."}'

# Target a specific session
curl -X POST "http://localhost:8000/synapse/send?session_id=SYNAPSE_SESSION_20260208_02_feature-b" \
  -d '{"content": "..."}'
```

### Archive Old Sessions

```bash
curl -X POST http://localhost:8000/synapse/purge
```
