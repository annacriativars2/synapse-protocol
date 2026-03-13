# SYNAPSE Orchestrator — Autonomous orchestration engine for Agent A
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md §4, 04_SUPERVISION.md §3
#
# Event-driven module: reacts to each response from Agent B via Redis.
# 1) Forward the response to the supervisor
# 2) Evaluate via LLM and decide the next action
# 3) Execute: iterate, transition, checkpoint, complete, escalate

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

from synapse.config import SynapseConfig
from synapse.journal import append_to_journal, read_last_entries
from synapse.messages import MessageType, SessionData, SessionStatus, SynapseMessage
from synapse import notifications

if TYPE_CHECKING:
    from synapse.email_sender import SynapseEmailSender
    from synapse.interfaces import LLMProvider, Notifier
    from synapse.redis_client import SynapseRedisClient
    from synapse.session import SynapseSession

logger = logging.getLogger("synapse.orchestrator")

# --- Safeguards ---
MAX_CONSECUTIVE_ITERATES = 15
MAX_SESSION_MESSAGES = 150
CHECKPOINT_INTERVAL_HOURS = 2
MAX_CONSECUTIVE_LLM_FAILURES = 3

# Blocked verb patterns in iterate messages during CONCEPTUALIZING phase
# These patterns detect execution requests outside the allowed scope
CONCEPTUALIZING_BLOCKED_PATTERNS = [
    r'\binstall(?:e[rsz]?|er|ation)\b',
    r'\bcompil(?:e[rsz]?|er|ation)\b',
    r'\bexecut(?:e[rsz]?|er|ion)\b',
    r'\bimplemen(?:te[rsz]?|ter|tation)\b',
    r'\bconfigur(?:e[rsz]?|er|ation)\b',
    r'\bdeploy(?:e[rsz]?|er|ment)\b',
    r'\bcreate\s+(?:the\s+)?files?\b',
    r'\blaunch\s+(?:the|a|an)\b',
    r'\bbuild\s+(?:the|a|an)\b',
    r'\bwrite\s+(?:the\s+)?code\b',
    r'\bstart\s+(?:the\s+)?(?:implemen|install|config)\b',
]


# --- Decision structures ---

class OrchestratorAction(str, Enum):
    ITERATE = "iterate"
    TRANSITION = "transition"
    CHECKPOINT = "checkpoint"
    COMPLETE = "complete"
    ESCALATE = "escalate"
    WAIT = "wait"


@dataclass
class OrchestratorDecision:
    action: OrchestratorAction
    next_message: Optional[str] = None
    transition_to: Optional[str] = None
    checkpoint_text: Optional[str] = None
    escalation_type: Optional[str] = None
    escalation_detail: Optional[str] = None
    reasoning: str = ""


# --- Phase descriptions for the LLM prompt ---

def _phase_description(status: SessionStatus) -> str:
    """Returns the phase description for the LLM prompt, using configured participant names."""
    a, b = SynapseConfig.AGENT_A_NAME, SynapseConfig.AGENT_B_NAME
    descriptions = {
        SessionStatus.CREATED: "Session just created. Must start conceptualization.",
        SessionStatus.CONCEPTUALIZING: (
            f"{a} and {b} are elaborating a plan. Goal: produce conceptualization documents "
            f"and reach consensus before submitting to the supervisor for approval."
        ),
        SessionStatus.AWAITING_APPROVAL: f"Documents submitted to the supervisor. Waiting for approval. Do not send anything to {b}.",
        SessionStatus.REVIEWING: "The supervisor is reading the documents.",
        SessionStatus.APPROVED: "The supervisor approved. Must start implementation.",
        SessionStatus.IMPLEMENTING: (
            f"Implementation in progress within the approved scope. {b} codes, {a} supervises. "
            f"Regular checkpoints to the supervisor."
        ),
        SessionStatus.PAUSED: "Session paused. Waiting for supervisor action.",
        SessionStatus.COMPLETED: "Session completed.",
        SessionStatus.CANCELLED: "Session cancelled.",
    }
    return descriptions.get(status, "")

# --- Orchestration prompt ---

