"""Tests for reading a session's context state out of a transcript."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.measure import read_session


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

    def test_dropped_is_derived_from_the_pre_post_pair_not_the_field(self):
        """SUPERSEDES `test_dropped_takes_the_latest_cumulative_figure_rather
        _than_summing`, which pinned "latest wins" on the strength of the
        field's NAME and said so: its docstring read "UNVERIFIED: no transcript
        available locally has more than one compaction."

        Measured 2026-08-26 across every transcript in ~/.claude/projects:
        cumulativeDroppedTokens == preTokens - postTokens in 5 of 5, and 0
        transcripts have compacted twice.

        The claim under test is that the answer no longer DEPENDS on which
        reading of "cumulative" is right. Here the fixture uses the cumulative
        reading -- the second field carries the running total -- and the summed
        pairs agree with it. See
        docs/superpowers/specs/2026-08-26-r141-working-tokens-design.md §2.
        """
        path = write_transcript([
            usage(900000),
            compaction(dropped=470000, pre=500000, post=30000),
            usage(700000),
            compaction(dropped=470000 + 560000, pre=600000, post=40000),
            usage(50000),
        ])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).dropped, 470000 + 560000)


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


def boundary(pre, post, cumulative=None, omit_pair=False):
    """A compact_boundary record carrying the preTokens/postTokens pair.

    Shape and arithmetic verified against every compaction in
    ~/.claude/projects on 2026-08-26: cumulativeDroppedTokens == preTokens -
    postTokens in 5 of 5, and no transcript has ever compacted twice — so the
    field's *cumulative* semantics are untested and are not relied on.
    """
    meta = {"cumulativeDroppedTokens": pre - post if cumulative is None
            else cumulative}
    if not omit_pair:
        meta["preTokens"] = pre
        meta["postTokens"] = post
    return {"type": "system", "subtype": "compact_boundary",
            "compactMetadata": meta}


class SessionWorkingTokens(unittest.TestCase):
    """The ruled unit: work accumulated ABOVE the session baseline.

    iladub `docs/superpowers/2026-08-26-context-regime-ruling.md` §3.
    """

    def test_working_is_tokens_above_the_baseline(self):
        path = write_transcript([usage(46_243), usage(96_243)])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).working, 50_000)

    def test_a_fresh_session_has_done_no_work_however_large_the_baseline(self):
        """The whole point of the re-denomination: a 46K baseline against a
        50K floor was 92.5% consumed before a word was typed."""
        path = write_transcript([usage(46_243)])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).working, 0)

    def test_working_never_goes_negative(self):
        """Clamped, matching the converted gauge. Wrong only conservatively."""
        path = write_transcript([usage(40_000), usage(30_000)])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).working, 0)


class SessionWorkingAcrossCompaction(unittest.TestCase):
    """A compaction lowers `tokens` without undoing the reasoning spent, so a
    naive subtraction falsely resets the floor. `working` must be CONTINUOUS
    across the boundary."""

    def test_compaction_does_not_reset_the_working_figure(self):
        # baseline 40k, work climbs to 1,000,000 => working 960,000.
        # Compaction drops to 60,000. Both figures include the baseline, so it
        # cancels: working must still read 960,000, not 20,000.
        path = write_transcript([
            usage(40_000),
            usage(1_000_000),
            boundary(pre=1_000_000, post=60_000),
            usage(60_000),
        ])
        self.addCleanup(os.unlink, path)

        session = read_session(path)
        self.assertTrue(session.compacted)
        self.assertEqual(session.working, 960_000)

    def test_dropped_is_summed_over_boundaries_not_taken_from_the_last(self):
        """No transcript has ever compacted twice, so `cumulative` is untested.
        Summing (preTokens - postTokens) per boundary is correct whether or not
        the field accumulates, which removes the dependency on that premise.

        Here each boundary's field carries only ITS OWN drop -- the reading that
        'latest wins' would silently undercount."""
        path = write_transcript([
            usage(10_000),
            boundary(pre=500_000, post=30_000, cumulative=470_000),
            boundary(pre=600_000, post=40_000, cumulative=560_000),
            usage(40_000),
        ])
        self.addCleanup(os.unlink, path)

        session = read_session(path)
        self.assertEqual(session.dropped, 470_000 + 560_000)
        self.assertEqual(session.working, 40_000 + 1_030_000 - 10_000)

    def test_falls_back_to_the_cumulative_field_when_the_pair_is_absent(self):
        path = write_transcript([
            usage(10_000),
            boundary(pre=500_000, post=30_000, omit_pair=True),
            usage(30_000),
        ])
        self.addCleanup(os.unlink, path)

        self.assertEqual(read_session(path).dropped, 470_000)
