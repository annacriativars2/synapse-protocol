# SYNAPSE Supervisor Listener
# Ref: SYNAPSE_SPEC/04_SUPERVISION.md §3
#
# Listens on the Redis supervisor channel and forwards
# notifications to the supervisor via the configured notifier.

from __future__ import annotations

import json
import logging
import threading
import time
from typing import TYPE_CHECKING, Optional

import redis

from synapse.config import SynapseConfig

if TYPE_CHECKING:
    from synapse.interfaces import Notifier

logger = logging.getLogger("synapse.supervisor_listener")


class SupervisorListener:
    """Listens on the supervisor Redis channel and forwards to the notifier."""

    def __init__(self, notifier: Notifier):
        """
        Args:
            notifier: Notifier instance with a send_message(text) method
        """
        self._notifier = notifier
        self._redis: redis.Redis = redis.Redis(
            host=SynapseConfig.REDIS_HOST,
            port=SynapseConfig.REDIS_PORT,
            decode_responses=True,
        )
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the listener in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("Supervisor listener started — supervisor channel → notifier")

    def stop(self) -> None:
        self._running = False

    def _listen(self) -> None:
        pubsub: Optional[redis.client.PubSub] = None
        while self._running:
            try:
                if pubsub is None:
                    pubsub = self._redis.pubsub()
                    pubsub.subscribe(SynapseConfig.CHANNEL_SUPERVISOR)

                for raw in pubsub.listen():
                    if not self._running:
                        break
                    if raw["type"] != "message":
                        continue

                    try:
                        message = json.loads(raw["data"])
                        content = message.get("content", "")
                        if content:
                            self._send_notification(content)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning("Malformed supervisor message: %s", e)

            except redis.ConnectionError:
                logger.error("Redis disconnected for supervisor listener, retrying...")
                pubsub = None
                time.sleep(SynapseConfig.REDIS_RECONNECT_DELAY)
            except Exception as e:
                logger.error("Supervisor listener error: %s", e)
                time.sleep(1)

    def _send_notification(self, content: str) -> None:
        """Sends content to the supervisor via the notifier."""
        try:
            self._notifier.send_message(content)
            logger.info("Supervisor notification sent: %s...", content[:80])
        except Exception as e:
            logger.error("Error sending notification: %s", e)
