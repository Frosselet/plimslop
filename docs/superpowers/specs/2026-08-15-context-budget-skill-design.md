# deadweight — design

*A skill, two hooks, and an evidence corpus that keep a coding-agent session honest about its own
context budget.*

**Date:** 2026-08-15
**Status:** design approved section-by-section; §10 written but not separately approved.
**Sources:** `BRIEF.md`, plus § Task 1 results (naming check and prior-art sweep, commit `d2d49ab`).

A note on ceremony: `BRIEF.md` settles "brainstorm yes, spec no, plan no". This document is the
brainstorm's output, not a full specification — no formal membrane, no derivation queries, no
falsifiable oracle. It lives under `docs/superpowers/specs/` only because that is the
brainstorming skill's default path.

## Provenance and inherited terms

deadweight was extracted from a private working repository where the problem was first recorded.
That repository is a **consumer** of this tool, not its home, and nothing here depends on it. Three
things carried over, and are referred to below by these names:

- **The prior rule** — a convention recorded there: *never work past 40% of the context window*,
  with 30% as the handoff mark. Its evidence was one uncontrolled, self-assessed, confounded
  session (2026-08-09). Its unit is wrong, and the error grows with window size: on the 1M window
  it was written for, 40% is 400,000 tokens. **deadweight exists because that rule was probably far
  too loose, not too strict**, and because its number could not be defended.
- **The recorded incidents** — occasions where a condensed index line was consumed as fact (twice),
  and where a stale code comment ("widened on this branch only", long since shipped) and an index
  row's own closing instruction were both wrong. A fresh session fixes none of these; opening the
  primary source does. These motivate §4.4 and are the strongest evidence in the design.
- **Evidence grading** — labelling a claim *asserted*, *proposed*, or *promoted* according to what
  supports it, rather than stating everything flatly. Every number deadweight ships carries such a
  grade, and the tool applies the same standard to its own output.

Beyond this section the origin repository is named only where a concrete cutover is described (§11).

---

## 1. What this is

Four shipped parts and one file, keeping a coding-agent session honest about its own context
budget, and collecting the evidence to say where the line actually sits.

The product's distinguishing claim is negative: **it does not ship a promoted constant.** Every
prior-art project found in the sweep ships a percentage threshold (60%, 55%/88%, colour zones).
This one denominates in absolute tokens, labels every number with its evidence grade, and builds
the corpus that can promote or demote those numbers.

**v1 surface:** both hooks, the skill, the corpus, the marker command, and the reader's three views
including baseline items (a) and (b). Everything in §12 is out. MVP remains one user, per
`BRIEF.md` § Scope discipline.

## 2. Decisions settled during the brainstorm

| question | decision |
| --- | --- |
| Form of the pre-flight | Task-shape gate with a conservative absolute floor, shipped as a graded assertion — not a cost model |
| How the skill is reached | Hook carries state; skill carries procedure. All procedural prose moves out of the hook |
| Where staleness lives | In scope, concentrated at the resumption seam |
| What outcome markers are | Rework events, attributed back to the producing turn |
| Floor structure | Tiered by task shape |
| Packaging | Thin tool with an accumulating corpus; adaptive floors deferred |
| Enforcement | `Stop` hook, configurable per tier |

Two of these were reached by rejecting an earlier answer, and the reasons are worth keeping:

**Human quality-marking was rejected.** A human cannot reliably tell good work from slop in a
frontier scope, or when the agent uses techniques and packages they do not know. Marking would
have been densest exactly where the user was least expert. The fix was to stop asking for a
*judgment* at *production time*: record **history** ("this was reverted, redone, abandoned"),
which needs memory rather than expertise, and **attribute on discovery**, letting the tool map the
artefact back to the turn that produced it. That decoupling of *caused-at* from *noticed-at* is
also the direct fix for the flaw in the prior rule's own evidence, where 40% was merely where degradation
became noticeable.

**Injecting the figure on every turn was rejected** in favour of injecting from the lowest floor
upward — see §3.

## 3. Architecture

| part | job | knows |
| --- | --- | --- |
| **hook** (`UserPromptSubmit`) | measure, publish state, append one log record | tokens, session, project — **not** task shape |
| **hook** (`Stop`) | enforce, per configured mode | tokens, configured mode — **not** task shape |
| **skill** | the three procedures and the tier table | the rule — **not** the number |
| **corpus** (append-only JSONL) | turn records, pre-flight records, rework markers | history |
| **reader** (one command) | resolve attribution, report, draw the curve | both |

