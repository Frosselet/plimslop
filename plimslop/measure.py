"""Read a session's context state out of a Claude Code transcript.

The figure that matters is absolute: input_tokens + cache_read_input_tokens +
cache_creation_input_tokens, as reported by the API for the most recent turn.

What the floor is compared against is `working` -- that figure MINUS the
session baseline, plus whatever compaction has discarded. See
docs/superpowers/specs/2026-08-26-r141-working-tokens-design.md.
"""

import json


class Session:
    """What a transcript says about the context state of one session."""

    def __init__(self, tokens, baseline, compacted=False, dropped=0):
        self.tokens = tokens
        self.baseline = baseline
        self.compacted = compacted
        self.dropped = dropped

    @property
    def working(self):
        """Work accumulated ABOVE the baseline -- the unit the floor is
        denominated in (iladub ruling 2026-08-26 §3).

        `dropped` is added back because a compaction lowers `tokens` without
        undoing the reasoning already spent. Both `preTokens` and `postTokens`
        include the baseline, so it cancels in their difference and this
        correction is exact rather than approximate: `working` is CONTINUOUS
        across a compaction boundary, which is the whole requirement.

        Clamped at 0, matching the status-line gauge. A missing transcript
        degrades to `baseline = 0`, which reports `working == tokens` -- wrong
        in the conservative direction.
        """
        return max(0, self.tokens + self.dropped - self.baseline)


def _usage_of(line):
    """The usage dict on this JSONL line, or None."""
    if '"usage"' not in line:
        return None
    try:
        message = json.loads(line).get("message") or {}
    except (ValueError, AttributeError):
        return None
    usage = message.get("usage")
    return usage if isinstance(usage, dict) else None


def _compaction_of(line):
    """The compactMetadata on this line if it is a compaction record, else None.

    Shape verified against live transcripts 2026-08-15: a compaction writes
    {"type": "system", "subtype": "compact_boundary", "compactMetadata": {...}}.
    """
    if '"compact_boundary"' not in line:
        return None
    try:
        record = json.loads(line)
    except (ValueError, AttributeError):
        return None
    if not isinstance(record, dict) or record.get("subtype") != "compact_boundary":
        return None
    meta = record.get("compactMetadata")
    return meta if isinstance(meta, dict) else {}


def _dropped_at(meta):
    """How much WORK this one boundary discarded.

    Derived from the preTokens/postTokens pair, never from the field named
    `cumulativeDroppedTokens`. Measured 2026-08-26 over every compaction in
    ~/.claude/projects: the field equals `preTokens - postTokens` in 5 of 5,
    and NO transcript has ever compacted twice -- so "cumulative" rests on the
    name alone. Per-boundary differences are disjoint, so summing them is
    correct whether the field accumulates or not, and the untested premise is
    removed rather than guarded.

    Returns (paired, field): the pair's own difference, and whatever the field
    claims. `read_session` reconciles them -- the field remains the only source
    for a record that omits the pair.
    """
    pre, post = meta.get("preTokens"), meta.get("postTokens")
    paired = max(0, pre - post) if isinstance(pre, int) and isinstance(post, int) else 0
    field = meta.get("cumulativeDroppedTokens", 0)
    return paired, (field if isinstance(field, int) else 0)


def _total(usage):
    return (usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0))


def read_session(path):
    """Session state derived from the transcript at `path`."""
    first = last = None
    paired_sum = 0          # per-boundary differences, summed
    field_latest = 0        # cumulativeDroppedTokens, latest wins
    compacted = False
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                meta = _compaction_of(line)
                if meta is not None:
                    compacted = True
                    paired, field = _dropped_at(meta)
                    paired_sum += paired
                    field_latest = field or field_latest
                    continue
                usage = _usage_of(line)
                if usage is None:
                    continue
                if first is None:
                    first = usage
                last = usage
    except OSError:
        # Missing, unreadable, or not a file. Never the reason a turn fails.
        return Session(tokens=0, baseline=0)
    # Both are lower bounds on the work discarded, and the larger is correct
    # under every reading: if the field really accumulates the two agree; if it
    # is per-boundary despite its name the sum is right and the field
    # undercounts; and a record without the pair leaves only the field.
    return Session(tokens=_total(last) if last else 0,
                   baseline=_total(first) if first else 0,
                   compacted=compacted,
                   dropped=max(paired_sum, field_latest))
