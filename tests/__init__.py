"""Test package init — redirects the corpus before any test can reach it.

`plimslop.corpus.default_path()` reads `PLIMSLOP_CORPUS` at call time, so
setting it here, once, covers every test and every subprocess they spawn:
anything that forgets to pass an explicit path writes to a throwaway file
instead of the user's real corpus.

This exists because the suite was found to have written 15 fabricated turn
records into the live corpus. The guard is asserted by
`test_corpus_isolation.py` so it cannot be quietly removed.
"""

import os
import tempfile

os.environ["PLIMSLOP_CORPUS"] = os.path.join(
    tempfile.mkdtemp(prefix="plimslop-tests-"), "corpus.jsonl")
