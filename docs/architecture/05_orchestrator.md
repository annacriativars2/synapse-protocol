# Autonomous Orchestrator

## 1. Overview

The orchestrator is the brain of Agent A's side of SYNAPSE. It receives every response from Agent B and autonomously decides the next action using an LLM-based evaluation.

```
Agent B response (via Redis)
         |
         v
    Orchestrator
         |
    +----|----+----+----+----+
    |    |    |    |    |    |
    v    v    v    v    v    v
 ITERATE TRANSITION CHECKPOINT COMPLETE ESCALATE WAIT
```

## 2. Decision Engine

### Input

For each Agent B response, the orchestrator receives:
- The message content and type
- The current session state (status, message count, checkpoints)
- The session contract (approved scope)
- Recent journal entries

### LLM Evaluation

The orchestrator calls Agent A's LLM (`get_llm_direct()`) with a structured prompt that includes:
- Session context (objective, current phase, message history)
- Agent B's response
- Available actions and their descriptions
- Safeguard status (iterate count, message count)

The LLM returns a structured decision:

```python
@dataclass
class OrchestratorDecision:
    action: OrchestratorAction     # What to do
    message: str                   # Message to send (if ITERATE)
    transition_to: SessionStatus   # Target state (if TRANSITION)
    escalation_reason: str         # Why (if ESCALATE)
    checkpoint_message: str        # Progress text (if CHECKPOINT)
```

### Decision Flow

```
1. Check safeguards (hard limits)
   |
   +-- Max messages reached? -> PAUSE session
   +-- Max iterates reached? -> CHECKPOINT, then continue
   +-- Max LLM failures?     -> PAUSE session
   |
2. Evaluate response via LLM
   |
3. Validate decision
   |
   +-- ITERATE: check scope compliance
   +-- TRANSITION: check valid transition
   +-- ESCALATE: format notification
   |
4. Execute decision
```

## 3. Actions in Detail

### ITERATE

The most common action. Sends the next message to Agent B.

```
1. Build scope header: [SYNAPSE:<status>] [SOURCE:orchestrator_iterate] [SCOPE:<objective>]
2. Construct message with session context
3. Check CONCEPTUALIZING_BLOCKED_PATTERNS if in conceptualization phase
4. Publish to synapse:nexa_to_claude
5. Increment iterate counter
6. Log to journal
```

### TRANSITION

Changes the session state.

```
1. Validate transition (VALID_TRANSITIONS map)
2. Update session status
3. Log to journal
4. If AWAITING_APPROVAL: notify supervisor (Telegram + Email)
5. If COMPLETED: generate 03_RESULTATS.md
```

### CHECKPOINT

Sends a progress update to the supervisor.

```
1. Format checkpoint notification
2. Publish to synapse:francis
3. Forward to Telegram
4. Add checkpoint to session.json
5. Reset iterate counter
```

### COMPLETE

Closes the session.

```
1. Generate 03_RESULTATS.md with:
   - Session objective
   - Summary of work done
   - List of deliverables
   - Statistics (messages, duration)
2. Transition to COMPLETED
3. Notify supervisor (Telegram + Email with attachments)
4. Discover deliverables (code/, tests/, docs/)
5. Send email with attachments
```

### ESCALATE

Requests supervisor intervention.

```
1. Format escalation with:
   - What action is requested
   - Why it's out of scope
   - Impact assessment
2. Notify supervisor via Telegram
3. Pause session or wait
4. Session blocked until supervisor decides
```

### WAIT

Does nothing. Used when:
- Session is in AWAITING_APPROVAL
- Session is PAUSED
- Waiting for external event

## 4. Safeguards (Hard Limits)

| Safeguard | Limit | Trigger | Action |
|-----------|-------|---------|--------|
| Consecutive iterates | 15 | Anti-infinite-loop | Auto-checkpoint, then continue |
| Session messages | 150 | Prevent explosion | Pause session |
| Checkpoint interval | 2 hours | Keep supervisor informed | Auto-checkpoint |
| LLM failures | 3 consecutive | Prevent cascade | Pause session |

### How safeguards work

```python
# Before every LLM evaluation:
if consecutive_iterates >= MAX_CONSECUTIVE_ITERATES:
    # Force checkpoint, reset counter
    return OrchestratorDecision(action=CHECKPOINT, ...)

if session.messages_count >= MAX_SESSION_MESSAGES:
    # Force pause
    return OrchestratorDecision(action=TRANSITION, transition_to=PAUSED, ...)

if time_since_last_checkpoint > CHECKPOINT_INTERVAL_HOURS:
    # Force checkpoint
    return OrchestratorDecision(action=CHECKPOINT, ...)
```

Safeguards are checked **before** the LLM evaluation, so they override any LLM decision.

## 5. Scope Enforcement

### During CONCEPTUALIZING

10 regex patterns block execution verbs:

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

If Agent B's response or the orchestrator's intended message matches any pattern during conceptualization, the action is blocked and logged.

### During IMPLEMENTING

The orchestrator validates actions against the `execution_contract` — the approved scope from the supervisor. If an action falls outside the contract:

1. Orchestrator detects out-of-scope
2. Escalation message sent to supervisor
3. Session may transition to AWAITING_APPROVAL for the new scope
4. Supervisor approves or rejects

## 6. Disagreement Resolution

If Agent A and Agent B disagree:

```
1. Agent with disagreement sends message type: "disagreement"
2. Orchestrator detects disagreement type
3. Both positions are logged in journal
4. Orchestrator attempts compromise (via LLM evaluation)
5. If no compromise:
   a. Format disagreement notification
   b. Send to supervisor via Telegram
   c. Include both positions
   d. Supervisor arbitrates
```

## 7. Session Handlers

The orchestrator exposes specific handlers for supervisor commands:

| Handler | Trigger | Action |
|---------|---------|--------|
| `handle_approval(session_id)` | Supervisor approves | Transition to IMPLEMENTING, send first implementation message |
| `handle_resume(session_id)` | Supervisor resumes | Reload context, send resume message to Agent B |
| `handle_revision(session_id, comment)` | Supervisor requests revision | Transition to CONCEPTUALIZING, forward comment |
