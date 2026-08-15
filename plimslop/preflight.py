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

    floor = FLOORS.get(args.shape)                  # mechanical is ungated
    over = floor is not None and args.tokens >= floor
    decision = "overridden" if (over and args.decision == "proceed") else args.decision

    session, source = _session(args.session, project, read(path))
    record = {"type": "preflight", "shape": args.shape, "tokens": args.tokens,
              "floor": floor, "decision": decision, "declared": args.decision,
              "session": session, "session_source": source,
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


def _summary(record, over):
    """Said out loud, because at this stage visibility is the enforcement. A
    threshold can be crossed silently; a shape and a figure stated together
    cannot."""
    figure = format(record["tokens"], ",")
    if record["decision"] == "overridden":
        return ("pre-flight: %s at %s tokens — OVERRIDE, past the %s floor. "
                "Logged." % (record["shape"], figure,
                             format(record["floor"], ",")))
    if over:
        return ("pre-flight: %s at %s tokens — over the %s floor, %s. Logged."
                % (record["shape"], figure, format(record["floor"], ","),
                   record["decision"]))
    return "pre-flight: %s at %s tokens — under the floor, %s. Logged." % (
        record["shape"], figure, record["decision"])


def _parse(argv):
    parser = argparse.ArgumentParser(prog="plimslop.preflight")
    parser.add_argument("--shape", required=True,
                        help="originating, executing or mechanical")
    parser.add_argument("--tokens", required=True, type=int,
                        help="the absolute figure reported for this session")
    parser.add_argument("--decision", required=True,
                        help="proceed or handoff — 'proceed' over a floor is "
                             "recorded as overridden")
    parser.add_argument("--session", default=None,
                        help="session id; inferred from the latest turn if omitted")
    parser.add_argument("--note", default=None, help="why")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
