# SYNAPSE Tests — Orchestrator
# Validates decision parsing, safeguards, and action dispatch.
# All external dependencies (LLM, Redis, Notifier, Session) are mocked.

import json
from unittest.mock import MagicMock, patch

import pytest

from synapse.messages import MessageType, SessionData, SessionStatus, SynapseMessage
from synapse.synapse_orchestrator import (
    MAX_CONSECUTIVE_ITERATES,
    OrchestratorAction,
    OrchestratorDecision,
    SynapseOrchestrator,
)


# ---- Fixtures ----

@pytest.fixture
def mock_session():
    """A minimal SessionData for orchestrator tests."""
    return SessionData(
        session_id="SYNAPSE_SESSION_20260313_01_orch",
        created_at="2026-03-13T10:00:00+00:00",
        created_by="agent_a",
        status=SessionStatus.CONCEPTUALIZING,
        objective="Test orchestrator decisions",
        contract="Analyze and document only",
        messages_count=5,
        last_activity="2026-03-13T11:00:00+00:00",
    )


@pytest.fixture
def mock_deps(mock_session):
    """Returns mocked dependencies for the orchestrator."""
    session_mgr = MagicMock()
    session_mgr.active = mock_session
    session_mgr.get.return_value = mock_session
    session_mgr._resolve_session.return_value = mock_session
    session_mgr.get_session_dir.return_value = None  # No filesystem in these tests

    redis_client = MagicMock()
    redis_client.publish_to_agent_b.return_value = "msg-id"
    redis_client.notify_supervisor.return_value = "notif-id"

    notifier = MagicMock()
    llm = MagicMock()

    return session_mgr, redis_client, notifier, llm


@pytest.fixture
def orchestrator(mock_deps):
    session_mgr, redis_client, notifier, llm = mock_deps
    return SynapseOrchestrator(
        session_manager=session_mgr,
        redis_client=redis_client,
        notifier=notifier,
        llm=llm,
    )


# ---- _parse_decision ----

class TestParseDecision:

    def test_parse_valid_json_iterate(self, orchestrator):
        raw = json.dumps({
            "action": "iterate",
            "next_message": "Please elaborate on section 2",
            "reasoning": "Need more detail",
        })
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.ITERATE
        assert decision.next_message == "Please elaborate on section 2"
        assert decision.reasoning == "Need more detail"

    def test_parse_valid_json_transition(self, orchestrator):
        raw = json.dumps({
            "action": "transition",
            "transition_to": "AWAITING_APPROVAL",
            "reasoning": "Plan is complete",
        })
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.TRANSITION
        assert decision.transition_to == "AWAITING_APPROVAL"

    def test_parse_valid_json_checkpoint(self, orchestrator):
        raw = json.dumps({
            "action": "checkpoint",
            "checkpoint_text": "50% implementation done",
            "next_message": "Continue with the API module",
            "reasoning": "Good progress",
        })
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.CHECKPOINT
        assert decision.checkpoint_text == "50% implementation done"
        assert decision.next_message == "Continue with the API module"

    def test_parse_valid_json_complete(self, orchestrator):
        raw = json.dumps({
            "action": "complete",
            "reasoning": "All tasks done, tests pass",
        })
        decision = orchestrator._parse_decision(raw)
        assert decision.action == OrchestratorAction.COMPLETE

    def test_parse_valid_json_escalate(self, orchestrator):
        raw = json.dumps({
            "action": "escalate",
            "escalation_type": "scope_violation",
            "escalation_detail": "Agent B started installing packages",
            "reasoning": "Out of scope",
        })
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.ESCALATE
        assert decision.escalation_type == "scope_violation"

    def test_parse_valid_json_wait(self, orchestrator):
        raw = json.dumps({
            "action": "wait",
            "reasoning": "Awaiting supervisor approval",
        })
        decision = orchestrator._parse_decision(raw)
        assert decision.action == OrchestratorAction.WAIT

    def test_parse_malformed_json_returns_wait(self, orchestrator):
        """Unparseable LLM output should gracefully fall back to WAIT."""
        decision = orchestrator._parse_decision("This is not JSON at all")

        assert decision.action == OrchestratorAction.WAIT
        assert "parse failed" in decision.reasoning.lower() or "JSON" in decision.reasoning

    def test_parse_json_in_markdown_code_block(self, orchestrator):
        """LLMs sometimes wrap JSON in ```json ... ``` blocks."""
        raw = '```json\n{"action": "iterate", "next_message": "Next step", "reasoning": "ok"}\n```'
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.ITERATE
        assert decision.next_message == "Next step"

    def test_parse_json_with_surrounding_text(self, orchestrator):
        """LLM may produce text before/after the JSON object."""
        raw = 'Here is my decision:\n{"action": "complete", "reasoning": "done"}\nThat was it.'
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.COMPLETE

    def test_parse_unknown_action_returns_wait(self, orchestrator):
        """An unknown action value should fall back to WAIT."""
        raw = json.dumps({"action": "destroy_everything", "reasoning": "chaos"})
        decision = orchestrator._parse_decision(raw)

        assert decision.action == OrchestratorAction.WAIT


# ---- _dict_to_decision ----

