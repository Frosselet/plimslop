"""Stop hook: enforcement at the turn boundary.

Wire it up in `~/.claude/settings.json`:

    "hooks": {"Stop": [{"hooks": [{"type": "command",
      "command": "python3 -m deadweight.stop 2>/dev/null || true"}]}]}

This fires at the END of a turn, so it catches you having crossed a floor, not
about to. The skill's say-it-out-loud step is the only thing acting before work
starts, and it stays soft. The two are complements.

Three constraints, all load-bearing (design §9):

- **One-step override.** A session is blocked at most once. A block you cannot
  pass in a single step gets the hook disabled wholesale, and then nothing is
  measured at all. The override is recorded, because an override nobody can
  count is a gate nobody can evaluate.
- **Never block into an unsatisfiable state.** If the baseline alone exceeds
  the floor, blocking would refuse every turn from the first one.
- **Never block a subagent.** Its context is separate; delegation is the
  remedy, not the offence.

Payload fields and the decision schema were verified against the hooks
reference on 2026-08-15. Note that `stop_hook_active` is NOT documented for
Stop, which is why the loop guard is the corpus rather than that flag.
"""

import json
import os
import sys

from deadweight.corpus import append, default_path, read
from deadweight.measure import read_session
from deadweight.report import SKILL
from deadweight.tiers import LOWEST_FLOOR

#: Enforcement strength tracks evidence grade. `originating` is literature
#: anchored, so it blocks; `executing` rests on nothing, so it must not.
DEFAULT_MODES = {"originating": "block", "executing": "warn", "mechanical": "off"}


def _modes(overrides=None):
    modes = dict(DEFAULT_MODES)
    for shape in modes:
        env = os.environ.get("DEADWEIGHT_MODE_" + shape.upper())
        if env in ("block", "warn", "off"):
            modes[shape] = env
    modes.update(overrides or {})
    return modes


def decide(session, blocked_before, is_subagent, modes):
    """Return (action, reason). Action is 'allow', 'warn' or 'block'."""
    if is_subagent:
        return "allow", ""
    if session.tokens < LOWEST_FLOOR:
        return "allow", ""

    over = (f"This session is at {session.tokens:,} absolute tokens, past the "
            f"{LOWEST_FLOOR:,} originating floor. Invoke the {SKILL} skill: name "
            "the shape of what you are about to do, and if it is originating "
            "work, write the handoff instead of starting it.")

    if session.baseline >= LOWEST_FLOOR:
        return "warn", (
            f"Baseline is {session.baseline:,} tokens, already at or above the "
            f"{LOWEST_FLOOR:,} originating floor before any conversation. The gate "
            "cannot be satisfied in this configuration, so it is not enforced. "
            "Reduce the baseline or revise the tier.")

    if blocked_before:
        return "warn", over + " (Already raised once this session; not blocking again.)"

    mode = modes.get("originating", "block")
    if mode == "off":
        return "allow", ""
    if mode == "warn":
        return "warn", over
    return "block", over


def main(stdin=sys.stdin, stdout=sys.stdout, corpus_path=None, modes=None):
    """Read the Stop payload, decide, emit. Always 0 — blocking is done with
    the decision schema, never with a non-zero exit."""
    try:
        payload = json.load(stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    transcript = payload.get("transcript_path")
    if not transcript:
        return 0

    session = read_session(transcript)
    if session.tokens == 0:
        return 0

    path = corpus_path if corpus_path is not None else default_path()
    session_id = payload.get("session_id")
    action, reason = decide(session,
                            blocked_before=_blocked_before(path, session_id),
                            is_subagent=bool(payload.get("agent_id")),
                            modes=_modes(modes))

    if action == "allow":
        return 0

    if action == "block":
        _record(path, session_id, session)
        output = {"hookSpecificOutput": {"hookEventName": "Stop",
                                         "permissionDecision": "deny",
                                         "permissionDecisionReason": reason}}
    else:
        output = {"systemMessage": reason}

    try:
        json.dump(output, stdout)
    except (TypeError, ValueError, OSError):
        return 0
    return 0


def _blocked_before(path, session_id):
    """Whether this session has already been blocked once."""
    return any(r.get("type") == "block" and r.get("session") == session_id
               for r in read(path))


def _record(path, session_id, session):
    try:
        append({"type": "block", "session": session_id,
                "tokens": session.tokens, "baseline": session.baseline,
                "floor": LOWEST_FLOOR}, path)
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
