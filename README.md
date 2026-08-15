# deadweight

*Know what your context is actually costing you, and what it is costing you for nothing.*

**Status: design stage. Nothing here is implemented yet.** The design is complete and reviewed:
[`docs/superpowers/specs/2026-08-15-context-budget-skill-design.md`](docs/superpowers/specs/2026-08-15-context-budget-skill-design.md).

---

## What it will be

A skill, two hooks, and a local evidence corpus that keep a coding-agent session honest about its
own context budget:

- **A skill** — the procedure. A pre-flight check gated on *task shape*, a handoff protocol, and a
  resumption protocol. This is the product.
- **Two hooks** — `UserPromptSubmit` measures and publishes the figure; `Stop` enforces, at a
  strength you configure per tier.
- **A corpus** — append-only, local, never transmitted. Records what your context cost and what got
  reworked, so the thresholds can eventually be argued with instead of inherited.

## Why it exists

Context-usage status lines for coding agents are a crowded field — over 700 of them. Tools that
watch the window and force a handoff are a smaller field, but a real one. **Every one surveyed
ships a percentage threshold**: end at 60% of the window, checkpoint at 55% and 88%, green/amber/red
zones.

A percentage is the wrong unit, and the error grows with the window. The literature anchors
degradation to *absolute* token counts — NoLiMa found 11 of 13 models below half their baseline at
32K; Chroma found decline beginning immediately rather than at a cliff. So 55% of a 200K window and
55% of a 1M window are not the same claim, and only one of them can be right. On a 1M window a 40%
rule permits 400,000 tokens, which is roughly an order of magnitude past where multi-step reasoning
is already compromised.

deadweight denominates in absolute tokens, ships every number with the evidence grade that supports
it, and builds the corpus that can promote or demote those numbers. **Its distinguishing claim is
negative: it does not ship a threshold it cannot defend.**

Three further things fall out of the design that the survey found nobody shipping:

- **Baseline is measured and reported separately.** Your MCP server schemas, `CLAUDE.md` and tool
  definitions are in the window before you type anything. If that baseline already exceeds a floor,
  the tool says so plainly rather than silently refusing all work.
- **Unused weight is named.** *"14 MCP servers connected, 9 never invoked in 40 sessions"* is a
  thirty-second decision, and it needs no token estimate to be actionable.
- **Auto-compaction does not reset a floor.** Compaction is a lossy summary of the session written
  by the tired session — a handoff with none of the discipline. It changes the number without
  undoing the damage.

## Non-goals

- Not a cost or billing tracker — `ccusage` and others do that well
- **Not a status line.** That field is thoroughly served; see the prior-art sweep in `BRIEF.md`
- Never applies changes to your configuration — it reports, you decide
- Never transmits the corpus anywhere
- **Never claims causality.** The corpus is observational, and the confound is unfixable: late
  sessions genuinely hold harder residual work

## Repository boundary

**This repository owns the skill, the hooks, the corpus format and the reader.** Other repositories
*consume* the skill; none of them host it. The skill and hooks install user-scope (`~/.claude/`) so
they survive branch switches and so a single corpus spans every project.

deadweight was extracted from a private working repository where the problem was first recorded.
That repository is now a consumer like any other, and nothing here depends on it — see § Provenance
in the design document for the three inherited ideas and what they were called.

## What is in the tree today

| path | what it is |
| --- | --- |
| `HANDOFF.md` | **current state — read this first.** Where things stand, what is unverified, what is next |
| `BRIEF.md` | history: the originating handoff, plus the naming check and prior-art sweep |
| `deadweight/` | the code — two hooks, measurement, tiers, corpus. 43 tests |
| `tests/` | `python3 -m unittest discover -s tests -t .` |
| `docs/unreviewed/` | quarantined, unapproved material. See `HANDOFF.md` §4 |
| `docs/superpowers/specs/…-design.md` | the design, approved section by section |
| `skills/managing-context-budget/SKILL.md` | **the skill — written and tested.** The one shipped part that exists |
| `skills/managing-context-budget/TESTS.md` | the pressure scenarios it was written against, and their results |
| `hooks/context_budget.py` | **inherited prototype, unmodified.** Percentage-denominated; superseded by the design. Kept for reference and diffing, not for use |
| `statusline-context-gauge.py` | prototype gauge. **Not to be published** — see the sweep. Personal script only |

## Open

Licensing is undecided. The reader's minimum *n* is not yet chosen. The two forked copies of the
gauge still need reconciling before either is edited.
