# HANDOFF — deadweight, 2026-08-15

Written at ~317K tokens, past this project's own originating floor by 6×. Written to the
recipe in `skills/managing-context-budget/SKILL.md` §Handoff, which is also the first real
use of that recipe.

## 1. Goal

Build **deadweight**: a skill, two hooks, and a local evidence corpus that keep a coding-agent
session honest about its own context budget — denominated in absolute tokens, with every number
carrying the evidence grade that supports it.

## 2. Where the primaries are

| primary | what to establish there |
| --- | --- |
| `README.md` | what the project claims to be, and its non-goals. Start here |
| `docs/superpowers/specs/2026-08-15-context-budget-skill-design.md` | the design, approved section by section. §10.1 records what was tested and the limits of that evidence — read it before trusting any number |
| `BRIEF.md` | history only. The originating handoff plus the naming check and prior-art sweep. Its opening status line describes the morning of 2026-08-15, not now |
| `skills/managing-context-budget/SKILL.md` | the shipped skill. Two procedures, not three |
| `skills/managing-context-budget/TESTS.md` | the pressure scenarios and their results. Fixtures are in `tests/fixtures/` |
| `deadweight/` | the code. `measure.py`, `tiers.py`, `report.py`, `corpus.py`, `hook.py`, `stop.py` |
| `tests/` | 43 tests. Run `python3 -m unittest discover -s tests -t .` before believing anything below |
| `git log` | commit messages carry the reasoning for each decision, including the ones that were reversed |
| `docs/unreviewed/reader-detailed-design.md` | **quarantined, see §4.** Not approved, not reviewed |

## 3. What was decided, and where each is recorded

| decision | recorded in |
| --- | --- |
| Name is `deadweight`; `context-discipline` was free but unclaimable | `BRIEF.md` § Task 1 results; commit `f5a0626` |
| Do not publish the gauge — 736 competing repos, one at ★27k | `BRIEF.md` § Task 1 results |
| Floors denominated in absolute tokens, tiered by task shape | design §4.1; `deadweight/tiers.py` |
| Resumption protocol tested and **cut** — 4/4 unguided runs passed | design §4.4; `TESTS.md` § Scenario C |
| Outcome markers are rework events attributed on discovery, not quality judgments | design §2 and §7 |
| Hook carries state, skill carries procedure | design §3 |
| Enforcement strength tracks evidence grade: block / warn / off | design §9; `deadweight/stop.py` |
| Stop hook's loop guard is the corpus, because `stop_hook_active` is undocumented for Stop | `deadweight/stop.py` docstring; commit `e860281` |

**The directory is still named `context-discipline`.** Renaming it is a `mv` plus reopening;
nothing in the code or docs depends on the old name.

## 4. Unverified or assumed

Reading this section does not promote anything in it.

- **No floor has been validated.** Not 50K, not 150K. The subagent tests asserted a token
  figure the agents never actually experienced (~35K real context while told 190K), so they
  test whether an agent honours a stated budget and nothing more. Only the corpus can validate
  a floor. **150K has no source at all** and is labelled as such in `tiers.py`.
- **`cumulativeDroppedTokens` semantics.** Implemented as a running total because the field is
  named that way; no local transcript has more than one compaction, so this was never observed.
  `tests/test_measure.py` marks it `UNVERIFIED` and names the case that would settle it.
- **Two reps per test arm**, against a method asking for five. Separation was total and reps
  converged, but the sample is thin.
- **Neither hook is installed.** Both are tested and committed; nothing is wired into any
  `settings.json`, so nothing is running and no corpus is accumulating. Wiring instructions are
  in each module's docstring. Installing them changes the live setup and wants explicit consent.
- **`docs/unreviewed/reader-detailed-design.md` (49KB) is not trustworthy as it stands.** It was
  produced by subagents running an invalid test scenario, racing each other on the same file, and
  it amended the approved design until that was reverted. It contains two ideas that looked
  genuinely good — reframing the refusal rule from sample size to interval width, and an argument
  that no trend should ever be fitted — but nothing in it has been checked. Treat as a source of
  proposals, not decisions.
- **Licensing undecided.** The reader's minimum *n* undecided.
- **The origin repo (`iladub`) still runs its own percentage-based hook** from
  `$CLAUDE_PROJECT_DIR/scripts/context_budget.py`. Deliberately untouched so nothing goes
  unmeasured before the replacement is installed. `hooks/context_budget.py` here is a
  byte-identical reference copy; do not edit it, or it becomes a fork.

## 5. Next concrete action

**Build the rework marker command, test-first.** It is the missing half of the corpus: `turn`
and `block` records are being written, but no `rework` record can exist yet, and without those
the reader has nothing to read and no floor can ever be argued with. Design §7 gives the record
shape and the attribution order (explicit → git-derived → unattributed, each carrying its method
and confidence).

Then the reader. Note that the reader is **originating** work under this project's own tier
table — start it in a fresh session, and check `docs/unreviewed/reader-detailed-design.md` for
proposals worth stealing before designing from scratch.
