"""Tests for reading a session's context state out of a transcript."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadweight.measure import read_session


def write_transcript(lines):
    """Write JSONL lines to a temp file and return its path."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for obj in lines:
        fh.write(json.dumps(obj) + "\n")
    fh.close()
    return fh.name


def usage(inp, cache_read=0, cache_creation=0):
    """An assistant turn carrying a usage record."""
    return {"type": "assistant",
            "message": {"usage": {"input_tokens": inp,
                                  "cache_read_input_tokens": cache_read,
                                  "cache_creation_input_tokens": cache_creation}}}


class ReadSessionTokens(unittest.TestCase):

    def test_tokens_sum_the_three_input_fields_of_the_last_usage_record(self):
        path = write_transcript([
            usage(10, 20, 30),          # earlier turn, must be ignored
            usage(100, 2000, 300),      # last turn: 2400
        ])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).tokens, 2400)


class ReadSessionBaseline(unittest.TestCase):
    """Baseline is what the window already held before conversation accumulated:
    system prompt, tool definitions, MCP schemas, CLAUDE.md, the skills listing."""

    def test_baseline_is_the_first_usage_record_not_the_last(self):
        path = write_transcript([
            usage(40000, 0, 0),         # first turn: baseline is 40000
            usage(100, 2000, 300),
        ])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).baseline, 40000)


def compaction(dropped, pre=1000577, post=24952, trigger="auto"):
    """A real compact_boundary record, shape verified against live transcripts."""
    return {"type": "system", "subtype": "compact_boundary",
            "content": "Conversation compacted", "level": "info",
            "compactMetadata": {"trigger": trigger, "preTokens": pre,
                                "postTokens": post,
                                "cumulativeDroppedTokens": dropped,
                                "durationMs": 103404}}


class ReadSessionCompaction(unittest.TestCase):
    """Compaction lowers the token count without undoing the damage, so it is
    read from the transcript's own record rather than inferred."""

    def test_a_session_with_no_compaction_reports_none_dropped(self):
        path = write_transcript([usage(100), usage(200)])
        self.addCleanup(os.unlink, path)

        session = read_session(path)
        self.assertFalse(session.compacted)
        self.assertEqual(session.dropped, 0)

    def test_compaction_is_detected_and_dropped_tokens_read_from_the_record(self):
        path = write_transcript([
            usage(1000577),
            compaction(dropped=975625),
            usage(24952),
        ])
        self.addCleanup(os.unlink, path)

        session = read_session(path)
        self.assertTrue(session.compacted)
        self.assertEqual(session.dropped, 975625)

    def test_dropped_takes_the_latest_cumulative_figure_rather_than_summing(self):
        """The field is named cumulativeDroppedTokens, so the last record already
        carries the running total and summing would double-count.

        UNVERIFIED: no transcript available locally has more than one compaction,
        so this follows the field's name rather than an observation. A session
        that compacts twice is the case that would settle it.
        """
        path = write_transcript([
            usage(900000),
            compaction(dropped=800000),
            usage(700000),
            compaction(dropped=1400000),
            usage(50000),
        ])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).dropped, 1400000)


class NeverBreaksTheTurn(unittest.TestCase):
    """Design §8: the tool is never the reason a session fails. Every one of
    these must yield a usable Session rather than raise."""

    def test_missing_transcript_reads_as_an_empty_session(self):
        session = read_session("/nonexistent/path/to/transcript.jsonl")
        self.assertEqual(session.tokens, 0)
        self.assertEqual(session.baseline, 0)

    def test_empty_transcript_reads_as_an_empty_session(self):
        path = write_transcript([])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).tokens, 0)

    def test_malformed_lines_are_skipped_and_valid_ones_still_read(self):
        path = write_transcript([usage(100, 200, 300)])
        with open(path, "a") as fh:
            fh.write('{"message": {"usage": TRUNCATED\n')
            fh.write("not json at all\n")
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).tokens, 600)

    def test_unreadable_transcript_reads_as_an_empty_session(self):
        path = write_transcript([usage(100)])
        os.chmod(path, 0o000)
        self.addCleanup(os.unlink, path)
        self.addCleanup(os.chmod, path, 0o600)

        self.assertEqual(read_session(path).tokens, 0)

    def test_a_directory_where_a_transcript_was_expected_reads_as_empty(self):
        path = tempfile.mkdtemp()
        self.addCleanup(os.rmdir, path)

        self.assertEqual(read_session(path).tokens, 0)


if __name__ == "__main__":
    unittest.main()
