# HANDOFF — plimslop, 2026-08-15

Written at ~355K tokens, seven times this project's own originating floor. Written to the recipe in
`skills/managing-context-budget/SKILL.md` §Handoff, which is the mitigation: **pointers can be
checked, conclusions cannot.** Nothing below is a conclusion. Where it says something is true, it
says where to look, and you should look.

This replaces an earlier handoff that had been patched eight times in one day. That file is in
`git log` if the layers matter.

## 1. Goal

**plimslop** keeps a coding-agent session honest about its own context budget, denominated in
absolute tokens, with every number carrying the evidence grade that supports it. All of it is
built and published. **None of it is validated** — that part is not a coding task, see §5.

## 2. Where the primaries are

| primary | what to establish there |
| --- | --- |
| https://github.com/Frosselet/plimslop | public since 2026-08-15. What the world can see |
| `README.md` | what the project claims, how it installs, and the `plimslop` allegory. Start here |
| `docs/superpowers/specs/2026-08-15-context-budget-skill-design.md` | the design, approved section by section. **§10.1 records what was actually tested and the limits of that evidence** — read it before trusting any number |
| `BRIEF.md` | history only. The originating handoff, the prior-art sweep, and **all four naming sweeps**, including the two that rejected names. The rejections are the evidence for the criterion |
| `skills/managing-context-budget/SKILL.md` | the shipped skill. Two procedures, not three |
| `skills/managing-context-budget/TESTS.md` | the pressure scenarios and their results. Fixtures in `tests/fixtures/` |
| `plimslop/` | the code: `measure`, `tiers`, `report`, `corpus`, `hook`, `stop`, `mark`, `reader` |
| `hooks/` | `hooks.json` and two launchers that locate the package relative to themselves |
| `tests/` | 90 tests. `python3 -m unittest discover -s tests -t .` before believing anything below |
| `~/.claude/plimslop/corpus.jsonl` | **the live corpus.** 19 records when this was written and one more every turn, so count it rather than trust that. Not in the repo and must never be — it holds project paths and filenames |
| `git log` | commit messages carry the reasoning for each decision, including the reversed ones |
| `docs/unreviewed/reader-detailed-design.md` | **quarantined, see §4.** Not approved, not reviewed |

## 3. What was decided, and where each is recorded

| decision | recorded in |
| --- | --- |
| Name is `plimslop`, after `context-discipline` → `deadweight` → `plimsoll` | `BRIEF.md` § Task 1, all four sweeps verbatim |
| Floors denominated in absolute tokens, tiered by task shape | design §4.1; `plimslop/tiers.py` |
| Resumption protocol tested and **cut** — 4/4 unguided runs passed | design §4.4; `TESTS.md` § Scenario C |
| Outcome markers are rework events attributed on discovery, not quality judgments | design §2 and §7 |
| Hook carries state, skill carries procedure | design §3 |
| Enforcement strength tracks evidence grade: block / warn / off | design §9; `plimslop/stop.py` |
| The gate speaks **once per session**, warn or block alike | `plimslop/stop.py` `_raised_before`; commit `654c609`. A warning every turn gets the hook disabled, and a disabled hook measures nothing |
| An explicit `--session` marker carries the session's token *interval*, never a point | `plimslop/mark.py` `_from_session` |
| A named `--commit` is `explicit` in method, still `inferred` in confidence | `plimslop/mark.py` `_from_git` docstring |
| Rework never attributes across projects | `plimslop/mark.py` `_turn_at`, `_within` |
| The reader's denominator is turns in band, **not producing turns** | `plimslop/reader.py` module docstring. The corpus records no tool use, so §7's denominator does not exist |
| Reader bands are the tier table's own regions, not a chosen histogram | `plimslop/reader.py` `BANDS` |
| Tests may never touch the real corpus | `tests/__init__.py`, asserted by `tests/test_corpus_isolation.py` |
| Apache-2.0 for code, CC-BY-4.0 for prose | `LICENSE`, `README.md` § Licensing. Recorded nowhere else — a decision, not a settlement |
| Published public on the owner's explicit instruction | commit `738f30d` |

