"""The reader: three views over the corpus.

    python3 -m deadweight.reader curve | baseline | tiers

Design §7. The behaviour that matters most here is the refusal: below a stated
n the reader reports the count and declines to state a rate. The prior rule
this project replaces exists because one session's observation was promoted,
and a tool that will happily draw a confident curve through four points is a
machine for manufacturing more of them.

Two departures from §7, both because the corpus cannot support what it asked
for, and both printed in the output rather than hidden:

- **The denominator is turns in the band, not producing turns.** §7's detailed
  design wanted a turn carrying a successful Write/Edit. Turn records carry no
  tool use, so that number does not exist. Turns overcount the denominator,
  which biases every rate *downward* — the safe direction for a tool whose
  purpose is to avoid overclaiming.
- **The bands are the tier table's own regions** rather than a chosen
  histogram. Anchoring them on the floors avoids inventing another constant,
  and it is the comparison the tiers exist to invite.
"""

import argparse
import sys

from deadweight.corpus import default_path, read
from deadweight.tiers import FLOORS

#: PROPOSED, not settled — see README § Open. n_report is the bar for stating
#: a rate at all; n_trend the bar for comparing two of them, which is a
#: stronger claim and needs more data. Neither is derived from a power
#: calculation, and until one exists these are two numbers somebody chose.
N_REPORT = 20
N_TREND = 50

#: The band a token figure falls in. Anchored on the floors, not invented.
BANDS = [("below 50,000", 0, 50_000),
         ("50,000–150,000", 50_000, 150_000),
         ("150,000 and up", 150_000, None)]


def main(argv=None, stdout=sys.stdout, corpus_path=None):
    args = _parse(argv if argv is not None else sys.argv[1:])
    records = read(corpus_path if corpus_path is not None else default_path())

    view = {"curve": _curve, "baseline": _baseline, "tiers": _tiers}.get(args.view)
    if view is None:
        stdout.write("unknown view: %s (try curve, baseline or tiers)\n" % args.view)
        return 2

    stdout.write(view(records) + "\n")
    return 0


def _curve(records):
    """Rework against tokens at production, stratified by band."""
    turns = [r for r in records if r.get("type") == "turn"]
    rework = [r for r in records if r.get("type") == "rework"]
    if not turns and not rework:
        return "curve — the corpus is empty. Nothing has been measured yet."

    lines = ["curve — rework against tokens at production", "",
             "  %-18s %7s %8s   %s" % ("band", "turns", "rework", "rate")]

    rates = []
    for name, low, high in BANDS:
        in_band = [t for t in turns if _within(t.get("tokens"), low, high)]
        marks = [r for r in rework if _within(r.get("tokens"), low, high)]
        n = len(in_band)
        if n >= N_REPORT:
            rate = 100.0 * len(marks) / n
            verdict = "%.0f%% (n=%d)" % (rate, n)
            rates.append((name, rate, n))
        else:
            verdict = "n=%d — this shows nothing" % n
        lines.append("  %-18s %7d %8d   %s" % (name, n, len(marks), verdict))

    lines += ["", "  " + _comparison(rates), "  " + _attribution(rework), "",
              "  thresholds: state a rate at n>=%d, compare bands at n>=%d — both"
              % (N_REPORT, N_TREND),
              "  PROPOSED, not settled; no power calculation stands behind either.",
              "  Denominator is turns in the band, not producing turns — the corpus",
              "  records no tool use. This biases every rate downward."]
    return "\n".join(lines)


def _comparison(rates):
    """Comparing two rates is a stronger claim than stating one, so it takes
    more data. A thin corpus must not be able to argue with a floor."""
    strong = [r for r in rates if r[2] >= N_TREND]
    if len(strong) < 2:
        return ("comparison: not enough to compare bands — needs n>=%d in two of them"
                % N_TREND)
    strong.sort(key=lambda r: -r[1])
    return "comparison: %s is higher than %s (%.0f%% vs %.0f%%)" % (
        strong[0][0], strong[-1][0], strong[0][1], strong[-1][1])


def _attribution(rework):
    """Unattributed markers are counted and displayed, never dropped: the
    unattributed fraction is a quality measure of the corpus itself."""
    if not rework:
        return "attribution: no rework has been marked yet"
    exact = sum(1 for r in rework if r.get("confidence") == "exact")
    inferred = sum(1 for r in rework if r.get("confidence") == "inferred")
    none = len(rework) - exact - inferred
    return "attribution: %d exact, %d inferred, %d unattributed (%.0f%% of markers)" % (
        exact, inferred, none, 100.0 * none / len(rework))


def _baseline(records):
    """§6. What is in the window before anything is typed."""
    seen = {}
    for record in records:
        if record.get("type") == "turn" and record.get("baseline"):
            seen[record.get("session")] = record["baseline"]
    if not seen:
        return "baseline — the corpus is empty. Nothing has been measured yet."

    figures = sorted(seen.values())
    lines = ["baseline — what is in the window before you type", "",
             "  sessions observed : %d" % len(figures),
             "  lowest            : %s" % format(figures[0], ","),
             "  median            : %s" % format(figures[len(figures) // 2], ","),
             "  highest           : %s" % format(figures[-1], ",")]

    for shape, floor in sorted(FLOORS.items(), key=lambda kv: kv[1]):
        if figures[-1] >= floor:
            lines += ["", "  A baseline of %s exceeds the %s floor of %s."
                      % (format(figures[-1], ","), shape, format(floor, ",")),
                      "  The gate cannot be satisfied in that configuration — reduce the",
                      "  baseline or revise the tier. It is not a reason to refuse all work."]
    return "\n".join(lines)


def _tiers(records):
    """The floors, their grades, and what the corpus can say about each."""
    turns = [r for r in records if r.get("type") == "turn"]
    rework = [r for r in records if r.get("type") == "rework"]

    lines = ["tiers — the floors and what the corpus says about them", "",
             "  originating    50,000   asserted, literature-anchored",
             "  executing     150,000   asserted, NO SOURCE — interpolated",
             "  mechanical     ungated  asserted from 'retrieval survives longer'", ""]

    for name, low, high in BANDS:
        n = len([t for t in turns if _within(t.get("tokens"), low, high)])
        marks = len([r for r in rework if _within(r.get("tokens"), low, high)])
        if n >= N_TREND:
            lines.append("  %-18s n=%-5d rework=%-4d SUPPORTS or CONTRADICTS is now"
                         " arguable" % (name, n, marks))
        else:
            lines.append("  %-18s n=%-5d rework=%-4d CANNOT YET SPEAK" % (name, n, marks))

    lines += ["",
              "  A floor is demoted only on an equivalence bound, never on a failure",
              "  to find a difference — otherwise a thin corpus demotes by being",
              "  underpowered, which is the prior rule's own error inverted."]
    return "\n".join(lines)


def _within(tokens, low, high):
    if not isinstance(tokens, int):
        return False                      # unattributed markers land in no band
    return tokens >= low and (high is None or tokens < high)


def _parse(argv):
    parser = argparse.ArgumentParser(prog="deadweight.reader")
    parser.add_argument("view", help="curve, baseline or tiers")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
