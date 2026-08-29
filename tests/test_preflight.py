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

    def run_preflight(self, *argv, cwd="/p", env=None):
        """`env` defaults to EMPTY, not to `os.environ`: this suite runs inside
        Claude Code, which exports CLAUDE_CODE_SESSION_ID, and a test that reads
        the ambient environment measures the machine it runs on."""
        out = io.StringIO()
        code = main(list(argv), out, corpus_path=self.corpus, cwd=cwd,
                    env={} if env is None else env)
        return code, out.getvalue()

    def record(self):
        with open(self.corpus) as fh:
            return [json.loads(l) for l in fh if l.strip()][-1]

    def turn(self, session, ts, project="/p", tokens=100_000, baseline=10_000,
             dropped=0):
        append({"type": "turn", "session": session, "project": project,
                "tokens": tokens, "baseline": baseline, "dropped": dropped,
                "ts": ts}, self.corpus)


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


class GatesOnMeasuredWorkingTokens(PreflightTestCase):
    """DECISION 2 (design §3): `--tokens` is whatever the caller typed, so the
    gate measures instead of asking. The baseline is already on disk -- the
    UserPromptSubmit hook writes it onto every `turn` record from the
    transcript, and `_session` already looks that record up.

    `--tokens` is kept, recorded verbatim as `declared_tokens`, and is
    advisory whenever a measurement exists. Measured 2026-08-26: 152 of 152
    preflight records in the live corpus join to a baseline.
    """

    def test_the_record_carries_the_measured_baseline_and_working_figure(self):
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=96_000, baseline=46_000)

        self.run_preflight("--shape", "originating", "--tokens", "96000",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["baseline"], 46_000)
        self.assertEqual(r["working"], 50_000)
        self.assertEqual(r["measured_tokens"], 96_000)
        self.assertTrue(r["measured"])

    def test_tokens_still_records_exactly_what_the_caller_declared(self):
        """Load-bearing for the ruling's own falsification test: the `tokens`
        key must keep the meaning it had in every record already written, or
        the pre/post comparison stops being like-for-like (design §3)."""
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=96_000, baseline=46_000)

        self.run_preflight("--shape", "originating", "--tokens", "12345",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["tokens"], 12_345)
        self.assertEqual(r["declared_tokens"], 12_345)

    def test_a_large_baseline_with_little_work_is_not_an_override(self):
        """The case the ruling exists for. Total 49,000 is under the floor
        anyway; what matters is that 96,000 total against a 46,000 baseline is
        NOT, and the old gate would have called it one."""
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=90_000, baseline=46_000)

        _, text = self.run_preflight("--shape", "originating",
                                     "--tokens", "90000", "--decision", "proceed")

        self.assertEqual(self.record()["decision"], "proceed")
        self.assertNotIn("OVERRIDE", text)

    def test_work_above_the_baseline_is_still_an_override(self):
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=110_000, baseline=46_000)

        _, text = self.run_preflight("--shape", "originating",
                                     "--tokens", "110000", "--decision", "proceed")

        self.assertEqual(self.record()["decision"], "overridden")
        self.assertIn("OVERRIDE", text)

    def test_a_caller_who_lowballs_the_figure_is_still_caught(self):
        """The module's stated design: it does not take the caller's word.
        Declaring 0 tokens does not buy a session out of the gate."""
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=110_000, baseline=46_000)

        _, text = self.run_preflight("--shape", "originating", "--tokens", "0",
                                     "--decision", "proceed")

        self.assertEqual(self.record()["decision"], "overridden")

    def test_compaction_is_carried_back_into_the_working_figure(self):
        self.turn("s1", "2026-08-26T09:00:00Z", tokens=50_000, baseline=46_000,
                  dropped=900_000)

        self.run_preflight("--shape", "originating", "--tokens", "50000",
                           "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["working"], 904_000)
        self.assertEqual(r["decision"], "overridden")


class WhenNothingHasBeenMeasured(PreflightTestCase):
    """Fallback: no turn record for this project means no baseline, so the
    command gates on the declared figure exactly as it did before, and says so
    rather than pretending to a measurement it does not have."""

    def test_it_falls_back_to_the_declared_figure(self):
        _, text = self.run_preflight("--shape", "originating",
                                     "--tokens", "190000", "--decision", "proceed")

        r = self.record()
        self.assertEqual(r["decision"], "overridden")
        self.assertIsNone(r["baseline"])
        self.assertIsNone(r["working"])
        self.assertFalse(r["measured"])

    def test_it_says_the_figure_was_not_measured(self):
        _, text = self.run_preflight("--shape", "originating",
                                     "--tokens", "190000", "--decision", "proceed")

        self.assertIn("unmeasured", text)


class ItNeverInheritsAnotherSessionsFigure(PreflightTestCase):
    """MEASURED 2026-08-29, iladub: a pre-flight run in a session created by
    `/clear` reported `working: 270265, measured: true` against a context that
    was near zero. The figure belonged to the CLEARED session.

    The chain: `hook.py` writes no turn record while a fresh transcript has no
    usage line yet, so the corpus has nothing for the new session; `_session`
    then inferred the session from the project's latest turn — the one just
    cleared — and `_measure` read its figure and stamped it `measured`.

    Claude Code names the running session in `CLAUDE_CODE_SESSION_ID`, and it is
    the same id the hook records (verified: env `acdcb012-…` == the session on
    that session's own turn records). Taking it removes the inheritance at the
    root: a session that has recorded no turn is *unmeasured*, which is the
    truth, rather than borrowing a neighbour's number.

    A `/clear` is not detectable and does not need to be: keying on the session
    the harness names makes every cross-session inheritance impossible at once,
    including two sessions open in one project.
    """

    ENV = {"CLAUDE_CODE_SESSION_ID": "fresh"}

    def test_the_running_session_is_taken_from_the_environment(self):
        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed", env=self.ENV)

        r = self.record()
        self.assertEqual(r["session"], "fresh")
        self.assertEqual(r["session_source"], "env")

    def test_a_cleared_sessions_figure_is_not_inherited(self):
        self.turn("cleared", ts="2026-08-29T08:41:19Z",
                  tokens=321_645, baseline=51_380)      # 270,265 working

        _, text = self.run_preflight("--shape", "originating", "--tokens",
                                     "3000", "--decision", "proceed",
                                     env=self.ENV)

        r = self.record()
        self.assertEqual(r["session"], "fresh")
        self.assertFalse(r["measured"])
        self.assertIsNone(r["working"])
        self.assertEqual(r["decision"], "proceed")      # NOT overridden
        self.assertIn("unmeasured", text)

    def test_it_measures_the_running_session_and_not_the_louder_neighbour(self):
        """The NEIGHBOUR's turn is the most recent one, so project-inference
        would take it — this is the second session open in the same project,
        the case that outlives `/clear` and is fixed by the same key. Written
        the other way round it passed with the repair deleted, because
        inference happened to land on the right session anyway."""
        self.turn("fresh", ts="2026-08-29T08:56:12Z",
                  tokens=94_615, baseline=51_487)       # 43,128 working
        self.turn("neighbour", ts="2026-08-29T09:10:00Z",
                  tokens=321_645, baseline=51_380)      # 270,265 working

        self.run_preflight("--shape", "originating", "--tokens", "3000",
                           "--decision", "proceed", env=self.ENV)

        r = self.record()
        self.assertEqual(r["working"], 43_128)
        self.assertEqual(r["decision"], "proceed")      # under the 50K floor

    def test_an_explicit_session_still_beats_the_environment(self):
        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed", "--session", "s9",
                           env=self.ENV)

        r = self.record()
        self.assertEqual(r["session"], "s9")
        self.assertEqual(r["session_source"], "given")

    def test_without_the_variable_it_still_infers_from_the_project(self):
        self.turn("current", ts="2026-08-15T14:00:00Z")

        self.run_preflight("--shape", "executing", "--tokens", "10000",
                           "--decision", "proceed", env={})

        r = self.record()
        self.assertEqual(r["session"], "current")
        self.assertEqual(r["session_source"], "inferred")


class TheRecordSaysWhichInstrumentWroteIt(PreflightTestCase):
    """`measured` was doing double duty: the reader splits the override rate
    into "written before R141" and "written after" on that flag alone
    (`reader._override`). Once a fresh session is legitimately unmeasured, a
    post-R141 record would be filed as pre-R141 — silently, and in exactly the
    arm the 2026-08-26 prediction is tested on. The instrument names itself."""

    def test_every_record_names_the_unit_it_was_gated_in(self):
        self.run_preflight("--shape", "originating", "--tokens", "40000",
                           "--decision", "proceed")

        self.assertEqual(self.record()["unit"], "working")

    def test_it_says_so_even_when_no_measurement_was_available(self):
        self.run_preflight("--shape", "originating", "--tokens", "40000",
                           "--decision", "proceed",
                           env={"CLAUDE_CODE_SESSION_ID": "fresh"})

        r = self.record()
        self.assertFalse(r["measured"])
        self.assertEqual(r["unit"], "working")
