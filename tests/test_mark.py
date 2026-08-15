"""Tests for the rework marker command.

Design §7: a rework record carries ts, target, attributed session/turn/tokens,
method and confidence. The attribution order is explicit -> git-derived ->
unattributed, and the last of those is a real outcome, never a dropped record:
the unattributed fraction is a quality measure of the corpus itself.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.corpus import append
from plimslop.mark import main


class MarkTestCase(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")

    def run_mark(self, *argv, cwd=None):
        """Run the command; return (exit_code, stdout)."""
        out = io.StringIO()
        code = main(list(argv), out, corpus_path=self.corpus, cwd=cwd)
        return code, out.getvalue()

    def records(self):
        with open(self.corpus) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def rework(self):
        return [r for r in self.records() if r["type"] == "rework"][-1]

    def turn(self, session, tokens, ts, baseline=0, project="/tmp/p"):
        """Put one turn record in the corpus, the way the hook would."""
        append({"type": "turn", "session": session, "project": project,
                "tokens": tokens, "baseline": baseline, "ts": ts},
               self.corpus)


class GitRepoTestCase(MarkTestCase):
    """A real repository with commits at controlled times. Git attribution is
    the workhorse of §7 and the part most able to be subtly wrong, so these
    tests run git rather than a stand-in for it."""

    def setUp(self):
        super().setUp()
        self.repo = tempfile.mkdtemp()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")

    def git(self, *argv, at=None):
        env = dict(os.environ)
        if at:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = at
        return subprocess.run(("git",) + argv, cwd=self.repo, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, check=True).stdout.strip()

    def commit(self, name, body, at):
        """Write a file and commit it at a fixed time. Returns the sha."""
        with open(os.path.join(self.repo, name), "w") as fh:
            fh.write(body)
        self.git("add", name)
        self.git("commit", "-q", "-m", "wrote " + name, at=at)
        return self.git("rev-parse", "HEAD")


class Unattributed(MarkTestCase):

    def test_a_marker_with_nothing_to_attribute_to_is_still_recorded(self):
        code, _ = self.run_mark("the retry logic I threw away")

        self.assertEqual(code, 0)
        record = self.records()[0]
        self.assertEqual(record["type"], "rework")
        self.assertEqual(record["target"], "the retry logic I threw away")
        self.assertEqual(record["method"], "unattributed")
        self.assertEqual(record["confidence"], "none")
        self.assertIsNone(record["session"])
        self.assertIsNone(record["tokens"])

    def test_it_says_the_marker_is_unattributed(self):
        """A marker that landed on no turn has to look different from one that
        did, at the moment it is written. Silent failure to attribute would
        make a thin corpus feel solid."""
        _, out = self.run_mark("the retry logic I threw away")

        self.assertIn("unattributed", out)

    def test_the_note_is_carried(self):
        _, _ = self.run_mark("parser.py", "--note", "rewritten from scratch")

        self.assertEqual(self.records()[0]["note"], "rewritten from scratch")


class ExplicitSession(MarkTestCase):
    """Attribution order step 1. The session is exact; the turn within it is
    not, so the record carries the interval it could have been produced in
    rather than a point it probably was not."""

    def test_the_session_is_recorded_exactly(self):
        self.turn("s1", 40_000, ts="2026-08-15T09:00:00Z")

        self.run_mark("parser.py", "--session", "s1")

        record = self.rework()
        self.assertEqual(record["method"], "explicit")
        self.assertEqual(record["confidence"], "exact")
        self.assertEqual(record["session"], "s1")

    def test_no_single_turn_is_claimed(self):
        self.turn("s1", 40_000, ts="2026-08-15T09:00:00Z")
        self.turn("s1", 317_000, ts="2026-08-15T14:00:00Z")

        self.run_mark("parser.py", "--session", "s1")

        self.assertIsNone(self.rework()["tokens"])

    def test_the_interval_spans_the_sessions_first_and_last_turn(self):
        self.turn("s1", 317_000, ts="2026-08-15T14:00:00Z")
        self.turn("s1", 40_000, ts="2026-08-15T09:00:00Z")
        self.turn("s2", 900_000, ts="2026-08-15T11:00:00Z")

        self.run_mark("parser.py", "--session", "s1")

        record = self.rework()
        self.assertEqual(record["tokens_lo"], 40_000)
        self.assertEqual(record["tokens_hi"], 317_000)

    def test_a_session_the_corpus_never_saw_is_still_exact(self):
        """The named session is a fact about the marker, not about the corpus.
        Losing the token interval does not make the attribution a guess."""
        self.run_mark("parser.py", "--session", "s-unseen")

        record = self.rework()
        self.assertEqual(record["method"], "explicit")
        self.assertEqual(record["confidence"], "exact")
        self.assertIsNone(record["tokens_lo"])
        self.assertIsNone(record["tokens_hi"])


class GitDerived(GitRepoTestCase):
    """Attribution order step 2, the workhorse: the marker names a file, git
    gives the commit, the turn records give the session that was running when
    that commit's work was done."""

    def test_the_commit_that_last_touched_the_file_is_found(self):
        sha = self.commit("parser.py", "one\ntwo\n", at="2026-08-15T12:00:00+0000")
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)

        self.run_mark("parser.py", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["method"], "git")
        self.assertEqual(record["commit"], sha)

    def test_it_attributes_to_the_last_turn_before_the_commit(self):
        """Commits happen after the work, so the producing turn is the latest
        one at or before the commit — never one that came after it."""
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("s1", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)
        self.turn("s2", 900_000, ts="2026-08-15T13:00:00Z", project=self.repo)

        self.run_mark("parser.py", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["session"], "s1")
        self.assertEqual(record["tokens"], 190_000)

    def test_the_attribution_is_flagged_inferred(self):
        """One commit can span many turns and lands after them. The mapping is
        an inference and the curve has to be able to render it as one."""
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)

        self.run_mark("parser.py", cwd=self.repo)

        self.assertEqual(self.rework()["confidence"], "inferred")

    def test_a_turn_spent_in_another_project_is_never_used(self):
        """The corpus is cross-project. Pinning rework here to a turn spent
        elsewhere would be worse than leaving it unattributed."""
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("elsewhere", 190_000, ts="2026-08-15T11:00:00Z",
                  project="/some/other/repo")

        self.run_mark("parser.py", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["method"], "unattributed")
        self.assertIsNone(record["session"])

    def test_the_commit_survives_even_when_no_turn_matches(self):
        """The commit is real evidence and stays in the record; only the turn
        attribution failed. A later reader with a fuller corpus can use it."""
        sha = self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")

        self.run_mark("parser.py", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["method"], "unattributed")
        self.assertEqual(record["commit"], sha)

    def test_a_file_git_has_never_seen_is_unattributed(self):
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)

        self.run_mark("scratch.py", cwd=self.repo)

        self.assertEqual(self.rework()["method"], "unattributed")


