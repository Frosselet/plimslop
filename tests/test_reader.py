"""Tests for the reader.

Design §7: three views, and one behaviour that matters more than the other
two — the reader refuses to draw conclusions from thin data. The prior rule
exists because one session's observation was promoted; a tool that will
happily draw a confident curve through four points is a machine for
manufacturing more of them.

So most of what is tested here is the tool declining to speak.
"""

import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.corpus import append
from plimslop.reader import main, N_REPORT


class ReaderTestCase(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")

    def view(self, name, *argv):
        out = io.StringIO()
        code = main([name, *argv], out, corpus_path=self.corpus)
        return code, out.getvalue()

    def turns(self, count, tokens, session="s", baseline=10_000):
        for i in range(count):
            append({"type": "turn", "session": "%s%d" % (session, i),
                    "project": "/p", "tokens": tokens, "baseline": baseline,
                    "ts": "2026-08-15T10:00:00Z"}, self.corpus)

    def rework(self, count, tokens, method="git", confidence="inferred"):
        for _ in range(count):
            append({"type": "rework", "target": "f.py", "method": method,
                    "confidence": confidence, "session": "s", "tokens": tokens,
                    "project": "/p"}, self.corpus)


class RefusesThinData(ReaderTestCase):
    """The central behaviour. Below the stated n the reader reports the count
    and declines to state a rate."""

    def test_a_band_below_the_threshold_states_no_rate(self):
        self.turns(3, tokens=190_000)
        self.rework(1, tokens=190_000)

        _, out = self.view("curve")

        self.assertIn("n=3", out)
        self.assertIn("this shows nothing", out)
        self.assertNotIn("33%", out)

    def test_a_band_at_the_threshold_states_a_rate(self):
        self.turns(N_REPORT, tokens=190_000)
        self.rework(N_REPORT // 10, tokens=190_000)

        _, out = self.view("curve")

        self.assertIn("10%", out)

    def test_it_never_compares_bands_on_report_level_data(self):
        """Two thresholds, not one: stating a rate is a lower bar than
        comparing two of them. n_report data must not produce a comparison."""
        self.turns(N_REPORT, tokens=20_000)
        self.turns(N_REPORT, tokens=190_000)
        self.rework(1, tokens=20_000)
        self.rework(N_REPORT // 2, tokens=190_000)

        _, out = self.view("curve")

        self.assertNotIn("higher than", out)
        self.assertIn("not enough to compare", out)

    def test_the_thresholds_are_printed_and_labelled_unsettled(self):
        """A refusal threshold nobody can see is a magic number."""
        self.turns(3, tokens=190_000)

        _, out = self.view("curve")

        self.assertIn(str(N_REPORT), out)
        self.assertIn("PROPOSED", out)


class CountsWhatItCannotAttribute(ReaderTestCase):
    """§7: unattributed markers are counted and displayed, never dropped. The
    unattributed fraction is a quality measure of the corpus itself."""

    def test_unattributed_markers_appear_in_the_output(self):
        self.rework(2, tokens=None, method="unattributed", confidence="none")

        _, out = self.view("curve")

        self.assertIn("unattributed", out)
        self.assertIn("2", out)

    def test_inferred_and_exact_attributions_are_distinguished(self):
        self.rework(1, tokens=190_000, method="git", confidence="inferred")
        self.rework(1, tokens=190_000, method="explicit", confidence="exact")

        _, out = self.view("curve")

        self.assertIn("inferred", out)
        self.assertIn("exact", out)

    def test_the_denominator_it_actually_used_is_named(self):
        """§7 wanted producing turns. The corpus records no tool use, so this
        is turns — and the output has to say so rather than imply otherwise."""
        self.turns(2, tokens=190_000)

        _, out = self.view("curve")

        self.assertIn("not producing turns", out)


class BaselineView(ReaderTestCase):

    def test_it_reports_the_observed_baseline(self):
        self.turns(1, tokens=60_000, baseline=34_650)

        _, out = self.view("baseline")

        self.assertIn("34,650", out)

    def test_a_baseline_over_a_floor_is_called_out(self):
        """If the baseline alone clears a floor, the gate cannot be satisfied
        and the user needs to hear that, not a silent refusal of all work."""
        self.turns(1, tokens=90_000, baseline=80_000)

        _, out = self.view("baseline")

        self.assertIn("exceeds", out)
        self.assertIn("50,000", out)


class TiersView(ReaderTestCase):

    def test_each_floor_is_printed_with_its_grade(self):
        _, out = self.view("tiers")

        self.assertIn("50,000", out)
        self.assertIn("150,000", out)
        self.assertIn("NO SOURCE", out)

    def test_a_thin_corpus_can_neither_support_nor_contradict(self):
        """A thin corpus must not be able to demote a floor by being
        underpowered — the prior rule's own error, inverted."""
        self.turns(3, tokens=190_000)
        self.rework(3, tokens=190_000)

        _, out = self.view("tiers")

        self.assertIn("CANNOT YET SPEAK", out)
        self.assertNotIn("CONTRADICTS", out)


class NeverBreaks(ReaderTestCase):

    def test_an_empty_corpus_exits_zero_and_says_so(self):
        code, out = self.view("curve")

        self.assertEqual(code, 0)
        self.assertIn("empty", out.lower())

    def test_an_unknown_view_exits_nonzero_without_a_traceback(self):
        code, out = self.view("prophecy")

        self.assertNotEqual(code, 0)
        self.assertIn("prophecy", out)


if __name__ == "__main__":
    unittest.main()


class OverrideView(ReaderTestCase):
    """DECISION 4 (design §5). The ruling's own falsifying instrument was
    computed by no code in either repo: `grep -n preflight plimslop/reader.py`
    had no hits, and the 54% came from an audit run by hand.

    The definition was RECOVERED, not chosen: scoring the corpus truncated to
    the 681 lines the audit saw reproduces its headline figures exactly --
    39/72 = 54.2% overall and 35/67 = 52.2% iladub-only -- only under
    `overridden / (gated records at or over their floor)`.
    """

    def preflights(self, count, tokens, shape="originating",
                   declared="proceed", working=None, baseline=None,
                   session="s", measured=None):
        for i in range(count):
            r = {"type": "preflight", "shape": shape, "tokens": tokens,
                 "floor": 50_000, "declared": declared, "project": "/p",
                 "session": "%s%d" % (session, i)}
            if measured is not None:
                r.update({"measured": measured, "working": working,
                          "baseline": baseline, "measured_tokens": tokens})
            append(r, self.corpus)

    def test_an_empty_corpus_says_so_rather_than_dividing_by_zero(self):
        code, text = self.view("override")
        self.assertEqual(code, 0)
        self.assertIn("nothing", text.lower())

    def test_it_refuses_to_state_a_rate_below_the_reporting_threshold(self):
        self.preflights(3, 90_000)
        _, text = self.view("override")
        self.assertIn("shows nothing", text)

    def test_the_rate_is_overridden_over_records_that_tripped_the_floor(self):
        """Denominator is records AT OR OVER the floor, not all gated records:
        of the times the gate actually fired, how often work proceeded anyway."""
        self.preflights(15, 90_000, declared="proceed")   # fired, overridden
        self.preflights(5, 90_000, declared="handoff", session="h")  # fired, complied
        self.preflights(30, 10_000, declared="proceed", session="u")  # never fired
        _, text = self.view("override")
        self.assertIn("15/20", text)
        self.assertIn("75%", text)

    def test_a_stop_decision_counts_as_compliance_not_override(self):
        """Carried deliberately from the audit so the comparison stays
        like-for-like: `stop` is accepted, undocumented, and was counted as
        compliance in the 54% figure (design §6)."""
        self.preflights(10, 90_000, declared="proceed")
        self.preflights(10, 90_000, declared="stop", session="s2")
        _, text = self.view("override")
        self.assertIn("10/20", text)

    def test_mechanical_records_are_ungated_and_never_counted(self):
        self.preflights(25, 900_000, shape="mechanical")
        _, text = self.view("override")
        self.assertIn("shows nothing", text)

    def test_it_scores_both_units_over_the_same_records(self):
        """The working unit is recoverable for records written BEFORE the
        change, by joining to the session's turn record -- measured 152 of 152
        in the live corpus. Without that the ruling's prediction has no
        pre-change side to compare against."""
        self.turns(1, 96_000, session="s0", baseline=46_000)
        self.preflights(25, 96_000, declared="proceed")

        _, text = self.view("override")

        self.assertIn("total", text)
        self.assertIn("working", text)
        # total unit: 96,000 >= 50,000, fires. working: 50,000 >= 50,000, fires.
        self.assertIn("25/25", text)

    def test_the_working_unit_can_disagree_with_the_total_unit(self):
        self.turns(1, 90_000, session="s0", baseline=46_000)
        self.preflights(25, 90_000, declared="proceed")

        _, text = self.view("override")

        # total: 90,000 trips the floor 25 times. working: 44,000 never does.
        self.assertIn("25/25", text)
        self.assertIn("the gate never fired", text)

    def test_it_separates_records_written_after_the_change_from_before(self):
        """§5 predicts a change in BEHAVIOUR. Re-scoring old decisions in the
        new unit is a counterfactual, not the prediction coming true, and the
        two must not be added together."""
        self.preflights(25, 90_000, declared="proceed")
        self.preflights(25, 90_000, declared="handoff", session="n",
                        measured=True, working=60_000, baseline=30_000)

        _, text = self.view("override")

        self.assertIn("counterfactual", text.lower())
        self.assertIn("observed", text.lower())