ORCHESTRATOR_PROMPT = """You are the orchestrator agent ({agent_a_name}) in a SYNAPSE collaboration session with {agent_b_name}.
You must analyze {agent_b_name}'s latest response and decide the next action.

CURRENT SESSION STATE:
- Session: {session_id}
- Status: {status}
- Objective: {objective}
- Messages exchanged: {messages_count}
- Expected phase: {phase_description}

SESSION CONTRACT (AUTHORIZED SCOPE):
{contract}

LATEST RESPONSE FROM {agent_b_name_upper}:
{agent_b_response}

RECENT JOURNAL:
{recent_journal}

DECISION RULES BY PHASE:

If status = CONCEPTUALIZING:
- ABSOLUTE SCOPE RULE: your iterate messages must remain STRICTLY within the
  contract scope above. Allowed verbs: analyze, research, reflect, document,
  plan, project, evaluate, compare.
  FORBIDDEN verbs: install, create, compile, execute, implement, configure,
  deploy, write code, launch, build.
- If {agent_b_name} has produced a structured document or complete plan and seems to have reached consensus
  → action: "transition", transition_to: "AWAITING_APPROVAL"
- If the discussion is progressing but not finished
  → action: "iterate" with a message requesting CLARIFICATIONS or DOCUMENTS,
    never execution actions
- If disagreement detected
  → action: "escalate"
- If {agent_b_name} has started executing (creating files, installing, compiling) WITHOUT approval
  → action: "escalate" type "scope_violation" — this is a contract violation

If status = IMPLEMENTING:
- The authorized scope is defined by the execution contract (documents approved by the supervisor).
- If {agent_b_name} reports that implementation is complete and tests pass
  → action: "complete"
- If {agent_b_name} reports significant progress (file created, milestone reached)
  → action: "checkpoint" with progress summary, AND next_message to continue
- If {agent_b_name} detects an action outside the execution contract scope
  → action: "escalate" type "approval_request"
- If work continues normally within scope
  → action: "iterate" to guide the next step

IMPORTANT:
- NEVER respond with action "wait" unless status is AWAITING_APPROVAL or PAUSED.
- For "iterate", the "next_message" field is REQUIRED and must be constructive.
- For "transition", the "transition_to" field is REQUIRED.
- For "checkpoint", both "checkpoint_text" AND "next_message" are REQUIRED.
- Your iterate messages MUST NOT look like execution instructions.

RESPOND ONLY with valid JSON, no text before or after:
{{
  "action": "iterate|transition|checkpoint|complete|escalate|wait",
  "next_message": "message to send to {agent_b_name} if action=iterate or checkpoint",
  "transition_to": "AWAITING_APPROVAL|COMPLETED",
  "checkpoint_text": "checkpoint text for the supervisor if action=checkpoint",
  "escalation_type": "disagreement|approval_request|scope_violation",
  "escalation_detail": "detail if action=escalate",
  "reasoning": "short explanation of your decision"
}}"""


