# HANDOFF — plimslop, 2026-08-15 (amended 2026-08-17)

**Amended 2026-08-17, `ae35510`:** §4's § Delivering the gate bullet said "NOT DONE" and was wrong
on all four items — see the disposition table there. Nothing else below was re-verified on that
date, so treat the rest as dated 2026-08-15 and check it. **Pushed 2026-08-17** — the public repo
had been 10 commits behind at `ad26067`, so until then it served a skill still containing both
rules Scenario D refuted.

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
| `plimslop/` | the code: `measure`, `tiers`, `report`, `corpus`, `hook`, `stop`, `mark`, `reader`, `preflight` |
| `hooks/` | `hooks.json` and two launchers that locate the package relative to themselves |
| `tests/` | 102 tests. `python3 -m unittest discover -s tests -t .` before believing anything below |
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
| A declared `proceed` above the floor is recorded as `overridden`, whatever the caller called it | `plimslop/preflight.py`; `SKILL.md` step 5. The declared value is kept beside it |
| The skill now names both logging commands | `SKILL.md` step 5 and § When work has to be redone |
| The gate is **logged always, spoken rarely** — invisible under the floor, two sentences over it, never a question that halts the loop | `SKILL.md` § Delivering the gate. Same principle `stop.py` `_raised_before` already applies to the hook (commit `654c609`): over-speaking gets the gate ignored |
| Subagent delegation is bounded to **measurement, never authorship** | `SKILL.md` § Pre-flight, the paragraph after the delegation remedy |

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
- **CORRECTION: the "60,000 baseline" finding was an artifact, not a finding.** Commit `9db0e90`'s
  message claims the reader "found something real — an observed baseline of 60,000 exceeds the
  50,000 originating floor... the first thing the corpus has said that nobody put there on
  purpose". **That is false.** The 60,000 came from `tests/test_entrypoint.py:39`
  (`transcript(60_000, 190_000)`, session `s1`, cwd `/tmp/p`) writing to the live corpus before the
  isolation fix. It was purged as synthetic hours later without anyone connecting the two. The
  corpus has held exactly one distinct baseline throughout: **34,650**, from one session. The
  commit message cannot be edited without rewriting public history, so it stands with this
  correction beside it. **The corpus has produced no findings. It is not old enough to have any.**
- **A session's first turn is never recorded, so short sessions are undercounted.** On turn one the
  transcript holds no usage yet, `measure.read_session` returns 0, and `hook.py` exits before
  writing. Every session contributes records from its *second* turn onward. Correct behaviour —
  there is genuinely nothing to measure yet — but the bias is not neutral: it removes exactly the
  short, low-token sessions that the `below 50,000` band most needs, which is the band with n=0
  today. A one-shot session contributes nothing at all. Verified 2026-08-15 by running a headless
  session and watching the corpus not grow, then a two-turn one and watching it grow by one.
- **The corpus spans two different baseline regimes and they are not comparable.** Until
  2026-08-15 ~16:29 UTC every record carries baseline 34,650. After it, 15,658 — `disableWorkflows`
  and `skillListingMaxDescChars: 200` were added to `~/.claude/settings.json`, cutting 18,992
  tokens (55%) from what is in the window before anything is typed. Measured by the hook itself,
  not by a harness. §6 keeps a baseline column precisely so "rework at 120K with a 34K baseline"
  and "rework at 120K with a 15K baseline" are not conflated — **so stratify by baseline before
  comparing anything across that boundary.** The Workflow tool alone was ~8,300 tokens of it.
- **`cumulativeDroppedTokens` semantics.** Implemented as a running total because the field is named
  that way; no local transcript has had more than one compaction, so it has never been observed.
  `tests/test_measure.py` marks it `UNVERIFIED` and names the case that would settle it.
- **Two reps per test arm**, against a method asking for five. Separation was total and reps
  converged, but the sample is thin.
