# SYNAPSE Configuration — Unified (Orchestrator + Bridge)

import os
from typing import Any, Dict


class SynapseConfig:
    """Centralized SYNAPSE configuration for all components."""

    # --- Redis ---
    REDIS_HOST = os.getenv("SYNAPSE_REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("SYNAPSE_REDIS_PORT", "6379"))
    REDIS_RECONNECT_DELAY = 5

    # --- Participants (configurable IDs and display names) ---
    AGENT_A_ID = os.getenv("SYNAPSE_AGENT_A_ID", "agent_a")
    AGENT_A_NAME = os.getenv("SYNAPSE_AGENT_A_NAME", "Agent A")
    AGENT_B_ID = os.getenv("SYNAPSE_AGENT_B_ID", "agent_b")
    AGENT_B_NAME = os.getenv("SYNAPSE_AGENT_B_NAME", "Agent B")
    SUPERVISOR_ID = os.getenv("SYNAPSE_SUPERVISOR_ID", "supervisor")
    SUPERVISOR_NAME = os.getenv("SYNAPSE_SUPERVISOR_NAME", "Supervisor")

    # Redis channels
    CHANNEL_A_TO_B = os.getenv("SYNAPSE_CHANNEL_A_TO_B", "synapse:agent_a_to_agent_b")
    CHANNEL_B_TO_A = os.getenv("SYNAPSE_CHANNEL_B_TO_A", "synapse:agent_b_to_agent_a")
    CHANNEL_SUPERVISOR = os.getenv("SYNAPSE_CHANNEL_SUPERVISOR", "synapse:supervisor")
    CHANNEL_CONTROL = "synapse:control"

    # --- Sessions ---
    SESSIONS_BASE_DIR = os.getenv("SYNAPSE_SESSIONS_DIR", "./synapse_sessions")
    SESSION_PREFIX = "SYNAPSE_SESSION"
    MAX_CONCURRENT_SESSIONS = int(os.getenv("SYNAPSE_MAX_SESSIONS", "3"))

    # Session files
    SESSION_JSON = "session.json"
    OBJECTIVE_FILE = "00_OBJECTIVE.md"
    OBJECTIF_FILE = OBJECTIVE_FILE  # Backward-compatible alias
    PLAN_FILE = "01_PLAN.md"
    JOURNAL_FILE = "02_JOURNAL.md"
    RESULTS_FILE = "03_RESULTS.md"
    RESULTATS_FILE = RESULTS_FILE  # Backward-compatible alias

    # --- Timeouts ---
    AGENT_RESPONSE_TIMEOUT = int(os.getenv("SYNAPSE_RESPONSE_TIMEOUT", "60"))
    AGENT_RETRY_MAX = 1

    # --- Messages ---
    MAX_MESSAGE_SIZE = 512 * 1024   # 512 KB
    IDEMPOTENCY_TTL = 86400         # 24h

    # --- Agent B CLI / Bridge ---
    WORKING_DIR = os.getenv("SYNAPSE_WORKING_DIR", ".")
    AGENT_B_BIN = os.getenv("SYNAPSE_AGENT_B_BIN", "claude")
    BRIDGE_PROCESS_TIMEOUT = int(os.getenv("SYNAPSE_BRIDGE_TIMEOUT", "1800"))
    MAX_CONSECUTIVE_TIMEOUTS = 3

    # --- File locks & fallback ---
    JOURNAL_LOCK_PATH = os.getenv("SYNAPSE_JOURNAL_LOCK", "./.synapse_journal.lock")
    FALLBACK_FILE = os.getenv("SYNAPSE_FALLBACK_FILE", "./.synapse_fallback.json")

    # --- Archives ---
    ARCHIVES_DIR = os.getenv("SYNAPSE_ARCHIVES_DIR", "./synapse_archives")

    # --- Notifications ---
    CHECKPOINT_INTERVAL_HOURS = 2

    # --- Bridge logging ---
    BRIDGE_LOG_FILE = os.getenv("SYNAPSE_BRIDGE_LOG", "./synapse_bridge.log")

    # --- YAML key → class attribute mapping ---
    _YAML_MAP: Dict[str, str] = {
        # redis
        "redis.host": "REDIS_HOST",
        "redis.port": "REDIS_PORT",
        # participants
        "participants.agent_a.id": "AGENT_A_ID",
        "participants.agent_a.name": "AGENT_A_NAME",
        "participants.agent_b.id": "AGENT_B_ID",
        "participants.agent_b.name": "AGENT_B_NAME",
        "participants.supervisor.id": "SUPERVISOR_ID",
        "participants.supervisor.name": "SUPERVISOR_NAME",
        # channels
        "channels.a_to_b": "CHANNEL_A_TO_B",
        "channels.b_to_a": "CHANNEL_B_TO_A",
        "channels.supervisor": "CHANNEL_SUPERVISOR",
        "channels.control": "CHANNEL_CONTROL",
        # sessions
        "sessions.base_dir": "SESSIONS_BASE_DIR",
        "sessions.prefix": "SESSION_PREFIX",
        "sessions.max_concurrent": "MAX_CONCURRENT_SESSIONS",
        "sessions.archives_dir": "ARCHIVES_DIR",
        # session_files
        "session_files.session_json": "SESSION_JSON",
        "session_files.objective": "OBJECTIVE_FILE",
        "session_files.plan": "PLAN_FILE",
        "session_files.journal": "JOURNAL_FILE",
        "session_files.results": "RESULTS_FILE",
        # timeouts
        "timeouts.agent_response": "AGENT_RESPONSE_TIMEOUT",
        "timeouts.agent_retry_max": "AGENT_RETRY_MAX",
        "timeouts.redis_reconnect_delay": "REDIS_RECONNECT_DELAY",
        "timeouts.bridge_process": "BRIDGE_PROCESS_TIMEOUT",
        "timeouts.max_consecutive_timeouts": "MAX_CONSECUTIVE_TIMEOUTS",
        # messages
        "messages.max_size": "MAX_MESSAGE_SIZE",
        "messages.idempotency_ttl": "IDEMPOTENCY_TTL",
        # notifications
        "notifications.checkpoint_interval_hours": "CHECKPOINT_INTERVAL_HOURS",
        # bridge
        "bridge.working_dir": "WORKING_DIR",
        "bridge.agent_b_bin": "AGENT_B_BIN",
        "bridge.log_file": "BRIDGE_LOG_FILE",
        # files
        "files.journal_lock": "JOURNAL_LOCK_PATH",
        "files.fallback": "FALLBACK_FILE",
    }

    @classmethod
    def _flatten_yaml(cls, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested YAML dict into dotted keys. e.g. {'redis': {'host': 'x'}} → {'redis.host': 'x'}"""
        flat: Dict[str, Any] = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(cls._flatten_yaml(value, full_key))
            else:
                flat[full_key] = value
        return flat

    @classmethod
    def from_yaml(cls, path: str) -> "SynapseConfig":
        """Load configuration from a YAML file. Requires pyyaml.

        Reads the YAML file, flattens nested keys (e.g. redis.host),
        maps them to class attributes via _YAML_MAP, and overrides
        the class-level defaults. Returns the class itself since
        SynapseConfig uses class attributes, not instance attributes.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            The SynapseConfig class with overridden attributes.

        Raises:
            ImportError: If pyyaml is not installed.
            FileNotFoundError: If the YAML file does not exist.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "pyyaml required for YAML config support: "
                "pip install pyyaml  (or: pip install synapse-protocol[yaml])"
            )

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw or not isinstance(raw, dict):
            return cls

        flat = cls._flatten_yaml(raw)

        for yaml_key, value in flat.items():
            attr_name = cls._YAML_MAP.get(yaml_key)
            if attr_name is not None:
                # Coerce type to match the existing attribute's type
                current = getattr(cls, attr_name, None)
                if current is not None and isinstance(current, int) and not isinstance(value, int):
                    value = int(value)
                setattr(cls, attr_name, value)

        # Keep backward-compatible aliases in sync
        cls.OBJECTIF_FILE = cls.OBJECTIVE_FILE
        cls.RESULTATS_FILE = cls.RESULTS_FILE

        return cls

    @classmethod
    def from_env(cls) -> "SynapseConfig":
        """Create config from environment variables (explicit method).

        Re-reads all os.getenv() calls to refresh class attributes
        from the current environment. This is the same behavior as
        the default class-level initialization, made explicit.

        Returns:
            The SynapseConfig class with refreshed attributes.
        """
        # Redis
        cls.REDIS_HOST = os.getenv("SYNAPSE_REDIS_HOST", "localhost")
        cls.REDIS_PORT = int(os.getenv("SYNAPSE_REDIS_PORT", "6379"))

        # Participants
        cls.AGENT_A_ID = os.getenv("SYNAPSE_AGENT_A_ID", "agent_a")
        cls.AGENT_A_NAME = os.getenv("SYNAPSE_AGENT_A_NAME", "Agent A")
        cls.AGENT_B_ID = os.getenv("SYNAPSE_AGENT_B_ID", "agent_b")
        cls.AGENT_B_NAME = os.getenv("SYNAPSE_AGENT_B_NAME", "Agent B")
        cls.SUPERVISOR_ID = os.getenv("SYNAPSE_SUPERVISOR_ID", "supervisor")
        cls.SUPERVISOR_NAME = os.getenv("SYNAPSE_SUPERVISOR_NAME", "Supervisor")

        # Channels
        cls.CHANNEL_A_TO_B = os.getenv("SYNAPSE_CHANNEL_A_TO_B", "synapse:agent_a_to_agent_b")
        cls.CHANNEL_B_TO_A = os.getenv("SYNAPSE_CHANNEL_B_TO_A", "synapse:agent_b_to_agent_a")
        cls.CHANNEL_SUPERVISOR = os.getenv("SYNAPSE_CHANNEL_SUPERVISOR", "synapse:supervisor")
        cls.CHANNEL_CONTROL = "synapse:control"

        # Sessions
        cls.SESSIONS_BASE_DIR = os.getenv("SYNAPSE_SESSIONS_DIR", "./synapse_sessions")
        cls.SESSION_PREFIX = "SYNAPSE_SESSION"
        cls.MAX_CONCURRENT_SESSIONS = int(os.getenv("SYNAPSE_MAX_SESSIONS", "3"))

        # Session files
        cls.SESSION_JSON = "session.json"
        cls.OBJECTIVE_FILE = "00_OBJECTIVE.md"
        cls.OBJECTIF_FILE = cls.OBJECTIVE_FILE
        cls.PLAN_FILE = "01_PLAN.md"
        cls.JOURNAL_FILE = "02_JOURNAL.md"
        cls.RESULTS_FILE = "03_RESULTS.md"
        cls.RESULTATS_FILE = cls.RESULTS_FILE

        # Timeouts
        cls.AGENT_RESPONSE_TIMEOUT = int(os.getenv("SYNAPSE_RESPONSE_TIMEOUT", "60"))
        cls.AGENT_RETRY_MAX = 1
        cls.REDIS_RECONNECT_DELAY = 5

        # Messages
        cls.MAX_MESSAGE_SIZE = 512 * 1024
        cls.IDEMPOTENCY_TTL = 86400

        # Bridge
        cls.WORKING_DIR = os.getenv("SYNAPSE_WORKING_DIR", ".")
        cls.AGENT_B_BIN = os.getenv("SYNAPSE_AGENT_B_BIN", "claude")
        cls.BRIDGE_PROCESS_TIMEOUT = int(os.getenv("SYNAPSE_BRIDGE_TIMEOUT", "1800"))
        cls.MAX_CONSECUTIVE_TIMEOUTS = 3

        # Files
        cls.JOURNAL_LOCK_PATH = os.getenv("SYNAPSE_JOURNAL_LOCK", "./.synapse_journal.lock")
        cls.FALLBACK_FILE = os.getenv("SYNAPSE_FALLBACK_FILE", "./.synapse_fallback.json")

        # Archives
        cls.ARCHIVES_DIR = os.getenv("SYNAPSE_ARCHIVES_DIR", "./synapse_archives")

        # Notifications
        cls.CHECKPOINT_INTERVAL_HOURS = 2

        # Bridge logging
        cls.BRIDGE_LOG_FILE = os.getenv("SYNAPSE_BRIDGE_LOG", "./synapse_bridge.log")

        return cls
