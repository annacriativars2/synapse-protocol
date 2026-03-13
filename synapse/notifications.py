# SYNAPSE Supervisor Notifications
# Ref: SYNAPSE_SPEC/04_SUPERVISION.md §3

import logging
from typing import Optional

from synapse.config import SynapseConfig
from synapse.messages import SessionData, SynapseMessage, MessageType

logger = logging.getLogger("synapse.notifications")


def format_session_created(session: SessionData) -> str:
    """New session notification (04_SUPERVISION.md §3.2)."""
    return (
        f"SYNAPSE | New Session\n"
        f"{'=' * 35}\n"
        f"Project: {session.session_id}\n"
        f"Objective: {session.objective}\n"
        f"Created by: {session.created_by.capitalize()}\n"
        f"Directory: {SynapseConfig.SESSIONS_BASE_DIR}/{session.session_id}/\n"
    )


def format_docs_ready(session: SessionData, doc_summary: str = "") -> str:
    """Documents ready for review notification (04_SUPERVISION.md §3.2)."""
    return (
        f"SYNAPSE | Documents Ready for Review\n"
        f"{'=' * 35}\n"
        f"Session: {session.session_id}\n\n"
        f"{doc_summary}\n\n"
        f"Directory: {SynapseConfig.SESSIONS_BASE_DIR}/{session.session_id}/\n\n"
        f"Actions:\n"
        f"  /synapse approve — Approve and start implementation\n"
        f"  /synapse reject [reason] — Reject with comment\n"
    )


def format_checkpoint(session: SessionData, progress: str) -> str:
    """Checkpoint notification (04_SUPERVISION.md §3.2)."""
    return (
        f"SYNAPSE Checkpoint | {session.session_id}\n"
        f"{'=' * 35}\n"
        f"{progress}\n\n"
        f"Messages exchanged: {session.messages_count}\n"
    )


def format_approval_needed(session: SessionData, action: str, reason: str, impact: str) -> str:
    """Out-of-scope approval notification (04_SUPERVISION.md §3.2).

    MUST include WHY and IMPACT (04_SUPERVISION.md §3.2 absolute rule).
    """
    return (
        f"SYNAPSE | Approval Required\n"
        f"{'=' * 35}\n"
        f"Session: {session.session_id}\n\n"
        f"Requested action:\n"
        f"  {action}\n\n"
        f"Why:\n"
        f"  {reason}\n\n"
        f"Impact:\n"
        f"  {impact}\n\n"
        f"/synapse approve — Allow this action\n"
        f"/synapse reject [reason] — Deny\n"
    )


def format_disagreement(session: SessionData, agent_a_position: str, agent_b_position: str) -> str:
    """Disagreement requiring arbitration notification (04_SUPERVISION.md §5.4)."""
    return (
        f"SYNAPSE | Disagreement — Arbitration Needed\n"
        f"{'=' * 35}\n"
        f"Session: {session.session_id}\n\n"
        f"{SynapseConfig.AGENT_A_NAME} position:\n"
        f"  {agent_a_position}\n\n"
        f"{SynapseConfig.AGENT_B_NAME} position:\n"
        f"  {agent_b_position}\n\n"
        f"Please make a decision.\n"
    )


def format_session_completed(session: SessionData, deliverables: Optional[list[dict]] = None) -> str:
    """Session completed notification (04_SUPERVISION.md §3.2)."""
    text = (
        f"SYNAPSE Session Completed | {session.session_id}\n"
        f"{'=' * 35}\n"
        f"Messages exchanged: {session.messages_count}\n\n"
    )

    if deliverables:
        text += "Deliverables:\n"
        for d in deliverables:
            text += f"  - {d.get('description', d.get('path', ''))}\n"
        text += "\n"

    session_dir = f"{SynapseConfig.SESSIONS_BASE_DIR}/{session.session_id}"
    text += (
        f"Full report: {session_dir}/{SynapseConfig.RESULTS_FILE}\n\n"
        f"From terminal:\n"
        f"  cat {session_dir}/{SynapseConfig.RESULTS_FILE}\n"
    )
    return text


def format_session_error(session: SessionData, error: str) -> str:
    """Critical error notification (04_SUPERVISION.md §3.1)."""
    return (
        f"SYNAPSE | Critical Error\n"
        f"{'=' * 35}\n"
        f"Session: {session.session_id}\n"
        f"Error: {error}\n\n"
        f"Session is PAUSED.\n"
        f"/synapse resume — Resume\n"
        f"/synapse cancel — Cancel\n"
    )


def format_health(health: dict, session: Optional[SessionData] = None) -> str:
    """Health check format (03_TRANSPORT.md §7.2)."""
    r = "ok" if health.get("redis_connected") else "ERROR"
    a = "ok" if health.get("agent_a_subscribed") else "no"
    b = "ok" if health.get("agent_b_subscribed") else "no"

    text = (
        f"SYNAPSE Health Check\n"
        f"  Redis: {r}\n"
        f"  {SynapseConfig.AGENT_A_NAME}: {a}\n"
        f"  {SynapseConfig.AGENT_B_NAME}: {b}\n"
    )

    if session:
        text += (
            f"  Active session: {session.session_id}\n"
            f"  Status: {session.status.value}\n"
            f"  Messages: {session.messages_count}\n"
        )
    else:
        text += "  Active session: none\n"

    return text
