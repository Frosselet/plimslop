# plimslop

*Know what your context is actually costing you, and what it is costing you for nothing.*

**Status: complete as designed — skill, both hooks, corpus, marker command, reader, plugin
packaging. Not validated.** It installs and runs; a corpus is accumulating on the
author's machine as of 2026-08-15, which means there is not yet enough of it to argue with any
floor. The design is complete and reviewed:
[`docs/superpowers/specs/2026-08-15-context-budget-skill-design.md`](docs/superpowers/specs/2026-08-15-context-budget-skill-design.md).

---

## What it is

A skill, two hooks, and a local evidence corpus that keep a coding-agent session honest about its
own context budget:

- **A skill** — the procedure. A pre-flight check gated on *task shape*, and a handoff protocol.
  This is the product. A resumption protocol was written, tested, and **cut** — unguided sessions
  passed it 4 times out of 4, so it was not worth the tokens.
- **Two hooks** — `UserPromptSubmit` measures and publishes the figure; `Stop` enforces, at a
  strength you configure per tier.
- **A corpus** — append-only, local, never transmitted. Records what your context cost and what got
  reworked, so the thresholds can eventually be argued with instead of inherited.

## Installing

plimslop is packaged as a Claude Code plugin: the skill and both hooks install together, and the
hook commands resolve their own location through `${CLAUDE_PLUGIN_ROOT}`, so there is no path to
edit by hand.

```
/plugin marketplace add Frosselet/plimslop
/plugin install plimslop@plimslop
```

Or from a local checkout, which is how the packaging was first verified:

```
claude plugin marketplace add /path/to/plimslop
claude plugin install plimslop@plimslop
claude plugin details plimslop@plimslop     # 1 skill, 2 hooks
```

Two things worth knowing before you do that:

- **A local install is a copy, not a link.** The plugin cache holds a frozen `0.1.0/`, so edits to
  your checkout do not reach the installed plugin. For developing the skill itself, symlink
  `skills/managing-context-budget` into `~/.claude/skills/` instead and wire the hooks by hand.
- **The `Stop` gate ships in `block` mode for originating work**, per §9 — that tier is the one
  with literature behind it. Set `DEADWEIGHT_MODE_ORIGINATING=warn` (or `off`) in your settings
  `env` to soften it. The session is spoken to at most once either way.

## Reading the corpus

```
python3 -m plimslop.reader curve      # rework against tokens at production
python3 -m plimslop.reader baseline   # what is in the window before you type
python3 -m plimslop.reader tiers      # the floors, and what the corpus can say
```

**Expect it to refuse.** Below a stated *n* it prints the count and declines to state a rate at
all — `n=3 — this shows nothing` — and comparing two bands takes more data than stating one rate.
Both thresholds are printed on every run and labelled `PROPOSED`, because no power calculation
stands behind either yet. A floor is demoted only on an equivalence bound, never on a failure to
find a difference: otherwise a thin corpus demotes a floor by being underpowered, which is exactly
the error that produced the rule this project replaces.

## Marking rework

The corpus only becomes evidence if the rework half of it gets written. When you find work that had
to be redone, mark it — at the moment you discover it, not when it was produced:

```
python3 -m plimslop.mark plimslop/parser.py --note "rewritten from scratch"
python3 -m plimslop.mark "plimslop/parser.py:40-58"     # blame the hunk, not the file
python3 -m plimslop.mark "the retry approach I abandoned" # no artefact: still recorded
python3 -m plimslop.mark README.md --session <session-id> # or --commit <sha>
```

It maps the target back to the turn that produced it — `git blame` for the commit, the turn records
for the session that was running when that commit's work was done. Every marker prints what it
attached to, and says `inferred` when the mapping was made from timestamps rather than named
outright. Markers it cannot attribute are **recorded as unattributed, never dropped**: the
unattributed fraction is how you tell a thin corpus from a solid one.

## Why `plimslop`

In 1876 Parliament made it a crime to load a British ship past a line painted on her hull. The man
who spent a decade shouting about it was Samuel Plimsoll, and the vessels he was shouting about
were *coffin ships*: overloaded, over-insured, and worth more to their owners on the seabed than at
the far end of the voyage. The crews were worth nothing to anybody in either case, so they drowned
on schedule.

The fix was not a rule about seamanship. Nobody asked the captain to search his feelings and report
whether he felt seaworthy — a judgment that gets less reliable in precise proportion to how much
water is coming aboard. The fix was **a mark on the outside of the hull**, where the harbourmaster
could read it from the quay, in the rain, without asking anyone's opinion.

An agent forty turns into a long session is a ship riding low. It does not feel overloaded. It
reports excellent visibility, cites the file it read this morning with total confidence, and gets
one clause of it backwards. What comes off the deck at that point is **slop** — and slop is a cargo
problem with a load-line cause.

Hence: **plimsoll + slop = `plimslop`.** The load line for the stuff you would rather not ship.

The metaphor also fixes the thing a quality checker gets wrong. **A Plimsoll line never inspects
the cargo.** It does not care whether the hold is full of grain, coal or pig iron, and it does not
grade the workmanship of the stevedores. It cares how deep you are sitting. `plimslop` measures the
water, not the goods: it will never tell you your work is bad — it cannot know — only that you are
riding low enough that it might be, and that an empty hull is cheap and close.

*(The line is also why British children do PE in plimsolls. The rubber band around a canvas shoe sat
at just the height where, if the water got above it, you were wet. Same joke, smaller vessel.)*

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

plimslop denominates in absolute tokens, ships every number with the evidence grade that supports
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

plimslop was extracted from a private working repository where the problem was first recorded.
That repository is now a consumer like any other, and nothing here depends on it — see § Provenance
in the design document for the three inherited ideas and what they were called.

## What is in the tree today

| path | what it is |
| --- | --- |
| `LICENSE` | Apache-2.0, canonical text. See § Licensing for the prose split |
| `HANDOFF.md` | **current state — read this first.** Where things stand, what is unverified, what is next |
| `BRIEF.md` | history: the originating handoff, plus the naming check and prior-art sweep |
| `plimslop/` | the code — two hooks, measurement, tiers, corpus, the marker command, the reader. 89 tests |
| `tests/` | `python3 -m unittest discover -s tests -t .` |
| `docs/unreviewed/` | quarantined, unapproved material. See `HANDOFF.md` §4 |
| `docs/superpowers/specs/…-design.md` | the design, approved section by section |
| `skills/managing-context-budget/SKILL.md` | **the skill.** Two procedures: pre-flight and handoff |
| `skills/managing-context-budget/TESTS.md` | the pressure scenarios it was written against, and their results |
| `.claude-plugin/` | plugin and marketplace manifests. Both validate against `claude plugin validate` |
| `hooks/` | `hooks.json` plus the two launchers the plugin invokes. They locate the package relative to themselves, so no `PYTHONPATH` is needed |

## Licensing

Copyright 2026 Francois Rosselet.

**Code is Apache-2.0** — see [`LICENSE`](LICENSE), verbatim canonical text.

**Prose is CC-BY-4.0**: `skills/`, `docs/`, `README.md`, `BRIEF.md`, `HANDOFF.md`. The split
follows the convention already used in the repository this was extracted from — the skill text is
vocabulary and procedure, read by people and models rather than executed.

## Open

The reader's minimum *n* is not yet chosen.