class GitDerivedHunk(GitRepoTestCase):

    def test_a_hunk_is_attributed_to_what_last_touched_those_lines(self):
        """§7 says a marker may name a file *or a hunk*. Blaming the lines is
        sharper than the file's latest commit: the reworked lines and the
        file's most recent edit are often different turns."""
        first = self.commit("parser.py", "one\ntwo\n", at="2026-08-15T10:00:00+0000")
        self.commit("parser.py", "one\ntwo\nthree\n", at="2026-08-15T14:00:00+0000")
        self.turn("early", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)
        self.turn("late", 300_000, ts="2026-08-15T13:00:00Z", project=self.repo)

        self.run_mark("parser.py:1-2", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["commit"], first)
        self.assertEqual(record["session"], "early")

    def test_a_single_line_hunk_is_accepted(self):
        self.commit("parser.py", "one\ntwo\n", at="2026-08-15T10:00:00+0000")
        self.turn("early", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)

        self.run_mark("parser.py:2", cwd=self.repo)

        self.assertEqual(self.rework()["session"], "early")


class ExplicitCommit(GitRepoTestCase):
    """Naming the commit skips the blame step but not the timestamp step, so
    the record is `explicit` in method and still `inferred` in confidence."""

    def test_the_named_commit_is_used_rather_than_the_targets_own_history(self):
        sha = self.commit("parser.py", "one\n", at="2026-08-15T10:00:00+0000")
        self.commit("other.py", "x\n", at="2026-08-15T16:00:00+0000")
        self.turn("early", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)
        self.turn("late", 600_000, ts="2026-08-15T15:00:00Z", project=self.repo)

        self.run_mark("other.py", "--commit", sha, cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["method"], "explicit")
        self.assertEqual(record["session"], "early")
        self.assertEqual(record["tokens"], 40_000)

    def test_the_turn_mapping_is_still_only_inferred(self):
        """A commit lands after the work and can span many turns. Naming it
        exactly does not make the turn behind it exact."""
        sha = self.commit("parser.py", "one\n", at="2026-08-15T10:00:00+0000")
        self.turn("early", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)

        self.run_mark("parser.py", "--commit", sha, cwd=self.repo)

        self.assertEqual(self.rework()["confidence"], "inferred")

    def test_a_commit_git_cannot_resolve_is_unattributed(self):
        self.commit("parser.py", "one\n", at="2026-08-15T10:00:00+0000")
        self.turn("early", 40_000, ts="2026-08-15T09:00:00Z", project=self.repo)

        self.run_mark("parser.py", "--commit", "0" * 40, cwd=self.repo)

        self.assertEqual(self.rework()["method"], "unattributed")


