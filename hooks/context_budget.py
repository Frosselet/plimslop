#!/usr/bin/env python3
"""Report context-window usage at the start of each turn, and warn past the thresholds.

Enforces the rule recorded as R76 in `docs/superpowers/residues.md`: accuracy degrades
well before the window is full, so a loop runs in a fresh session and specs are written
early. Self-monitoring is the thing that fails first, so this runs as a hook — the
harness executes it regardless of how tired the model is.

Reads the hook payload on stdin (`transcript_path`), takes the LAST recorded usage in
that transcript, and reports

    context = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

against the window. That is the real per-turn figure the API reports, not a proxy.

Measured on the session that produced this rule (2026-08-09): 93% used, 40% crossed at
turn 222 of 763 — so 71% of the session ran past the threshold, and it is the later part
that produced five blocked specs while the early part shipped a loop.
"""
import json
import os
import sys

WINDOW = int(os.environ.get("CLAUDE_CONTEXT_WINDOW", "1000000"))
HANDOFF_PCT = 30      # write/refresh the loop handoff while still accurate
STOP_PCT = 40         # finish the step, hand off, start a fresh session


def last_usage(path: str):
    """The most recent usage record in the transcript, or None."""
    found = None
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    msg = json.loads(line).get("message") or {}
                except (ValueError, AttributeError):
                    continue
                u = msg.get("usage")
                if isinstance(u, dict):
                    found = u
    except OSError:
        return None
    return found


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0                                  # never break the turn
    path = payload.get("transcript_path")
    if not path or not os.path.exists(path):
        return 0                                  # first turn of a session

    u = last_usage(path)
    if not u:
        return 0
    used = (u.get("input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0))
    pct = 100.0 * used / WINDOW

    if pct < HANDOFF_PCT:
        return 0                                  # silent below the handoff mark

    if pct < STOP_PCT:
        note = (f"CONTEXT {pct:.0f}% ({used:,} tokens). Past the {HANDOFF_PCT}% handoff mark: "
                "refresh the loop handoff memory NOW, while still accurate. Do not defer it "
                "to the end of the session — that is when it gets written badly.")
    else:
        note = (f"CONTEXT {pct:.0f}% ({used:,} tokens). THRESHOLD EXCEEDED "
                f"(limit {STOP_PCT}%). Finish the current step, make sure the loop handoff "
                "is written, and tell the user to start a fresh session. Do NOT begin new "
                "design work, and do not write or revise a spec — accuracy past this mark is "
                "measurably worse (R76).")

    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                      "additionalContext": note},
               "systemMessage": f"context {pct:.0f}%"}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
