# SYNAPSE API Routes — Agent A side
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md, 04_SUPERVISION.md

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from synapse.config import SynapseConfig
from synapse.messages import SynapseMessage, MessageType, SessionStatus
from synapse.redis_client import SynapseRedisClient
from synapse.session import SynapseSession
from synapse.journal import append_to_journal, read_last_entries
from synapse import notifications
from synapse.email_sender import get_email_sender

if TYPE_CHECKING:
    from synapse.interfaces import LLMProvider, Notifier
    from synapse.synapse_orchestrator import SynapseOrchestrator

logger = logging.getLogger("synapse.routes")
router = APIRouter(prefix="/synapse", tags=["SYNAPSE"])

# --- Shared instances (initialized at startup via init_synapse) ---
_redis_client: Optional[SynapseRedisClient] = None
_session_manager: Optional[SynapseSession] = None
_orchestrator: Optional[SynapseOrchestrator] = None


def init_synapse(notifier: Optional[Notifier] = None, llm: Optional[LLMProvider] = None) -> None:
    """Initializes SYNAPSE components. Called at app startup.

    Args:
        notifier: Optional notifier instance with send_message(text) method.
                  Must implement the Notifier protocol (see interfaces.py).
                  If None, notifications are logged only.
        llm: Optional LLM provider with chat() method.
             Must implement the LLMProvider protocol (see interfaces.py).
             Required for autonomous orchestration decisions.
    """
    global _redis_client, _session_manager, _orchestrator
    _redis_client = SynapseRedisClient()
    _session_manager = SynapseSession()

    from synapse.synapse_orchestrator import SynapseOrchestrator

    if notifier is None:
        logger.warning("No notifier configured — supervisor notifications will be logged only")
        notifier = _LogOnlyNotifier()

    _orchestrator = SynapseOrchestrator(
        session_manager=_session_manager,
        redis_client=_redis_client,
        notifier=notifier,
        email_sender=get_email_sender(),
        llm=llm,
    )

    # Subscribe to messages from Agent B and control channel
    _redis_client.subscribe(
        [SynapseConfig.CHANNEL_B_TO_A, SynapseConfig.CHANNEL_CONTROL],
        _handle_incoming_message,
    )
    logger.info("SYNAPSE initialized — Redis subscriber + orchestrator active")


class _LogOnlyNotifier:
    """Fallback notifier that just logs messages."""
    def send_message(self, text: str) -> None:
        logger.info("[NOTIFICATION] %s", text[:200])


def get_redis_client() -> SynapseRedisClient:
    if not _redis_client:
        raise HTTPException(status_code=503, detail="SYNAPSE not initialized")
    return _redis_client


def get_session_manager() -> SynapseSession:
    if not _session_manager:
        raise HTTPException(status_code=503, detail="SYNAPSE not initialized")
    return _session_manager


# --- Callback for incoming messages ---

def _handle_incoming_message(channel: str, message: SynapseMessage) -> None:
    """Callback when a message arrives from Agent B or the control channel.
    Routes to the correct session via message.session_id (multi-session support).
    """
    session_mgr = _session_manager
    if not session_mgr:
        return

    if channel == SynapseConfig.CHANNEL_B_TO_A:
        # Route by session_id from the message
        sid = message.session_id
        session = session_mgr.get(sid) if sid else session_mgr.active
        logger.info("Message from Agent B [%s] session=%s: %s...", message.type.value, sid, message.content[:100])

        if session:
            session_mgr.increment_messages(session_id=session.session_id)
            session_dir = session_mgr.get_session_dir(session.session_id)
            if session_dir:
                append_to_journal(session_dir, f"{SynapseConfig.AGENT_B_NAME} [{message.type.value}] : {message.content[:200]}")

            # Orchestrator processes Agent B's response (routed to correct session)
            if _orchestrator:
                try:
                    _orchestrator.handle_agent_b_response(message, session_id=session.session_id)
                except Exception as e:
                    logger.error("Orchestrator error [%s]: %s", session.session_id, e, exc_info=True)
        else:
            logger.warning("Message for unknown session: %s", sid)

    elif channel == SynapseConfig.CHANNEL_CONTROL:
        logger.info("Control command: %s", message.content)
        _handle_control_command(message)