class TestDictToDecision:

    def test_dict_to_decision_all_fields(self, orchestrator):
        data = {
            "action": "escalate",
            "next_message": "msg",
            "transition_to": "APPROVED",
            "checkpoint_text": "cp",
            "escalation_type": "disagreement",
            "escalation_detail": "detail",
            "reasoning": "reason",
        }
        decision = orchestrator._dict_to_decision(data)

        assert decision.action == OrchestratorAction.ESCALATE
        assert decision.next_message == "msg"
        assert decision.transition_to == "APPROVED"
        assert decision.checkpoint_text == "cp"
        assert decision.escalation_type == "disagreement"
        assert decision.escalation_detail == "detail"
        assert decision.reasoning == "reason"

    def test_dict_to_decision_missing_action_defaults_wait(self, orchestrator):
        decision = orchestrator._dict_to_decision({})
        assert decision.action == OrchestratorAction.WAIT

    def test_dict_to_decision_missing_optional_fields(self, orchestrator):
        data = {"action": "iterate", "next_message": "do X"}
        decision = orchestrator._dict_to_decision(data)

        assert decision.action == OrchestratorAction.ITERATE
        assert decision.next_message == "do X"
        assert decision.transition_to is None
        assert decision.checkpoint_text is None
        assert decision.escalation_type is None
        assert decision.reasoning == ""


# ---- Safeguards ----

class TestSafeguards:

    def test_max_consecutive_iterates_triggers_checkpoint(self, orchestrator, mock_session, mock_deps):
        """After MAX_CONSECUTIVE_ITERATES, the safeguard should fire."""
        session_mgr, redis_client, notifier, llm = mock_deps

        # Simulate MAX_CONSECUTIVE_ITERATES consecutive iterations
        ctx = orchestrator._get_ctx(mock_session.session_id)
        ctx["consecutive_iterates"] = MAX_CONSECUTIVE_ITERATES

        forced = orchestrator._check_safeguards(mock_session)

        # The safeguard does NOT force-stop (returns False) but resets counter
        # and adds a checkpoint + notification
        assert forced is False
        assert ctx["consecutive_iterates"] == 0
        session_mgr.add_checkpoint.assert_called_once()
        notifier.send_message.assert_called_once()

    def test_max_session_messages_pauses_session(self, orchestrator, mock_session, mock_deps):
        """When total messages exceed the limit, session should be paused."""
        session_mgr, redis_client, notifier, llm = mock_deps
        mock_session.messages_count = 150  # MAX_SESSION_MESSAGES

        forced = orchestrator._check_safeguards(mock_session)

        assert forced is True
        session_mgr.transition.assert_called()
        notifier.send_message.assert_called()

    def test_below_limits_no_safeguard(self, orchestrator, mock_session):
        """Normal operation: no safeguard should trigger."""
        ctx = orchestrator._get_ctx(mock_session.session_id)
        ctx["consecutive_iterates"] = 2
        mock_session.messages_count = 5

        forced = orchestrator._check_safeguards(mock_session)
        assert forced is False


# ---- LLM failure handling ----

class TestLLMFailureHandling:

    def test_handle_llm_failure_returns_wait(self, orchestrator, mock_session):
        decision = orchestrator._handle_llm_failure(mock_session)
        assert decision.action == OrchestratorAction.WAIT

    def test_consecutive_llm_failures_pause_session(self, orchestrator, mock_session, mock_deps):
        """After MAX_CONSECUTIVE_LLM_FAILURES, session should be paused."""
        session_mgr, redis_client, notifier, llm = mock_deps

        ctx = orchestrator._get_ctx(mock_session.session_id)
        ctx["consecutive_llm_failures"] = 3  # MAX_CONSECUTIVE_LLM_FAILURES

        orchestrator._handle_llm_failure(mock_session)

        session_mgr.transition.assert_called()
        notifier.send_message.assert_called()


# ---- handle_agent_b_response (integration with mocks) ----

class TestHandleAgentBResponse:

    def test_skips_paused_sessions(self, orchestrator, mock_session, mock_deps):
        """Orchestrator should not act on paused/completed/cancelled sessions."""
        session_mgr, redis_client, notifier, llm = mock_deps
        mock_session.status = SessionStatus.PAUSED

        msg = SynapseMessage(
            session_id=mock_session.session_id,
            sender="agent_b",
            type=MessageType.DIALOGUE,
            content="Hello",
        )
        orchestrator.handle_agent_b_response(msg, session_id=mock_session.session_id)

        # LLM should NOT have been called
        llm.chat.assert_not_called()

    def test_evaluates_and_executes_on_active_session(self, orchestrator, mock_session, mock_deps):
        """On an active session, the orchestrator should call the LLM and act."""
        session_mgr, redis_client, notifier, llm = mock_deps
        mock_session.status = SessionStatus.CONCEPTUALIZING

        llm.chat.return_value = {
            "success": True,
            "response": json.dumps({
                "action": "iterate",
                "next_message": "Please clarify section 3",
                "reasoning": "Need more details",
            }),
        }

        msg = SynapseMessage(
            session_id=mock_session.session_id,
            sender="agent_b",
            type=MessageType.DIALOGUE,
            content="Here is my analysis of section 2...",
        )

        # Provide a session_dir so journal append doesn't fail
        session_mgr.get_session_dir.return_value = None

        orchestrator.handle_agent_b_response(msg, session_id=mock_session.session_id)

        llm.chat.assert_called_once()
        # Should have sent a message to agent B
        redis_client.publish_to_agent_b.assert_called_once()
