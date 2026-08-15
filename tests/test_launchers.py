"""Tests for the hook launchers the plugin invokes.

The installed hooks used to carry an absolute PYTHONPATH pointing at one
checkout on one machine. A published plugin cannot: it is unpacked wherever
the plugin cache happens to be. So the launchers must locate the package
relative to themselves, with no environment set for them at all.

These tests run the launchers as real subprocesses from an unrelated working
directory with a scrubbed environment, because that is the only way to prove
the bootstrap works — importing them in-process would find `deadweight` on
the test runner's own sys.path and prove nothing.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")


def transcript(*usages):
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for total in usages:
        fh.write(json.dumps({"message": {"usage": {"input_tokens": total}}}) + "\n")
    fh.close()
    return fh.name


class LauncherTestCase(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")
        self.elsewhere = tempfile.mkdtemp()

    def launch(self, script, payload):
        """Run a launcher the way a plugin would: from an unrelated directory,
        with nothing on PYTHONPATH pointing at this checkout."""
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["DEADWEIGHT_CORPUS"] = self.corpus
        done = subprocess.run([sys.executable, os.path.join(HOOKS, script)],
                              input=json.dumps(payload), cwd=self.elsewhere,
                              env=env, text=True, capture_output=True)
        return done


class UserPromptSubmitLauncher(LauncherTestCase):

    def test_it_reports_the_figure_without_a_pythonpath(self):
        path = transcript(40_000, 190_000)
        self.addCleanup(os.unlink, path)

        done = self.launch("deadweight_user_prompt_submit.py",
                           {"transcript_path": path, "session_id": "s1",
                            "cwd": "/tmp/p"})

        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("190,000", json.loads(done.stdout)["systemMessage"])

    def test_it_appends_the_turn_record(self):
        path = transcript(190_000)
        self.addCleanup(os.unlink, path)

        self.launch("deadweight_user_prompt_submit.py",
                    {"transcript_path": path, "session_id": "s1", "cwd": "/tmp/p"})

        with open(self.corpus) as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(records[0]["type"], "turn")


class StopLauncher(LauncherTestCase):

    def test_it_decides_without_a_pythonpath(self):
        path = transcript(20_000, 190_000)
        self.addCleanup(os.unlink, path)

        done = self.launch("deadweight_stop.py",
                           {"transcript_path": path, "session_id": "s1"})

        self.assertEqual(done.returncode, 0, done.stderr)
        decision = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")


class NeverBreaksTheTurn(LauncherTestCase):
    """Design §8. A launcher is one more place the tool can cost a turn."""

    def test_malformed_stdin_still_exits_zero(self):
        for script in ("deadweight_user_prompt_submit.py", "deadweight_stop.py"):
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            done = subprocess.run([sys.executable, os.path.join(HOOKS, script)],
                                  input="{not json", cwd=self.elsewhere, env=env,
                                  text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, script)


if __name__ == "__main__":
    unittest.main()
