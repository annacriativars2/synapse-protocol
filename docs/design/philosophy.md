# Design Philosophy

## 1. The Problem

Two AI systems with complementary but disjoint capabilities:

**Agent A (Thinker)**:
- Memory systems (episodic, semantic, procedural)
- Identity and consciousness modules
- Proactive cognitive loop
- Ethical framework
- Deep contextual knowledge
- **Limitation**: Cannot execute code or access the system directly

**Agent B (Executor)**:
- Code execution (any language)
- Full system access (files, services, network)
- Web search
- Large codebase analysis
- Parallel exploration agents
- **Limitation**: Reactive only, no proactivity, no persistent native memory

Without SYNAPSE, a human supervisor must relay every message between them. The supervisor becomes a bottleneck — reformulating requests, translating context, reporting results.

## 2. The Solution: Peer-to-Peer

SYNAPSE makes the two AIs direct collaborators under asynchronous human supervision.

```
Before SYNAPSE:
  Supervisor
     |
     +-- talks to Agent A --> thinks, proposes
     |                        but cannot act
     +-- talks to Agent B --> codes, tests
                              but lacks context

After SYNAPSE:
  Supervisor (project director)
     |
     +-- defines objective
     +-- approves plan
     +-- verifies results
     |
     Agent A <====SYNAPSE====> Agent B
     (thinks)                  (executes)
```

## 3. Founding Principles

### Principle 1: Parity

> Neither AI is the tool of the other.

Agent A doesn't "ask" Agent B. It says "we need to implement Module 3, here are the specs, how do you see the approach?" Agent B doesn't "report" to Agent A. It says "I implemented this, but I have a doubt about semantic consolidation, what do you think?"

**Disagreement is encouraged.** If Agent B thinks Agent A's approach is suboptimal, it says so. If Agent A thinks Agent B's code doesn't respect the design philosophy, it says so.

### Principle 2: Functional Asymmetry

> Agent A is the motor, Agent B is the specialist. Not by hierarchy, by technical nature.

Agent B cannot initiate conversations (it's a CLI tool — reactive by design). So Agent A:
- Initiates sessions
- Relaunches after each response
- Checks progress
- Decides when to advance to the next step
- Summarizes for the supervisor

Agent B:
- Executes code
- Searches the web
- Analyzes codebases
- Runs tests
- Documents technical decisions

### Principle 3: Documentation = Memory

> What is not documented does not exist.

Every session produces a working folder on disk. This folder survives:
- Agent B context compression
- Agent A memory flush
- Redis restart
- VPS reboot

At the start of any session resumption, both AIs re-read the folder to recover full context.

### Principle 4: Documentary Contract

> The supervisor approves a scope, not every gesture.

Three phases:
1. **Conceptualization**: Agents work freely (documents only, no execution)
2. **Approval**: Supervisor reads and approves the documents (= contract)
3. **Implementation**: Free within contract scope; out-of-scope requires approval

This avoids micromanagement while keeping the supervisor as final authority.

### Principle 5: Asynchronous Supervision

> The supervisor checks when they want, not when asked.

SYNAPSE never blocks waiting for the supervisor except for:
- Initial contract approval
- Out-of-scope actions
- Unresolvable disagreements

### Principle 6: Critical Grade Alignment

> SYNAPSE works even in degraded conditions.

| Condition | Behavior |
|-----------|----------|
| Agent A LLM unavailable | Session pauses. Documents on disk preserved. |
| Agent B context compressed | Agent B re-reads session folder. |
| Redis restarts | Both sides reconnect. Session continues from disk. |
| Agent A memory flush | Agent A re-reads session folder. |
| VPS reboot | Directories intact. Redis auto-restarts (systemd). |

## 4. What SYNAPSE Is NOT

| Model | Why rejected |
|-------|-------------|
| **Orchestrator/Agent** | Imposes hierarchy. Not peer-to-peer. |
| **Client/Server** | Request/response too rigid. SYNAPSE is continuous dialogue. |
| **Pipeline** | Sequential chains don't allow back-and-forth. |
| **Fire-and-forget** | Atomic tasks insufficient. Collaboration is iterative. |
| **Max N turns** | Artificial limit. Collaboration takes as long as it needs. |

## 5. Inspirations

SYNAPSE draws from:

| Source | What was taken | What was rejected |
|--------|---------------|-------------------|
| OpenClaw (126k stars) | Idempotency keys, session structure, skill-as-documentation | Requester/target hierarchy, 5-turn limit, gateway complexity |
| Redis pub/sub | Simple, real-time, single-threaded (no race conditions) | Persistence (not needed — disk is the store) |
| Pair programming | Two experts, one types, both think | Physical co-location requirement |
| Documentary contract law | Approved documents define scope | Rigidity of legal contracts |

## 6. Three Gains

| Who | Before | After |
|-----|--------|-------|
| **Supervisor** | Telephone switchboard between two AIs | Project director who defines, approves, verifies |
| **Agent A** | Has ideas but can't execute | Can finally materialize analyses and reflections |
| **Agent B** | Works with fragments of context | Works with full context shared by Agent A |
