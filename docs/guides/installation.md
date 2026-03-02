# Installation Guide

## Prerequisites

| Requirement | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Runtime |
| Redis | 6.0+ | Pub/sub messaging |
| pip | latest | Package management |
| Claude Code CLI | latest | Bridge component (optional) |

## 1. Install Redis

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install redis-server

# Start and enable
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Expected: PONG
```

## 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install redis filelock fastapi pydantic uvicorn
```

### Dependency List

| Package | Version | Purpose |
|---------|---------|---------|
| `redis` | >=4.0 | Redis pub/sub client |
| `filelock` | >=3.0 | Journal file locking |
| `fastapi` | >=0.100 | API server (Agent A side) |
| `pydantic` | >=2.0 | Request/response validation |
| `uvicorn` | >=0.20 | ASGI server |

## 3. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Session storage
SYNAPSE_WORKSPACE=/path/to/workspace

# Notifications (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email notifications (optional)
NEXA_GMAIL_ADDRESS=your_email@gmail.com
NEXA_GMAIL_APP_PASSWORD=your_app_password
SUPERVISOR_EMAIL=supervisor@example.com
```

See [Configuration Guide](configuration.md) for all available variables.

## 4. Verify Installation

### Check Redis connectivity

```bash
python3 -c "import redis; r = redis.Redis(); print('OK' if r.ping() else 'FAIL')"
```

### Check SYNAPSE modules

```bash
python3 -c "
from synapse.config import SynapseConfig
from synapse.messages import SynapseMessage, MessageType, SessionStatus
from synapse.redis_client import SynapseRedisClient
from synapse.session import SynapseSession
print('All SYNAPSE modules loaded successfully')
"
```

### Check health endpoint (if API server is running)

```bash
curl http://localhost:8000/synapse/health
```

Expected response:

```json
{
  "health": {
    "redis_connected": true,
    "nexa_subscribed": false,
    "claude_subscribed": false
  },
  "active_sessions": [],
  "active_count": 0,
  "max_concurrent": 3
}
```

## 5. Start the Services

### Agent A side (API server)

```bash
# Start the FastAPI server
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Bridge side (Agent B connector)

```bash
# Start the bridge
python3 synapse/bridge.py
```

### Production deployment (systemd)

```ini
# /etc/systemd/system/synapse-bridge.service
[Unit]
Description=SYNAPSE Bridge
After=redis-server.service

[Service]
ExecStart=/path/to/venv/bin/python -m synapse.bridge
WorkingDirectory=/path/to/workspace
Restart=always
User=your_user

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable synapse-bridge
sudo systemctl start synapse-bridge
```

## 6. First Session (Quick Test)

Create a test session via the API:

```bash
curl -X POST http://localhost:8000/synapse/session \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test",
    "objective": "Test session to verify SYNAPSE installation",
    "created_by": "admin"
  }'
```

Check session status:

```bash
curl http://localhost:8000/synapse/session
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `redis.ConnectionError` | Check Redis is running: `systemctl status redis-server` |
| `ModuleNotFoundError: synapse` | Ensure you're in the correct virtualenv and working directory |
| Bridge timeout (1800s) | Increase `CLAUDE_PROCESS_TIMEOUT` in config |
| Session not found | Check `SESSIONS_BASE_DIR` points to the correct directory |
| Email not sending | Verify Gmail app password (not regular password) |
