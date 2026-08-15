"""Tests for the pre-flight logging command.

Design §7: the pre-flight record carries ts, session, declared shape, tokens,
floor and decision — **including overridden**. Logging the override is the
entire point of the record: "a gate whose circumvention nobody can measure is
a gate that will be circumvented", and the override rate is the honest measure
of whether the tiers are usable at all. At 90% the tiers are wrong, not the user.

The load-bearing behaviour here is that the command does not take the caller's
word for it. A session that declares `proceed` while over the floor has
overridden the gate, whatever it chose to call the decision.
"""

import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.corpus import append
from plimslop.preflight import main


class PreflightTestCase(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")

    def run_preflight(self, *argv, cwd="/p"):
        out = io.StringIO()
        code = main(list(argv), out, corpus_path=self.corpus, cwd=cwd)
        return code, out.getvalue()

    def record(self):
        with open(self.corpus) as fh:
            return [json.loads(l) for l in fh if l.strip()][-1]

    def turn(self, session, ts, project="/p"):
        append({"type": "turn", "session": session, "project": project,
                "tokens": 100_000, "baseline": 10_000, "ts": ts}, self.corpus)


class TheRecord(PreflightTestCase):

    def test_it_carries_the_shape_tokens_floor_and_decision(self):
        self.run_preflight("--shape", "originating", "--tokens", "40000",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["type"], "preflight")
        self.assertEqual(r["shape"], "originating")
        self.assertEqual(r["tokens"], 40_000)
        self.assertEqual(r["floor"], 50_000)
        self.assertEqual(r["decision"], "proceed")
        self.assertEqual(r["project"], "/p")

    def test_a_note_is_carried(self):
        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed", "--note", "small edit")

        self.assertEqual(self.record()["note"], "small edit")


class ItDoesNotTakeYourWordForIt(PreflightTestCase):
    """The anti-rationalisation mechanism. A model can talk itself past a
    threshold; it cannot talk the arithmetic out of the record."""

    def test_proceeding_over_the_floor_is_recorded_as_overridden(self):
        self.run_preflight("--shape", "originating", "--tokens", "190000",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["decision"], "overridden")
        self.assertEqual(r["declared"], "proceed")

    def test_proceeding_under_the_floor_stays_proceed(self):
        self.run_preflight("--shape", "originating", "--tokens", "40000",
                           "--decision", "proceed")

        self.assertEqual(self.record()["decision"], "proceed")

    def test_handing_off_over_the_floor_is_honoured_not_rewritten(self):
        """Obeying the gate is the case the record must never mislabel."""
        self.run_preflight("--shape", "originating", "--tokens", "190000",
                           "--decision", "handoff")

        self.assertEqual(self.record()["decision"], "handoff")

    def test_mechanical_is_ungated_so_it_can_never_be_an_override(self):
        self.run_preflight("--shape", "mechanical", "--tokens", "900000",
                           "--decision", "proceed")

        r = self.record()
        self.assertIsNone(r["floor"])
        self.assertEqual(r["decision"], "proceed")

    def test_the_output_says_override_out_loud(self):
        """The gate's enforcement at this stage is visibility."""
        _, out = self.run_preflight("--shape", "originating", "--tokens",
                                    "190000", "--decision", "proceed")

        self.assertIn("OVERRIDE", out.upper())
        self.assertIn("190,000", out)


class Session(PreflightTestCase):
    """Records that cannot be tied to a session cannot produce a rate, so the
    command infers one — and says that it inferred it."""

    def test_an_explicit_session_is_used_and_marked_as_given(self):
        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed", "--session", "s9")

        r = self.record()
        self.assertEqual(r["session"], "s9")
        self.assertEqual(r["session_source"], "given")

    def test_it_falls_back_to_the_latest_turn_in_this_project(self):
        self.turn("old", ts="2026-08-15T09:00:00Z")
        self.turn("current", ts="2026-08-15T14:00:00Z")

        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["session"], "current")
        self.assertEqual(r["session_source"], "inferred")

    def test_a_turn_from_another_project_is_not_borrowed(self):
        self.turn("elsewhere", ts="2026-08-15T14:00:00Z", project="/other")

        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed")

        r = self.record()
        self.assertIsNone(r["session"])
        self.assertEqual(r["session_source"], "unknown")


class NeverLosesTheRecord(PreflightTestCase):

    def test_an_unwritable_corpus_fails_loudly(self):
        out = io.StringIO()

        code = main(["--shape", "originating", "--tokens", "1", "--decision",
                     "proceed"], out, corpus_path="/nonexistent/dir/c.jsonl")

        self.assertNotEqual(code, 0)
        self.assertIn("not recorded", out.getvalue().lower())

    def test_an_unknown_shape_is_refused_without_writing(self):
        code, out = self.run_preflight("--shape", "vibes", "--tokens", "10",
                                       "--decision", "proceed")

        self.assertNotEqual(code, 0)
        self.assertIn("vibes", out)
        self.assertFalse(os.path.exists(self.corpus))


if __name__ == "__main__":
    unittest.main()
