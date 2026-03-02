# Human Supervision Model

## 1. Philosophy

SYNAPSE implements a **documentary contract** model for human supervision:

> The supervisor approves a scope of work, not every individual action.

This transforms the supervisor's role from **intermediary** (passing messages between AIs) to **project director** (defining objectives, approving plans, verifying results).

### What the supervisor does

```
Supervisor in SYNAPSE:
+-- Defines the objective (before session)
+-- Approves the contract (Phase 2 - blocking)
+-- Receives checkpoints (Phase 3 - informational)
+-- Approves out-of-scope actions (Phase 3 - blocking if needed)
+-- Arbitrates disagreements (if agents can't compromise)
+-- Verifies results (end of session)
+-- Can at any time: pause, resume, cancel, check status
```

### What the supervisor does NOT do

- Relay messages between agents
- Approve every file modification
- Monitor the session in real-time
- Be available 24/7

## 2. Notification Channels

### Telegram (Real-Time)

Primary channel for time-sensitive notifications.

| Notification | When | Format |
|-------------|------|--------|
| Session created | New session starts | Session ID, objective |
| Docs ready | AWAITING_APPROVAL | Summary + file list + action buttons |
| Checkpoint | Progress milestone | Progress summary |
| Approval needed | Out-of-scope action | Action, WHY, IMPACT |
| Disagreement | Agents can't agree | Both positions |
| Session completed | Work done | Deliverables list |
| Error | Critical failure | Error details |

### Email (Gmail SMTP)

Secondary channel for document delivery.

| Email | When | Attachments |
|-------|------|-------------|
| Docs for review | AWAITING_APPROVAL | 00_OBJECTIF.md, 01_PLAN.md, docs/*.md |
| Session report | COMPLETED | 03_RESULTATS.md, code/*, tests/*, docs/* |

### VPS Direct Access

The supervisor can always access session files directly:

```bash
# View session status
cat /path/to/SYNAPSE_SESSION_<date>/session.json | jq .

# Read journal
tail -50 /path/to/SYNAPSE_SESSION_<date>/02_JOURNAL.md

# List deliverables
ls -la /path/to/SYNAPSE_SESSION_<date>/code/
```

## 3. Supervisor Commands

### Via Telegram

| Command | Action | Valid States |
|---------|--------|-------------|
| `/synapse approve` | Approve plan or out-of-scope action | AWAITING_APPROVAL, PAUSED |
| `/synapse reject [reason]` | Reject with explanation | AWAITING_APPROVAL, REVIEWING |
| `/synapse revise [comment]` | Request modifications | AWAITING_APPROVAL, REVIEWING |
| `/synapse pause` | Pause the session | Any active state |
| `/synapse resume` | Resume paused session | PAUSED |
| `/synapse cancel` | Cancel the session | Any state |
| `/synapse status` | Check current status | Any (informational) |
| `/synapse log` | Read recent journal | Any (informational) |

### Command Flow

```
Supervisor types /synapse approve
    |
    v
Telegram bot receives command
    |
    v
Bot publishes to synapse:control (Redis)
    |
    v
Agent A receives on control channel
    |
    v
_handle_control_command() processes:
    1. Resolve target session (by session_id or most recent)
    2. Validate current state allows this transition
    3. Execute transitions (AWAITING_APPROVAL -> REVIEWING -> APPROVED -> IMPLEMENTING)
    4. Trigger orchestrator handler (handle_approval)
    5. Orchestrator sends first implementation message to Agent B
```

## 4. Documentary Contract

### What is the contract?

The approved documents (primarily `01_PLAN.md`) define the exact scope of work:

- What files can be created or modified
- What actions are authorized
- What the expected deliverables are

### Contract lifecycle

```
Phase 1: Agents produce documents freely
                |
                v
Phase 2: Supervisor reads and approves
         (documents become the CONTRACT)
                |
                v
Phase 3: Agents work within contract
         (actions within scope = free execution)
         (actions outside scope = approval required)
```

### Out-of-scope detection

When the orchestrator or an agent identifies an action outside the contract:

1. Escalation message formatted with:
   - **What**: The action requested
   - **Why**: Justification
   - **Impact**: What it affects
2. Supervisor notified via Telegram
3. Session pauses (or transitions to AWAITING_APPROVAL)
4. Supervisor decides: approve, reject, or revise

## 5. Approval Iteration

Approval is not binary. The supervisor can iterate as many times as needed:

```
REVIEWING --> CONCEPTUALIZING --> AWAITING_APPROVAL --> REVIEWING --> ...
  (revise)     (modifications)     (re-submit)          (re-read)
      |
      +----> APPROVED (when supervisor is satisfied)
```

This is a dialogue, not a vote. The supervisor can:
- Ask for specific changes
- Request additional analysis
- Narrow or widen the scope
- Redirect the approach entirely

## 6. Security Gates

Certain actions **always** require supervisor approval, regardless of the contract:

| Action | Reason |
|--------|--------|
| File deletion | Irreversible |
| Credential modification | Security sensitive |
| Service restart | System stability |
| Git push | External visibility |
| Network configuration | Security boundary |

These gates are enforced by the orchestrator and cannot be bypassed by the contract.

## 7. Traceability

Every action is traceable:

| What | Where | Format |
|------|-------|--------|
| All messages | `02_JOURNAL.md` | Timestamped append-only log |
| State changes | `session.json` | Status + transition history |
| Supervisor decisions | `02_JOURNAL.md` | "Francis approves/rejects: reason" |
| Checkpoints | `session.json` + Telegram | Progress markers |
| Approvals | `session.json` | `approved_at`, `approved_scope` |

The journal is the **black box** of the collaboration. It survives:
- Agent context compression
- Agent memory flush
- Redis restart
- VPS reboot

## 8. Asynchronous Model

SYNAPSE never blocks waiting for the supervisor, except for:
1. Initial contract approval (Phase 2)
2. Out-of-scope actions
3. Unresolvable disagreements

In all other cases, the supervisor receives informational notifications and can check in at their convenience. The agents work autonomously within the approved scope.

This model is designed for scenarios where the supervisor has other responsibilities and cannot monitor the session continuously.
