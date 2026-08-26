# Design — R141: gate on working tokens, and compute the override rate

**Date:** 2026-08-26 · **Base:** `main` @ `d1cbb2a`, clean, suite green (107 passed).
**Implements:** iladub's 2026-08-26 ruling (`docs/superpowers/2026-08-26-context-regime-ruling.md` §3),
recorded in iladub `CLAUDE.md` § Loop & context hygiene. **This document does not re-open that ruling.**

The handoff `HANDOFF-R141-working-tokens.md` named two decisions and made neither. Both are made
here, with the measurement each rests on inline.

---

## §1 The ruled unit

> `working = tokens − baseline`, and the floor is compared against `working`.

plimslop already measures both terms (`measure.py:79-82`); nothing subtracted them. The gauge at
`~/.claude/statusline-context-gauge.py` was converted on 2026-08-26 and the gate was not, so **the
bar and the gate currently disagree by exactly the baseline.**

---

## §2 DECISION 1 — compaction accounting

A compaction lowers `tokens` without undoing the reasoning already spent, so naive `tokens −
baseline` **falsely resets the floor** — the failure the skill names outright (*"Compaction does not
reset a floor"*).

### What was measured

Every `compact_boundary` record in every transcript under `~/.claude/projects/` (2026-08-26):

```
pre=1001427 post=22672 cum=978755 pre-post=978755 match=True trigger=auto
pre=1002162 post=26013 cum=976149 pre-post=976149 match=True trigger=auto
pre=1000672 post=30955 cum=969717 pre-post=969717 match=True trigger=auto
pre=1000114 post=26659 cum=973455 pre-post=973455 match=True trigger=auto
pre=1020485 post=38303 cum=982182 pre-post=982182 match=True trigger=auto
compactions per transcript: [0, 0, 0, 0, 1, 1, 1, 1, 1]
transcripts with >1 compaction: 0
```

Two facts follow, and they point in opposite directions:

1. **`cumulativeDroppedTokens == preTokens − postTokens`, exactly, 5 of 5.** The field is derived,
   not independent information.
2. **No transcript has ever compacted twice.** So the word *cumulative* in the field name is
   **untested**. `measure.py:67-68` comments *"cumulativeDroppedTokens is a running total, latest
   wins"* — that is an inference from the name, not a measurement.

### Why the subtraction is sound at all

`preTokens` and `postTokens` both include the baseline, which is re-sent every turn and never
dropped. So the baseline **cancels** in the difference, and `pre − post` is exactly the *work*
removed. That is what makes the correction arithmetically exact rather than approximate:

```
working_before = preTokens − baseline
after:  tokens = postTokens,  dropped = preTokens − postTokens
        tokens + dropped − baseline = postTokens + (preTokens − postTokens) − baseline
                                    = preTokens − baseline = working_before   ∎
```

`working` is therefore **continuous across a compaction boundary** — it does not reset, which is the
whole requirement.

### RULED

> **`working = tokens + dropped − baseline`, where `dropped` is the SUM over compaction boundaries
> of `(preTokens − postTokens)` — derived from the pair, never read from
> `cumulativeDroppedTokens`.**

Deriving from the pair **removes** the untested premise instead of guarding it:

- if the field really is cumulative, the sum equals the last value — identical behaviour, and the
  measured `match=True` rows are the proof for the n=1 case;
- if it is per-boundary despite its name, the sum is right and *"latest wins"* silently undercounts,
  making the gate too permissive on exactly the sessions that have done the most work.

Correct under both readings, so the reading never has to be settled. `cumulativeDroppedTokens`
survives only as a **fallback** when a boundary record omits `preTokens`/`postTokens`.

`working` is clamped at 0 — matching the converted gauge, and wrong only in the conservative
direction.

---

## §3 DECISION 2 — where the baseline enters `preflight`

`stop.py` measures the transcript, so it can subtract. `preflight` is a CLI the model invokes by
hand: `--tokens` is **whatever the caller typed**.

The handoff listed three options. The constraint that decides between them is its own:

> *Whichever is chosen, §5's comparison must be computed the same way on both sides of the change
> or the ruling's own prediction becomes untestable.*

- **(a) the hook prints working tokens and callers pass that** — silently redefines `--tokens` for
  every record already written. Old records would say *total* and new ones *working* under the same
  key, indistinguishable. **This destroys the comparison. Rejected.**
- **(b) `preflight` grows `--baseline`** — doubles the untrusted-input surface that this module's own
  docstring exists to close (*"It does not take the caller's word for the decision… A model can
  rationalise its way past a threshold; it cannot rationalise the arithmetic out of the log"*).
  **Rejected.**
- **(c) `preflight` measures it itself** — chosen, in a cheaper form than the handoff assumed.

### The form: measure from the corpus, not the transcript

`preflight._session()` (`preflight.py:56-67`) **already** looks up the latest `turn` record for this
project. That record already carries `tokens` and `baseline`, written from the transcript by the
`UserPromptSubmit` hook (`hook.py:55-62`). **No transcript hunting, no new I/O path, no new caller
argument** — the measurement is already on disk, one lookup away, and the lookup is already written.

### RULED

> **`preflight` reads `baseline`, `tokens` and `dropped` from the latest `turn` record for the
> project, computes `working` itself, and gates on that. `--tokens` is retained, and is advisory
> whenever a measurement exists.**

Consequences, all deliberate:

- **`tokens` keeps its meaning in every record, before and after: the caller's declared figure.**
  It is *not* overwritten with the measured total — that would silently change the key's provenance
  mid-corpus, which is option (a)'s defect wearing a different hat. New records only *add* keys:
  `declared_tokens` (a duplicate of `tokens`, so the intent survives if `tokens` is ever
  re-purposed), `measured_tokens`, `baseline`, `working`, `measured`. §5's comparison survives
  because the total unit is still scored on the same key it always was.
- **It closes an ambiguity the gauge conversion opened.** The status line now renders *working*
  tokens, so a model reading `0k/50k` will type `--tokens 0` while another reads the raw total.
  `--tokens` is already ambiguous in the live corpus. Measuring makes the ambiguity harmless.
- **Fallback:** no `turn` record for the project ⇒ `baseline: null`, `working: null`, gate on
  `--tokens` exactly as today, and say `unmeasured` in the summary line.

**Measured, this session:** `preflight records joinable to a baseline: 152 of 152`. The join is not
hypothetical, and it works retroactively over the entire corpus.

---

## §4 DECISION 3 — `stop.py:68`, the unsatisfiable-gate guard

```python
if session.baseline >= LOWEST_FLOOR:
    return "warn", ("… The gate cannot be satisfied in this configuration …")
```

Under a baseline-relative floor, `working` at turn one is `tokens − baseline ≈ 0` **for any baseline
whatsoever**. No baseline can make the gate unsatisfiable, so the guard's message is now **false**,
and a gate that says something false is worse than one that says nothing.

> **RULED: delete the branch. Do not invent a replacement threshold.**

An oversized baseline is still a real problem — it eats the *window* — but that is window pressure,
not gate satisfiability, and no evidence here supports a number for it. Inventing one would repeat
the defect `tiers.py` already labels `NO SOURCE`.

The same false claim is duplicated in prose at `reader.py:130-133` and `report.py:40-46`; both are
corrected with the branch, or the deletion just moves the falsehood.

---

## §5 DECISION 4 — the override rate, computed by code

`grep -n preflight plimslop/reader.py` → **no hits.** The ruling's own falsifying instrument is
computed by no code in either repo; the 54% came from an audit run by hand.

### The definition, recovered by reproduction

The audit's headline was *54.2% overall (39/72), 52.2% iladub-only (35/67)*. Several plausible
definitions were scored against the corpus truncated to the 681 lines the audit saw:

```
@681 lines: all/gated     39/118 = 33.1%
            all/overfloor 39/72  = 54.2%   ← reproduces
            all/allpf     39/149 = 26.2%
            iladub/gated  35/113 = 31.0%
            iladub/overfloor 35/67 = 52.2%  ← reproduces
```

> **The definition is: `overridden ÷ (gated records at or over their floor)`** — of the times the
> gate actually fired, how often the session proceeded anyway. Both headline figures reproduce
> exactly, so this is recovered rather than guessed.

### RULED

> **`reader.py` grows an `override` view computing that ratio in BOTH units over the same records,
> labelled, under the existing `N_REPORT` refusal discipline.**

The two numbers answer different questions and must not be conflated:

- **counterfactual (available now)** — what past decisions score in the new unit;
- **observed (needs new corpus)** — whether behaviour actually changes, which is §5's prediction.

**Counterfactual, measured this session:**

```
ALL      total  : gate fired 74, overridden 38 ->  51.4%
ALL      working: gate fired 43, overridden 17 ->  39.5%
iladub   total  : gate fired 68, overridden 36 ->  52.9%
iladub   working: gate fired 38, overridden 16 ->  42.1%
```

The gate would have fired **42% less often**, and the override rate falls 51.4% → 39.5%. **This is
not confirmation of §5's prediction** — it is a re-score of decisions taken under the old gate, and
§5 predicts a change in *behaviour* under the new one. Do not let it be cited as the prediction
coming true.

*(51.4% here vs the stored-field 54.1% at the same 690 lines: the re-score recomputes overriddenness
from `declared == "proceed"` rather than reading the stored `decision`, and 2 records carry
`declared: null`. The recomputation is the like-for-like one, since the stored field was written
under the old unit.)*

---

## §6 What this does NOT do

- **It does not validate 50,000 or 150,000.** `tiers.py` still labels 150K `NO SOURCE`. This changes
  what the numbers are measured *against*, not whether they are right.
- **It does not settle R140** (`PLIMSLOP_MODE_ORIGINATING=warn` in user-scope settings). R140 is
  sequenced *after* this and stays open.
- **It does not change `--decision` validation.** `stop` is accepted and undocumented (20 records);
  the audit counted it as compliance and the reader here counts it the same way, so the comparison
  stays like-for-like. Only the `--help` text is corrected, which changes no arithmetic.
- **It does not touch §4 of the ruling** — the unverified premise that baseline tokens cost
  multi-step reasoning less than working tokens. If that premise is false this whole change is
  wrong, and no code here can tell.


---

## §7 FALSIFICATION

Every change was inverted and the suite re-run. Baseline: **107 passed** at `d1cbb2a`; after:
**134 passed**.

| inverted | tests that failed |
|---|---|
| `working` drops the compaction add-back | `test_compaction_does_not_reset_the_working_figure`, `test_dropped_is_summed_over_boundaries…` |
| `working` drops the baseline subtraction | 5 in `SessionWorkingTokens` / `SessionWorkingAcrossCompaction` |
| `dropped` reverts to latest-wins | `test_dropped_is_summed_over_boundaries_not_taken_from_the_last` |
| `stop.py` gates on `session.tokens` again | `test_a_large_baseline_with_little_work_done_is_allowed`, `test_a_compacted_session_is_judged_on_what_it_has_actually_done` |
| `preflight` ignores the measurement | `test_a_caller_who_lowballs_the_figure_is_still_caught`, `test_a_large_baseline_with_little_work_is_not_an_override` |
| `reader` denominator becomes all gated records | `test_the_rate_is_overridden_over_records_that_tripped_the_floor` |
| `report.py` speaks the total again | `test_a_large_baseline_with_little_work_tells_the_model_nothing` |

All restored; 134 passed.

**Four existing tests were deliberately superseded**, each replaced by one asserting the opposite
with the reason in its docstring — never weakened or deleted quietly:

| superseded | why |
|---|---|
| `test_dropped_takes_the_latest_cumulative_figure_rather_than_summing` | its own docstring said `UNVERIFIED`; §2 replaces the premise with a derivation |
| `NeverBlockIntoAnUnsatisfiableState` (2 tests) | the guard's premise is false under a baseline-relative floor — §4 |
| `UnsatisfiableGate` (2 tests) | same false claim, in what the model is told |
| `test_the_reason_names_the_figure_and_the_skill` | the figure named is now the working one |

## §8 The live corpus, after the change

```
$ python3 -m plimslop.reader override
override — how often the gate fired, and how often it was passed

  total    38/74 = 51% overridden
  working  17/43 = 40% overridden

  Splitting the working unit by when the record was written, because
  re-scoring old decisions is NOT the same claim as observing new ones:
    counterfactual (written before R141)  17/43 = 40% overridden
    observed       (written after R141)   the gate never fired in this unit (n=0) — this shows nothing
```

**The `observed` row is the one that matters, and it is empty by construction.** §5's prediction
cannot be tested until new records accumulate under the new gate — roughly three weeks of corpus.
Anyone reading the 40% counterfactual as the prediction coming true has misread it: those are
decisions taken under the old gate, re-scored.

## §9 The skill was converted too

`skills/managing-context-budget/SKILL.md` told the model to read *"the absolute token count reported
for this session"*. Left alone it would have disagreed with the gate by exactly the baseline — the
same defect the ruling's §8 fixed for the status-line gauge, in the artefact the model actually
reads. It now names the working figure, states the tier table is denominated in it, and carries §4's
unverified premise rather than hiding it.

**It IS in this repo and the diff is in this commit.** Recorded because the first draft of this
section claimed the opposite: `~/.claude/skills/managing-context-budget` is a **symlink** to
`plimslop/skills/managing-context-budget`, so editing the user-scope path edited the tracked file.
`git status` caught it. The genuinely-untracked artefact is the *other* one —
`~/.claude/statusline-context-gauge.py`, verified absent from `git ls-files` in **both** repos — and
conflating the two is exactly the error to avoid when the handoff says "user-scope".

## §10 End-to-end, on this session's own transcript

```
$ echo '{"session_id":"smoke","cwd":"…/iladub","transcript_path":"…"}' | python3 -m plimslop.hook
{"systemMessage": "plimslop 111,964 working / 158,919 (16%)", …
 "additionalContext": "CONTEXT 111,964 tokens of work above a 46,955-token baseline. …"}

$ echo '{"session_id":"smoke","transcript_path":"…"}' | PLIMSLOP_MODE_ORIGINATING=block python3 -m plimslop.stop
{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason":
 "This session has done 111,964 tokens of work above its 46,955-token baseline, …"}}

$ plimslop preflight --shape originating --tokens 0 --decision proceed --session smoke
pre-flight: originating at 111,964 working tokens — OVERRIDE, past the 50,000 floor. Logged.
  → {'tokens': 0, 'declared_tokens': 0, 'measured_tokens': 158919, 'baseline': 46955,
     'working': 111964, 'measured': True, 'decision': 'overridden'}
```

The last line is the point of DECISION 2: a caller who declares **0 tokens** is still recorded as
having overridden at 111,964. The old code would have logged `under the floor, proceed`.

## §11 KNOWN LIMITATION — `preflight`'s measurement is as fresh as the last user prompt

Found by running the shipped command on this session, twice, minutes apart:

```
$ plimslop preflight --shape originating --tokens 0 --decision proceed --session smoke
pre-flight: originating at 111,964 working tokens — OVERRIDE …     # read from the transcript
$ plimslop preflight --shape executing --tokens 0 --decision proceed
pre-flight: executing at 85,810 working tokens — under the floor …  # read from the turn record
```

Both are correct; they measure different instants. `turn` records are written by the
**UserPromptSubmit** hook, so there is exactly one per user prompt. Inside a long turn — this one
did an entire implementation without an intervening prompt — `preflight` reports the figure **as of
the turn's start** and does not see work done since.

**Why this is tolerable, not a defect to fix here.** The pre-flight is specified to run *before*
starting work (skill § Pre-flight, step 1), which is near a turn boundary, where the lag is
smallest. And the case it would miss is caught anyway: `stop.py` reads the transcript directly and
fires at the turn boundary, so a session that burns a floor mid-turn is spoken to at the end of it.

**Why it is nonetheless recorded rather than left silent.** The lag is unbounded in principle — a
single turn can be arbitrarily long — and it biases in the **permissive** direction, which is the
direction this project treats as dangerous. Closing it means teaching `preflight` to read the
transcript itself, which is option (c) in the handoff's fuller form and was rejected here only as
unnecessary, not as wrong. **The right trigger to revisit is evidence**: if `reader override` ever
shows sessions declaring `proceed` under a floor that `stop.py` then refuses in the same session,
that is this gap, and it is countable from the corpus that now exists.
