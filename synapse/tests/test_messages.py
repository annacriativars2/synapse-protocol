# SYNAPSE Tests — Messages, SessionData, transitions
# Validates serialization, validation, and state machine definitions.

import json
import uuid

import pytest

from synapse.messages import (
    MessageType,
    SessionStatus,
    SynapseMessage,
    SessionData,
    VALID_TRANSITIONS,
)


# ---- SynapseMessage serialization ----

class TestSynapseMessageSerialization:

    def test_message_roundtrip_preserves_all_fields(self):
        """to_json then from_json must return an equivalent message."""
        original = SynapseMessage(
            session_id="sess-001",
            sender="agent_a",
            type=MessageType.DIALOGUE,
            content="Hello from agent A",
            metadata={"key": "value"},
        )
        raw = original.to_json()
        restored = SynapseMessage.from_json(raw)

        assert restored.session_id == original.session_id
        assert restored.sender == original.sender
        assert restored.type == MessageType.DIALOGUE
        assert restored.content == original.content
        assert restored.id == original.id
        assert restored.timestamp == original.timestamp
        assert restored.metadata == {"key": "value"}

    def test_message_roundtrip_with_all_message_types(self):
        """Every MessageType must survive a roundtrip."""
        for mt in MessageType:
            msg = SynapseMessage(
                session_id="sess-002",
                sender="agent_b",
                type=mt,
                content=f"Testing {mt.value}",
            )
            restored = SynapseMessage.from_json(msg.to_json())
            assert restored.type == mt

    def test_message_to_json_produces_valid_json(self):
        """to_json must produce parseable JSON."""
        msg = SynapseMessage(
            session_id="sess-003",
            sender="agent_a",
            type=MessageType.PROPOSAL,
            content="A proposal",
        )
        data = json.loads(msg.to_json())
        assert data["type"] == "proposal"
        assert data["session_id"] == "sess-003"

    def test_message_unknown_type_kept_as_string(self):
        """An unknown type string should be preserved (not raise)."""
        raw = json.dumps({
            "id": str(uuid.uuid4()),
            "session_id": "sess-004",
            "sender": "synapse",
            "type": "custom_notification",
            "content": "something",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "metadata": {},
        })
        msg = SynapseMessage.from_json(raw)
        assert msg.type == "custom_notification"

    def test_message_defaults_id_and_timestamp(self):
        """id and timestamp should be auto-generated if not provided."""
        msg = SynapseMessage(
            session_id="sess-005",
            sender="agent_a",
            type=MessageType.ACTION,
            content="do something",
        )
        assert msg.id  # non-empty UUID
        assert msg.timestamp  # non-empty ISO string


# ---- SynapseMessage validation ----

class TestSynapseMessageValidation:

    def test_valid_dialogue_message(self):
        msg = SynapseMessage(
            session_id="sess-010",
            sender="agent_a",
            type=MessageType.DIALOGUE,
            content="Hello",
        )
        assert msg.validate() is True

    def test_invalid_message_empty_content(self):
        msg = SynapseMessage(
            session_id="sess-011",
            sender="agent_a",
            type=MessageType.DIALOGUE,
            content="",
        )
        assert msg.validate() is False

    def test_invalid_message_empty_sender(self):
        msg = SynapseMessage(
            session_id="sess-012",
            sender="",
            type=MessageType.DIALOGUE,
            content="Hello",
        )
        assert msg.validate() is False

    def test_approval_request_requires_metadata(self):
        """APPROVAL_REQUEST must include 'approval_reason' in metadata."""
        msg_no_reason = SynapseMessage(
            session_id="sess-013",
            sender="agent_a",
            type=MessageType.APPROVAL_REQUEST,
            content="Need approval",
            metadata={},
        )
        assert msg_no_reason.validate() is False

        msg_with_reason = SynapseMessage(
            session_id="sess-014",
            sender="agent_a",
            type=MessageType.APPROVAL_REQUEST,
            content="Need approval",
            metadata={"approval_reason": "Out of scope action"},
        )
        assert msg_with_reason.validate() is True


# ---- SessionData serialization ----

