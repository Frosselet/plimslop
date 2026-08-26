"""Tests for what the UserPromptSubmit hook emits.

Design §3: below the lowest defined floor the figure goes to the human only
(systemMessage, which never enters model context); at or above it, the model
gets additionalContext carrying the number and a pointer to the skill.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.measure import Session
from plimslop.report import build_output

WINDOW = 1_000_000


class BelowTheLowestFloor(unittest.TestCase):

    def test_the_human_sees_the_figure(self):
        out = build_output(Session(tokens=12_000, baseline=8_000), WINDOW)
        self.assertIn("12,000", out["systemMessage"])

    def test_nothing_reaches_the_model(self):
        """Spending context to police context is a bad trade: below every floor
        the model has no decision to make, so it is told nothing."""
        out = build_output(Session(tokens=12_000, baseline=8_000), WINDOW)
        self.assertNotIn("hookSpecificOutput", out)


class AtOrAboveTheLowestFloor(unittest.TestCase):

    def test_the_model_is_given_the_working_figure_and_the_baseline(self):
        """R141: the figure the floor is compared against is `working`. The
        baseline is printed beside it so the total stays recoverable."""
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("150,000", context)
        self.assertIn("40,000", context)

    def test_the_model_is_pointed_at_the_skill(self):
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("managing-context-budget", context)

    def test_the_percentage_is_never_offered_to_the_model(self):
        """§3: WINDOW demotes to display only. A percentage in the model's ear
        is what makes 190K read as a comfortable 19%."""
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("19%", context)
        self.assertNotIn("%", context)

    def test_the_floor_that_was_crossed_is_named(self):
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("50,000", context)


class ABaselineOverTheFloorIsNoLongerUnsatisfiable(unittest.TestCase):
    """SUPERSEDES `UnsatisfiableGate`.

    That class asserted the model be told "you cannot originate in this
    configuration" whenever the baseline alone exceeded a floor. Under a
    baseline-relative floor that claim is false -- the baseline is subtracted,
    so it never consumes the allowance. Design §4.
    """

    def test_a_large_baseline_with_little_work_tells_the_model_nothing(self):
        out = build_output(Session(tokens=62_000, baseline=60_000), WINDOW)
        self.assertNotIn("hookSpecificOutput", out)

    def test_the_model_is_never_told_the_gate_cannot_be_satisfied(self):
        out = build_output(Session(tokens=200_000, baseline=60_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("cannot", context.lower())


class Compaction(unittest.TestCase):
    """§8: compaction lowers the number without undoing the damage, so a
    compacted session must not read as though it were fresh."""

    def test_a_compacted_session_is_flagged_even_though_tokens_are_low(self):
        session = Session(tokens=25_000, baseline=20_000,
                          compacted=True, dropped=975_625)
        out = build_output(session, WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("975,625", context)

    def test_the_working_figure_carries_the_dropped_tokens_back(self):
        """R141: tokens - baseline would read 5,000 here. The session has in
        fact done 980,625 tokens of work, and that is what it is told."""
        session = Session(tokens=25_000, baseline=20_000,
                          compacted=True, dropped=975_625)
        out = build_output(session, WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("980,625", context)

    def test_an_uncompacted_low_session_still_tells_the_model_nothing(self):
        out = build_output(Session(tokens=25_000, baseline=20_000), WINDOW)
        self.assertNotIn("hookSpecificOutput", out)


if __name__ == "__main__":
    unittest.main()
