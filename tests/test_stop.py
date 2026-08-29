"""Tests for the Stop hook: enforcement at the turn boundary.

Design §9. Enforcement strength tracks evidence grade, the block is always
passable in one step, and it never blocks into a state you cannot satisfy.

Payload and decision schema verified against the hooks reference 2026-08-15:
blocking is hookSpecificOutput.permissionDecision == "deny".
"""

import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.stop import _modes, main


def transcript(*usages):
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for total in usages:
        fh.write(json.dumps({"message": {"usage": {"input_tokens": total}}}) + "\n")
    fh.close()
    return fh.name


class StopHookCase(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")

    def run_hook(self, payload, modes=None):
        out = io.StringIO()
        code = main(io.StringIO(json.dumps(payload)), out,
                    corpus_path=self.corpus, modes=modes)
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None)

    def blocked(self, out):
        if not out:
            return False
        specific = out.get("hookSpecificOutput") or {}
        return specific.get("permissionDecision") == "deny"


class BelowTheFloor(StopHookCase):

    def test_does_not_block(self):
        path = transcript(12_000)
        self.addCleanup(os.unlink, path)

        code, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertEqual(code, 0)
        self.assertFalse(self.blocked(out))


class AboveTheFloor(StopHookCase):

    def test_blocks_by_default(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        code, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertEqual(code, 0)
        self.assertTrue(self.blocked(out))

    def test_the_reason_names_the_figure_and_the_skill(self):
        """The figure named is the WORKING one (R141). It used to assert the
        raw 190,000 total; under the ruled unit that number is not what the
        floor was compared against, and printing it would invite the reader to
        check arithmetic that no longer applies. The baseline is printed beside
        it so the total remains recoverable."""
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("170,000", reason)      # 190,000 - 20,000 baseline
        self.assertIn("20,000", reason)
        self.assertIn("managing-context-budget", reason)

    def test_warn_mode_does_not_block(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path},
                               modes={"originating": "warn"})

        self.assertFalse(self.blocked(out))

    def test_off_mode_does_not_block(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path},
                               modes={"originating": "off"})

        self.assertFalse(self.blocked(out))