**The hook cannot evaluate the gate.** It knows the token count; it cannot know whether the next
action is originating a spec or grepping a file. Only the model knows the task shape. The
pre-flight is therefore necessarily split — hook supplies the number, model classifies the shape,
skill supplies the rule. This is a property of where the information lives, not a preference.

**The hook stops carrying procedural prose.** Today the "what to do about it" text lives in
`context_budget.py`; it moves wholesale into the skill. Two copies of the procedure would drift,
and drift between a condensed copy and its source is precisely the staleness mechanism this
project is about, turned on its own tooling.

**`WINDOW` demotes to display only.** Gates are denominated in absolute tokens. The percentage is
still rendered for humans, because 47K/1M is easier to feel than 47,000, but no decision anywhere
reads it.

**What reaches the model, and when:**

- **Below the lowest defined floor** (50K — mechanical is ungated, so the originating floor is the
  lowest number in the table) — `systemMessage` only. The human sees the number; it never enters
  model context, costs nothing, accumulates nothing.
- **At or above that floor** — `additionalContext` carries the number and the pointer to the skill.

This fixes the silence bug in the current hook, which is mute below `HANDOFF_PCT` — 300K on the 1M
window it runs on, i.e. inert across the entire range where the damage accumulates. The new hook
speaks from the lowest floor, below every gate. It does not speak before that because below the
lowest floor every task shape is permitted, so the model has no decision to make; injecting ~15
tokens per turn from turn one would spend thousands of tokens over a long session to deliver
information that never changes behaviour. Spending context to police context is a bad trade.

**Scope:** all parts user-scope (`~/.claude/`), following the gauge's precedent. Surviving branch
switches matters, and a single cross-project corpus reaches a useful *n* far sooner. Records carry
a project field, so per-project views remain available.

## 4. The skill

### 4.1 Tier table

Three shapes, kept few because classification has to stay reliable under exactly the conditions
that make it sloppy.

| shape | what it is | floor | grade |
| --- | --- | --- | --- |
| **originating** | spec, plan, design, architecture, starting a loop, review — multi-step reasoning producing something others build on | **50K** | asserted, literature-anchored |
| **executing** | implementing from a plan that already exists in writing; the reasoning is externalised | **150K** | asserted, **weakest** — extrapolated, no direct support |
| **mechanical** | reading, searching, answering, a named edit, running tests | ungated | asserted from "retrieval survives longer" |

The 50K figure is anchored on NoLiMa (11 of 13 models below half their baseline at 32K), Chroma's
18-model finding that decline begins immediately rather than at a cliff, and the commonly cited
~50K figure. Against these, the prior rule's 40% of a 1M window — 400K — is roughly an order of magnitude
past where multi-step reasoning is already compromised.

**The 150K executing floor has no source behind it** and the shipped text must say so. It is an
interpolation between a defensible floor and no floor, and it should be the first tier the corpus
argues with.

### 4.2 Pre-flight

Before starting work, not as a warning afterwards:

1. Name the shape aloud.
2. Read the current absolute token figure — from the `additionalContext` line the hook injects
   (§3). Below the lowest defined floor no line is injected, which is itself the answer: every
   shape is permitted.
3. Over the floor for that shape → **do not start; hand off first.**
4. Log the decision, including an override.

**The skill's rule is uniform; enforcement strength is not.** Step 3 reads "do not start" for every
gated shape regardless of the mode configured in §9. The mode governs only what the `Stop` hook
does about a violation — `warn` does not soften the rule, it declines to block. This separation is
deliberate: the rule is a claim about when work is sound, the mode is a claim about how much
confidence the evidence supports. Collapsing them would let a weak evidence grade quietly rewrite
the procedure.

Step 1 carries the weight. A model can rationalise past a threshold silently; it cannot rationalise
past one *out loud* without the human watching "originating, 190K, proceeding anyway" go by. The
gate's real enforcement at this stage is visibility. Refusal by a degraded model is the same
self-monitoring that fails first — which is why §7 adds a mechanism that does not depend on it.

### 4.3 Handoff

Written **as pointers, not conclusions**:

- goal, one line
- where the primaries are — paths, commits, spec files
- what was decided, and *where that decision is recorded* — not a restatement of it
- what is unverified or assumed, quarantined under its own heading
- the next concrete action

