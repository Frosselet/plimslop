"""The pre-flight logging command: record that the gate was evaluated.

    python3 -m plimslop.preflight --shape originating --tokens 190000 \\
        --decision proceed [--session ID] [--note ...]

Design §7. Logging the override is the point of this record: *a gate whose
circumvention nobody can measure is a gate that will be circumvented*, and the
override rate is the honest measure of whether the tiers are usable at all. At
90% the tiers are wrong, not the user.

**It does not take the caller's word for the decision.** A session that
declares `proceed` while over the floor for its declared shape has overridden
the gate, whatever it chose to call it, and the record says `overridden` with
the declared value kept beside it. A model can rationalise its way past a
threshold; it cannot rationalise the arithmetic out of the log.

**Nor for the figure** (R141). `--tokens` is whatever the caller typed, so the
floor is compared against a MEASURED `working` figure -- tokens above the
session baseline, compaction added back -- recovered from the latest `turn`
record for this project, which the UserPromptSubmit hook writes from the
transcript. `--tokens` is recorded verbatim as `declared_tokens` and, when a
measurement exists, is advisory. The `tokens` key keeps exactly the meaning it
has always had, because the ruling's own falsification test needs the pre- and
post-change corpus to be scored the same way. See
docs/superpowers/specs/2026-08-26-r141-working-tokens-design.md §3.
"""

import argparse
import os
import sys

from plimslop.corpus import append, default_path, read
from plimslop.tiers import FLOORS


def main(argv=None, stdout=sys.stdout, corpus_path=None, cwd=None):
    """Record one pre-flight decision. Returns an exit code."""
    args = _parse(argv if argv is not None else sys.argv[1:])
    project = cwd or os.getcwd()
    path = corpus_path if corpus_path is not None else default_path()

    if args.shape not in ("originating", "executing", "mechanical"):
        stdout.write("unknown shape: %s (try originating, executing or "
                     "mechanical)\n" % args.shape)
        return 2

    corpus = read(path)
    session, source = _session(args.session, project, corpus)
    measured = _measure(session, project, corpus)

    floor = FLOORS.get(args.shape)                  # mechanical is ungated
    figure = args.tokens if measured is None else measured["working"]
    over = floor is not None and figure >= floor
    decision = "overridden" if (over and args.decision == "proceed") else args.decision

    record = {"type": "preflight", "shape": args.shape, "tokens": args.tokens,
              "declared_tokens": args.tokens,
              "floor": floor, "decision": decision, "declared": args.decision,
              "session": session, "session_source": source,
              "measured": measured is not None,
              "measured_tokens": measured and measured["tokens"],
              "baseline": measured and measured["baseline"],
              "working": measured and measured["working"],
              "project": project, "note": args.note}

    try:
        append(record, path)
    except OSError as failure:
        stdout.write("pre-flight NOT RECORDED (%s)\n" % failure)
        return 1
    stdout.write(_summary(record, over) + "\n")
    return 0


def _session(given, project, corpus):
    """Which session this decision belongs to. A pre-flight record that cannot
    be tied to a session cannot contribute to a rate, so an unnamed one falls
    back to the latest turn seen in this project — and says it inferred that."""
    if given:
        return given, "given"
    turns = sorted((r for r in corpus
                    if r.get("type") == "turn" and r.get("project") == project),
                   key=lambda r: r.get("ts") or "")
    if not turns:
        return None, "unknown"
    return turns[-1].get("session"), "inferred"


def _measure(session, project, corpus):
    """What the transcript said, via the latest `turn` record.

    Returns None when nothing has been measured for this project -- an
    unmeasured gate falls back to the declared figure rather than inventing a
    baseline of zero, which would read every session as fully worked.
    """
    turns = [r for r in corpus
             if r.get("type") == "turn"
             and (r.get("session") == session if session else True)
             and r.get("project") == project
             and isinstance(r.get("baseline"), int)]
    if not turns:
        return None
    latest = max(turns, key=lambda r: r.get("ts") or "")
    tokens = latest.get("tokens") or 0
    baseline = latest.get("baseline") or 0
    dropped = latest.get("dropped") or 0
    return {"tokens": tokens, "baseline": baseline,
            "working": max(0, tokens + dropped - baseline)}


def _summary(record, over):
    """Said out loud, because at this stage visibility is the enforcement. A
    threshold can be crossed silently; a shape and a figure stated together
    cannot."""
    if record["measured"]:
        figure = "%s working tokens" % format(record["working"], ",")
    else:
        figure = "%s tokens (unmeasured — no turn recorded for this project)" % (
            format(record["tokens"], ","))

    if record["decision"] == "overridden":
        return ("pre-flight: %s at %s — OVERRIDE, past the %s floor. "
                "Logged." % (record["shape"], figure,
                             format(record["floor"], ",")))
    if over:
        return ("pre-flight: %s at %s — over the %s floor, %s. Logged."
                % (record["shape"], figure, format(record["floor"], ","),
                   record["decision"]))
    return "pre-flight: %s at %s — under the floor, %s. Logged." % (
        record["shape"], figure, record["decision"])


def _parse(argv):
    parser = argparse.ArgumentParser(prog="plimslop.preflight")
    parser.add_argument("--shape", required=True,
                        help="originating, executing or mechanical")
    parser.add_argument("--tokens", required=True, type=int,
                        help="the figure you believe this session is at; "
                             "advisory — the gate measures the session itself "
                             "when a turn has been recorded for this project")
    parser.add_argument("--decision", required=True,
                        help="proceed, handoff or stop — 'proceed' over a "
                             "floor is recorded as overridden")
    parser.add_argument("--session", default=None,
                        help="session id; inferred from the latest turn if omitted")
    parser.add_argument("--note", default=None, help="why")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
