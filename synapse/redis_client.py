# SYNAPSE Redis Client
# Ref: SYNAPSE_SPEC/03_TRANSPORT.md §1-3, §5

from __future__ import annotations

import json
import os
import time
import logging
import threading
from typing import Callable, Optional

import redis

from synapse.config import SynapseConfig
from synapse.messages import SynapseMessage

logger = logging.getLogger("synapse.redis")


class SynapseRedisClient:
    """Client Redis pub/sub for SYNAPSE — Agent A side."""

    def __init__(self):
        self._redis = redis.Redis(
            host=SynapseConfig.REDIS_HOST,
            port=SynapseConfig.REDIS_PORT,
            decode_responses=True,
        )
        self._pubsub: Optional[redis.client.PubSub] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False
        # Idempotency (03_TRANSPORT.md §5.1)
        self._processed_ids: dict[str, float] = {}

    # --- Publishing ---

    def publish_to_agent_b(self, message: SynapseMessage) -> str:
        """Publishes a message from Agent A to Agent B (03_TRANSPORT.md §3.1)."""
        return self._publish(SynapseConfig.CHANNEL_A_TO_B, message)

    def publish_to_agent_a(self, message: SynapseMessage) -> str:
        """Publishes a message from Agent B to Agent A (used by bridge)."""
        return self._publish(SynapseConfig.CHANNEL_B_TO_A, message)

    def notify_supervisor(self, session_id: str, notification_type: str, content: str) -> str:
        """Sends a notification to the supervisor (03_TRANSPORT.md §3.3)."""
        msg = SynapseMessage(
            session_id=session_id,
            sender="synapse",
            type=notification_type,
            content=content,
        )
        return self._publish(SynapseConfig.CHANNEL_SUPERVISOR, msg)

    def publish_control(self, command: str, session_id: str, data: Optional[dict] = None) -> str:
        """Publishes a supervisor control command."""
        msg = SynapseMessage(
            session_id=session_id,
            sender=SynapseConfig.SUPERVISOR_ID,
            type="control",
            content=command,
            metadata=data or {},
        )
        return self._publish(SynapseConfig.CHANNEL_CONTROL, msg)

    def _publish(self, channel: str, message: SynapseMessage) -> str:
        """Publishes with file fallback (03_TRANSPORT.md §5.3)."""
        payload = message.to_json()
        try:
            self._redis.publish(channel, payload)
            logger.info("Published to %s: %s", channel, message.id)
            return message.id
        except redis.ConnectionError:
            logger.error("Redis down, file fallback for %s", message.id)
            self._fallback_write(payload)
            return message.id

    def _fallback_write(self, payload: str) -> None:
        """Atomic file write fallback (03_TRANSPORT.md §5.3)."""
        temp_file = SynapseConfig.FALLBACK_FILE + ".tmp"
        try:
            with open(temp_file, "w") as f:
                f.write(payload)
            os.rename(temp_file, SynapseConfig.FALLBACK_FILE)
        except OSError as e:
            logger.error("Fallback write failed: %s", e)

    # --- Subscription ---

    def subscribe(self, channels: list[str], callback: Callable[[str, SynapseMessage], None]) -> None:
        """Subscribes to one or more channels with callback (03_TRANSPORT.md §3.2).

        The callback receives (channel_name, SynapseMessage).
        """
        self._pubsub = self._redis.pubsub()
        self._pubsub.subscribe(*channels)
        self._running = True

        def _listen():
            while self._running:
                try:
                    raw = self._pubsub.get_message(timeout=1.0)
                    if raw is None or not self._running:
                        continue
                    if raw["type"] != "message":
                        continue
                    try:
                        message = SynapseMessage.from_json(raw["data"])
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.warning("Malformed message ignored: %s", e)
                        continue

                    # Idempotency check
                    if self._is_duplicate(message.id):
                        logger.debug("Duplicate ignored: %s", message.id)
                        continue

                    callback(raw["channel"], message)
                except redis.ConnectionError:
                    logger.error("Redis disconnected, reconnecting...")
                    time.sleep(SynapseConfig.REDIS_RECONNECT_DELAY)
                    try:
                        self._pubsub = self._redis.pubsub()
                        self._pubsub.subscribe(*channels)
                    except redis.ConnectionError:
                        pass
                except Exception as e:
                    logger.error("Listener error: %s", e)
                    time.sleep(1)

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()
        logger.info("Subscribed to %s", channels)

    def stop(self) -> None:
        """Stops the listener."""
        self._running = False
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception as e:
                logger.warning("Error closing pubsub: %s", e)
            finally:
                self._pubsub = None

    # --- Idempotency (03_TRANSPORT.md §5.1) ---

    _CLEANUP_THRESHOLD = 1000

    def _is_duplicate(self, message_id: str) -> bool:
        now = time.time()
        # Cleanup only when dict exceeds threshold
        if len(self._processed_ids) > self._CLEANUP_THRESHOLD:
            self._processed_ids = {
                mid: ts for mid, ts in self._processed_ids.items()
                if now - ts < SynapseConfig.IDEMPOTENCY_TTL
            }
        if message_id in self._processed_ids:
            return True
        self._processed_ids[message_id] = now
        return False

    # --- Health Check (03_TRANSPORT.md §7.1) ---

    def health(self) -> dict:
        """Checks the health of SYNAPSE infrastructure."""
        result = {
            "redis_connected": False,
            "agent_a_subscribed": False,
            "agent_b_subscribed": False,
            "active_session": None,
        }
        try:
            self._redis.ping()
            result["redis_connected"] = True
        except redis.ConnectionError:
            return result

        try:
            channels = self._redis.pubsub_numsub(
                SynapseConfig.CHANNEL_A_TO_B,
                SynapseConfig.CHANNEL_B_TO_A,
            )
            result["agent_b_subscribed"] = channels.get(SynapseConfig.CHANNEL_A_TO_B, 0) > 0
            result["agent_a_subscribed"] = channels.get(SynapseConfig.CHANNEL_B_TO_A, 0) > 0
        except Exception:
            pass

        return result
