"""The README must not document a control that the code does not read.

Found 2026-08-15: README told the reader to set `DEADWEIGHT_MODE_ORIGINATING=warn`
to soften the Stop gate, a leftover from the `deadweight` -> `plimslop` rename.
`stop.py` has always read `PLIMSLOP_MODE_<SHAPE>`, so the documented variable did
nothing at all — and its failure was silent in the worst direction: the gate the
reader was trying to soften stayed in `block`, with no message saying the setting
had been ignored.

A gate that cannot be softened by its own documented escape hatch is a gate that
gets uninstalled instead. That is the same failure the project already knows in
another form (`stop.py` `_raised_before`: a warning every turn gets the hook
disabled, and a disabled hook measures nothing) — over-blocking and over-speaking
both end with the tool switched off.

These tests are cheap and dumb on purpose: they compare strings in prose against
strings in code, which is the drift no reviewer reliably catches by reading.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class TheDocsNameTheVariablesTheCodeReads(unittest.TestCase):

    def test_the_mode_prefix_in_the_readme_matches_stop_py(self):
        prefix = re.search(r'os\.environ\.get\(\s*"([A-Z_]*MODE_)"',
                           _read("plimslop", "stop.py"))
        self.assertIsNotNone(prefix, "stop.py no longer builds a MODE_ env name "
                                     "the way this test assumes; update the test")
        prefix = prefix.group(1)

        readme = _read("README.md")

        # Score the INSTRUCTION, not the name. An earlier version of this test
        # exempted any name the README explained anywhere — and because the
        # README explains the historical name once, that exempted it everywhere,
        # including where it was still being handed out as an instruction. The
        # test then passed with the bug reintroduced, which is a test that pins
        # nothing. Exemptions keyed on a name do not scope to an occurrence.
        instructed = re.findall(r"Set +`([A-Z][A-Z0-9_]*_MODE_[A-Z]+)", readme)
        self.assertTrue(instructed,
                        "README instructs no MODE_ variable at all; if the "
                        "wording changed, update this pattern rather than "
                        "letting the guard go quiet")

        wrong = {name for name in instructed if not name.startswith(prefix)}
        self.assertEqual(wrong, set(),
                         "README instructs env var(s) the code never reads; "
                         "stop.py reads names starting %r" % prefix)

    def test_the_corpus_env_var_is_named_correctly_wherever_documented(self):
        var = re.search(r'os\.environ\.get\(\s*"([A-Z_]+CORPUS)"',
                        _read("plimslop", "corpus.py")).group(1)
        for doc in ("README.md",):
            for found in re.findall(r"\b([A-Z][A-Z0-9_]*_CORPUS)\b", _read(doc)):
                self.assertEqual(found, var,
                                 "%s documents %s; corpus.py reads %s"
                                 % (doc, found, var))


class TheEntryPointIsRunnable(unittest.TestCase):

    def test_the_launcher_exists_and_is_executable(self):
        launcher = os.path.join(ROOT, "bin", "plimslop")
        self.assertTrue(os.path.exists(launcher), "bin/plimslop is missing")
        self.assertTrue(os.access(launcher, os.X_OK),
                        "bin/plimslop is not executable; chmod +x it")

    def test_the_launcher_dispatches_only_the_three_real_commands(self):
        launcher = _read("bin", "plimslop")
        for cmd in ("preflight", "mark", "reader"):
            self.assertIn(cmd, launcher, "launcher does not dispatch %r" % cmd)
            self.assertTrue(
                os.path.exists(os.path.join(ROOT, "plimslop", cmd + ".py")),
                "launcher dispatches %r but plimslop/%s.py does not exist"
                % (cmd, cmd))

    def test_the_readme_does_not_tell_anyone_to_glob_the_plugin_cache(self):
        """The globbing alias pinned whichever version sorted last, so a session
        could log against a frozen copy while its author edited a checkout."""
        readme = _read("README.md")
        for line in readme.splitlines():
            if line.strip().startswith(("export ", "alias ")) and "cache/plimslop" in line:
                self.fail("README still hands out a cache-globbing alias: %s" % line.strip())


if __name__ == "__main__":
    unittest.main()
