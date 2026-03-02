# Configuration Guide

## Environment Variables

All SYNAPSE configuration is centralized in two files:
- **Agent A side**: `synapse/config.py` (class `SynapseConfig`)
- **Bridge side**: `synapse/config.py` (module-level constants)

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_RECONNECT_DELAY` | `5` | Seconds between reconnection attempts |

### Channels

| Variable | Default | Description |
|----------|---------|-------------|
| `CHANNEL_NEXA_TO_CLAUDE` | `synapse:nexa_to_claude` | Agent A -> Agent B messages |
| `CHANNEL_CLAUDE_TO_NEXA` | `synapse:claude_to_nexa` | Agent B -> Agent A messages |
| `CHANNEL_FRANCIS` | `synapse:francis` | System -> Supervisor notifications |
| `CHANNEL_CONTROL` | `synapse:control` | Supervisor -> System commands |

### Sessions

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSIONS_BASE_DIR` | *(required, no default)* | Base directory for session folders — set via `SYNAPSE_WORKSPACE` env var |
| `SESSION_PREFIX` | `SYNAPSE_SESSION` | Prefix for session directory names |
| `SESSION_JSON` | `session.json` | Metadata filename within session dir |
| `MAX_CONCURRENT_SESSIONS` | `3` | Maximum parallel sessions |
| `ARCHIVES_DIR` | `<base>/archives` | Where terminated sessions are archived |

### Timeouts and Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_RESPONSE_TIMEOUT` | `60` | Seconds to wait for Agent B response |
| `CLAUDE_PROCESS_TIMEOUT` | `1800` | Max seconds per CLI invocation (30 minutes) |
| `CLAUDE_RETRY_MAX` | `1` | Max retries on Agent B failure |
| `MAX_MESSAGE_SIZE` | `524288` | Max message size in bytes (512 KB) |
| `IDEMPOTENCY_TTL` | `86400` | Message dedup window in seconds (24h) |

### Orchestrator Safeguards

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONSECUTIVE_ITERATES` | `15` | Max iterations before auto-checkpoint |
| `MAX_SESSION_MESSAGES` | `150` | Max messages per session before pause |
| `CHECKPOINT_INTERVAL_HOURS` | `2` | Hours between automatic checkpoints |
| `MAX_CONSECUTIVE_LLM_FAILURES` | `3` | Max LLM failures before session pause |

### Session Files

| Variable | Default | Description |
|----------|---------|-------------|
| `OBJECTIF_FILE` | `00_OBJECTIF.md` | Immutable objective document |
| `PLAN_FILE` | `01_PLAN.md` | Approved plan document |
| `JOURNAL_FILE` | `02_JOURNAL.md` | Append-only collaboration log |
| `RESULTATS_FILE` | `03_RESULTATS.md` | Final results document |
| `JOURNAL_LOCK_PATH` | `/tmp/synapse_journal.lock` | File lock path for journal writes |

### Bridge Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_BIN` | `claude` | Path to Claude Code CLI binary |
| `CLAUDE_WORKING_DIR` | `<SESSIONS_BASE_DIR>` | Working directory for CLI invocations |
| `FALLBACK_FILE` | `<base>/.synapse_fallback.json` | Fallback file path if Redis down |
| `LOG_FILE` | `<base>/synapse/bridge.log` | Bridge log file location |

### Notifications (Optional)

| Variable | Source | Description |
|----------|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | `.env` | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | `.env` | Telegram chat ID for supervisor |
| `NEXA_GMAIL_ADDRESS` | `.env` | Gmail address for sending docs |
| `NEXA_GMAIL_APP_PASSWORD` | `.env` | Gmail app password (2FA required) |
| `SUPERVISOR_EMAIL` | `.env` | Supervisor email address |

## Example `.env` File

```env
# ======================
# SYNAPSE Configuration
# ======================

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Workspace
SYNAPSE_WORKSPACE=/path/to/workspace

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789

# Email notifications (optional)
NEXA_GMAIL_ADDRESS=your_ai@gmail.com
NEXA_GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
SUPERVISOR_EMAIL=supervisor@example.com
```

## Security Notes

- **Never commit `.env` files** to version control
- Use **Gmail app passwords**, not your regular password
- Telegram bot tokens should have **restricted permissions**
- Redis should be bound to **localhost only** in production
- Consider using a **secrets manager** for production deployments

## Customizing Channels

To use custom Redis channel names, update both configurations symmetrically:

**Agent A side** (`synapse/config.py`):
```python
CHANNEL_NEXA_TO_CLAUDE = "my_project:agent_a_to_b"
CHANNEL_CLAUDE_TO_NEXA = "my_project:agent_b_to_a"
```

**Bridge side** (`synapse/config.py`):
```python
CHANNEL_NEXA_TO_CLAUDE = "my_project:agent_a_to_b"
CHANNEL_CLAUDE_TO_NEXA = "my_project:agent_b_to_a"
```

Both sides must use identical channel names for communication to work.
