"""Tests for what the UserPromptSubmit hook emits.

Design §3: below the lowest defined floor the figure goes to the human only
(systemMessage, which never enters model context); at or above it, the model
gets additionalContext carrying the number and a pointer to the skill.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadweight.measure import Session
from deadweight.report import build_output

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

    def test_the_model_is_given_the_absolute_figure(self):
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("190,000", context)

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


class UnsatisfiableGate(unittest.TestCase):
    """§5: a heavy MCP setup can exceed a floor before the first prompt. The
    tool must say so plainly rather than silently refuse all work."""

    def test_a_baseline_over_the_floor_is_reported_as_unsatisfiable(self):
        out = build_output(Session(tokens=62_000, baseline=60_000), WINDOW)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("60,000", context)
        self.assertIn("cannot", context.lower())

    def test_a_baseline_under_the_floor_says_nothing_about_being_unsatisfiable(self):
        out = build_output(Session(tokens=190_000, baseline=40_000), WINDOW)
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

    def test_an_uncompacted_low_session_still_tells_the_model_nothing(self):
        out = build_output(Session(tokens=25_000, baseline=20_000), WINDOW)
        self.assertNotIn("hookSpecificOutput", out)


if __name__ == "__main__":
    unittest.main()
