#!/usr/bin/env python3
"""
SYNAPSE Agent Bridge — Generic Redis ↔ AgentExecutor bridge
Ref: SYNAPSE_SPEC/03_TRANSPORT.md §4

This service listens on Redis for messages from Agent A and forwards them
to an AgentExecutor, then publishes responses back on Redis.

Architecture:
    Redis (agent_a_to_agent_b) → Bridge → Executor → Bridge → Redis (agent_b_to_agent_a)

Usage:
    python bridge.py
    or via systemd: synapse-bridge.service
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import types
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis

from synapse.config import SynapseConfig as config
from synapse.interfaces import AgentExecutor

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.BRIDGE_LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("synapse.bridge")


class AgentBridge:
    """Generic Redis ↔ AgentExecutor bridge.

    Handles Redis pub/sub, message routing, idempotency, reconnection,
    and delegates actual execution to an injected executor.
    """

    def __init__(self, executor: AgentExecutor):
        """
        Args:
            executor: Any object implementing the AgentExecutor protocol
                      (see interfaces.py). Must have execute(message, session_context) -> str
                      and supports_resume() -> bool.
        """
        self._executor = executor
        self._redis_client: Optional[redis.Redis] = None
        self._running: bool = False
        self._current_session_id: Optional[str] = None
        self._processed_ids: dict[str, float] = {}

    # --- Lifecycle ---

    def start(self) -> None:
        """Main entry point — connect, subscribe, process messages."""
        self._running = True

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("=" * 50)
        logger.info("SYNAPSE Bridge started")
        logger.info("=" * 50)

        if not self._connect_redis():
            sys.exit(1)

        # Look for an active session to resume
        session_data = self._find_active_session()
        if session_data:
            self._current_session_id = session_data.get("session_id")
            logger.info("Active session found: %s", self._current_session_id)

            if self._executor.supports_resume():
                resume_id = (
                    session_data.get("agent_b_session_id")
                    or session_data.get("claude_code_session_id")  # Legacy compat
                )
                if resume_id:
                    self._executor.agent_session_id = resume_id
                    logger.info("Executor session ID: %s (--resume available)", resume_id)
        else:
            logger.info("No active session — waiting")

        # Subscribe and run
        pubsub = self._redis_client.pubsub()
        pubsub.subscribe(config.CHANNEL_A_TO_B, config.CHANNEL_CONTROL)
        logger.info("Subscribed to %s and %s", config.CHANNEL_A_TO_B, config.CHANNEL_CONTROL)

        self._main_loop(pubsub, session_data or {})

        logger.info("SYNAPSE Bridge stopped")
        try:
            pubsub.unsubscribe()
            pubsub.close()
        except Exception:
            pass

    def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False

    # --- Main loop ---

    def _main_loop(self, pubsub: redis.client.PubSub, session_data: dict) -> None:
        """Core message processing loop (03_TRANSPORT.md §4.3)."""
        while self._running:
            try:
                raw = pubsub.get_message(timeout=1.0)
                if raw is None or raw["type"] != "message":
                    continue

                try:
                    message = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Malformed message ignored")
                    continue

                message_id = message.get("id", "")
                if self._is_duplicate(message_id):
                    logger.debug("Duplicate ignored: %s", message_id)
                    continue

                channel = raw["channel"]

                if channel == config.CHANNEL_CONTROL:
                    self._handle_control(message)
                    continue

                # Message from Agent A → execute
                session_id = message.get("session_id", "")
                content = message.get("content", "")
                msg_type = message.get("type", "dialogue")

                if not content:
                    continue

                logger.info("Message from %s [%s]: %s...", config.AGENT_A_NAME, msg_type, content[:100])

                # Reload session if needed
                if session_id != self._current_session_id:
                    session_data = self._find_active_session()
                    self._current_session_id = session_id
                    if self._executor.supports_resume():
                        resume_id = (
                            session_data.get("agent_b_session_id")
                            or session_data.get("claude_code_session_id")
                        )
                        if resume_id:
                            self._executor.agent_session_id = resume_id

                if not session_data:
                    session_data = {"session_id": session_id, "status": "UNKNOWN"}

                # Execute via the injected executor
                response = self._executor.execute(content, session_data)

                # Determine response type
                response_type = "dialogue"
                if msg_type == "approval_request":
                    response_type = "decision"

                self._publish_to_agent_a(session_id, response_type, response)

                # Notify supervisor on max consecutive timeouts
                if hasattr(self._executor, 'consecutive_timeouts'):
                    if self._executor.consecutive_timeouts >= config.MAX_CONSECUTIVE_TIMEOUTS:
                        self._notify_supervisor(
                            session_id,
                            f"SYNAPSE: {config.MAX_CONSECUTIVE_TIMEOUTS} consecutive timeouts."
                        )

            except redis.ConnectionError:
                logger.error("Redis disconnected, reconnecting...")
                if not self._connect_redis():
                    break
                pubsub = self._redis_client.pubsub()
                pubsub.subscribe(config.CHANNEL_A_TO_B, config.CHANNEL_CONTROL)

            except Exception as e:
                logger.error("Main loop error: %s", e, exc_info=True)
                time.sleep(1)

    # --- Redis ---

    def _connect_redis(self) -> bool:
        """Connect to Redis with retry."""
        while self._running:
            try:
                self._redis_client = redis.Redis(
                    host=config.REDIS_HOST,
                    port=config.REDIS_PORT,
                    decode_responses=True,
                )
                self._redis_client.ping()
                logger.info("Redis connected")
                return True
            except redis.ConnectionError:
                logger.error("Redis unavailable, retry in %ss...", config.REDIS_RECONNECT_DELAY)
                time.sleep(config.REDIS_RECONNECT_DELAY)
        return False

    def _publish_to_agent_a(self, session_id: str, msg_type: str, content: str,
                            metadata: Optional[dict] = None) -> None:
        """Publishes a response back to Agent A."""
        message = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender": config.AGENT_B_ID,
            "type": msg_type,
            "content": content,
            "metadata": metadata or {},
        }
        try:
            self._redis_client.publish(
                config.CHANNEL_B_TO_A, json.dumps(message, ensure_ascii=False)
            )
            logger.info("Response published [%s]: %s...", msg_type, content[:100])
        except redis.ConnectionError:
            logger.error("Redis down, cannot publish response")
            self._fallback_write(message)

    def _notify_supervisor(self, session_id: str, content: str) -> None:
        """Sends a notification to the supervisor channel."""
        message = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender": "synapse",
            "type": "notification",
            "content": content,
        }
        try:
            self._redis_client.publish(
                config.CHANNEL_SUPERVISOR, json.dumps(message, ensure_ascii=False)
            )
        except redis.ConnectionError:
            logger.error("Redis down for supervisor notification")

    @staticmethod
    def _fallback_write(message: dict) -> None:
        """Atomic file write fallback (03_TRANSPORT.md §5.3)."""
        temp_file = config.FALLBACK_FILE + ".tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(message, f, ensure_ascii=False)
            os.rename(temp_file, config.FALLBACK_FILE)
        except OSError as e:
            logger.error("Fallback write failed: %s", e)

    # --- Session discovery ---

    @staticmethod
    def _find_active_session() -> dict:
        """Finds the most recent active SYNAPSE session on disk."""
        base = config.SESSIONS_BASE_DIR
        if not os.path.isdir(base):
            return {}
        for name in sorted(os.listdir(base), reverse=True):
            if not name.startswith("SYNAPSE_SESSION"):
                continue
            session_json = os.path.join(base, name, config.SESSION_JSON)
            if not os.path.exists(session_json):
                continue
            try:
                with open(session_json, "r") as f:
                    data = json.load(f)
                if data.get("status") not in ("COMPLETED", "CANCELLED"):
                    return data
            except (json.JSONDecodeError, OSError):
                continue
        return {}

    # --- Idempotency (03_TRANSPORT.md §5.1) ---

    def _is_duplicate(self, message_id: str) -> bool:
        now = time.time()
        to_remove = [
            mid for mid, ts in self._processed_ids.items()
            if now - ts > config.IDEMPOTENCY_TTL
        ]
        for mid in to_remove:
            del self._processed_ids[mid]
        if message_id in self._processed_ids:
            return True
        self._processed_ids[message_id] = now
        return False

    # --- Control commands ---

    def _handle_control(self, message: dict) -> None:
        """Handles supervisor control commands."""
        command = message.get("content", "").strip().lower()
        logger.info("Control command: %s", command)

        if command == "cancel":
            self._current_session_id = None
            if self._executor.supports_resume():
                self._executor.agent_session_id = None
            logger.info("Session cancelled by supervisor")

    # --- Signal ---

    def _signal_handler(self, signum: int, frame: Optional[types.FrameType]) -> None:
        logger.info("Signal %s received, stopping bridge...", signum)
        self._running = False


# --- Entry point ---

def main() -> None:
    """Default entry point: AgentBridge + ClaudeCodeExecutor."""
    from synapse.executor import ClaudeCodeExecutor

    executor = ClaudeCodeExecutor()
    bridge = AgentBridge(executor)
    bridge.start()


if __name__ == "__main__":
    main()