def _handle_control_command(message: SynapseMessage) -> None:
    """Handles a supervisor control command (04_SUPERVISION.md §4).
    Multi-session: uses message.session_id to target a specific session.
    """
    session_mgr = _session_manager
    if not session_mgr:
        return

    command = message.content.strip().lower()

    # Route to specific session or most recent
    sid = message.session_id
    session = session_mgr.get(sid) if sid else session_mgr.active
    if not session:
        logger.warning("Control command for non-existent session: %s", sid)
        return

    sid = session.session_id

    try:
        if command == "approve":
            if session.status == SessionStatus.AWAITING_APPROVAL:
                session_mgr.transition(SessionStatus.REVIEWING, "Supervisor review", session_id=sid)
                session_mgr.transition(SessionStatus.APPROVED, "Supervisor approved", session_id=sid)
                session_mgr.transition(SessionStatus.IMPLEMENTING, "Implementation started", session_id=sid)
                if _orchestrator:
                    _orchestrator.handle_approval(session_id=sid)
            elif session.status == SessionStatus.PAUSED:
                session_mgr.transition(SessionStatus.IMPLEMENTING, "Supervisor approved out-of-scope action", session_id=sid)
                if _orchestrator:
                    _orchestrator.handle_resume(session_id=sid)

        elif command == "reject":
            reason = message.metadata.get("reason", "")
            if session.status in (SessionStatus.AWAITING_APPROVAL, SessionStatus.REVIEWING):
                session_mgr.transition(SessionStatus.CONCEPTUALIZING, f"Supervisor rejected: {reason}", session_id=sid)

        elif command == "revise":
            comment = message.metadata.get("comment", "")
            if session.status in (SessionStatus.AWAITING_APPROVAL, SessionStatus.REVIEWING):
                session_mgr.transition(SessionStatus.CONCEPTUALIZING, f"Supervisor requests revision: {comment}", session_id=sid)
                if _orchestrator:
                    _orchestrator.handle_revision(session_id=sid, comment=comment)

        elif command == "pause":
            session_mgr.transition(SessionStatus.PAUSED, "Supervisor requested pause", session_id=sid)

        elif command == "resume":
            if session.status == SessionStatus.PAUSED:
                session_mgr.transition(SessionStatus.IMPLEMENTING, "Supervisor resumed", session_id=sid)
                if _orchestrator:
                    _orchestrator.handle_resume(session_id=sid)

        elif command == "cancel":
            session_mgr.transition(SessionStatus.CANCELLED, "Supervisor cancelled session", session_id=sid)

    except ValueError as e:
        logger.warning("Transition refused [%s]: %s", sid, e)


# ========== ENDPOINTS ==========


class CreateSessionRequest(BaseModel):
    project_name: str
    objective: str
    created_by: str = SynapseConfig.AGENT_A_ID
    shared_context: list = []


class SendMessageRequest(BaseModel):
    type: str = "dialogue"
    content: str
    metadata: dict = {}


@router.post("/session")
def create_session(req: CreateSessionRequest) -> dict:
    """Creates a new SYNAPSE session. Multi-session: N parallel sessions."""
    session_mgr = get_session_manager()
    redis_client = get_redis_client()

    try:
        session = session_mgr.create(
            project_name=req.project_name,
            objective=req.objective,
            created_by=req.created_by,
            shared_context=req.shared_context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Auto-transition to CONCEPTUALIZING
    session_mgr.transition(SessionStatus.CONCEPTUALIZING, "Session started",
                           session_id=session.session_id)

    # Notify supervisor
    notification = notifications.format_session_created(session)
    redis_client.notify_supervisor(session.session_id, "session_created", notification)

    return {"status": "created", "session": session.to_dict()}


@router.get("/session")
def get_session(session_id: Optional[str] = None) -> dict:
    """Returns the state of a session (by ID or most recent)."""
    session_mgr = get_session_manager()
    session = session_mgr.get(session_id) if session_id else session_mgr.active

    if not session:
        return {"status": "no_active_session"}

    return {"status": "ok", "session": session.to_dict()}


@router.get("/sessions")
def list_sessions() -> dict:
    """Lists all sessions (active and archived)."""
    session_mgr = get_session_manager()
    active = session_mgr.active_sessions
    return {
        "sessions": session_mgr.list_sessions(),
        "active_count": len(active),
        "active_ids": [s.session_id for s in active],
        "max_concurrent": SynapseConfig.MAX_CONCURRENT_SESSIONS,
    }


@router.post("/send")
def send_message(req: SendMessageRequest, session_id: Optional[str] = None) -> dict:
    """Agent A sends a message to Agent B via Redis.
    Multi-session: pass session_id query param to target a specific session."""
    session_mgr = get_session_manager()
    redis_client = get_redis_client()

    session = session_mgr.get(session_id) if session_id else session_mgr.active
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    msg_type = MessageType(req.type)
    message = SynapseMessage(
        session_id=session.session_id,
        sender=SynapseConfig.AGENT_A_ID,
        type=msg_type,
        content=req.content,
        metadata=req.metadata,
    )

    if not message.validate():
        raise HTTPException(status_code=400, detail="Invalid message")

    payload = message.to_json()
    if len(payload.encode()) > SynapseConfig.MAX_MESSAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Message too large ({len(payload)} bytes). Max: {SynapseConfig.MAX_MESSAGE_SIZE}."
        )

    redis_client.publish_to_agent_b(message)
    session_mgr.increment_messages(session_id=session.session_id)

    session_dir = session_mgr.get_session_dir(session.session_id)
    if session_dir:
        append_to_journal(session_dir, f"{SynapseConfig.AGENT_A_NAME} [{msg_type.value}] : {req.content[:200]}")

    return {"status": "sent", "message_id": message.id, "session_id": session.session_id}


