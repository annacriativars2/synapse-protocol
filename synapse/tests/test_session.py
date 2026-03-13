# SYNAPSE Tests — Session Manager
# Validates session lifecycle: creation, transitions, multi-session, purge.
# All tests use tmp dirs via config_override — never touches the real filesystem.

import json
import os

import pytest

from synapse.config import SynapseConfig
from synapse.messages import SessionData, SessionStatus
from synapse.session import SynapseSession


# ---- Session creation ----

class TestSessionCreation:

    def test_create_session_returns_session_data(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("myproject", "Build a widget", created_by="agent_a")

        assert isinstance(session, SessionData)
        assert session.status == SessionStatus.CREATED
        assert session.objective == "Build a widget"
        assert session.created_by == "agent_a"
        assert "myproject" in session.session_id

    def test_create_session_creates_directory_structure(self, config_override):
        """Session directory must contain docs/, code/, tests/ and session.json."""
        mgr = SynapseSession()
        session = mgr.create("proj", "objective")
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

        assert os.path.isdir(session_dir)
        assert os.path.isdir(os.path.join(session_dir, "docs"))
        assert os.path.isdir(os.path.join(session_dir, "code"))
        assert os.path.isdir(os.path.join(session_dir, "tests"))
        assert os.path.isfile(os.path.join(session_dir, SynapseConfig.SESSION_JSON))

    def test_create_session_writes_valid_session_json(self, config_override):
        """session.json must be valid JSON matching the SessionData fields."""
        mgr = SynapseSession()
        session = mgr.create("proj", "objective", shared_context=["ref.md"])
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

        with open(os.path.join(session_dir, SynapseConfig.SESSION_JSON)) as f:
            data = json.load(f)

        assert data["session_id"] == session.session_id
        assert data["status"] == "CREATED"
        assert data["objective"] == "objective"
        assert "ref.md" in data["shared_context"]

    def test_create_session_writes_objective_file(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "My important objective")
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

        objective_path = os.path.join(session_dir, SynapseConfig.OBJECTIVE_FILE)
        assert os.path.isfile(objective_path)
        with open(objective_path) as f:
            content = f.read()
        assert "My important objective" in content

    def test_create_session_writes_journal_file(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "objective")
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

        journal_path = os.path.join(session_dir, SynapseConfig.JOURNAL_FILE)
        assert os.path.isfile(journal_path)
        with open(journal_path) as f:
            content = f.read()
        assert "Session Journal" in content

    def test_create_session_with_contract(self, config_override):
        """If a contract is provided, it should be stored (not the objective)."""
        mgr = SynapseSession()
        session = mgr.create("proj", "Big objective", contract="Only analyze X")

        assert session.contract == "Only analyze X"

    def test_create_session_without_contract_uses_objective(self, config_override):
        """If no contract is provided, the objective is used as the default contract."""
        mgr = SynapseSession()
        session = mgr.create("proj", "Analyze the codebase")

        assert session.contract == "Analyze the codebase"


# ---- State transitions ----

class TestSessionTransitions:

    def _create_and_start(self, config_override):
        """Helper: creates a session and moves it to CONCEPTUALIZING."""
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)
        return mgr, session

    def test_valid_transition_created_to_conceptualizing(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        updated = mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)

        assert updated.status == SessionStatus.CONCEPTUALIZING

    def test_valid_transition_conceptualizing_to_awaiting(self, config_override):
        mgr, session = self._create_and_start(config_override)
        updated = mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=session.session_id)

        assert updated.status == SessionStatus.AWAITING_APPROVAL

    def test_invalid_transition_raises_valueerror(self, config_override):
        """CREATED cannot go directly to IMPLEMENTING."""
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")

        with pytest.raises(ValueError, match="Invalid transition"):
            mgr.transition(SessionStatus.IMPLEMENTING, session_id=session.session_id)

    def test_cancel_from_any_non_terminal_state(self, config_override):
        """CANCELLED is reachable from any state except COMPLETED and CANCELLED."""
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)
        updated = mgr.transition(SessionStatus.CANCELLED, session_id=session.session_id)

        assert updated.status == SessionStatus.CANCELLED

    def test_cancel_from_completed_raises(self, config_override):
        """Cannot cancel an already completed session."""
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        # Walk the full lifecycle: CREATED -> CONCEPTUALIZING -> AWAITING -> REVIEWING -> APPROVED -> IMPLEMENTING -> COMPLETED
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=session.session_id)
        mgr.transition(SessionStatus.REVIEWING, session_id=session.session_id)
        mgr.transition(SessionStatus.APPROVED, session_id=session.session_id)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=session.session_id)
        mgr.transition(SessionStatus.COMPLETED, session_id=session.session_id)

        with pytest.raises(ValueError, match="Cannot cancel"):
            mgr.transition(SessionStatus.CANCELLED, session_id=session.session_id)

    def test_transition_updates_last_activity(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        old_activity = session.last_activity

        updated = mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)
        assert updated.last_activity >= old_activity

    def test_approved_sets_approved_at(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=session.session_id)
        mgr.transition(SessionStatus.REVIEWING, session_id=session.session_id)
        updated = mgr.transition(SessionStatus.APPROVED, session_id=session.session_id)

        assert updated.approved_at is not None

    def test_transition_persists_to_disk(self, config_override):
        """After transition, session.json should reflect the new status."""
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)

        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)
        with open(os.path.join(session_dir, SynapseConfig.SESSION_JSON)) as f:
            data = json.load(f)
        assert data["status"] == "CONCEPTUALIZING"

    def test_transition_nonexistent_session_raises(self, config_override):
        mgr = SynapseSession()
        with pytest.raises(RuntimeError, match="not found"):
            mgr.transition(SessionStatus.CONCEPTUALIZING, session_id="nonexistent")