- **`SKILL.md` § Delivering the gate was HALF REFUTED by its own test. CORRECTED — all four items,
  across two sessions.** This bullet was written at 21:44 on 2026-08-15; `2face9a` landed at 21:48
  and did the first two, so the "NOT DONE" below was stale four minutes after it was written. The
  remaining two were done 2026-08-17 (§ disposition at the end of this bullet).
  It shipped on one observed session (2026-08-15, iladub R87) before `TESTS.md` § Scenario D was run.
  Scenario D was then run the same day, 5 reps × 4 arms, and the numbers are in `TESTS.md`:
  - **The under-floor rule made the behaviour worse** — 1.0 announcement sentences against a **0.4**
    control, 4/5 announcing against 2/5. The control was barely failing, so by this project's own
    method the guidance should never have been written. Agents now emit a compressed *log receipt*;
    one, told the first sentence belongs to the user, kept the receipt and moved it to the end.
  - **The over-floor recipe works** — 10.4 → **3.8** sentences, 0/5 over-correcting.
  - **Its ≤2-sentence budget contradicts its own required parts** (reversibility, and step 5's log),
    so 0/5 pass strictly while 5/5 pass if those parts are counted as part of the gate.
  - **The "never a question that ends the turn" clause is unsupported** — 0/5 in both baselines.

  **Disposition of all four, with where to check each:**

  | recommended | done | where |
  | --- | --- | --- |
  | delete the under-floor rule | 2026-08-15 | `2face9a`; `SKILL.md` § Delivering the gate now says "Do not re-add it" |
  | keep the over-floor recipe | kept | `SKILL.md` § Delivering the gate, the two numbered parts |
  | fix the sentence budget to match its own parts | 2026-08-15 | `2face9a`; "**The budget is these two parts — never a sentence count**" |
  | drop or demote the question clause | 2026-08-17 | demoted to one mention carrying its own grade; Common-mistakes row dropped. Reasoning in `TESTS.md` § Scenario D, **DISPOSED 2026-08-17** |

  The last row is the only judgment call among the four, and it went the *weaker* way: demote, not
  delete, because § Limits records that reps score a single response while the R87 halt was
  mid-session — so 0/10 is a blind test, not evidence of absence. Argue with that row, not with the
  other three. `SKILL.md` § Note on scope no longer claims Scenario D is unrun.

  **Both correcting sessions were themselves overrides** — 206K refused it, 2026-08-17 proceeded at
  64K against a 50K floor, logged. The §4 note below, that this skill cannot be maintained under its
  own constraint, still stands and is now evidenced three times.
- **The floors measure volume, not scope — and a session can diverge while fully compliant.** The
  2026-08-15 session that ran Scenario D named every shape, logged every gate, and honestly reported
  every result, and still drifted from one skill section to four files across two repos plus a
  corpus-integrity investigation. Nothing in the tool sees that. Absolute tokens say how much is in
  the window, never how many distinct things are; they rose *because* of the drift, but as a lagging
  symptom that cannot separate "read a lot about one thing" from "touched six things". A session can
  be at 60K and scattered or at 220K and tightly on one artefact. Whether that is worth instrumenting
  is undecided — recording it because the gate not firing on the thing that actually went wrong is
  evidence about the gate.
- **The skill has no procedure for its own maintenance under its own constraint.** Editing it is
  originating; testing it costs a scenario battery. So a session that seriously improves this skill
  crosses the floor in the act of improving it — twice on 2026-08-15 alone. Its only offered remedy
  is delegation, which § Pre-flight now correctly forbids for authorship. No resolution proposed.
- **Agents claim to log without logging — HALF FIXED, and the remaining half is a design problem.**
  Diagnosed 2026-08-15. Two separable failures:
  - **"couldn't run" — FIXED in `edd05c9`.** `cd /tmp && python3 -m plimslop.preflight` (the literal
    command SKILL.md gave) raised `ModuleNotFoundError`; it resolved only from the repo root, while
    `settings.json` wires both *hooks* with an explicit `PYTHONPATH`. Hence a corpus of 56 turns and
    28 preflights. `bin/plimslop` existed but was not symlinked, so it was inert. Docs now lead with
    `plimslop preflight …` and `~/.local/bin`.
  - **"didn't try" — did NOT survive the fix. Re-measured after `edd05c9`, scoring the corpus
    instead of the claim: 10 of 10 reps across both arms wrote a real `preflight` record; phantom
    logging went 4/5 → 0/5.** The earlier reading — that "didn't try" was a separate and more serious
    failure — was wrong: it was downstream of a command that could not run. **Confound, and it is the
    test author's:** the rep prompt names `PLIMSLOP_CORPUS`, so two variables moved at once. The
    defensible claim is "the failure did not recur under these conditions", not "the path fix caused
    it". One clean arm, with the redirect delivered without naming the binary, would settle it.

  **Why the obvious detector cannot be built as it stands.** A `turn` record carries
  `type, session, project, tokens, baseline, compacted, dropped, ts` (`hook.py:55-62`) — volume only.
  **`shape` exists nowhere but the `preflight` record, which only the agent writes.** So "an
  originating turn happened with no preflight" is *not an observable of the corpus*, and
  `stop.py` cannot test it however it is wired. Access is not the obstacle: `stop.py:102` has the
  session id, `stop.py:132` already reads the corpus before deciding, and `_raised_before`
  (`:126-133`) is the exact "scan for a record of type T matching this session, act once" query.
  The obstacles are (a) shape is unobservable and (b) the one-speak-per-session slot at `:12-19` is
  already spent on the volume gate.

  **Three findings that came out of the same diagnostic and are separately actionable:**
  - **The override rate is computed by no code in this repo.** `reader.py` selects only `turn`
    (`:58`, `:116`, `:139`) and `rework`; it never reads `preflight`. The skill calls the override
    rate *"the only honest measure of whether these floors are usable"* and nothing measures it.
  - **Session attribution is entirely heuristic, and `project` is unreliable too.** Of 28 preflight
    records: `inferred` 24, `unknown` 2, absent 2, **`given` 0** — no agent has ever passed
    `--session`, so every attribution reverse-matches "latest turn in this project"
    (`preflight.py:56-67`). And the rerun found 3 of 5 records carrying the *parent* session's cwd
    as `project`, because the agent logged without `cd`-ing. Both fields the join depends on are
    weak at the same time.
  - **The design's stated verification is falsified.** Spec `:435-437` says *"the corpus is its own
    test harness: `preflight` records show whether the model actually classified the shape"*. D1
    shows a missing record coexisting with a confident on-screen claim that it was written.

  Corpus as of diagnosis: 90 records, 5 groups, 1 of 4 turn-bearing sessions with zero preflights —
  but that session has a single turn, and `hook.py:39-40` never records turn 1, so the population is
  biased toward long sessions, which is the opposite of where D1 saw the failure. **The 25% is not a
  rate to quote.** Also minor doc drift: spec `:294` claims `turn` carries turn index, model and
  window; `hook.py:55-62` writes none of them.
- **The `slop` in the name is unresolved, not resolved.** Design §2 rejects quality-marking outright;
  *slop* is a quality word. `README.md` § Why `plimslop` argues the tool measures the water and not
  the goods, which is a good answer to a real objection, not a disappearance of it.
- **`statusline-context-gauge.py` is recoverable from git history** (`777179f`…`d5c194f`) though the
  sweep said not to publish it. Left knowingly: purging rewrites all SHAs and breaks the commit
  citations in §3 and `BRIEF.md`. That reasoning was sound when nothing was public and is weaker now.
- **The commands are not on anyone's PATH after a plugin install.** `mark`, `preflight` and
  `reader` are modules in the plugin cache; the hooks and skill work immediately but those three
  need `PYTHONPATH`. `README.md` § Installing gives aliases, tested against a real install. A
  proper entry point (`__main__.py` or a console script) was not built.
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

**Use it, and mark rework when you find it.** There is no next build step. The designed loop is
closed: the hook measures, the skill gates and logs, `mark` records what had to be redone, the
reader refuses to draw conclusions until there is something to draw them from.

What the corpus needs now is elapsed time and honest marking — which is the part no amount of code
substitutes for, and the part most easily avoided by building more code. The first question it can
eventually answer is the one the project exists for: **is 50K anywhere near right, and is 150K
defensible at all?** Neither can be touched at this *n*.

Small things, if hands are idle and a fresh session wants them:

- ~~**Push `ae35510`, or decide not to.**~~ **Done 2026-08-17.** The gap was 10 commits, not 2 —
  worth knowing that this repo drifts from its remote silently, because the skill is a symlink into
  the checkout and therefore behaves correctly here whatever the remote holds. Nothing warns you.
- **`SKILL.md:44` reads as more current than it is.** It presents 4-of-5 phantom logging as the
  standing result; the rerun found 0/5 (`TESTS.md` § RERUN). It is honestly qualified — *"while the
  command was in fact unresolvable"* — and the rerun carries the author's own confound, so it is not
  clearly wrong. Left untouched 2026-08-17 as outside that session's scope. Decide it, don't inherit it.
- **The commands need a proper entry point.** After a plugin install they are only reachable via
  `PYTHONPATH`; see §4.
- **`docs/unreviewed/` holds one unimplemented idea worth deciding on** — that no trend should ever
  be fitted. `reader.py` fits none, but by omission rather than decision. Making it explicit would
  close the gap between what the tool does and what anyone can tell it does.
