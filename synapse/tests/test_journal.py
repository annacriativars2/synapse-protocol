# SYNAPSE Tests — Journal
# Validates append-only journal writes and reads.

import os

import pytest

from synapse.config import SynapseConfig
from synapse.journal import append_to_journal, read_last_entries


@pytest.fixture
def journal_dir(tmp_path, config_override):
    """Creates a session directory with an empty journal file."""
    session_dir = tmp_path / "session_journal_test"
    session_dir.mkdir()
    journal_path = session_dir / SynapseConfig.JOURNAL_FILE
    journal_path.write_text("# Session Journal\n", encoding="utf-8")
    return str(session_dir)


@pytest.fixture
def empty_journal_dir(tmp_path, config_override):
    """Creates a session directory without any journal file."""
    session_dir = tmp_path / "session_no_journal"
    session_dir.mkdir()
    return str(session_dir)


class TestAppendToJournal:

    def test_append_writes_entry_to_file(self, journal_dir):
        append_to_journal(journal_dir, "First entry")

        journal_path = os.path.join(journal_dir, SynapseConfig.JOURNAL_FILE)
        content = open(journal_path).read()
        assert "First entry" in content

    def test_append_multiple_entries_are_ordered(self, journal_dir):
        append_to_journal(journal_dir, "Entry A")
        append_to_journal(journal_dir, "Entry B")
        append_to_journal(journal_dir, "Entry C")

        journal_path = os.path.join(journal_dir, SynapseConfig.JOURNAL_FILE)
        content = open(journal_path).read()
        pos_a = content.index("Entry A")
        pos_b = content.index("Entry B")
        pos_c = content.index("Entry C")
        assert pos_a < pos_b < pos_c

    def test_append_adds_timestamp_header(self, journal_dir):
        """Each entry should be prefixed with a ## timestamp header."""
        append_to_journal(journal_dir, "Timestamped entry")

        journal_path = os.path.join(journal_dir, SynapseConfig.JOURNAL_FILE)
        content = open(journal_path).read()
        # The format is "## YYYY-MM-DD HH:MM — entry"
        assert "## " in content
        assert "Timestamped entry" in content

    def test_append_to_nonexistent_journal_creates_file(self, empty_journal_dir):
        """Appending to a directory without a journal should create the file."""
        append_to_journal(empty_journal_dir, "Brand new entry")

        journal_path = os.path.join(empty_journal_dir, SynapseConfig.JOURNAL_FILE)
        assert os.path.isfile(journal_path)
        content = open(journal_path).read()
        assert "Brand new entry" in content


class TestReadLastEntries:

    def test_read_last_entries_returns_correct_count(self, journal_dir):
        for i in range(10):
            append_to_journal(journal_dir, f"Entry {i}")

        result = read_last_entries(journal_dir, count=3)
        # Should contain the last 3 entries
        assert "Entry 9" in result
        assert "Entry 8" in result
        assert "Entry 7" in result
        # Should NOT contain early entries
        assert "Entry 0" not in result

    def test_read_last_entries_with_fewer_than_count(self, journal_dir):
        append_to_journal(journal_dir, "Only entry")

        result = read_last_entries(journal_dir, count=5)
        assert "Only entry" in result

    def test_read_last_entries_empty_journal(self, journal_dir):
        """Reading from a journal with only the header should return something."""
        result = read_last_entries(journal_dir, count=5)
        assert isinstance(result, str)

    def test_read_last_entries_no_journal_file(self, empty_journal_dir):
        """Reading from a directory without a journal file should return empty string."""
        result = read_last_entries(empty_journal_dir, count=5)
        assert result == ""
