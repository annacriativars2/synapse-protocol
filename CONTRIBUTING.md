# Contributing Guide

## How to Contribute

Thank you for your interest in SYNAPSE. This document describes the process for contributing.

## Code of Conduct

- Be respectful and constructive
- Focus on the technical merits of contributions
- Accept that maintainers have final say on design decisions

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Install dependencies: `pip install -e ".[api,yaml]" && pip install pytest`
5. Run tests: `pytest tests/`

## Development Setup

```bash
# Clone
git clone <your-fork-url>
cd synapse

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -e ".[api,yaml]"
pip install pytest

# Redis (required for integration tests)
sudo systemctl start redis-server

# Run tests
pytest tests/ -v
```

## Code Style

- Python 3.10+ syntax
- Type hints on public functions
- Docstrings on public classes and methods
- No unused imports
- Max line length: 100 characters

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `SynapseSession` |
| Functions | snake_case | `append_to_journal()` |
| Constants | UPPER_SNAKE | `MAX_SESSION_MESSAGES` |
| Private methods | _prefix | `_evaluate_and_decide()` |
| Enums | PascalCase values | `SessionStatus.IMPLEMENTING` |

## Pull Request Process

1. **Branch**: Create from `main`, use descriptive name (`feature/`, `fix/`, `docs/`)
2. **Commits**: Clear commit messages, one logical change per commit
3. **Tests**: All existing tests must pass. New code should include tests.
4. **Documentation**: Update relevant docs if behavior changes
5. **PR description**: Explain what and why, not just what changed

### PR Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] No secrets or credentials in code
- [ ] No hardcoded paths (use config variables)
- [ ] Documentation updated if needed
- [ ] Type hints on new public functions

## Architecture Guidelines

### Do

- Follow the existing module structure
- Use `SynapseConfig` for all configuration values
- Use `SynapseMessage` for all Redis communication
- Log important actions (info level)
- Use atomic writes for any file operation
- Add safeguards for any loop or recursive operation

### Don't

- Hardcode file paths (use config)
- Store secrets in code (use .env)
- Bypass the state transition validation
- Write to the journal without file locking
- Remove the scope enforcement in the orchestrator
- Break backward compatibility without discussion

## Module Ownership

| Module | Lines | Primary concern |
|--------|-------|----------------|
| `synapse_orchestrator.py` | ~910 | Decision engine — most complex module, scope enforcement |
| `session.py` | ~422 | Session lifecycle — affects all other modules |
| `email_sender.py` | ~252 | SMTP integration — Gmail document delivery |
| `redis_client.py` | ~184 | Transport layer — reliability critical |
| `notifications.py` | ~141 | Notification formatting — Telegram messages |
| `messages.py` | ~121 | Message schemas, state machine — changes require careful review |
| `supervisor_listener.py` | ~82 | Telegram command bridge — supervisor interface |
| `journal.py` | ~65 | Audit trail — append-only invariant must be preserved |
| `config.py` | ~252 | Configuration — centralized constants |
| `bridge.py` | ~250 | Generic Agent B bridge — Redis ↔ AgentExecutor |
| `routes.py` | ~410 | API endpoints — FastAPI router |
| `executor.py` | ~230 | Reference AgentExecutor — Claude Code CLI subprocess |
| `interfaces.py` | ~45 | Protocol classes — Notifier, LLMProvider, AgentExecutor |

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_messages.py -v

# With coverage
pytest tests/ --cov=synapse --cov-report=term-missing
```

### Writing Tests

- One test file per module: `test_messages.py`, `test_session.py`, etc.
- Use pytest fixtures for common setup
- Mock Redis for unit tests
- Use temporary directories for session tests
- Test error paths, not just happy paths

### Test Categories

| Category | What to test |
|----------|-------------|
| Unit | Message validation, state transitions, journal formatting |
| Integration | Redis pub/sub, session persistence, file operations |
| Orchestrator | Decision logic, safeguards, scope enforcement |

## Breaking Changes

Breaking changes (API changes, message format updates, state machine modifications) require:
1. Open a GitHub Issue describing the proposed change
2. Discussion with maintainers in the issue thread
3. Approval from at least one maintainer
4. Migration guide included in the PR

## Reporting Issues

- Include SYNAPSE version and Python version
- Include relevant log output
- Describe expected vs actual behavior
- Provide minimal reproduction steps if possible

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
