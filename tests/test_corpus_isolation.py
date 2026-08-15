"""The suite must never write to the real corpus.

Found the hard way: 15 fabricated `turn` records for session `s1`, project
`/tmp/p`, sitting in the live corpus. `test_entrypoint.py` calls the hook with
`corpus_path=None`, which falls through to `default_path()` — so every run of
the suite was inventing evidence in the file the floors are meant to be argued
from.

A corpus that silently accumulates synthetic records is worse than no corpus:
it produces confident numbers from data nobody put there on purpose, which is
the exact failure this project exists to prevent, committed by its own tests.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimsoll.corpus import default_path


class TheSuiteCannotTouchTheRealCorpus(unittest.TestCase):

    def test_the_default_path_is_redirected_while_testing(self):
        home = os.path.expanduser("~")
        self.assertFalse(default_path().startswith(os.path.join(home, ".claude")),
                         "tests resolve the corpus to %s — a real run would "
                         "write fabricated records there" % default_path())


if __name__ == "__main__":
    unittest.main()
