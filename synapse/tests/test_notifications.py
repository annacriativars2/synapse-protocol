# SYNAPSE Tests — Notifications
# Validates that format_* functions produce non-empty, correct output.

import pytest

from synapse.config import SynapseConfig
from synapse.messages import SessionData, SessionStatus
from synapse import notifications


@pytest.fixture
def session():
    """Minimal SessionData for notification tests."""
    return SessionData(
        session_id="SYNAPSE_SESSION_20260313_01_notif",
        created_at="2026-03-13T10:00:00+00:00",
        created_by="agent_a",
        status=SessionStatus.IMPLEMENTING,
        objective="Build notification tests",
        messages_count=12,
        last_activity="2026-03-13T12:00:00+00:00",
    )


class TestFormatSessionCreated:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_session_created(session)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_session_id(self, session):
        result = notifications.format_session_created(session)
        assert session.session_id in result

    def test_contains_objective(self, session):
        result = notifications.format_session_created(session)
        assert session.objective in result


class TestFormatDocsReady:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_docs_ready(session)
        assert len(result) > 0

    def test_contains_approval_actions(self, session):
        result = notifications.format_docs_ready(session)
        assert "/synapse approve" in result


class TestFormatCheckpoint:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_checkpoint(session, "50% done")
        assert len(result) > 0

    def test_contains_progress_text(self, session):
        result = notifications.format_checkpoint(session, "Milestone reached")
        assert "Milestone reached" in result

    def test_contains_message_count(self, session):
        result = notifications.format_checkpoint(session, "progress")
        assert str(session.messages_count) in result


class TestFormatApprovalNeeded:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_approval_needed(
            session, "Install package X", "Required for feature Y", "Adds 50MB dependency"
        )
        assert len(result) > 0

    def test_contains_why_and_impact(self, session):
        result = notifications.format_approval_needed(
            session, "action", "the reason", "the impact"
        )
        assert "the reason" in result
        assert "the impact" in result


class TestFormatDisagreement:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_disagreement(session, "Use Redis", "Use PostgreSQL")
        assert len(result) > 0

    def test_contains_agent_names(self, session):
        result = notifications.format_disagreement(session, "pos A", "pos B")
        assert SynapseConfig.AGENT_A_NAME in result
        assert SynapseConfig.AGENT_B_NAME in result


class TestFormatSessionCompleted:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_session_completed(session)
        assert len(result) > 0

    def test_contains_results_file_reference(self, session):
        result = notifications.format_session_completed(session)
        assert SynapseConfig.RESULTS_FILE in result

    def test_with_deliverables(self, session):
        deliverables = [{"description": "API module"}, {"path": "/code/api.py"}]
        result = notifications.format_session_completed(session, deliverables=deliverables)
        assert "API module" in result


class TestFormatSessionError:

    def test_returns_non_empty_string(self, session):
        result = notifications.format_session_error(session, "Redis connection lost")
        assert len(result) > 0

    def test_contains_error_message(self, session):
        result = notifications.format_session_error(session, "Timeout after 60s")
        assert "Timeout after 60s" in result


class TestFormatHealth:

    def test_connected_state(self, session):
        health = {
            "redis_connected": True,
            "agent_a_subscribed": True,
            "agent_b_subscribed": True,
        }
        result = notifications.format_health(health, session=session)
        assert "ok" in result
        assert session.session_id in result

    def test_disconnected_state(self):
        health = {
            "redis_connected": False,
            "agent_a_subscribed": False,
            "agent_b_subscribed": False,
        }
        result = notifications.format_health(health)
        assert "ERROR" in result
        assert "none" in result

    def test_contains_agent_names(self):
        health = {
            "redis_connected": True,
            "agent_a_subscribed": False,
            "agent_b_subscribed": False,
        }
        result = notifications.format_health(health)
        assert SynapseConfig.AGENT_A_NAME in result
        assert SynapseConfig.AGENT_B_NAME in result

    def test_without_session(self):
        health = {"redis_connected": True, "agent_a_subscribed": False, "agent_b_subscribed": False}
        result = notifications.format_health(health, session=None)
        assert "none" in result