## 4. Unverified or assumed

Reading this section does not promote anything in it.

- **No floor has been validated.** Not 50K, not 150K. The subagent tests asserted a token figure the
  agents never experienced (~35K real context while told 190K), so they test whether an agent
  honours a *stated* budget and nothing more. Only the corpus can validate a floor.
  **150K has no source at all** and is labelled so in `tiers.py`.
- **The reader's thresholds (20, 50) are invented.** No power calculation stands behind either. They
  print as `PROPOSED` on every run, which makes them visible, not correct.
- **The reader was built at 272K tokens**, 5.5× the originating floor, on an explicit override after
  two earlier sessions refused that exact task. The override is a `preflight` record in the corpus.
  If the reader turns out subtly wrong, that is the first place to look — and the most likely form
  of the error is a confident-sounding refusal boundary rather than a crash.
- **The corpus was polluted by its own test suite and purged.** `test_entrypoint.py` ran the hook
  with `corpus_path=None`, falling through to `default_path()`; 17 fabricated records were removed
  and 14 real ones kept. **If any real record was misclassified as synthetic, it is gone** — the
  pre-purge backup was only ever in a session scratchpad.
- **`cumulativeDroppedTokens` semantics.** Implemented as a running total because the field is named
  that way; no local transcript has had more than one compaction, so it has never been observed.
  `tests/test_measure.py` marks it `UNVERIFIED` and names the case that would settle it.
- **Two reps per test arm**, against a method asking for five. Separation was total and reps
  converged, but the sample is thin.
- **The `slop` in the name is unresolved, not resolved.** Design §2 rejects quality-marking outright;
  *slop* is a quality word. `README.md` § Why `plimslop` argues the tool measures the water and not
  the goods, which is a good answer to a real objection, not a disappearance of it.
- **`statusline-context-gauge.py` is recoverable from git history** (`777179f`…`d5c194f`) though the
  sweep said not to publish it. Left knowingly: purging rewrites all SHAs and breaks the commit
  citations in §3 and `BRIEF.md`. That reasoning was sound when nothing was public and is weaker now.
- **`docs/unreviewed/reader-detailed-design.md` (49KB) is not trustworthy** and is now public. It was
  produced by subagents running an invalid test scenario and racing on one file. Two ideas in it
  looked good — reframing the refusal rule from sample size to interval width, and an argument that
  no trend should ever be fitted — and **the second was not implemented**; `reader.py` draws no
  trend, but by omission rather than by decision. Treat as proposals.

### What is installed on this machine, and how

Not a fork: everything points at this checkout, so editing the repo changes the live setup.

- Both hooks in `~/.claude/settings.json`, via `PYTHONPATH=/Volumes/WD Green/dev/git/plimslop`.
  `Stop` runs in `warn` (`PLIMSLOP_MODE_ORIGINATING=warn`); the shipped default is `block`.
- The skill at `~/.claude/skills/managing-context-budget`, a symlink into the checkout.
- **Not** installed as a plugin — a directory or GitHub install makes a frozen `0.1.0/` copy, which
  would fork the skill and stop tracking edits. Verified installable from GitHub, then removed.
- If the WD Green volume is unmounted, hooks and skill silently vanish. That is the designed failure.

## 5. Next concrete action

**Make the skill write `preflight` records.** It is the last piece of the designed loop that does not
exist: §7 says the skill logs every gate evaluation *including overrides*, and nothing does. The two
`preflight` records in the corpus were written by hand. Without them the override rate — which §7
calls "the honest measure of whether the tiers are usable" — cannot be computed at all, and a gate
whose circumvention nobody can measure is a gate that will be circumvented.

It is small: a `plimslop.preflight` command in the shape of `mark.py`, plus a step in `SKILL.md`
telling the model to run it. Note `SKILL.md` currently does not mention the marker command either.

**After that, the project's next move is elapsed time, not code.** The corpus was at 19 records when
this was written and every reader view correctly refuses to say anything. Nothing about the floors can be argued until
the thing has run for weeks and rework has actually been marked. Building more tooling in the
meantime is the most tempting way to avoid finding out whether the tool is right.
