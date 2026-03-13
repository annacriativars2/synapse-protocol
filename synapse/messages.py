# SYNAPSE Messages
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md §3, 03_TRANSPORT.md §2

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Union


class MessageType(str, Enum):
    """SYNAPSE message types (02_PROTOCOLE.md §3.2)."""
    DIALOGUE = "dialogue"
    PROPOSAL = "proposal"
    DECISION = "decision"
    ACTION = "action"
    CHECKPOINT = "checkpoint"
    APPROVAL_REQUEST = "approval_request"
    DISAGREEMENT = "disagreement"
    RESUME = "resume"
    DELIVERY = "delivery"


class SessionStatus(str, Enum):
    """SYNAPSE session states (02_PROTOCOLE.md §1.2)."""
    CREATED = "CREATED"
    CONCEPTUALIZING = "CONCEPTUALIZING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    IMPLEMENTING = "IMPLEMENTING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Allowed transitions (02_PROTOCOLE.md §1.3)
VALID_TRANSITIONS = {
    SessionStatus.CREATED: [SessionStatus.CONCEPTUALIZING],
    SessionStatus.CONCEPTUALIZING: [SessionStatus.AWAITING_APPROVAL, SessionStatus.PAUSED],
    SessionStatus.AWAITING_APPROVAL: [SessionStatus.REVIEWING, SessionStatus.CONCEPTUALIZING],
    SessionStatus.REVIEWING: [SessionStatus.CONCEPTUALIZING, SessionStatus.APPROVED, SessionStatus.CANCELLED],
    SessionStatus.APPROVED: [SessionStatus.IMPLEMENTING],
    SessionStatus.IMPLEMENTING: [SessionStatus.PAUSED, SessionStatus.COMPLETED, SessionStatus.AWAITING_APPROVAL],
    SessionStatus.PAUSED: [SessionStatus.IMPLEMENTING, SessionStatus.CONCEPTUALIZING],
}
# CANCELLED is reachable from any state (except COMPLETED and CANCELLED)


@dataclass
class SynapseMessage:
    """Message exchanged between agents via Redis."""

    session_id: str
    sender: str                     # agent ID (e.g. "agent_a", "agent_b", "supervisor")
    type: Union[MessageType, str]
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serializes for Redis publication."""
        data = asdict(self)
        data["type"] = self.type.value if isinstance(self.type, MessageType) else self.type
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "SynapseMessage":
        """Deserializes from a Redis message."""
        data = json.loads(raw)
        try:
            data["type"] = MessageType(data["type"])
        except ValueError:
            pass  # Keep as string for notification/control types
        return cls(**data)

    def validate(self) -> bool:
        """Validates required fields (02_PROTOCOLE.md §3.3)."""
        if not all([self.id, self.session_id, self.timestamp, self.sender, self.type, self.content]):
            return False
        if not self.sender:
            return False
        if self.type == MessageType.APPROVAL_REQUEST and "approval_reason" not in self.metadata:
            return False
        return True


@dataclass
class SessionData:
    """Session metadata stored in session.json (02_PROTOCOLE.md §2.2)."""

    session_id: str
    created_at: str
    created_by: str                 # agent or supervisor ID
    status: SessionStatus
    objective: str
    working_directory: str = "."
    agent_b_session_id: Optional[str] = None
    shared_context: list = field(default_factory=list)
    approved_at: Optional[str] = None
    approved_scope: list = field(default_factory=list)
    contract: str = ""                  # Authorized scope in CONCEPTUALIZING
    execution_contract: str = ""        # Authorized scope in IMPLEMENTING (set at approval)
    messages_count: int = 0
    last_activity: Optional[str] = None
    checkpoints: list = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        data["status"] = SessionStatus(data["status"])
        # Backward compatibility: fields added after V1
        data.setdefault("contract", "")
        data.setdefault("execution_contract", "")
        return cls(**data)
