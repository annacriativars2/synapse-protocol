# SYNAPSE Protocol

**Peer-to-peer collaboration protocol between AI agents with human supervision**

---

## What is SYNAPSE?

SYNAPSE is a collaboration protocol that enables two AI systems to work together as peers on complex tasks, under asynchronous human supervision.

Unlike orchestrator/agent models where one AI commands another, SYNAPSE implements a **peer-to-peer** relationship: both AIs contribute expertise, can disagree, and must justify their positions. A human supervisor defines objectives, approves plans, and verifies results — without being the intermediary for every message.

### Key Features

- **Peer-to-peer collaboration** — No hierarchy between AI agents
- **Phase-based workflow** — Conceptualization, Approval, Implementation
- **Documentary contract** — Approved documents define the scope of work
- **Asynchronous human supervision** — Supervisor approves plans, not every action
- **Redis pub/sub transport** — Real-time messaging with 4 unidirectional channels
- **Session persistence** — All work documented on disk, survives restarts
- **Autonomous orchestration** — LLM-driven decision engine with safeguards
- **Multi-session support** — Up to 3 concurrent isolated sessions
- **Resilience** — Idempotency, fallback files, atomic writes, reconnection

### Architecture Overview

```
                    Human Supervisor
                    (Pluggable: Telegram, Email, Custom)
                          |
              approve / reject / pause
                          |
                          v
   +------------------+   Redis   +------------------+
   |                  | --------> |                  |
   |   AI Agent A     |           |   AI Agent B     |
   |   (Thinker)      | <-------- |   (Executor)     |
   |                  |           |                  |
   +------------------+           +------------------+
           |                              |
           +--------- Shared Disk --------+
           |   Session Directory          |
           |   (objectives, plans,        |
           |    journal, results)         |
           +------------------------------+
```

### How It Works

1. **Session Creation** — Agent A creates a session with a clear objective
2. **Conceptualization** — Both agents discuss, analyze, and produce documents
3. **Approval** — Supervisor reviews and approves the plan (documentary contract)
4. **Implementation** — Agents work within the approved scope
5. **Completion** — Results documented, supervisor notified

### Communication Channels

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `synapse:agent_a_to_agent_b` | Agent A -> Agent B | Work requests, iterations |
| `synapse:agent_b_to_agent_a` | Agent B -> Agent A | Responses, proposals |
| `synapse:supervisor` | System -> Supervisor | Notifications, checkpoints |
| `synapse:control` | Supervisor -> System | Commands: approve, reject, pause |

### Session Directory Structure

```
SYNAPSE_SESSION_<YYYYMMDD>_<counter>_<project>/
+-- session.json       # Metadata: status, counters, checkpoints
+-- 00_OBJECTIVE.md    # Immutable objective
+-- 01_PLAN.md         # Approved plan (documentary contract)
+-- 02_JOURNAL.md      # Append-only collaboration log
+-- 03_RESULTS.md      # Final results
+-- docs/              # Conceptual documents
+-- code/              # Source code produced
+-- tests/             # Test results
```

### Requirements

- Python 3.10+
- Redis server

### Installation

```bash
pip install synapse-protocol

# With FastAPI support (for Agent A side)
pip install synapse-protocol[api]

# With YAML config support
pip install synapse-protocol[yaml]
```

### Quick Start

```python
from synapse.config import SynapseConfig
from synapse.session import SynapseSession
from synapse.messages import SynapseMessage, MessageType

# Create a session manager
sessions = SynapseSession()
session = sessions.create(
    project_name="my-project",
    objective="Build a REST API with authentication",
)

# Build a message
msg = SynapseMessage(
    session_id=session.session_id,
    sender=SynapseConfig.AGENT_A_ID,
    type=MessageType.DIALOGUE,
    content="Let's start by defining the API endpoints.",
)

print(msg.to_json())  # Ready for Redis publish
```

See the [Quick Start Guide](docs/guides/quickstart.md) for a complete walkthrough.

### Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/guides/installation.md) | Setup and first run |
| [Configuration Guide](docs/guides/configuration.md) | Environment variables |
| [Architecture Overview](docs/architecture/01_overview.md) | High-level design |
| [Protocol](docs/architecture/04_state_machine.md) | Session states and transitions |
| [API Reference](docs/api/endpoints.md) | REST API endpoints |
| [Security Model](docs/design/security.md) | Threats and safeguards |

### Protocol Family

SYNAPSE is designed as the foundation of a broader protocol family for structured AI communication. The core DNA — standardized message envelope, idempotency, lifecycle management, safety limits, and full traceability — adapts to different topologies: peer-to-peer, hierarchical, or contract-based.

This repository covers the peer-to-peer protocol. Other topologies are in active development.

### License

Apache 2.0 — see [LICENSE](LICENSE) for details.

---