class PreferenceOrder(GitRepoTestCase):

    def test_an_explicit_session_beats_what_git_would_have_said(self):
        """§7's order is explicit first. The human naming the session knows
        something git's timestamps do not."""
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("blamed", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)
        self.turn("named", 80_000, ts="2026-08-15T08:00:00Z", project=self.repo)

        self.run_mark("parser.py", "--session", "named", cwd=self.repo)

        record = self.rework()
        self.assertEqual(record["session"], "named")
        self.assertEqual(record["confidence"], "exact")


class NeverLosesTheMarker(MarkTestCase):
    """A marker is written when rework is *discovered* — usually mid-task. It
    must cost nothing and must not fail silently."""

    def test_outside_a_git_repository_the_marker_is_still_written(self):
        code, _ = self.run_mark("parser.py", cwd=tempfile.mkdtemp())

        self.assertEqual(code, 0)
        self.assertEqual(self.rework()["method"], "unattributed")

    def test_a_corpus_that_cannot_be_written_is_reported_and_fails_loudly(self):
        """The hooks swallow write failures because a lost record beats a lost
        turn. A marker is the whole point of the command: if it did not land,
        the user has to know."""
        out = io.StringIO()

        code = main(["parser.py"], out, corpus_path="/nonexistent/dir/corpus.jsonl")

        self.assertNotEqual(code, 0)
        self.assertIn("not recorded", out.getvalue().lower())

    def test_the_marker_records_which_project_it_came_from(self):
        self.run_mark("parser.py", cwd="/tmp/proj")

        self.assertEqual(self.rework()["project"], "/tmp/proj")


class WhatTheUserSees(GitRepoTestCase):

    def test_an_inferred_attribution_is_shown_as_inferred(self):
        """The one line printed back is where an over-confident attribution
        would be caught. It has to carry the session, the figure it landed on,
        and the fact that the mapping was inferred."""
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)

        _, out = self.run_mark("parser.py", cwd=self.repo)

        self.assertIn("s1", out)
        self.assertIn("190,000", out)
        self.assertIn("inferred", out)

    def test_a_session_seen_at_one_figure_is_not_shown_as_a_range(self):
        """`190,000–190,000` reads as a measurement of nothing. One observed
        turn is still one figure — and still not a pinned turn."""
        self.turn("s1", 190_000, ts="2026-08-15T11:00:00Z", project=self.repo)

        _, out = self.run_mark("parser.py", "--session", "s1", cwd=self.repo)

        self.assertNotIn("190,000–190,000", out)
        self.assertIn("190,000", out)

    def test_a_turn_record_with_no_session_does_not_break_the_report(self):
        """The corpus is append-only and old records outlive schema changes.
        A record it cannot name is still a record it must not choke on."""
        append({"type": "turn", "project": self.repo, "tokens": 190_000,
                "ts": "2026-08-15T11:00:00Z"}, self.corpus)
        self.commit("parser.py", "one\n", at="2026-08-15T12:00:00+0000")

        code, out = self.run_mark("parser.py", cwd=self.repo)

        self.assertEqual(code, 0)
        self.assertIn("190,000", out)


if __name__ == "__main__":
    unittest.main()
