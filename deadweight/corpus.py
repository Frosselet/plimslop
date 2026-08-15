"""The append-only local corpus.

Local only, never transmitted. It records project paths, filenames and work
patterns, which is exactly why it does not leave the machine.
"""

import json
import os
import time


def default_path():
    """Where the corpus lives when nothing overrides it."""
    return os.path.expanduser(
        os.environ.get("DEADWEIGHT_CORPUS", "~/.claude/deadweight/corpus.jsonl"))


def append(record, path=None):
    """Append one record, stamping it with the time it was written."""
    path = path or default_path()
    record = dict(record)
    record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
