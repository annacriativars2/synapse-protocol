# SYNAPSE Tests — Shared fixtures
# All filesystem tests use tmp_path to avoid touching real directories.

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from synapse.config import SynapseConfig
from synapse.messages import SessionData, SessionStatus


@pytest.fixture
def tmp_sessions_dir(tmp_path):
    """Temporary directory for SYNAPSE sessions."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    return sessions


@pytest.fixture
def tmp_archives_dir(tmp_path):
    """Temporary directory for SYNAPSE archives."""
    archives = tmp_path / "archives"
    archives.mkdir()
    return archives


@pytest.fixture
def config_override(tmp_sessions_dir, tmp_archives_dir, tmp_path):
    """Patches SynapseConfig to use temporary directories.

    Every test that touches the filesystem should use this fixture
    so nothing is written outside of the tmp_path.
    """
    patches = {
        "SESSIONS_BASE_DIR": str(tmp_sessions_dir),
        "ARCHIVES_DIR": str(tmp_archives_dir),
        "JOURNAL_LOCK_PATH": str(tmp_path / ".synapse_journal.lock"),
        "FALLBACK_FILE": str(tmp_path / ".synapse_fallback.json"),
    }
    with patch.multiple(SynapseConfig, **patches):
        yield patches


@pytest.fixture
def sample_session():
    """Creates a minimal SessionData for use in tests."""
    now = datetime.now(timezone.utc).isoformat()
    return SessionData(
        session_id="SYNAPSE_SESSION_20260313_01_test",
        created_at=now,
        created_by="agent_a",
        status=SessionStatus.CREATED,
        objective="Write functional tests for SYNAPSE",
        shared_context=["ref_doc_1.md"],
        last_activity=now,
    )
