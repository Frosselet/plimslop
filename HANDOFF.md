# HANDOFF — deadweight, 2026-08-15

Written at ~317K tokens, past this project's own originating floor by 6×. Written to the
recipe in `skills/managing-context-budget/SKILL.md` §Handoff, which is also the first real
use of that recipe.

**Updated later the same day at 112,882 tokens** — measured with `deadweight.measure` against the
session's own transcript, not estimated — by the session that built the marker command. That
session was asked to start the reader, ran the pre-flight, found itself at 2.3× the originating
floor, and stopped instead. §5 is what it handed over. Nothing about the reader was designed there.

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
| `deadweight/` | the code. `measure.py`, `tiers.py`, `report.py`, `corpus.py`, `hook.py`, `stop.py`, `mark.py` |
| `tests/` | 68 tests. Run `python3 -m unittest discover -s tests -t .` before believing anything below |
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
| An explicit `--session` marker carries the session's token *interval*, never a point inside it | `deadweight/mark.py` `_from_session`; decided 2026-08-15, recorded nowhere else |
| A named `--commit` is `explicit` in method but still `inferred` in confidence — the commit-to-turn mapping is by timestamp either way | `deadweight/mark.py` `_from_git` docstring. Reads §7's "explicit is exact" as being about naming, not about the turn |
| A turn spent in another project never attributes rework here; a session run from a parent directory reads as a miss | `deadweight/mark.py` `_turn_at`, `_within` |

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
- **Both hooks are now installed**, user-scope, on 2026-08-15 with explicit consent. They run from
  the repo checkout via `PYTHONPATH=/Volumes/WD Green/dev/git/context-discipline` in
  `~/.claude/settings.json` — not copied to `~/.claude/`, so there is no fork to drift. If that
  volume is unmounted the hooks silently no-op, which is the designed failure. `Stop` runs in
  `warn` mode via `DEADWEIGHT_MODE_ORIGINATING=warn`; the `block` default was not used.
  The corpus at `~/.claude/deadweight/corpus.jsonl` starts accumulating from the next turn, so
  **every figure the reader will ever see begins after this date.**
- **`docs/unreviewed/reader-detailed-design.md` (49KB) is not trustworthy as it stands.** It was
  produced by subagents running an invalid test scenario, racing each other on the same file, and
  it amended the approved design until that was reverted. It contains two ideas that looked
  genuinely good — reframing the refusal rule from sample size to interval width, and an argument
  that no trend should ever be fitted — but nothing in it has been checked. Treat as a source of
  proposals, not decisions.
- **Licensing undecided.** The reader's minimum *n* undecided.
- **The origin repo (`iladub`) no longer runs its own percentage-based hook.** Its
  `.claude/settings.json` existed only to register that hook and was deleted on 2026-08-15, once
  the replacement was installed, so the two would not both fire there. The deletion is staged but
  **not committed** in that repo. `iladub/scripts/context_budget.py` is deliberately kept — it is
  the original of the byte-identical reference copy at `hooks/context_budget.py` here, and
  deleting it would strand that provenance. Do not edit either, or one becomes a fork.

## 5. Next concrete action

**The reader.** The marker command is built (`deadweight/mark.py`, 25 tests), so all three record
types can now exist. Nothing has been marked yet, and nothing can be until a hook is installed and
turn records start accumulating — the corpus is still empty.

The reader is **originating** work under this project's own tier table — start it in a fresh
session, and check `docs/unreviewed/reader-detailed-design.md` for proposals worth stealing before
designing from scratch.

**There is no schema document.** The records the reader has to read are defined only by the code
that writes them, so read these four places before designing against §7's table:

| record | written by | note |
| --- | --- | --- |
| `turn` | `deadweight/hook.py` `_record` | no turn index, no model, no window — §7 lists all three |
| `block` | `deadweight/stop.py` `_record` | §7's table does not mention this type at all |
| `rework` | `deadweight/mark.py` `main` + `_from_session` / `_from_git` | field set varies by method: `tokens_lo`/`tokens_hi` only for explicit sessions, `commit`/`commit_ts` only when a commit was found |
| `preflight` | **nothing yet** | §7 says the skill writes it. The skill does not. No override has ever been logged, so the override rate §7 calls "the honest measure of whether the tiers are usable" cannot be computed |

Two smaller things the marker surfaced, neither done:

- **Nothing tells anyone to run the marker.** `SKILL.md` has two procedures and does not mention
  marking rework. Whether a third procedure belongs there — or whether marking is the human's job
  and not the agent's — is not settled anywhere, so it was left alone rather than decided quietly.
- **Turn records have no turn index**, though design §7 lists one. `mark.py` pins attribution to a
  turn record's `ts` instead. Fine for the curve; worth knowing before the reader assumes an index.
