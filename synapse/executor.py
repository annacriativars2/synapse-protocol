# SYNAPSE Agent Executor — Claude Code CLI implementation
# Ref: SYNAPSE_SPEC/03_TRANSPORT.md §4
#
# This module implements the AgentExecutor protocol for the Claude Code CLI.
# It can be replaced with any other executor (API call, different CLI, etc.)
# by implementing the AgentExecutor protocol defined in interfaces.py.

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional

from synapse.config import SynapseConfig as config

logger = logging.getLogger("synapse.executor")


class ClaudeCodeExecutor:
    """AgentExecutor implementation for the Claude Code CLI.

    Manages a persistent CLI session via --resume, handles timeouts in 3 layers,
    and scans for produced files as fallback.
    """

    def __init__(self):
        self._session_id: Optional[str] = None  # CLI session ID for --resume
        self._consecutive_timeouts: int = 0

    @property
    def agent_session_id(self) -> Optional[str]:
        return self._session_id

    @agent_session_id.setter
    def agent_session_id(self, value: Optional[str]) -> None:
        self._session_id = value

    def supports_resume(self) -> bool:
        return True

    def execute(self, message: str, session_context: dict) -> str:
        """Calls the Agent B CLI and returns the response.

        Uses --resume if a CLI session exists,
        otherwise creates a new session with SYNAPSE context.
        (03_TRANSPORT.md §4.5)

        Args:
            message: The message content to send to the CLI.
            session_context: dict with at least "session_id", "status", and other session data.

        Returns:
            The text response from the CLI.
        """
        cmd = [
            config.AGENT_B_BIN,
            "-p", message,
            "--output-format", "json",
            "--allowedTools", "Bash", "Edit", "Write", "Read", "Glob", "Grep",
            "Task", "WebFetch", "WebSearch", "NotebookEdit",
        ]

        # Optional: add extra directories for Agent B to access
        add_dirs = os.getenv("SYNAPSE_AGENT_B_ADD_DIRS", "")
        for d in add_dirs.split(","):
            d = d.strip()
            if d:
                cmd.extend(["--add-dir", d])

        # --resume if we have a session ID (03_TRANSPORT.md §4.5)
        if self._session_id:
            cmd.extend(["--resume", self._session_id])
        else:
            system_prompt = self._build_system_prompt(session_context)
            cmd.extend(["--append-system-prompt", system_prompt])

        logger.info("Calling CLI: resume=%s", self._session_id is not None)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=config.WORKING_DIR,
            )

            try:
                stdout, stderr = proc.communicate(timeout=config.BRIDGE_PROCESS_TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return self._handle_timeout(stdout, session_context)

            if proc.returncode != 0:
                error = stderr.strip() if stderr else "Unknown error"
                logger.error("CLI error (rc=%s): %s", proc.returncode, error)

                # If --resume fails, fallback to new session
                if self._session_id:
                    logger.info("Fallback: new session without --resume")
                    self._session_id = None
                    return self.execute(message, session_context)

                return f"[CLI error: {error}]"

            # Success — reset timeout counter
            self._consecutive_timeouts = 0

            stdout = stdout.strip()
            if not stdout:
                return "[Empty response from CLI]"

            try:
                response_data = json.loads(stdout)
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    self._session_id = new_session_id
                    self._save_session_id(
                        session_context.get("session_id"), new_session_id
                    )
                return response_data.get("result", stdout)

            except json.JSONDecodeError:
                return stdout

        except FileNotFoundError:
            logger.error("CLI not found: %s", config.AGENT_B_BIN)
            return f"[Error: CLI not found ({config.AGENT_B_BIN})]"
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            return f"[Unexpected error: {e}]"

    # --- System prompt ---

    def _build_system_prompt(self, session_data: dict) -> str:
        """Builds the SYNAPSE system prompt (03_TRANSPORT.md §4.4)."""
        session_id = session_data.get("session_id", "unknown")
        session_dir = os.path.join(config.SESSIONS_BASE_DIR, session_id)

        prompt = (
            f"You are in a SYNAPSE collaboration session with {config.AGENT_A_NAME}.\n"
            f"Session: {session_id}\n"
        )

        # Read objective
        objective_path = os.path.join(session_dir, config.OBJECTIVE_FILE)
        if os.path.exists(objective_path):
            with open(objective_path, "r") as f:
                prompt += f"\nObjective:\n{f.read()}\n"

        # Read plan
        plan_path = os.path.join(session_dir, "01_PLAN.md")
        if os.path.exists(plan_path):
            with open(plan_path, "r") as f:
                prompt += f"\nPlan:\n{f.read()}\n"

        # Last journal entries
        journal_path = os.path.join(session_dir, "02_JOURNAL.md")
        if os.path.exists(journal_path):
            with open(journal_path, "r") as f:
                journal = f.read()
            if len(journal) > 2000:
                journal = "...\n" + journal[-2000:]
            prompt += f"\nRecent journal:\n{journal}\n"

        prompt += (
            f"\nCurrent phase: {session_data.get('status', 'UNKNOWN')}\n"
            f"\nYou collaborate with {config.AGENT_A_NAME} as peer engineers."
            f"\nYour responses will be forwarded to {config.AGENT_A_NAME} via Redis."
            f"\n\nIMPORTANT RULE — RESPONSE FORMAT:"
            f"\nYour text response must be SHORT and CONCISE (30 lines max)."
            f"\nLike an agent reporting: summarize what you did, list produced files, flag issues."
            f"\nExample: 'I produced 3 files in docs/: 01_AUDIT.md, 02_PLAN.md, 03_RESULTS.md."
            f" See these files for details.'"
            f"\nIf you need to provide detailed or exhaustive content, write it in a .md file in docs/."
            f"\nNEVER put detailed content in your text response — always in a file."
            f"\n\nIMPORTANT RULE — FILES:"
            f"\nAll documents you generate (analyses, plans, reports, projections)"
            f"\nmust be placed in the session's docs/ directory:"
            f"\n  {session_dir}/docs/"
            f"\nNEVER place documents elsewhere. The supervisor receives these files by email for review."
        )

        return prompt

    # --- Timeout handling (3 layers) ---

    def _handle_timeout(self, partial_stdout: str, session_data: dict) -> str:
        """Intelligent timeout handling in 3 layers."""
        self._consecutive_timeouts += 1
        timeout_s = config.BRIDGE_PROCESS_TIMEOUT
        max_t = config.MAX_CONSECUTIVE_TIMEOUTS
        logger.error("CLI timeout (%ss) -- %s/%s", timeout_s, self._consecutive_timeouts, max_t)

        # Layer 1: partial stdout recovered via Popen?
        if partial_stdout and partial_stdout.strip():
            logger.info("Partial response recovered after timeout")
            try:
                response_data = json.loads(partial_stdout.strip())
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    self._session_id = new_session_id
                    self._save_session_id(
                        session_data.get("session_id"), new_session_id
                    )
                self._consecutive_timeouts = 0
                return response_data.get("result", partial_stdout.strip())
            except json.JSONDecodeError:
                self._consecutive_timeouts = 0
                return partial_stdout.strip()

        # Layer 2: scan produced files
        files_summary = self._scan_session_files(session_data)

        # Layer 3: max consecutive timeouts reached?
        if self._consecutive_timeouts >= max_t:
            logger.warning("Max consecutive timeouts reached (%s)", max_t)
            self._consecutive_timeouts = 0
            msg = f"[STOP — {max_t} consecutive timeouts. Session paused.]"
            if files_summary:
                msg += f"\n{files_summary}"
            return msg

        if files_summary:
            return f"[Timeout but work detected]\n{files_summary}"

        return f"[CLI timeout ({timeout_s}s) — attempt {self._consecutive_timeouts}/{max_t}]"

    @property
    def consecutive_timeouts(self) -> int:
        return self._consecutive_timeouts

    # --- File scanning ---

    @staticmethod
    def _scan_session_files(session_data: dict) -> str:
        """Scans files produced in the session's docs/ directory (Layer 2 anti-timeout)."""
        session_id = session_data.get("session_id", "")
        if not session_id:
            return ""

        docs_dir = os.path.join(config.SESSIONS_BASE_DIR, session_id, "docs")
        if not os.path.isdir(docs_dir):
            return ""

        files = []
        for f in sorted(os.listdir(docs_dir)):
            filepath = os.path.join(docs_dir, f)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append(f"  - {f} ({size:,} bytes)")

        if not files:
            return ""

        return f"Files produced in docs/ ({len(files)}):\n" + "\n".join(files)

    # --- Session ID persistence ---

    @staticmethod
    def _save_session_id(synapse_session_id: str, cli_session_id: str) -> None:
        """Stores the CLI session ID in session.json (03_TRANSPORT.md §4.4)."""
        if not synapse_session_id:
            return
        session_json = os.path.join(
            config.SESSIONS_BASE_DIR, synapse_session_id, config.SESSION_JSON
        )
        if not os.path.exists(session_json):
            return

        try:
            with open(session_json, "r") as f:
                data = json.load(f)
            data["agent_b_session_id"] = cli_session_id
            temp = session_json + ".tmp"
            with open(temp, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.rename(temp, session_json)
            logger.info("CLI session ID saved: %s", cli_session_id)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Unable to save session ID: %s", e)