**Named anti-pattern: summarising the primaries into the handoff.** That manufactures precisely the artefact behind the recorded
incidents — a condensed secondary source, written by a tired session, read as fact by a fresh one.

### 4.4 Resumption — TESTED AND CUT

**This procedure does not ship.** It was pressure-tested before the skill was written and the
failure it defends against did not occur.

Four subagent runs with no guidance were given a handoff that was wrong about the value to change,
and in two of them also wrong about which file to edit and carrying a closing instruction that
would have blocked the correct answer. **All four opened the primary, caught the contradiction,
made the correct edit, and escalated the conflicting instruction rather than resolving it alone.**
This held on the harder fixture, where nothing in the code hinted that the handoff was wrong and
trusting it was the path of least effort.

The credulous reader this section was designed for did not appear. The failure is entirely on the
**write** side — see §4.3, where 2 of 2 unguided runs produced finality claims and explicit
do-not-verify instructions. That reframes the recorded incidents: an index line consumed as fact is
not primarily a reading failure, it is a writing failure that happened one session earlier.

The reasoning is kept below because it remains the correct remedy *if* a corpus ever shows
resumption failing. It should not be re-added from first principles.

> The handoff is a pointer, not a source.

> 1. Read it.
> 2. Before acting on anything load-bearing, open the primary it points at.
> 3. The quarantine section stays unverified; reading it does not promote it.
> 4. **Handoff and primary disagree → the primary wins, and the handoff is corrected.**
>
> Rule 4 makes the protocol self-healing, and is the rule that would have caught the recorded
> incidents.

Note that unguided agents did all four of these unprompted.

### 4.5 Subagent delegation is a remedy, not a loophole

Subagent context is separate, so moving a bounded piece of work into one genuinely keeps the main
session under a floor. The skill states this explicitly; otherwise the model treats delegation as
cheating and routes around the one mechanism that actually helps.

## 5. Baseline

The measured figure is the whole prompt — system prompt, tool definitions, every MCP server's
schemas, CLAUDE.md, the skills listing. A heavy MCP setup can start a session at 40K+, leaving 10K
of headroom under a 50K floor and refusing all originating work from turn two.

Baseline is not the same kind of material as conversational residue, and the brief's three
mechanisms come apart on it:

| mechanism | applies to baseline? |
| --- | --- |
| attention dilution | **yes** — forty tool definitions are genuinely more candidate material to attend to wrongly |
| positional burial | **no** — baseline sits at the top of the prompt, the strong end of the U-curve |
| staleness | **yes, and badly** — a wrong CLAUDE.md line or tool description sits in every single turn |
| accumulation | **no** — flat and cached, it does not grow |

**Decision: gate on total, record baseline as its own field, report it separately.** Baseline needs
no new machinery — it is the token count at the session's first recorded usage.

Three consequences:

1. **The corpus carries a baseline column.** "Rework at 120K with a 20K baseline" and "rework at
   120K with a 90K baseline" are different experiments; a corpus that cannot separate them will
   manufacture another ungrounded constant. No prior-art project records this.
2. **Baseline is a reported finding, not noise.** "You start every session 90% of the way to the
   originating floor" is actionable and currently invisible.
3. **An unsatisfiable gate says so, loudly.** If baseline ≥ a floor: *"baseline 60K exceeds the 50K
   originating floor — you cannot originate in this configuration; reduce baseline or revise the
   tier."* It must never silently block everything.

Accepted deliberately: for a genuinely heavy setup, the honest reading of the literature is that
originating work is already compromised before the first prompt. The tool reports something true
and unwelcome.

## 6. Baseline attribution and prescribed actions

"Your baseline is high" is useless. "These three MCP servers cost 18K per session and you have
invoked none of them in 40 sessions" is a thirty-second decision. The tool never says what you
*need* — it cannot know. It says what you *paid for and did not use*, which is a fact.

| piece | cost | ships in |
| --- | --- | --- |
| (a) total baseline + unsatisfiable-gate warning | trivial — first usage record | **v1** |
| (b) observed use per tool and per server | cheap — transcripts already record every tool call | **v1** |
| (c) per-source token attribution | moderate, and approximate | fast follow |

(b) is the sharp one: *"14 MCP servers connected, 9 never invoked in 40 sessions"* is actionable
with no token estimate at all, and it answers "what should I cut?" well enough that (c) mostly
refines the ordering.

