"""The reader: four views over the corpus.

    python3 -m plimslop.reader curve | baseline | tiers | override

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

from plimslop.corpus import default_path, read
from plimslop.tiers import FLOORS

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

    view = {"curve": _curve, "baseline": _baseline, "tiers": _tiers,
            "override": _override}.get(args.view)
    if view is None:
        stdout.write("unknown view: %s (try curve, baseline, tiers or "
                     "override)\n" % args.view)
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


def _override(records):
    """How often the gate fired, and how often it was proceeded past anyway.

    THE DEFINITION IS RECOVERED, NOT CHOSEN. The 2026-08-26 audit reported
    54.2% overall (39/72) and 52.2% iladub-only (35/67). Scoring the corpus
    truncated to the 681 lines it saw:

        all/gated     39/118 = 33.1%
        all/overfloor 39/72  = 54.2%   <- reproduces
        all/allpf     39/149 = 26.2%

    so the denominator is records that TRIPPED their floor, not all gated
    records. Both headline figures reproduce exactly. Design §5.

    Two units are scored over the same records. The working unit is available
    for records written before R141 by joining to the session's `turn` record
    -- measured 152 of 152 in the live corpus -- without which the ruling's
    prediction would have no pre-change side to compare against.

    Overriddenness is RECOMPUTED from `declared`, never read from the stored
    `decision` field. It has to be: that field was written by comparing the
    caller's figure to the floor under the OLD unit, so reusing it would score
    the working unit with the total unit's answer. The cost is that the total
    unit reads 38/74 here where the audit reported 39/72 -- 9 corpus lines have
    been added since, and 2 records carry `declared: null`. The recomputation
    is the like-for-like one; see the design §5.
    """
    preflights = [r for r in records if r.get("type") == "preflight"]
    if not preflights:
        return "override — the corpus is empty. Nothing has been measured yet."

    baselines = {}
    for record in records:
        if record.get("type") == "turn" and isinstance(record.get("baseline"), int):
            baselines.setdefault(record.get("session"), record["baseline"])

    lines = ["override — how often the gate fired, and how often it was passed", ""]
    for unit in ("total", "working"):
        lines.append("  %s" % _rate_line(unit, preflights, baselines))

    lines += ["",
              "  Splitting the working unit by when the record was written, because",
              "  re-scoring old decisions is NOT the same claim as observing new ones:"]
    before = [r for r in preflights if not r.get("measured")]
    after = [r for r in preflights if r.get("measured")]
    lines.append("    counterfactual (written before R141)  %s"
                 % _rate_line("working", before, baselines, bare=True))
    lines.append("    observed       (written after R141)   %s"
                 % _rate_line("working", after, baselines, bare=True))

    lines += ["",
              "  PREDICTION under test (ruling §5): the observed rate falls materially",
              "  below 54%. If it stays flat, the unit was never the problem and the",
              "  ruling is refuted by its own instrument.",
              "  A `stop` decision counts as compliance, as the 54% figure counted it.",
              "  Thresholds: state a rate at n>=%d — PROPOSED, not settled." % N_REPORT]
    return "\n".join(lines)


def _rate_line(unit, preflights, baselines, bare=False):
    """One unit's rate, or a refusal. The refusal is the point of the reader."""
    fired = [r for r in preflights if _fired(r, unit, baselines)]
    label = "" if bare else "%-8s " % unit
    if len(fired) < N_REPORT:
        if not fired:
            return "%sthe gate never fired in this unit (n=%d) — this shows nothing" % (
                label, len(preflights))
        return "%sn=%d — this shows nothing" % (label, len(fired))
    overridden = [r for r in fired if r.get("declared") == "proceed"]
    return "%s%d/%d = %.0f%% overridden" % (
        label, len(overridden), len(fired), 100.0 * len(overridden) / len(fired))


def _fired(record, unit, baselines):
    """Whether the gate tripped for this record, in this unit."""
    floor = FLOORS.get(record.get("shape"))
    if floor is None:
        return False                        # mechanical is ungated
    figure = _figure(record, unit, baselines)
    return figure is not None and figure >= floor


def _figure(record, unit, baselines):
    """The number this record is scored on.

    `tokens` keeps the meaning it has always had — the caller's declared
    figure — so the total unit is computed the same way on both sides of the
    change. `measured_tokens` is preferred where it exists because it is the
    same quantity, measured rather than typed.
    """
    if unit == "total":
        measured = record.get("measured_tokens")
        return measured if isinstance(measured, int) else record.get("tokens")
    working = record.get("working")
    if isinstance(working, int):
        return working
    tokens = record.get("tokens")
    baseline = baselines.get(record.get("session"))
    if not isinstance(tokens, int) or not isinstance(baseline, int):
        return None                         # unjoinable: scored in neither
    return max(0, tokens - baseline)


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
                      "  Since R141 the floor is compared against work ABOVE the baseline,",
                      "  so this no longer makes the gate unsatisfiable — it costs window,",
                      "  not allowance. Reducing it is worth doing; it is not urgent."]
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
    parser = argparse.ArgumentParser(prog="plimslop.reader")
    parser.add_argument("view", help="curve, baseline, tiers or override")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
