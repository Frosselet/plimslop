"""UserPromptSubmit hook: measure the session, publish state, record the turn.

Wire it up in `~/.claude/settings.json`:

    "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
      "command": "python3 -m deadweight.hook 2>/dev/null || true"}]}]}

The `|| true` is belt and braces. This module already refuses to fail: every
error path returns 0 and the turn proceeds. A context tool that costs you a
turn is worse than no context tool.
"""

import json
import os
import sys

from deadweight.corpus import append, default_path
from deadweight.measure import read_session
from deadweight.report import build_output

#: Display only. No decision anywhere reads the percentage this produces.
WINDOW = int(os.environ.get("CLAUDE_CONTEXT_WINDOW", "1000000"))


def main(stdin=sys.stdin, stdout=sys.stdout, corpus_path=None, window=WINDOW):
    """Read the hook payload, emit state, append the turn record. Always 0."""
    try:
        payload = json.load(stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    transcript = payload.get("transcript_path")
    if not transcript:
        return 0                                   # first turn of a session

    session = read_session(transcript)
    if session.tokens == 0:
        return 0                                   # nothing measured yet

    _record(session, payload, corpus_path)

    try:
        json.dump(build_output(session, window), stdout)
    except (TypeError, ValueError, OSError):
        return 0
    return 0


def _record(session, payload, corpus_path):
    """Append the turn record. A corpus we cannot write is a lost record,
    never a lost turn, so this swallows everything."""
    try:
        append({"type": "turn",
                "session": payload.get("session_id"),
                "project": payload.get("cwd"),
                "tokens": session.tokens,
                "baseline": session.baseline,
                "compacted": session.compacted,
                "dropped": session.dropped},
               corpus_path if corpus_path is not None else default_path())
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
