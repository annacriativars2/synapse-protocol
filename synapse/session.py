# SYNAPSE Session Manager — Multi-session support
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md §1-2
# Refactored: supports N concurrent sessions (max MAX_CONCURRENT_SESSIONS)

from __future__ import annotations

import json
import os
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from synapse.config import SynapseConfig
from synapse.messages import SessionData, SessionStatus, VALID_TRANSITIONS

logger = logging.getLogger("synapse.session")


class SynapseSession:
    """Manages the lifecycle of SYNAPSE sessions.

    Supports N simultaneous active sessions (02_PROTOCOLE.md §1).
    Backward-compatible: the .active property returns the most recent session.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}  # session_id -> SessionData
        self._load_active_sessions()

    # --- Creation ---

    def create(self, project_name: str, objective: str, created_by: str = SynapseConfig.AGENT_A_ID,
               shared_context: Optional[list[str]] = None, contract: str = "") -> SessionData:
        """Creates a new SYNAPSE session.

        Allows multiple simultaneous sessions up to MAX_CONCURRENT_SESSIONS.
        Args:
            contract: Authorized scope. If empty, uses the objective as initial contract.
        """
        active_count = len(self.active_sessions)
        if active_count >= SynapseConfig.MAX_CONCURRENT_SESSIONS:
            raise RuntimeError(
                f"Maximum {SynapseConfig.MAX_CONCURRENT_SESSIONS} simultaneous sessions reached. "
                f"Active sessions: {[s.session_id for s in self.active_sessions]}"
            )

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        session_id = self._generate_unique_id(date_str, project_name)
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session_id)

        # Create session directory (02_PROTOCOLE.md §2.1)
        os.makedirs(session_dir, exist_ok=True)
        os.makedirs(os.path.join(session_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "code"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "tests"), exist_ok=True)

        logger.info("[DEBUG] create() objective len=%s, contract len=%s", len(objective), len(contract) if contract else 'none')

        session = SessionData(
            session_id=session_id,
            created_at=now.isoformat(),
            created_by=created_by,
            status=SessionStatus.CREATED,
            objective=objective,
            shared_context=shared_context or [],
            contract=contract or objective,
            last_activity=now.isoformat(),
        )

        logger.info("[DEBUG] SessionData objective len=%s, contract len=%s", len(session.objective), len(session.contract))

        # Write session.json
        self._write_session_json(session_dir, session)

        # Post-write verification
        import json as _json
        with open(os.path.join(session_dir, SynapseConfig.SESSION_JSON), "r") as _f:
            _written = _json.load(_f)
        logger.info("[DEBUG] session.json written objective len=%s", len(_written.get('objective', '')))

        # Write 00_OBJECTIVE.md (immutable — 02_PROTOCOLE.md §2.3)
        objective_content = f"""# Session Objective

**Requested by** : {created_by.capitalize()}
**Date** : {now.strftime("%Y-%m-%d")}

## Original request
{objective}

## Scope contract (authorized scope)
{session.contract}

## Reference documents
"""
        for ref in (shared_context or []):
            objective_content += f"- {ref}\n"

        self._write_file(os.path.join(session_dir, SynapseConfig.OBJECTIVE_FILE), objective_content)

        # Initialize 02_JOURNAL.md (02_PROTOCOLE.md §2.4)
        journal_content = f"""# Session Journal — {session_id}

