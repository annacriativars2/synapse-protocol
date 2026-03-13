# SYNAPSE Journal
# Ref: SYNAPSE_SPEC/02_PROTOCOLE.md §2.4, 03_TRANSPORT.md §5.5

import os
import logging
from datetime import datetime, timezone

import filelock

from synapse.config import SynapseConfig

logger = logging.getLogger("synapse.journal")


def append_to_journal(session_dir: str, entry: str) -> None:
    """Appends an entry to the journal with file locking (03_TRANSPORT.md §5.5).

    The journal is append-only — previous entries are never modified.
    It serves as the black box of the collaboration.
    """
    journal_path = os.path.join(session_dir, SynapseConfig.JOURNAL_FILE)
    lock = filelock.FileLock(SynapseConfig.JOURNAL_LOCK_PATH)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    formatted_entry = f"\n## {now} — {entry}\n"

    try:
        with lock:
            with open(journal_path, "a", encoding="utf-8") as f:
                f.write(formatted_entry)
        logger.debug("Journal entry added: %s...", entry[:80])
    except OSError as e:
        logger.error("Journal write failed: %s", e)
        raise


def append_raw(session_dir: str, raw_text: str) -> None:
    """Appends raw text to the journal (for details under an entry)."""
    journal_path = os.path.join(session_dir, SynapseConfig.JOURNAL_FILE)
    lock = filelock.FileLock(SynapseConfig.JOURNAL_LOCK_PATH)

    try:
        with lock:
            with open(journal_path, "a", encoding="utf-8") as f:
                f.write(raw_text + "\n")
    except OSError as e:
        logger.error("Journal raw write failed: %s", e)


def read_last_entries(session_dir: str, count: int = 5) -> str:
    """Reads the last N journal entries."""
    journal_path = os.path.join(session_dir, SynapseConfig.JOURNAL_FILE)
    if not os.path.exists(journal_path):
        return ""

    with open(journal_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by "## " headers
    sections = content.split("\n## ")
    if len(sections) <= count:
        return content

    result = "\n## ".join(sections[-count:])
    return f"## {result}"