class OneStepOverride(StopHookCase):
    """§9: a block that cannot be passed in one step gets disabled wholesale,
    and then nothing is measured."""

    def test_the_same_session_is_never_blocked_twice(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)
        payload = {"session_id": "s", "transcript_path": path}

        _, first = self.run_hook(payload)
        _, second = self.run_hook(payload)

        self.assertTrue(self.blocked(first))
        self.assertFalse(self.blocked(second))

    def test_a_different_session_is_still_blocked(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        self.run_hook({"session_id": "s1", "transcript_path": path})
        _, out = self.run_hook({"session_id": "s2", "transcript_path": path})

        self.assertTrue(self.blocked(out))

    def test_the_override_is_recorded_so_the_rate_can_be_measured(self):
        """An override nobody can count is a gate nobody can evaluate."""
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        self.run_hook({"session_id": "s", "transcript_path": path})

        with open(self.corpus) as fh:
            kinds = [json.loads(line)["type"] for line in fh if line.strip()]
        self.assertIn("block", kinds)


class RaisedOncePerSession(StopHookCase):
    """§9's one-step constraint applies to warnings too. A hook that speaks at
    the end of every single turn past the floor gets switched off wholesale,
    and then nothing is measured at all — which is the failure the whole
    project dies of, not a matter of taste."""

    def warned(self, out):
        return bool(out and out.get("systemMessage"))

    def test_a_warning_is_not_repeated_every_turn(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)
        payload = {"session_id": "s", "transcript_path": path}
        warn = {"originating": "warn"}

        _, first = self.run_hook(payload, modes=warn)
        _, second = self.run_hook(payload, modes=warn)

        self.assertTrue(self.warned(first))
        self.assertFalse(self.warned(second))

    def test_a_different_session_is_still_warned(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)
        warn = {"originating": "warn"}

        self.run_hook({"session_id": "s1", "transcript_path": path}, modes=warn)
        _, out = self.run_hook({"session_id": "s2", "transcript_path": path},
                               modes=warn)

        self.assertTrue(self.warned(out))

    def test_a_warning_is_recorded_as_a_warning_not_as_a_block(self):
        """Both are 'the gate spoke once', but a warning is not a refusal and
        the corpus must not let the reader count it as one."""
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        self.run_hook({"session_id": "s", "transcript_path": path},
                      modes={"originating": "warn"})

        with open(self.corpus) as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(records[0]["type"], "block")
        self.assertEqual(records[0]["action"], "warn")

    def test_a_block_is_recorded_as_a_block(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        self.run_hook({"session_id": "s", "transcript_path": path})

        with open(self.corpus) as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(records[0]["action"], "block")


class GatesOnWorkingTokens(StopHookCase):
    """The ruled unit: work accumulated ABOVE the session baseline.

    iladub `docs/superpowers/2026-08-26-context-regime-ruling.md` §3, and
    docs/superpowers/specs/2026-08-26-r141-working-tokens-design.md.
    """

    def test_a_large_baseline_with_little_work_done_is_allowed(self):
        """The case the ruling exists for: iladub's own 46,243-token baseline
        against a 50,000 floor left 3 of 482 recorded turns ever under it."""
        path = transcript(46_243, 50_000)     # working = 3,757
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertIsNone(out)

    def test_work_above_the_baseline_still_trips_the_floor(self):
        path = transcript(46_243, 100_000)    # working = 53,757
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertTrue(self.blocked(out))

    def test_the_message_quotes_the_working_figure_not_the_total(self):
        path = transcript(46_243, 100_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        reason = json.dumps(out)
        self.assertIn("53,757", reason)


class ABaselineOverTheFloorNoLongerDisablesTheGate(StopHookCase):
    """SUPERSEDES `NeverBlockIntoAnUnsatisfiableState`.

    That class encoded a real constraint -- "if the baseline alone exceeds the
    floor, blocking would refuse all work from turn one" -- which was TRUE
    while the floor was compared against total window occupancy. Under a
    baseline-relative floor `working` is ~0 at turn one for ANY baseline, so no
    baseline can make the gate unsatisfiable and the guard's message ("The gate
    cannot be satisfied in this configuration") is now false.

    Design §4: delete the branch rather than invent a replacement threshold.
    """

    def test_a_baseline_over_the_floor_still_blocks_once_work_is_done(self):
        path = transcript(60_000, 190_000)   # baseline 60,000, working 130,000
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertTrue(self.blocked(out))

    def test_it_no_longer_claims_the_gate_cannot_be_satisfied(self):
        path = transcript(60_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertNotIn("cannot be satisfied", json.dumps(out))


class CompactionDoesNotResetTheGate(StopHookCase):
    """A compaction lowers `tokens` without undoing the reasoning spent."""

    def test_a_compacted_session_is_judged_on_what_it_has_actually_done(self):
        fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        fh.write(json.dumps({"message": {"usage": {"input_tokens": 40_000}}}) + "\n")
        fh.write(json.dumps({"message": {"usage": {"input_tokens": 900_000}}}) + "\n")
        fh.write(json.dumps({"type": "system", "subtype": "compact_boundary",
                             "compactMetadata": {"preTokens": 900_000,
                                                 "postTokens": 45_000,
                                                 "cumulativeDroppedTokens": 855_000}}) + "\n")
        fh.write(json.dumps({"message": {"usage": {"input_tokens": 45_000}}}) + "\n")
        fh.close()
        self.addCleanup(os.unlink, fh.name)

        # Naive tokens - baseline would read 5,000 and allow. The session has
        # in fact done 860,000 tokens of work.
        _, out = self.run_hook({"session_id": "s", "transcript_path": fh.name})

        self.assertTrue(self.blocked(out))


class Subagents(StopHookCase):
    """§4.5: subagent context is separate, so delegation is the remedy. A hook
    that blocks subagents punishes the one mechanism that actually helps."""

    def test_a_subagent_is_never_blocked(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path,
                                "agent_id": "a1", "agent_type": "general-purpose"})

        self.assertFalse(self.blocked(out))


class NeverBreaksTheTurn(StopHookCase):

    def test_malformed_stdin_exits_zero_without_blocking(self):
        out = io.StringIO()
        code = main(io.StringIO("{not json"), out, corpus_path=self.corpus)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "")

    def test_a_missing_transcript_exits_zero_without_blocking(self):
        code, out = self.run_hook({"session_id": "s",
                                   "transcript_path": "/nope/gone.jsonl"})
        self.assertEqual(code, 0)
        self.assertFalse(self.blocked(out))

    def test_an_unwritable_corpus_does_not_prevent_the_decision(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)
        out = io.StringIO()

        code = main(io.StringIO(json.dumps({"session_id": "s",
                                            "transcript_path": path})),
                    out, corpus_path="/nonexistent/dir/corpus.jsonl")

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()


class TheDocumentedEscapeHatchActuallyWorks(StopHookCase):
    """`PLIMSLOP_MODE_<SHAPE>` is the control the README tells a reader to set
    to soften the gate, and it is what currently holds `originating` at `warn`
    while the 2026-08-26 prediction is under observation (iladub R140).

    Nothing tested that it does anything. `test_docs_match_code` compares the
    NAME in the prose against the name in the code — which is what caught the
    `DEADWEIGHT_` leftover — but a variable can be spelled correctly on both
    sides and still be read into a value nobody applies. That failure is silent
    in the worst direction: the gate the reader is trying to soften keeps
    blocking, and a blocking gate gets uninstalled.

    These go through `main` with `modes=None`, which is the path the real hook
    takes; the shape-specific tests above all inject `modes` and so never
    exercise the environment at all.
    """

    def over_the_floor(self):
        path = transcript(20_000, 190_000)       # 170,000 working, originating
        self.addCleanup(os.unlink, path)
        return {"session_id": "s", "transcript_path": path}

    def test_warn_in_the_environment_stops_the_gate_blocking(self):
        with mock.patch.dict(os.environ,
                             {"PLIMSLOP_MODE_ORIGINATING": "warn"}):
            _, out = self.run_hook(self.over_the_floor())

        self.assertFalse(self.blocked(out))

    def test_the_shipped_default_blocks_when_the_environment_is_silent(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            _, out = self.run_hook(self.over_the_floor())

        self.assertTrue(self.blocked(out))

    def test_a_value_that_is_not_a_mode_is_ignored_rather_than_obeyed(self):
        """Asserted against `_modes` and not through the hook ON PURPOSE.
        `decide` treats every mode that is not `off` or `warn` as `block`, so a
        junk value fails safe and is INVISIBLE end-to-end: written that way this
        test passed with the `in ("block", "warn", "off")` guard deleted, which
        is a test pinning nothing. The guard's whole effect is keeping the mode
        vocabulary closed at the boundary that reads it, so that is where it is
        pinned."""
        with mock.patch.dict(os.environ,
                             {"PLIMSLOP_MODE_ORIGINATING": "yes"}):
            self.assertEqual(_modes()["originating"], "block")