(c) must be **reconstructed** — Claude Code hands the hook no breakdown of its own system prompt.
Measure CLAUDE.md directly, count each server's tool schemas, count the skills listing, and carry
an explicit **unattributed remainder**. The remainder is displayed, never silently distributed
across known sources; a reconstruction that appears to add up exactly gets trusted more than it
deserves.

**Two hard non-goals here:**

- **The tool reports; it never applies.** No editing `settings.json`, no disconnecting servers, no
  trimming CLAUDE.md. An agent that prunes its own configuration to improve its own metric would be
  modifying the thing it measures.
- **No recommendation without evidence behind it.** Never "drop server X" as a judgment; always
  "server X costs ~12K per session, invoked 0 times in your last 40." If the corpus is too thin to
  say that, the tool says nothing — evidence grading applied to its own output.

Noted: this makes the product substantially useful to people who do not care about context
discipline at all, and it is the part the sweep found nobody shipping. It may be what drives
adoption, with the protocol arriving as the reason it was built.

## 7. Corpus, attribution, and the reader

**Storage.** Append-only JSONL under `~/.claude/deadweight/`. **Local only, never transmitted** — it
records project paths, filenames and work patterns, and the docs must say so.

**Record types**, deliberately few:

| type | written by | carries |
| --- | --- | --- |
| `turn` | `UserPromptSubmit` hook, every turn | ts, session, project, turn index, total tokens, baseline tokens, model, window, post-compaction flag |
| `preflight` | skill, when the gate is evaluated | ts, session, declared shape, tokens, floor, decision — including **overridden** |
| `rework` | marker command | ts, target, attributed session/turn/tokens, method, confidence, note |

Logging `overridden` is the point of the pre-flight record: a gate whose circumvention nobody can
measure is a gate that will be circumvented. **The override rate is the honest measure of whether
the tiers are usable** — at 90% the tiers are wrong, not the user.

Tool-invocation statistics are **derived, not logged per turn**. The reader computes them from
transcripts and writes a rolled-up `session_summary` when it runs, so the figures survive
transcript rotation without duplicating data every turn.

**Attribution**, in preference order:

1. **Explicit** — the marker names a session or a commit. Exact.
2. **Git-derived** — the marker names a file or hunk; `git blame` gives the commit and its
   timestamp; turn records give the session and token count spanning that time. Uses only git and
   the log. This is the workhorse.
3. **Unattributed** — recorded with no producing turn.

Two honesty requirements. Git attribution is **approximate**: commits happen after the work,
sometimes long after, and one commit can span many turns — so every rework record carries its
`method` and a confidence flag, and the curve renders inferred points differently from exact ones.
And unattributed markers are **counted and displayed, never dropped**; the unattributed fraction is
a quality measure of the corpus itself, and hiding it would make a thin corpus look solid.

**The reader**, one command, three views:

- `curve` — rework against tokens-at-production, stratified by shape and baseline band
- `baseline` — the §6 report
- `tiers` — current floors, their grades, and whether the corpus supports, contradicts, or cannot
  yet speak to each

**The reader refuses to draw conclusions from thin data.** Below a stated *n* it reports
`n=3 — this shows nothing` and declines to plot a trend. This is the most important behaviour in
the project: the prior rule exists because one session's observation was promoted, and a tool that
will happily draw a confident curve through four points is a machine for manufacturing more of them.
The refusal is the product's central claim made executable.

**Detailed design: `2026-08-15-reader-detailed-design.md`.** This section settles what the reader
*is*; that document settles what it *does* — exact output for all three views, the attribution
algorithm step by step, the refusal rule, and the `session_summary` rollup mechanics. It is the
document to implement from, and it adds three decisions this section does not make plus one
correction to §10, all of which want review before coding starts:

- **the rate's denominator is the *producing turn*** — a turn with a successful `Write`/`Edit` —
  rather than the turn, the session or the pre-flight record. Flagged there as the most
  consequential and most arguable choice in the reader
- **the refusal is two thresholds, not one** — `n_report` to state a rate at all, `n_trend` to plot
  or compare it. Both *proposed*, and the tool prints the power arithmetic that argues against them
- **`CONTRADICTS` requires an equivalence bound**, not merely a failure to find a difference, so a
  thin corpus cannot demote a floor by being underpowered — the prior rule's error, inverted
