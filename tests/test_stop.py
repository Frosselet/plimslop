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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadweight.stop import main


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
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("190,000", reason)
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


class NeverBlockIntoAnUnsatisfiableState(StopHookCase):
    """§5: if the baseline alone exceeds the floor, blocking would refuse all
    work from turn one and the tool gets uninstalled inside a day."""

    def test_a_baseline_over_the_floor_degrades_to_a_warning(self):
        path = transcript(60_000, 190_000)   # baseline 60,000 > 50,000 floor
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertFalse(self.blocked(out))

    def test_it_says_why_rather_than_going_quiet(self):
        path = transcript(60_000, 190_000)
        self.addCleanup(os.unlink, path)

        _, out = self.run_hook({"session_id": "s", "transcript_path": path})

        self.assertIn("60,000", out["systemMessage"])


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
