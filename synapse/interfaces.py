# SYNAPSE Protocol — Abstract interfaces
# These protocols define the extension points for integrating SYNAPSE
# with any LLM, notification system, or agent executor.

from typing import Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    """Sends notifications to the supervisor (Telegram, Slack, console, etc.)."""

    def send_message(self, text: str) -> None: ...


@runtime_checkable
class LLMProvider(Protocol):
    """Provides LLM capabilities to the orchestrator for decision-making.

    The orchestrator calls chat() with a prompt describing the current session
    state and Agent B's latest response, and expects a JSON decision back.

    Returns:
        dict with at minimum:
          - "success": bool
          - "response": str (the LLM text output) if success=True
          - "error": str if success=False
    """

    def chat(self, user_message: str, memory_context: str = "",
             temperature: float = 0.3, max_tokens: int = 512) -> dict: ...


@runtime_checkable
class AgentExecutor(Protocol):
    """Executes tasks for an agent (CLI subprocess, API call, etc.).

    Used by the bridge to invoke Agent B's underlying tool.
    """

    def execute(self, message: str, session_context: dict) -> str: ...

    def supports_resume(self) -> bool: ...