- **§10's post-compaction test should read the explicit `compact_boundary` transcript record**
  rather than infer compaction from a discontinuity in the totals

## 8. Failure modes and non-goals

**Overriding rule: the tool is never the reason a session fails.** Unreadable transcript, malformed
payload, corpus write failure, permissions — all return silently. Existing hook behaviour; it stays.

**Compaction is stated exactly in the transcript — no heuristic needed.** Verified 2026-08-15
against real transcripts: a compaction writes a record with `type: "system"`,
`subtype: "compact_boundary"`, carrying `compactMetadata` with `trigger` (`auto` / manual),
`preTokens`, `postTokens`, `cumulativeDroppedTokens`, `durationMs` and the preserved-segment UUIDs.
One observed instance: `preTokens` 1,000,577 → `postTokens` 24,952, `cumulativeDroppedTokens`
975,625. So the hook reads the event rather than inferring it from a discontinuity, and
`cumulativeDroppedTokens` gives something better than a flag — a running total of how much of the
session's own history has been discarded, which is a more honest measure of a resumed session's
standing than its current token count.

**Compaction resets the number but not the damage.** When auto-compact fires, total tokens drop
sharply and every gate re-opens — but a compacted session is not a fresh one. Compaction is lossy
summarisation of the session's own history, which makes **auto-compact a handoff written by the
tired session with none of the pointer discipline of §4.3**: exactly the artefact §4.4 exists to
defend against, generated automatically at the worst possible moment. Therefore compaction events
are recorded, post-compaction turns are flagged in the corpus, and a post-compaction session does
**not** count as satisfying a floor. Crossing a compaction should be treated as a *stronger*
handoff trigger than crossing a threshold.

**The model ignores the skill.** The real failure mode. §4.2's mitigations raise the cost of
ignoring the gate and make it visible; they do not prevent it. §9 is the response.

**Model switching mid-session** changes the window and may change the baseline; `model` is recorded
per turn.

**Corpus growth** is one small record per turn — years of use before size matters, but rotation
should be documented.

**Non-goals:**

- Not a cost or billing tracker — `ccusage` and others do that
- Not a status line — settled by the prior-art sweep
- Never applies changes to configuration
- Never transmits the corpus
- **Never claims causality.** The corpus is observational and the confound is unfixable: late
  sessions hold harder residual work. Stratification narrows it; nothing here eliminates it. The
  reader's language stays correlational, or the project reproduces the prior rule's original sin with better
  instrumentation.

## 9. Enforcement configuration

A `Stop` hook can block the response until the checkpoint is raised. Shipped, and configurable per
tier. Design principle for the defaults: **enforcement strength tracks evidence grade** — a floor
with no source behind it has no business hard-blocking anyone.

| shape | default mode | why |
| --- | --- | --- |
| originating | **block** | 50K is literature-anchored; the tier the project exists for |
| executing | **warn** | 150K is the weakest number in the design; it must not stop work |
| mechanical | **off** | ungated |

Default-blocking on originating is aggressive, and this project's own history argues for it: the prior
rule was already written *with* a hook warning behind it, and was run past for 71% of the session
that produced it. Soft enforcement is the thing we have direct evidence does not work here.

Three constraints, all load-bearing:

- **One-step override, always available.** A block that cannot be passed in a single action gets
  disabled wholesale, and then nothing is measured. Overrides are logged (§7).
- **Never block into an unsatisfiable state.** If baseline ≥ the floor (§5), the mode degrades to
  `warn` and emits the "you cannot originate in this configuration" message. Otherwise a heavy MCP
  setup produces a session that refuses all work from turn one, and the tool is uninstalled inside
  a day — correctly.
- **`Stop` fires at turn end, not turn start.** It catches you *having* crossed a floor, not
  *about* to. §4.2's say-it-out-loud step remains the only thing acting before work begins, and it
  stays soft. The two are complements, not redundant.

## 10. Verification

*Written but not separately approved in the brainstorm — review this section specifically.*

**Code — hook and reader.** Unit tests, with the highest-value cases being the failure paths,
because §8's overriding rule is the one guarantee that must hold absolutely:

- malformed payload, missing transcript, unreadable transcript, unwritable corpus → exit 0, no output
- baseline computed correctly from a first-usage record; absent on a fresh session
- unsatisfiable-gate degradation fires when baseline ≥ floor
- attribution resolves explicit, git-derived, and unattributed cases, and stamps confidence correctly
- **reader refuses to plot below the stated *n*** — this deserves a test of its own
- post-compaction flag set from the transcript's compact_boundary record