@router.post("/transition/{new_status}")
def transition_session(new_status: str, session_id: Optional[str] = None) -> dict:
    """Changes a session's state. Multi-session: pass session_id query param."""
    session_mgr = get_session_manager()
    redis_client = get_redis_client()

    try:
        status = SessionStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown status: {new_status}")

    try:
        session = session_mgr.transition(status, session_id=session_id)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    sid = session.session_id

    if status == SessionStatus.AWAITING_APPROVAL:
        notification = notifications.format_docs_ready(session)
        redis_client.notify_supervisor(sid, "docs_ready", notification)
        try:
            email = get_email_sender()
            if email.is_configured:
                session_dir = session_mgr.get_session_dir(sid)
                if session_dir:
                    result = email.send_docs_for_review(
                        session_id=sid,
                        session_dir=session_dir,
                        summary=f"Objective: {session.objective}\nPhase: Conceptualization complete",
                    )
                    logger.info("Email docs for review: %s", result)
        except Exception as e:
            logger.error("Error sending email AWAITING_APPROVAL: %s", e, exc_info=True)

    if status == SessionStatus.COMPLETED:
        notification = notifications.format_session_completed(session)
        redis_client.notify_supervisor(sid, "session_completed", notification)
        try:
            email = get_email_sender()
            if email.is_configured:
                session_dir = session_mgr.get_session_dir(sid)
                if session_dir:
                    result = email.send_session_report(
                        session_id=sid,
                        session_dir=session_dir,
                        report=f"Session completed.\nObjective: {session.objective}\nMessages: {session.messages_count}",
                    )
                    logger.info("Email session completed: %s", result)
        except Exception as e:
            logger.error("Error sending email COMPLETED: %s", e, exc_info=True)

    return {"status": "transitioned", "session": session.to_dict()}


@router.post("/checkpoint")
def send_checkpoint(progress: str, session_id: Optional[str] = None) -> dict:
    """Sends a checkpoint to the supervisor. Multi-session: pass session_id query param."""
    session_mgr = get_session_manager()
    redis_client = get_redis_client()

    session = session_mgr.get(session_id) if session_id else session_mgr.active
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    session_mgr.add_checkpoint("info", progress, session_id=session.session_id)
    notification = notifications.format_checkpoint(session, progress)
    redis_client.notify_supervisor(session.session_id, "checkpoint", notification)

    return {"status": "checkpoint_sent", "session_id": session.session_id}


@router.post("/approval-request")
def request_approval(action: str, reason: str, impact: str, session_id: Optional[str] = None) -> dict:
    """Request out-of-scope approval. Multi-session: pass session_id."""
    session_mgr = get_session_manager()
    redis_client = get_redis_client()

    session = session_mgr.get(session_id) if session_id else session_mgr.active
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    notification = notifications.format_approval_needed(session, action, reason, impact)
    redis_client.notify_supervisor(session.session_id, "approval_needed", notification)

    session_dir = session_mgr.get_session_dir(session.session_id)
    if session_dir:
        append_to_journal(session_dir, f"Out-of-scope approval request: {action}")

    return {"status": "approval_requested", "session_id": session.session_id}


@router.get("/journal")
def get_journal(count: int = 5, session_id: Optional[str] = None) -> dict:
    """Reads the last journal entries. Multi-session: pass session_id."""
    session_mgr = get_session_manager()

    if session_id:
        session_dir = session_mgr.get_session_dir(session_id)
    else:
        session_dir = session_mgr.session_dir

    if not session_dir:
        raise HTTPException(status_code=404, detail="No active session")

    entries = read_last_entries(session_dir, count)
    return {"entries": entries}


@router.post("/purge")
def purge_sessions(keep_last: int = 0, max_age_days: int = 0) -> dict:
    """Archives terminated sessions (COMPLETED/CANCELLED)."""
    session_mgr = get_session_manager()
    purged = session_mgr.purge_sessions(keep_last=keep_last, max_age_days=max_age_days)

    all_sessions = session_mgr.list_sessions()
    remaining = sum(1 for s in all_sessions if s.get("status") in ("COMPLETED", "CANCELLED"))

    return {
        "status": "purged",
        "purged": purged,
        "purged_count": len(purged),
        "remaining_terminated": remaining,
        "archive_dir": SynapseConfig.ARCHIVES_DIR,
    }


@router.get("/health")
def health_check() -> dict:
    """Checks the health of SYNAPSE infrastructure."""
    redis_client = get_redis_client()
    session_mgr = get_session_manager()

    health = redis_client.health()
    active = session_mgr.active_sessions

    return {
        "health": health,
        "active_sessions": [s.to_dict() for s in active],
        "active_count": len(active),
        "max_concurrent": SynapseConfig.MAX_CONCURRENT_SESSIONS,
        "session": active[0].to_dict() if active else None,  # Backwards compat
        "formatted": notifications.format_health(health, session_mgr.active),
    }
