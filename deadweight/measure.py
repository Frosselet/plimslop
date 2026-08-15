"""Read a session's context state out of a Claude Code transcript.

The figure that matters is absolute: input_tokens + cache_read_input_tokens +
cache_creation_input_tokens, as reported by the API for the most recent turn.
"""

import json


class Session:
    """What a transcript says about the context state of one session."""

    def __init__(self, tokens, baseline, compacted=False, dropped=0):
        self.tokens = tokens
        self.baseline = baseline
        self.compacted = compacted
        self.dropped = dropped


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


def _total(usage):
    return (usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0))


def read_session(path):
    """Session state derived from the transcript at `path`."""
    first = last = None
    dropped = 0
    compacted = False
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                meta = _compaction_of(line)
                if meta is not None:
                    compacted = True
                    # cumulativeDroppedTokens is a running total, latest wins.
                    dropped = meta.get("cumulativeDroppedTokens", dropped)
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
    return Session(tokens=_total(last) if last else 0,
                   baseline=_total(first) if first else 0,
                   compacted=compacted,
                   dropped=dropped)