**Skill — markdown, not unit-testable.** Its verification is behavioural, and the corpus is its own
test harness: `preflight` records show whether the model actually classified the shape and stated
it. Two observable acceptance measures, both already in the design:

- **override rate** — usability of the tiers
- **unattributed fraction** — quality of the corpus

**Falsifiability of the tiers.** Each floor ships with the observation that would demote it, stated
in the shipped text. For originating: a corpus with adequate *n* showing no elevation of rework
rate for originating work begun above 50K, stratified by baseline band, demotes the 50K figure. If
no such observation can be specified for a tier, that tier is not an assertion but a preference and
should be labelled one.

### 10.1 What was actually tested (2026-08-15)

The skill was written TDD-style: baselines first, skill second, re-run third.

| behaviour | baseline (no skill) | with skill |
| --- | --- | --- |
| pre-flight gate | **2/2 failed** — context never considered at all | **2/2 passed** |
| handoff authoring | **2/2 failed** — finality claims, explicit do-not-verify instructions | **2/2 passed** |
| resumption | **4/4 passed** — nothing to fix | not shipped (§4.4) |

Both GREEN arms converged: reps produced near-identical structure rather than diverging
interpretations, which is the signal that wording binds.

**Limits of this evidence, stated so it is not oversold:**

- **Two reps per arm.** The methodology asks for five or more. Separation was total and convergence
  strong, but the sample is thin, and the claim it supports is only the binary one — *guidance
  changes behaviour*.
- **The token figure was asserted, not experienced.** Subagents ran at roughly 35K of real context
  while being told they were at 190K. These runs therefore test whether an agent *honours a stated
  budget*. **They cannot validate the 50K floor, or any floor.** Only the corpus (§7) can, which is
  the reason §7 exists.
- **The gate does not fix missing information.** One GREEN run put it exactly: *"a fresh session
  with a clean window would have invented an answer here just as readily as I would have."* The
  fixture's README and its docstring contradicted each other about where cleanup lived; no context
  budget repairs that. deadweight addresses degraded reasoning, not absent facts, and the shipped
  documentation must not imply otherwise.
- **Six earlier runs were discarded** for test-design faults: a fabricated premise (a spec demanded
  for a codebase that did not exist), and contamination (subagents inherit the parent's working
  directory, so they read this repo's own design document and applied it — one cited §4.3 and §4.4
  by number). Baselines must run in neutral, self-contained fixtures.

## 11. Open items

- **Naming.** `context-discipline` is free on PyPI and uncollided on GitHub but *unclaimable* —
  generic descriptive vocabulary in this exact domain. Rename before any push. Not yet chosen.
- **Licensing.** Undecided. The origin repository uses Apache-2.0 for code and CC-BY-4.0 for
  vocabulary; this repo
  is separate and the choice is open.
- **The gauge — settled 2026-08-15.** Prior-art sweep said do not publish, so the repo copy was
  deleted before publication. It remains a personal script at `~/.claude/statusline-context-gauge.py`,
  now the only copy, which also ends the fork the two copies had created. It is still in this
  repo's git history.
- **Reconciling with the origin repo — settled 2026-08-15.** The replacement was installed
  user-scope first, then the origin's `.claude/settings.json` was deleted, so the two never both
  fired. The feared breakage did not occur: the gauge's `HANDOFF_PCT`/`STOP_PCT` import is guarded
  by an existence check and degrades to its own defaults. This repo's reference copy of
  `context_budget.py` was deleted with it — a copy kept for diffing against a private repo is a
  dependency on that repo, and the original still exists on the origin side.
- **The stated *n*** for the reader's refusal threshold is not yet chosen.

## 12. Deferred

- **Adaptive floors** (brainstorm approach B) — the hook moving floors per project from corpus
  evidence. This is the endgame and the one thing no prior-art project does, but a floor that moves
  on thin data is a tuned constant with extra steps. It ships when the corpus can carry it, and
  that promotion is the product's first real evidence claim.
- **(c) per-source token attribution** — §6.
- **Dissemination.** Per `BRIEF.md`: publishing the discipline is defensible today, publishing a
  threshold is not. The ★0–3 ceiling across the entire prior-art protocol cohort is its own signal.