class TestSessionDataSerialization:

    def test_session_data_roundtrip_preserves_all_fields(self):
        """to_dict then from_dict must return equivalent data."""
        original = SessionData(
            session_id="SYNAPSE_SESSION_20260313_01_test",
            created_at="2026-03-13T10:00:00+00:00",
            created_by="agent_a",
            status=SessionStatus.CONCEPTUALIZING,
            objective="Build something",
            shared_context=["doc.md"],
            contract="Analyze only",
            execution_contract="",
            messages_count=5,
            last_activity="2026-03-13T11:00:00+00:00",
            checkpoints=[{"at": "2026-03-13T10:30:00+00:00", "type": "info", "message": "ok"}],
        )
        d = original.to_dict()
        restored = SessionData.from_dict(d)

        assert restored.session_id == original.session_id
        assert restored.status == SessionStatus.CONCEPTUALIZING
        assert restored.objective == original.objective
        assert restored.shared_context == ["doc.md"]
        assert restored.contract == "Analyze only"
        assert restored.messages_count == 5
        assert restored.checkpoints == original.checkpoints

    def test_session_data_to_dict_serializes_status_as_string(self):
        session = SessionData(
            session_id="sess",
            created_at="t",
            created_by="a",
            status=SessionStatus.IMPLEMENTING,
            objective="obj",
        )
        d = session.to_dict()
        assert d["status"] == "IMPLEMENTING"
        assert isinstance(d["status"], str)

    def test_session_data_from_dict_backward_compatible(self):
        """from_dict should handle missing 'contract' and 'execution_contract' fields."""
        data = {
            "session_id": "sess-old",
            "created_at": "t",
            "created_by": "a",
            "status": "CREATED",
            "objective": "old objective",
            "working_directory": ".",
            "agent_b_session_id": None,
            "shared_context": [],
            "approved_at": None,
            "approved_scope": [],
            "messages_count": 0,
            "last_activity": None,
            "checkpoints": [],
        }
        # No 'contract' or 'execution_contract' keys
        session = SessionData.from_dict(data)
        assert session.contract == ""
        assert session.execution_contract == ""


# ---- SessionStatus enum ----

class TestSessionStatus:

    def test_all_expected_statuses_exist(self):
        expected = {
            "CREATED", "CONCEPTUALIZING", "AWAITING_APPROVAL", "REVIEWING",
            "APPROVED", "IMPLEMENTING", "PAUSED", "COMPLETED", "CANCELLED",
        }
        actual = {s.value for s in SessionStatus}
        assert actual == expected

    def test_status_is_string_enum(self):
        """SessionStatus values should be usable as plain strings."""
        assert SessionStatus.CREATED == "CREATED"
        assert str(SessionStatus.IMPLEMENTING) == "SessionStatus.IMPLEMENTING"


# ---- VALID_TRANSITIONS ----

class TestValidTransitions:

    def test_transitions_cover_all_non_terminal_states(self):
        """Every non-terminal status must have at least one valid transition."""
        terminal = {SessionStatus.COMPLETED, SessionStatus.CANCELLED}
        for status in SessionStatus:
            if status not in terminal:
                assert status in VALID_TRANSITIONS, f"{status.value} missing from VALID_TRANSITIONS"
                assert len(VALID_TRANSITIONS[status]) > 0, f"{status.value} has no transitions"

    def test_terminal_states_have_no_transitions(self):
        """COMPLETED and CANCELLED must not appear as keys in VALID_TRANSITIONS."""
        assert SessionStatus.COMPLETED not in VALID_TRANSITIONS
        assert SessionStatus.CANCELLED not in VALID_TRANSITIONS

    def test_created_can_only_go_to_conceptualizing(self):
        assert VALID_TRANSITIONS[SessionStatus.CREATED] == [SessionStatus.CONCEPTUALIZING]

    def test_conceptualizing_can_go_to_awaiting_or_paused(self):
        targets = VALID_TRANSITIONS[SessionStatus.CONCEPTUALIZING]
        assert SessionStatus.AWAITING_APPROVAL in targets
        assert SessionStatus.PAUSED in targets