# ---- Multi-session ----

class TestMultiSession:

    def test_create_two_sessions_both_tracked(self, config_override):
        mgr = SynapseSession()
        s1 = mgr.create("proj-a", "First objective")
        s2 = mgr.create("proj-b", "Second objective")

        assert mgr.get(s1.session_id) is not None
        assert mgr.get(s2.session_id) is not None
        assert len(mgr.active_sessions) == 2

    def test_active_returns_most_recent(self, config_override):
        mgr = SynapseSession()
        mgr.create("proj-a", "First")
        s2 = mgr.create("proj-b", "Second")

        # The second session is the most recent
        assert mgr.active.session_id == s2.session_id

    def test_max_concurrent_sessions_enforced(self, config_override):
        mgr = SynapseSession()
        max_sessions = SynapseConfig.MAX_CONCURRENT_SESSIONS

        for i in range(max_sessions):
            mgr.create(f"proj-{i}", f"Objective {i}")

        with pytest.raises(RuntimeError, match="Maximum"):
            mgr.create("one-too-many", "Overflow")

    def test_completed_session_frees_slot(self, config_override):
        """Completing a session should allow creating a new one."""
        mgr = SynapseSession()
        max_sessions = SynapseConfig.MAX_CONCURRENT_SESSIONS

        sessions = []
        for i in range(max_sessions):
            sessions.append(mgr.create(f"proj-{i}", f"Obj {i}"))

        # Complete the first session through the full lifecycle
        sid = sessions[0].session_id
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=sid)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=sid)
        mgr.transition(SessionStatus.REVIEWING, session_id=sid)
        mgr.transition(SessionStatus.APPROVED, session_id=sid)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=sid)
        mgr.transition(SessionStatus.COMPLETED, session_id=sid)

        # Now we should be able to create a new one
        new_session = mgr.create("proj-new", "New objective")
        assert new_session is not None


# ---- Session listing ----

