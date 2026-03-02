# Security Model

## 1. Threat Model

### Assets to Protect

| Asset | Risk | Impact |
|-------|------|--------|
| Session data (objectives, plans) | Unauthorized access | Business logic exposure |
| Credentials (.env) | Leakage | Account compromise |
| Redis channels | Injection | Unauthorized commands |
| File system | Unauthorized modification | Data corruption |
| Supervisor identity | Impersonation | Unauthorized approvals |

### Trust Boundaries

```
+--- Trusted (same VPS) ---+
|                           |
|  Agent A  <-> Redis <-> Bridge (Agent B)
|                           |
+---------------------------+
            |
            | (TLS)
            v
   External Services:
   - Telegram Bot API
   - Gmail SMTP
   - Claude Code CLI (Anthropic API)
```

All SYNAPSE components run on the same machine. Redis is bound to localhost. External communications use TLS.

## 2. Scope Enforcement

### Phase-Based Access Control

| Phase | Allowed Actions | Blocked Actions |
|-------|----------------|----------------|
| CONCEPTUALIZING | Read, analyze, discuss, write docs | Install, compile, execute, deploy, modify code |
| IMPLEMENTING | Actions within approved contract | Actions outside contract |
| Any phase | Read session files, write journal | Delete session files, modify 00_OBJECTIF.md |

### Blocked Patterns (CONCEPTUALIZING)

The orchestrator enforces 10 regex patterns that block execution verbs during conceptualization. The patterns support French verb conjugations:

```python
BLOCKED_PATTERNS = [
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

### Execution Contract (IMPLEMENTING)

During implementation, actions are validated against the approved scope (`execution_contract`). Out-of-scope actions trigger:
1. Automatic escalation to supervisor
2. Session may pause until approval

### Security Gates (Always Require Approval)

Certain actions always require supervisor approval regardless of contract:

| Action | Reason |
|--------|--------|
| File deletion | Irreversible data loss |
| Credential modification | Security boundary |
| Service restart | System stability |
| Git push | External visibility |
| Network configuration | Security perimeter |

## 3. Communication Security

### Redis

- **Binding**: localhost only (no external access)
- **Authentication**: None required (same-machine trust)
- **Encryption**: Not needed (localhost traffic)
- **Hardening**: Disable `CONFIG` command in production

### Telegram

- **Bot token**: Stored in `.env` (never in code)
- **Chat ID validation**: Only responds to configured supervisor chat
- **TLS**: Enforced by Telegram API

### Email (Gmail SMTP)

- **App password**: Stored in `.env` (never in code)
- **TLS**: Enforced (smtp.gmail.com:587)
- **2FA**: Required for app passwords

## 4. Secret Management

### Current Approach

Secrets stored in `.env` files:

| Secret | Location | Type |
|--------|----------|------|
| Telegram bot token | `.env` | API key |
| Telegram chat ID | `.env` | Identifier |
| Gmail address | `.env` | Email |
| Gmail app password | `.env` | Credential |
| API keys | `.env` | API key |

### Rules

- `.env` files **never** committed to version control
- `.gitignore` must include `.env`, `session.json`, `*.log`
- Credentials **never** appear in log output
- Bridge config uses localhost paths only

### File Permissions

```bash
# Session directories: owner-only access
chmod 700 /path/to/SYNAPSE_SESSION_*

# Environment files: owner-only read
chmod 600 .env

# Journal lock file
chmod 600 /tmp/synapse_journal.lock
```

### Redis Hardening

```conf
# /etc/redis/redis.conf (production)

# Bind to localhost only
bind 127.0.0.1 ::1

# Disable dangerous commands
rename-command CONFIG ""
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Set memory limit
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### For Open-Source

- Provide `.env.example` with placeholder values
- Document all required secrets
- The `.env` approach is suitable for development; for production, consider a secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.)

## 5. Data Protection

### Session Isolation

- Each session has its own directory
- Sessions cannot access each other's data
- Multi-session routing uses `session_id` from messages

### Immutable Objective

`00_OBJECTIF.md` is written once at session creation and never modified. This prevents retroactive scope changes.

### Append-Only Journal

`02_JOURNAL.md` only appends entries. Previous entries cannot be modified or deleted. This provides a tamper-evident audit trail.

### Atomic Writes

All file writes use `.tmp` + `os.rename()`:
- Prevents partial writes from crashes
- Prevents corrupt `session.json`
- Prevents incomplete journal entries

## 6. Safeguards Against Runaway

| Safeguard | Limit | Purpose |
|-----------|-------|---------|
| Max consecutive iterates | 15 | Prevent infinite loops |
| Max session messages | 150 | Prevent session explosion |
| Checkpoint interval | 2 hours | Ensure supervisor awareness |
| Max LLM failures | 3 | Prevent error cascade |
| Message size | 512 KB | Prevent memory issues |
| Concurrent sessions | 3 | Prevent resource exhaustion |

## 7. Audit and Traceability

| Event | Logged Where | Format |
|-------|-------------|--------|
| All messages | `02_JOURNAL.md` | Timestamped entries |
| State transitions | `session.json` | Status field updates |
| Supervisor decisions | `02_JOURNAL.md` | "Francis approves/rejects: reason" |
| Checkpoints | `session.json` + Telegram | Progress markers |
| Errors | Application logs | Standard logging |
| Redis traffic | Monitorable | `redis-cli psubscribe "synapse:*"` |

## 8. Recommendations for Production

1. **Redis**: Bind to localhost, disable `CONFIG`, set `maxmemory`
2. **Secrets**: Use a dedicated secrets manager (HashiCorp Vault, etc.)
3. **Monitoring**: Set up alerts for session message count, LLM failures
4. **Backup**: Regular backup of session directories
5. **Access**: Restrict file permissions on session directories
6. **Logging**: Rotate logs, exclude credentials from output
7. **Network**: Firewall Redis port (6379) from external access