## {now.strftime("%Y-%m-%d %H:%M")} — Creation
- Session created by {created_by}
- Objective: {objective}
"""
        self._write_file(os.path.join(session_dir, SynapseConfig.JOURNAL_FILE), journal_content)

        self._sessions[session_id] = session
        logger.info("Session created: %s (active: %s)", session_id, len(self.active_sessions))
        return session

    # --- State transitions ---

    def transition(self, new_status: SessionStatus, reason: str = "",
                   session_id: Optional[str] = None) -> SessionData:
        """Changes a session's state (02_PROTOCOLE.md §1.3).

        Args:
            new_status: The new status
            reason: Reason for the transition
            session_id: Target session ID. If None, uses the most recent session.
        """
        session = self._resolve_session(session_id)
        if not session:
            raise RuntimeError("No active session." if not session_id
                               else f"Session {session_id} not found.")

        current = session.status

        # CANCELLED is always reachable (except from COMPLETED/CANCELLED)
        if new_status == SessionStatus.CANCELLED:
            if current in (SessionStatus.COMPLETED, SessionStatus.CANCELLED):
                raise ValueError(f"Cannot cancel a {current.value} session.")
        elif new_status not in VALID_TRANSITIONS.get(current, []):
            raise ValueError(
                f"Invalid transition: {current.value} -> {new_status.value}. "
                f"Allowed transitions: {[s.value for s in VALID_TRANSITIONS.get(current, [])]}"
            )

        old_status = current
        session.status = new_status
        session.last_activity = datetime.now(timezone.utc).isoformat()

        if new_status == SessionStatus.APPROVED:
            session.approved_at = session.last_activity

        self._save_session(session)
        logger.info("Transition [%s]: %s -> %s (%s)", session.session_id, old_status.value, new_status.value, reason)
        return session

    # --- Accessors ---

    @property
    def active(self) -> Optional[SessionData]:
        """Backward-compatible: returns the most recent active session."""
        sessions = self.active_sessions
        if not sessions:
            return None
        return max(sessions, key=lambda s: s.last_activity or s.created_at)

    @property
    def active_sessions(self) -> List[SessionData]:
        """All non-terminated sessions."""
        return [
            s for s in self._sessions.values()
            if s.status not in (SessionStatus.COMPLETED, SessionStatus.CANCELLED)
        ]

    @property
    def session_dir(self) -> Optional[str]:
        """Backward-compatible: directory of the most recent session."""
        session = self.active
        if not session:
            return None
        return os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

    def get(self, session_id: str) -> Optional[SessionData]:
        """Retrieves a session by its ID."""
        return self._sessions.get(session_id)

    def get_session_dir(self, session_id: str) -> Optional[str]:
        """Directory of a specific session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)

    def increment_messages(self, session_id: Optional[str] = None) -> None:
        """Increments the message counter."""
        session = self._resolve_session(session_id)
        if session:
            session.messages_count += 1
            session.last_activity = datetime.now(timezone.utc).isoformat()
            self._save_session(session)

    def set_agent_b_session_id(self, agent_b_session_id: str, session_id: Optional[str] = None) -> None:
        """Stores Agent B's session ID for --resume (03_TRANSPORT.md §4.4)."""
        session = self._resolve_session(session_id)
        if session:
            session.agent_b_session_id = agent_b_session_id
            self._save_session(session)

    def set_contract(self, contract: str, session_id: Optional[str] = None) -> None:
        """Sets the scope contract (authorized scope in CONCEPTUALIZING)."""
        session = self._resolve_session(session_id)
        if session:
            session.contract = contract
            self._save_session(session)

    def set_execution_contract(self, execution_contract: str, session_id: Optional[str] = None) -> None:
        """Sets the execution contract (authorized scope in IMPLEMENTING)."""
        session = self._resolve_session(session_id)
        if session:
            session.execution_contract = execution_contract
            self._save_session(session)

    def set_approved_scope(self, scope: list[str], session_id: Optional[str] = None) -> None:
        """Sets the approved scope (04_SUPERVISION.md §2.2)."""
        session = self._resolve_session(session_id)
        if session:
            session.approved_scope = scope
            self._save_session(session)

    def add_checkpoint(self, checkpoint_type: str, message: str, session_id: Optional[str] = None) -> None:
        """Adds a checkpoint (04_SUPERVISION.md §3.3)."""
        session = self._resolve_session(session_id)
        if session:
            session.checkpoints.append({
                "at": datetime.now(timezone.utc).isoformat(),
                "type": checkpoint_type,
                "message": message,
            })
            self._save_session(session)

    # --- Purge (archival) ---

    def purge_sessions(self, keep_last: int = 0, max_age_days: int = 0) -> list[str]:
        """Archives terminated sessions (COMPLETED/CANCELLED).

        Moves directories to ARCHIVES_DIR, does not delete anything.

        Args:
            keep_last: Keep the N most recent terminated sessions.
            max_age_days: Only purge sessions older than X days.

        Returns:
            List of archived session_ids.
        """
        all_sessions = self.list_sessions()
        terminated = [
            s for s in all_sessions
            if s.get("status") in ("COMPLETED", "CANCELLED")
        ]

        # Sort by last_activity descending (most recent first)
        terminated.sort(
            key=lambda s: s.get("last_activity") or s.get("created_at", ""),
            reverse=True,
        )

        # Keep the N most recent
        if keep_last > 0:
            to_purge = terminated[keep_last:]
        else:
            to_purge = terminated

        # Filter by age if requested
        if max_age_days > 0:
            now = datetime.now(timezone.utc)
            filtered = []
            for s in to_purge:
                ts = s.get("last_activity") or s.get("created_at", "")
                if ts:
                    try:
                        session_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        age = (now - session_time).days
                        if age >= max_age_days:
                            filtered.append(s)
                    except (ValueError, TypeError):
                        filtered.append(s)
                else:
                    filtered.append(s)
            to_purge = filtered

        if not to_purge:
            return []

        os.makedirs(SynapseConfig.ARCHIVES_DIR, exist_ok=True)

        purged = []
        for s in to_purge:
            sid = s.get("session_id", "")
            if not sid:
                continue
            source = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, sid)
            destination = os.path.join(SynapseConfig.ARCHIVES_DIR, sid)

            if not os.path.isdir(source):
                continue

            try:
                shutil.move(source, destination)
                # Remove from memory if loaded
                self._sessions.pop(sid, None)
                purged.append(sid)
                logger.info("Session archived: %s -> %s", sid, destination)
            except Exception as e:
                logger.error("Archive error %s: %s", sid, e)

        return purged

    # --- Session listing ---

    def list_sessions(self) -> list[dict]:
        """Lists all sessions (active and archived)."""
        sessions = []
        base = SynapseConfig.SESSIONS_BASE_DIR
        for name in sorted(os.listdir(base)):
            if not name.startswith(SynapseConfig.SESSION_PREFIX):
                continue
            session_json = os.path.join(base, name, SynapseConfig.SESSION_JSON)
            if os.path.exists(session_json):
                try:
                    with open(session_json, "r") as f:
                        data = json.load(f)
                    sessions.append(data)
                except (json.JSONDecodeError, OSError):
                    pass
        return sessions

    # --- Unique ID generation ---

    def _generate_unique_id(self, date_str: str, project_name: str) -> str:
        """Generates a unique session_id with an incremental counter.

        Scans existing directories (active + archives) to avoid collisions.
        Format: SYNAPSE_SESSION_20260203_01_telegram-request
        """
        prefix = f"{SynapseConfig.SESSION_PREFIX}_{date_str}_"
        suffix = f"_{project_name}"
        existing_counters = set()

        # Scan the main directory and archives
        for base_dir in (SynapseConfig.SESSIONS_BASE_DIR, SynapseConfig.ARCHIVES_DIR):
            if not os.path.isdir(base_dir):
                continue
            for name in os.listdir(base_dir):
                if name.startswith(prefix) and name.endswith(suffix):
                    # Extract the counter between the prefix and the suffix
                    middle = name[len(prefix):-len(suffix)] if len(suffix) > 0 else name[len(prefix):]
                    if middle.isdigit():
                        existing_counters.add(int(middle))

        # Also check in-memory sessions (not yet on disk)
        for sid in self._sessions:
            if sid.startswith(prefix) and sid.endswith(suffix):
                middle = sid[len(prefix):-len(suffix)] if len(suffix) > 0 else sid[len(prefix):]
                if middle.isdigit():
                    existing_counters.add(int(middle))

        counter = max(existing_counters, default=0) + 1
        return f"{prefix}{counter:02d}{suffix}"

    # --- Resolution ---

    def _resolve_session(self, session_id: Optional[str] = None) -> Optional[SessionData]:
        """Resolves a session by ID or returns the most recent one."""
        if session_id:
            return self._sessions.get(session_id)
        return self.active

    # --- Persistence ---

    def _save_session(self, session: SessionData) -> None:
        """Saves a specific session."""
        session_dir = os.path.join(SynapseConfig.SESSIONS_BASE_DIR, session.session_id)
        self._write_session_json(session_dir, session)

    def _load_active_sessions(self) -> None:
        """Loads all active sessions at startup."""
        base = SynapseConfig.SESSIONS_BASE_DIR
        if not os.path.isdir(base):
            return
        for name in sorted(os.listdir(base), reverse=True):
            if not name.startswith(SynapseConfig.SESSION_PREFIX):
                continue
            session_json = os.path.join(base, name, SynapseConfig.SESSION_JSON)
            if not os.path.exists(session_json):
                continue
            try:
                with open(session_json, "r") as f:
                    data = json.load(f)
                session = SessionData.from_dict(data)
                if session.status not in (SessionStatus.COMPLETED, SessionStatus.CANCELLED):
                    self._sessions[session.session_id] = session
                    logger.info("Active session loaded: %s (%s)", session.session_id, session.status.value)
            except (json.JSONDecodeError, OSError, KeyError) as e:
                logger.warning("Unable to load %s: %s", name, e)
                continue

        logger.info("Active sessions at startup: %s", len(self._sessions))

    @staticmethod
    def _write_session_json(session_dir: str, session: SessionData) -> None:
        """Atomic write of session.json (03_TRANSPORT.md §5.4)."""
        filepath = os.path.join(session_dir, SynapseConfig.SESSION_JSON)
        temp_path = filepath + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            os.rename(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    @staticmethod
    def _write_file(filepath: str, content: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
