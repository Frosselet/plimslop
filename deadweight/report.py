"""Turn a measured session into what the hook emits.

Two audiences, deliberately separated:

- the human, via `systemMessage` — never enters model context, so it is free
  and may carry the percentage, which is easier to feel than a raw count;
- the model, via `additionalContext` — costs tokens on every turn it appears,
  so it appears only from the lowest floor upward, and it never carries a
  percentage, because a percentage is what makes 190K read as a tolerable 19%.
"""

from deadweight.tiers import FLOORS, LOWEST_FLOOR

SKILL = "managing-context-budget"


def build_output(session, window):
    """The dict the hook writes to stdout for this session."""
    human = f"deadweight {session.tokens:,}"
    if window:
        human += f" ({100.0 * session.tokens / window:.0f}%)"

    if session.tokens < LOWEST_FLOOR and not session.compacted:
        return {"systemMessage": human}

    return {"systemMessage": human,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _for_the_model(session)}}


def _for_the_model(session):
    lines = [f"CONTEXT {session.tokens:,} tokens (absolute).",
             f"Originating floor is {FLOORS['originating']:,}; "
             f"executing floor is {FLOORS['executing']:,}.",
             f"Before starting work, invoke the {SKILL} skill: name the task "
             "shape, compare against its floor, and hand off rather than start "
             "if you are over it."]

    if session.baseline >= LOWEST_FLOOR:
        lines.append(
            f"NOTE: this session's baseline is {session.baseline:,} tokens — "
            f"already at or above the {LOWEST_FLOOR:,} originating floor before "
            "any conversation. You cannot originate in this configuration. "
            "Reduce the baseline (unused MCP servers, CLAUDE.md) or revise the "
            "tier; do not simply proceed.")

    if session.compacted:
        lines.append(
            f"NOTE: this session has been compacted, discarding {session.dropped:,} "
            "tokens of its own history. The token count above is therefore not a "
            "measure of how much work this session has done. Compaction is a "
            "handoff written without the discipline; treat it as a reason to hand "
            "off, not as a reset.")

    return " ".join(lines)