class TestSessionListing:

    def test_list_sessions_returns_all(self, config_override):
        mgr = SynapseSession()
        mgr.create("proj-a", "A")
        mgr.create("proj-b", "B")

        listing = mgr.list_sessions()
        assert len(listing) == 2
        ids = {s["session_id"] for s in listing}
        assert all("proj-a" in sid or "proj-b" in sid for sid in ids)

    def test_list_sessions_empty_directory(self, config_override):
        mgr = SynapseSession()
        listing = mgr.list_sessions()
        assert listing == []


# ---- Session purge/archive ----

class TestSessionPurge:

    def test_purge_moves_completed_session_to_archives(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        sid = session.session_id

        # Complete the session
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=sid)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=sid)
        mgr.transition(SessionStatus.REVIEWING, session_id=sid)
        mgr.transition(SessionStatus.APPROVED, session_id=sid)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=sid)
        mgr.transition(SessionStatus.COMPLETED, session_id=sid)

        purged = mgr.purge_sessions()
        assert sid in purged
        assert os.path.isdir(os.path.join(SynapseConfig.ARCHIVES_DIR, sid))
        assert not os.path.isdir(os.path.join(SynapseConfig.SESSIONS_BASE_DIR, sid))

    def test_purge_does_not_archive_active_sessions(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=session.session_id)

        purged = mgr.purge_sessions()
        assert purged == []
        assert os.path.isdir(os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id))

    def test_purge_keep_last_preserves_recent(self, config_override):
        mgr = SynapseSession()

        # Create and complete two sessions
        s1 = mgr.create("proj-a", "A")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=s1.session_id)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=s1.session_id)
        mgr.transition(SessionStatus.REVIEWING, session_id=s1.session_id)
        mgr.transition(SessionStatus.APPROVED, session_id=s1.session_id)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=s1.session_id)
        mgr.transition(SessionStatus.COMPLETED, session_id=s1.session_id)

        s2 = mgr.create("proj-b", "B")
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=s2.session_id)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=s2.session_id)
        mgr.transition(SessionStatus.REVIEWING, session_id=s2.session_id)
        mgr.transition(SessionStatus.APPROVED, session_id=s2.session_id)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=s2.session_id)
        mgr.transition(SessionStatus.COMPLETED, session_id=s2.session_id)

        purged = mgr.purge_sessions(keep_last=1)
        # Should purge only the older one
        assert len(purged) == 1

    def test_purge_removes_session_from_memory(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        sid = session.session_id
        mgr.transition(SessionStatus.CONCEPTUALIZING, session_id=sid)
        mgr.transition(SessionStatus.AWAITING_APPROVAL, session_id=sid)
        mgr.transition(SessionStatus.REVIEWING, session_id=sid)
        mgr.transition(SessionStatus.APPROVED, session_id=sid)
        mgr.transition(SessionStatus.IMPLEMENTING, session_id=sid)
        mgr.transition(SessionStatus.COMPLETED, session_id=sid)

        mgr.purge_sessions()
        assert mgr.get(sid) is None


# ---- Session accessors ----

class TestSessionAccessors:

    def test_increment_messages(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        assert session.messages_count == 0

        mgr.increment_messages(session_id=session.session_id)
        assert mgr.get(session.session_id).messages_count == 1

    def test_set_contract(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.set_contract("New scope", session_id=session.session_id)

        assert mgr.get(session.session_id).contract == "New scope"

    def test_add_checkpoint(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        mgr.add_checkpoint("info", "Progress report", session_id=session.session_id)

        updated = mgr.get(session.session_id)
        assert len(updated.checkpoints) == 1
        assert updated.checkpoints[0]["type"] == "info"
        assert updated.checkpoints[0]["message"] == "Progress report"

    def test_get_session_dir(self, config_override):
        mgr = SynapseSession()
        session = mgr.create("proj", "obj")
        session_dir = mgr.get_session_dir(session.session_id)

        assert session_dir is not None
        assert session.session_id in session_dir
        assert os.path.isdir(session_dir)

    def test_get_nonexistent_session_returns_none(self, config_override):
        mgr = SynapseSession()
        assert mgr.get("nonexistent") is None
        assert mgr.get_session_dir("nonexistent") is None