class SynapseOrchestrator:
    """Autonomous orchestration engine for SYNAPSE sessions.

    Event-driven: reacts to Agent B responses (Redis callback).
    Uses an LLM to decide actions.
    """

    def __init__(self, session_manager: SynapseSession, redis_client: SynapseRedisClient,
                 notifier: Notifier, email_sender: Optional[SynapseEmailSender] = None,
                 llm: Optional[LLMProvider] = None):
        self._session_mgr = session_manager
        self._redis = redis_client
        self._notifier = notifier
        self._email = email_sender
        self._llm = llm

        # Per-session counters (multi-session support)
        self._session_contexts: Dict[str, dict] = {}

    def _get_ctx(self, session_id: str) -> dict:
        """Get or create per-session context."""
        if session_id not in self._session_contexts:
            self._session_contexts[session_id] = {
                "consecutive_iterates": 0,
                "consecutive_llm_failures": 0,
            }
        return self._session_contexts[session_id]

    # ========== ENTRY POINTS ==========

    def handle_agent_b_response(self, message: SynapseMessage, session_id: Optional[str] = None) -> None:
        """Main entry point — called when Agent B responds via Redis.

        Args:
            message: The message from Agent B
            session_id: Target session ID (for multi-session routing).
                        If None, uses the most recent session.
        """
        if session_id:
            session = self._session_mgr.get(session_id)
        else:
            session = self._session_mgr.active
        if not session:
            return

        sid = session.session_id

        # Step 1: skip if session is waiting (no forward, no action)
        if session.status in (
            SessionStatus.AWAITING_APPROVAL,
            SessionStatus.PAUSED,
            SessionStatus.COMPLETED,
            SessionStatus.CANCELLED,
        ):
            logger.info("Session %s in %s, no orchestrator action", sid, session.status.value)
            return

        # Store Agent B response for later use (e.g. file extraction)
        ctx = self._get_ctx(session.session_id)
        ctx["last_agent_b_response"] = message.content

        # Step 3: check safeguards
        forced = self._check_safeguards(session)
        if forced:
            return

        # Step 4: evaluate and decide via LLM
        decision = self._evaluate_and_decide(message, session)

        # Step 5: journal the decision
        session_dir = self._session_mgr.get_session_dir(sid)
        if session_dir:
            append_to_journal(
                session_dir,
                f"Orchestrator [{decision.action.value}] : {decision.reasoning}"
            )

        # Step 6: execute
        self._execute(decision, session)

    def handle_approval(self, session_id: Optional[str] = None) -> None:
        """Called when the supervisor approves via /synapse approve."""
        session = self._session_mgr._resolve_session(session_id)
        if not session:
            return

        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0

        # Read plan if available
        session_dir = self._session_mgr.get_session_dir(session.session_id)
        plan_content = ""
        if session_dir:
            plan_path = os.path.join(session_dir, "01_PLAN.md")
            if os.path.exists(plan_path):
                try:
                    with open(plan_path, "r", encoding="utf-8") as f:
                        plan_content = f.read()[:3000]
                except Exception:
                    pass

        # Store execution contract = approved documents
        if plan_content:
            self._session_mgr.set_execution_contract(plan_content, session_id=session.session_id)
            logger.info("Execution contract set [%s]: %s chars", session.session_id, len(plan_content))

        kickoff = (
            f"The supervisor approved the plan. Moving to implementation.\n\n"
            f"Objective: {session.objective}\n"
        )
        if plan_content:
            kickoff += f"\nApproved plan (EXECUTION SCOPE — only the actions described below):\n{plan_content}\n"
        kickoff += "\nStart implementation according to the plan. Report your progress."

        self._send_to_agent_b(kickoff, MessageType.ACTION, session, source="supervisor_approval")
        logger.info("Orchestrator [%s]: kickoff implementation after supervisor approval", session.session_id)

    def handle_revision(self, session_id: Optional[str] = None, comment: str = "") -> None:
        """Called when the supervisor requests a revision via /synapse revise."""
        session = self._session_mgr._resolve_session(session_id)
        if not session:
            return

        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0

        # List existing documents for context
        session_dir = self._session_mgr.get_session_dir(session.session_id)
        existing_docs = ""
        if session_dir:
            docs_dir = os.path.join(session_dir, "docs")
            if os.path.isdir(docs_dir):
                files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]
                if files:
                    existing_docs = ", ".join(sorted(files))

        revision_msg = (
            f"The supervisor has reviewed the documents and requests a revision.\n\n"
            f"Supervisor comment: {comment}\n\n"
            f"Original objective: {session.objective}\n"
        )
        if existing_docs:
            revision_msg += f"Existing documents in docs/: {existing_docs}\n"
        revision_msg += (
            f"\nModify the documents in docs/ according to the supervisor's comment. "
            f"Do not create unnecessary new files, update existing ones. "
            f"When done, summarize the modifications made."
        )

        self._send_to_agent_b(revision_msg, MessageType.DIALOGUE, session, source="supervisor_revision")
        logger.info("Orchestrator [%s]: revision requested by supervisor: %s", session.session_id, comment[:100])

    def handle_resume(self, session_id: Optional[str] = None) -> None:
        """Called when the supervisor resumes a session via /synapse resume."""
        session = self._session_mgr._resolve_session(session_id)
        if not session:
            return

        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0

        journal_context = self._get_journal_context(3, session)
        resume_msg = (
            f"Session resumed by the supervisor.\n"
            f"Objective: {session.objective}\n"
            f"Recent activity:\n{journal_context}\n\n"
            f"Continue the work."
        )

        self._send_to_agent_b(resume_msg, MessageType.RESUME, session, source="supervisor_resume")
        logger.info("Orchestrator [%s]: session resumed after supervisor resume", session.session_id)

    # ========== FORWARD TO SUPERVISOR ==========

    def _forward_to_supervisor(self, message: SynapseMessage, session: Optional[SessionData] = None) -> None:
        """Forwards Agent B's response to the supervisor."""
        if session is None:
            session = self._session_mgr.active
        content = message.content

        msg_type = message.type.value if isinstance(message.type, MessageType) else message.type
        header = f"SYNAPSE | {SynapseConfig.AGENT_B_NAME} [{msg_type}]"
        if session:
            header += f"\nSession: {session.session_id}"

        max_content = 3500 - len(header) - 50
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[... truncated — /synapse log to see full]"

        text = f"{header}\n{'=' * 30}\n{content}"

        try:
            self._notifier.send_message(text)
            logger.info("Agent B response forwarded to supervisor")
        except Exception as e:
            logger.error("Error forwarding to supervisor: %s", e)

    # ========== LLM DECISION ENGINE ==========

    def _evaluate_and_decide(self, message: SynapseMessage, session: Optional[SessionData] = None) -> OrchestratorDecision:
        """Evaluates Agent B's response via LLM and returns a decision."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return OrchestratorDecision(action=OrchestratorAction.WAIT, reasoning="No session")

        journal_context = self._get_journal_context(5, session)
        phase_desc = _phase_description(session.status) or "Unknown phase"

        # Active contract based on phase
        if session.status == SessionStatus.IMPLEMENTING and session.execution_contract:
            active_contract = session.execution_contract
        else:
            active_contract = session.contract or session.objective

        prompt = ORCHESTRATOR_PROMPT.format(
            agent_a_name=SynapseConfig.AGENT_A_NAME,
            agent_b_name=SynapseConfig.AGENT_B_NAME,
            agent_b_name_upper=SynapseConfig.AGENT_B_NAME.upper(),
            session_id=session.session_id,
            status=session.status.value,
            objective=session.objective,
            messages_count=session.messages_count,
            phase_description=phase_desc,
            contract=active_contract[:2000],
            agent_b_response=message.content[:3000],
            recent_journal=journal_context[:2000],
        )

        if not self._llm:
            logger.error("No LLM provider configured — cannot make orchestration decisions")
            return self._handle_llm_failure(session)

        try:
            result = self._llm.chat(
                user_message=prompt,
                memory_context="",
                temperature=0.3,
                max_tokens=512,
            )

            ctx = self._get_ctx(session.session_id)
            if result.get("success"):
                ctx["consecutive_llm_failures"] = 0
                return self._parse_decision(result["response"])
            else:
                ctx["consecutive_llm_failures"] += 1
                logger.error("LLM failure: %s", result.get('error'))
                return self._handle_llm_failure(session)

        except Exception as e:
            ctx = self._get_ctx(session.session_id)
            ctx["consecutive_llm_failures"] += 1
            logger.error("LLM exception: %s", e)
            return self._handle_llm_failure(session)

    def _parse_decision(self, llm_response: str) -> OrchestratorDecision:
        """Parses the LLM JSON response into a structured decision."""
        # Attempt 1: direct JSON
        try:
            data = json.loads(llm_response.strip())
            return self._dict_to_decision(data)
        except json.JSONDecodeError:
            pass

        # Attempt 2: extract from markdown ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", llm_response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return self._dict_to_decision(data)
            except json.JSONDecodeError:
                pass

        # Attempt 3: regex for JSON object
        match = re.search(r"\{[^{}]*\"action\"[^{}]*\}", llm_response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return self._dict_to_decision(data)
            except json.JSONDecodeError:
                pass

        # Fallback: WAIT
        logger.warning("Unable to parse LLM decision: %s", llm_response[:200])
        return OrchestratorDecision(
            action=OrchestratorAction.WAIT,
            reasoning=f"JSON parse failed: {llm_response[:100]}",
        )

    def _dict_to_decision(self, data: dict) -> OrchestratorDecision:
        """Converts a dict to OrchestratorDecision with validation."""
        try:
            action = OrchestratorAction(data.get("action", "wait"))
        except ValueError:
            action = OrchestratorAction.WAIT

        return OrchestratorDecision(
            action=action,
            next_message=data.get("next_message"),
            transition_to=data.get("transition_to"),
            checkpoint_text=data.get("checkpoint_text"),
            escalation_type=data.get("escalation_type"),
            escalation_detail=data.get("escalation_detail"),
            reasoning=data.get("reasoning", ""),
        )

    # ========== EXECUTORS ==========

    def _execute(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Dispatches execution based on the decided action."""
        if session is None:
            session = self._session_mgr.active
        if not session or session.status in (
            SessionStatus.PAUSED, SessionStatus.CANCELLED, SessionStatus.COMPLETED
        ):
            logger.info("Session %s, action cancelled", session.status.value if session else 'None')
            return

        executors = {
            OrchestratorAction.ITERATE: self._execute_iterate,
            OrchestratorAction.TRANSITION: self._execute_transition,
            OrchestratorAction.CHECKPOINT: self._execute_checkpoint,
            OrchestratorAction.COMPLETE: self._execute_complete,
            OrchestratorAction.ESCALATE: self._execute_escalate,
            OrchestratorAction.WAIT: lambda d, s: logger.info("WAIT [%s]: %s", s.session_id, d.reasoning),
        }

        executor = executors.get(decision.action)
        if executor:
            try:
                executor(decision, session)
            except Exception as e:
                logger.error("Execution error %s: %s", decision.action.value, e, exc_info=True)
                self._handle_orchestrator_error(e, session)

    def _execute_iterate(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Sends the next message to Agent B."""
        if not decision.next_message:
            logger.warning("Iterate without next_message, skip")
            return
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        # Safeguard: check that iterate message doesn't request execution
        # in CONCEPTUALIZING phase (contract violation)
        if session.status == SessionStatus.CONCEPTUALIZING:
            msg_lower = decision.next_message.lower()
            for pattern in CONCEPTUALIZING_BLOCKED_PATTERNS:
                if re.search(pattern, msg_lower, re.IGNORECASE):
                    logger.warning(
                        "Scope violation [%s]: iterate blocked "
                        "in CONCEPTUALIZING, pattern='%s', "
                        "message='%s...'",
                        session.session_id, pattern, decision.next_message[:100]
                    )
                    # Convert to escalation instead of sending
                    self._execute_escalate(OrchestratorDecision(
                        action=OrchestratorAction.ESCALATE,
                        escalation_type="scope_violation",
                        escalation_detail=(
                            f"The orchestrator attempted to send an execution message "
                            f"in CONCEPTUALIZING phase: '{decision.next_message[:200]}...'"
                        ),
                        reasoning="Iterate message outside contract detected by safeguard",
                    ), session)
                    return

        ctx = self._get_ctx(session.session_id)
        self._send_to_agent_b(decision.next_message, MessageType.DIALOGUE, session,
                             source="orchestrator_iterate")
        ctx["consecutive_iterates"] += 1
        logger.info("Iterate [%s] #%s: %s...", session.session_id, ctx['consecutive_iterates'], decision.next_message[:80])

    def _execute_transition(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Changes the session state."""
        if not decision.transition_to:
            logger.warning("Transition without target, skip")
            return

        try:
            target = SessionStatus(decision.transition_to)
        except ValueError:
            logger.error("Invalid status: %s", decision.transition_to)
            return

        sid = session.session_id if session else None
        session = self._session_mgr.transition(target, decision.reasoning, session_id=sid)
        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0
        logger.info("Transition [%s] to %s", session.session_id, target.value)

        # Side effects
        if target == SessionStatus.AWAITING_APPROVAL:
            self._collect_generated_docs(session)
            notif = notifications.format_docs_ready(session)
            self._redis.notify_supervisor(session.session_id, "docs_ready", notif)
            self._send_docs_email(session)

    def _execute_checkpoint(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Sends a checkpoint to the supervisor."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        checkpoint_text = decision.checkpoint_text or decision.reasoning
        self._session_mgr.add_checkpoint("info", checkpoint_text, session_id=session.session_id)

        notif = notifications.format_checkpoint(session, checkpoint_text)
        self._redis.notify_supervisor(session.session_id, "checkpoint", notif)
        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0
        logger.info("Checkpoint [%s] sent: %s...", session.session_id, checkpoint_text[:80])

        # If next_message, continue the work
        if decision.next_message:
            self._send_to_agent_b(decision.next_message, MessageType.DIALOGUE, session,
                                 source="orchestrator_iterate")
            ctx["consecutive_iterates"] = 1

    def _execute_complete(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Closes the session: results, transition, notification."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        session_dir = self._session_mgr.get_session_dir(session.session_id)

        # Write 03_RESULTS.md
        if session_dir:
            results_content = self._generate_results(session, decision)
            results_path = os.path.join(session_dir, "03_RESULTS.md")
            try:
                with open(results_path, "w", encoding="utf-8") as f:
                    f.write(results_content)
                logger.info("03_RESULTS.md written in %s", session_dir)
            except Exception as e:
                logger.error("Error writing results: %s", e)

        # Transition
        self._session_mgr.transition(SessionStatus.COMPLETED, decision.reasoning,
                                     session_id=session.session_id)

        # Notifications
        notif = notifications.format_session_completed(session)
        self._redis.notify_supervisor(session.session_id, "session_completed", notif)

        # Email with deliverables
        if self._email.is_configured and session_dir:
            try:
                self._email.send_session_report(
                    session_id=session.session_id,
                    session_dir=session_dir,
                    report=(
                        f"Session completed.\n"
                        f"Objective: {session.objective}\n"
                        f"Messages: {session.messages_count}"
                    ),
                )
            except Exception as e:
                logger.error("Error email completion: %s", e)

        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0
        logger.info("Session [%s] completed by orchestrator", session.session_id)

    def _execute_escalate(self, decision: OrchestratorDecision, session: Optional[SessionData] = None) -> None:
        """Escalates to the supervisor (disagreement or out-of-scope approval)."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        escalation_type = decision.escalation_type or "approval_request"
        detail = decision.escalation_detail or decision.reasoning

        if escalation_type == "approval_request":
            notif = notifications.format_approval_needed(
                session, detail, "Orchestrator detected out-of-scope action", detail
            )
        else:
            notif = f"SYNAPSE | Disagreement\n{'=' * 30}\nSession: {session.session_id}\n\n{detail}"

        self._redis.notify_supervisor(session.session_id, escalation_type, notif)

        session_dir = self._session_mgr.get_session_dir(session.session_id)
        if session_dir:
            append_to_journal(session_dir, f"Escalation [{escalation_type}] : {detail[:200]}")

        ctx = self._get_ctx(session.session_id)
        ctx["consecutive_iterates"] = 0
        logger.info("Escalation [%s] %s: %s...", session.session_id, escalation_type, detail[:80])

    # ========== SAFEGUARDS ==========

    def _check_safeguards(self, session: SessionData) -> bool:
        """Checks safeguards. Returns True if a forced action was taken."""
        ctx = self._get_ctx(session.session_id)

        # Max total messages
        if session.messages_count >= MAX_SESSION_MESSAGES:
            logger.warning("Safeguard [%s]: %s messages reached", session.session_id, session.messages_count)
            try:
                self._session_mgr.transition(SessionStatus.PAUSED, "Safeguard: max messages reached",
                                             session_id=session.session_id)
            except (RuntimeError, ValueError):
                pass
            self._notifier.send_message(
                f"SYNAPSE | Safeguard\n{'=' * 30}\n"
                f"Session: {session.session_id}\n"
                f"{session.messages_count} messages exchanged (max {MAX_SESSION_MESSAGES}).\n"
                f"Session paused.\n\n"
                f"/synapse resume {session.session_id} — Continue\n"
                f"/synapse cancel {session.session_id} — Cancel"
            )
            return True

        # Anti-loop: too many consecutive iterations
        if ctx["consecutive_iterates"] >= MAX_CONSECUTIVE_ITERATES:
            logger.warning("Safeguard [%s]: %s consecutive iterations", session.session_id, ctx['consecutive_iterates'])
            ctx["consecutive_iterates"] = 0
            self._session_mgr.add_checkpoint(
                "safeguard",
                f"{MAX_CONSECUTIVE_ITERATES} consecutive iterations without checkpoint",
                session_id=session.session_id,
            )
            self._notifier.send_message(
                f"SYNAPSE | Auto Checkpoint\n{'=' * 30}\n"
                f"Session: {session.session_id}\n"
                f"{MAX_CONSECUTIVE_ITERATES} exchanges since last checkpoint.\n"
                f"Objective: {session.objective}\n"
                f"Total messages: {session.messages_count}\n\n"
                f"Session continues. /synapse pause {session.session_id} if needed."
            )
            return False

        # Time checkpoint (2h)
        if session.checkpoints:
            try:
                last_cp = session.checkpoints[-1].get("at", "")
                if last_cp:
                    last_time = datetime.fromisoformat(last_cp)
                    hours = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
                    if hours >= CHECKPOINT_INTERVAL_HOURS:
                        self._session_mgr.add_checkpoint(
                            "time", f"Auto checkpoint ({hours:.1f}h elapsed)",
                            session_id=session.session_id,
                        )
                        self._notifier.send_message(
                            f"SYNAPSE | Heartbeat\n{'=' * 30}\n"
                            f"Session: {session.session_id}\n"
                            f"{hours:.1f}h since last checkpoint.\n"
                            f"Messages: {session.messages_count}\n"
                            f"Status: {session.status.value}"
                        )
            except Exception:
                pass

        return False

    def _handle_llm_failure(self, session: Optional[SessionData] = None) -> OrchestratorDecision:
        """Handles consecutive LLM failures."""
        if session is None:
            session = self._session_mgr.active
        if session:
            ctx = self._get_ctx(session.session_id)
            if ctx["consecutive_llm_failures"] >= MAX_CONSECUTIVE_LLM_FAILURES:
                logger.error("Safeguard [%s]: %s consecutive LLM failures", session.session_id, ctx['consecutive_llm_failures'])
                try:
                    self._session_mgr.transition(
                        SessionStatus.PAUSED,
                        f"Safeguard: {ctx['consecutive_llm_failures']} LLM failures",
                        session_id=session.session_id,
                    )
                except (RuntimeError, ValueError):
                    pass
                self._notifier.send_message(
                    f"SYNAPSE | LLM Error\n{'=' * 30}\n"
                    f"Session: {session.session_id}\n"
                    f"The orchestrator LLM failed {ctx['consecutive_llm_failures']} times.\n"
                    f"Session paused.\n\n"
                    f"/synapse resume {session.session_id} — Resume"
                )
                ctx["consecutive_llm_failures"] = 0
        return OrchestratorDecision(
            action=OrchestratorAction.WAIT,
            reasoning="LLM failure"
        )

    def _handle_orchestrator_error(self, error: Exception, session: Optional[SessionData] = None) -> None:
        """Handles orchestrator execution errors."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        try:
            if session.status not in (
                SessionStatus.PAUSED, SessionStatus.COMPLETED, SessionStatus.CANCELLED
            ):
                self._session_mgr.transition(
                    SessionStatus.PAUSED,
                    f"Orchestrator error: {str(error)[:100]}",
                    session_id=session.session_id,
                )
        except (RuntimeError, ValueError):
            pass

        try:
            self._notifier.send_message(
                f"SYNAPSE | Orchestrator Error\n{'=' * 30}\n"
                f"Session: {session.session_id}\n"
                f"Error: {str(error)[:200]}\n\n"
                f"/synapse resume {session.session_id} — Resume"
            )
        except Exception:
            pass

    # ========== HELPERS ==========

    def _send_to_agent_b(self, content: str, msg_type: MessageType, session: Optional[SessionData] = None,
                        source: str = "orchestrator") -> None:
        """Sends a message to Agent B via Redis with scope header."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return

        # Scope header so Agent B knows the authorized scope
        if session.status == SessionStatus.IMPLEMENTING and session.execution_contract:
            contract_summary = session.execution_contract[:300]
        else:
            contract_summary = (session.contract or session.objective)[:300]

        scope_header = (
            f"[SYNAPSE:{session.status.value}] "
            f"[SOURCE:{source}] "
            f"[SCOPE:{contract_summary}]"
        )
        tagged_content = f"{scope_header}\n\n{content}"

        msg = SynapseMessage(
            session_id=session.session_id,
            sender=SynapseConfig.AGENT_A_ID,
            type=msg_type,
            content=tagged_content,
        )
        self._redis.publish_to_agent_b(msg)
        self._session_mgr.increment_messages(session_id=session.session_id)

        session_dir = self._session_mgr.get_session_dir(session.session_id)
        if session_dir:
            append_to_journal(session_dir, f"{SynapseConfig.AGENT_A_NAME} [{msg_type.value}] : {content[:200]}")

    def _collect_generated_docs(self, session: SessionData) -> None:
        """Copies documents generated by Agent B outside the session to docs/.

        Scans Agent B's last response to extract mentioned file paths.
        If a file exists but is not in the session directory, it is copied to docs/.
        """
        session_dir = self._session_mgr.get_session_dir(session.session_id)
        if not session_dir:
            return

        ctx = self._get_ctx(session.session_id)
        response = ctx.get("last_agent_b_response", "")
        if not response:
            return

        docs_dir = os.path.join(session_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        # Extract absolute file paths mentioned in the response
        paths = re.findall(r"(/\S+\.(?:md|txt|py|json|yaml|yml))", response)

        import shutil
        for path in paths:
            # Clean trailing punctuation
            path = path.rstrip(".,;:!?\"'`)")
            if not os.path.isfile(path):
                continue
            if path.startswith(session_dir):
                continue  # Already in session directory

            dest = os.path.join(docs_dir, os.path.basename(path))
            try:
                shutil.copy2(path, dest)
                logger.info("Document copied to docs/: %s -> %s", path, dest)
            except Exception as e:
                logger.error("Error copying document %s: %s", path, e)

    def _send_docs_email(self, session: SessionData) -> None:
        """Sends the documents email for review."""
        if not self._email.is_configured:
            return

        session_dir = self._session_mgr.get_session_dir(session.session_id)
        if not session_dir:
            return

        try:
            result = self._email.send_docs_for_review(
                session_id=session.session_id,
                session_dir=session_dir,
                summary=(
                    f"Objective: {session.objective}\n"
                    f"Phase: Conceptualization complete"
                ),
            )
            logger.info("Email docs review: %s", result)
        except Exception as e:
            logger.error("Error email docs: %s", e)

    def _get_journal_context(self, count: int = 5, session: Optional[SessionData] = None) -> str:
        """Reads the last journal entries."""
        if session is None:
            session = self._session_mgr.active
        if not session:
            return ""
        session_dir = self._session_mgr.get_session_dir(session.session_id)
        if not session_dir:
            return ""
        try:
            return read_last_entries(session_dir, count) or ""
        except Exception:
            return ""

    def _generate_results(self, session: SessionData, decision: OrchestratorDecision) -> str:
        """Generates the 03_RESULTS.md content."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # List produced files
        session_dir = self._session_mgr.get_session_dir(session.session_id)
        files_produced = []
        if session_dir:
            for subdir in ["docs", "code", "tests"]:
                d = os.path.join(session_dir, subdir)
                if os.path.exists(d):
                    for f in os.listdir(d):
                        files_produced.append(f"{subdir}/{f}")

        files_list = "\n".join(f"- {f}" for f in files_produced) if files_produced else "- No files produced"

        return (
            f"# Session Results — {session.session_id}\n\n"
            f"**Completion date**: {now}\n"
            f"**Objective**: {session.objective}\n"
            f"**Messages exchanged**: {session.messages_count}\n\n"
            f"---\n\n"
            f"## Files produced\n\n{files_list}\n\n"
            f"---\n\n"
            f"## Conclusion\n\n{decision.reasoning}\n\n"
            f"---\n\n"
            f"*Document automatically generated by the SYNAPSE orchestrator.*\n"
        )
