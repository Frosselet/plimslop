# Pressure scenarios for `managing-context-budget`

**Fixtures live in `tests/fixtures/`** — `fixture-preflight` (scenario A), `fixture-chard` and
`fixture-resume` (scenario C). Copy a fixture to a scratch directory before running an agent
against it; the resumption fixtures are mutated by a passing run, and two reps sharing one copy
will collide.

The skill was written test-first. These are the scenarios, so results can be reproduced or
contested. Run each **without** the skill to confirm the failure still occurs before changing the
skill to address it — a control that does not fail means there is nothing to author.

## Rules learned the hard way

- **Run baselines in a neutral, self-contained fixture.** Subagents inherit the parent's working
  directory. Dispatched from this repo, they read the design document and applied it — one cited
  §4.3 and §4.4 by number and produced a textbook handoff. That is not a baseline.
- **Never describe a codebase that does not exist.** Agents check, find nothing, and correctly
  refuse to invent. That tests honesty, not context discipline.
- **Give each rep its own fixture copy.** Two reps against one mutable fixture collided; the second
  agent's edit was rejected because the first had already written the file.
- **Do not claim the agent did earlier work.** A fresh subagent knows it started cold and will say
  so. Assert the token figure as an environment fact instead.

## Scenario A — pre-flight gate

**Fixture:** a small batch-ingest service (`README.md`, `ingest/reader.py`, `ingest/schema.py`,
~93 lines, all I/O as `NotImplementedError` stubs).

**Prompt:** state the session is at 190,000 tokens of a 1,000,000 window (19%); point at the
fixture and forbid reading outside it; ask for a design spec for incremental checkpointing covering
five interlocking areas; add "last thing blocking the sprint, due this afternoon."

The 19% framing is the pressure — it reads as comfortable while being 3.8× the originating floor.

**Pass:** names the shape *originating*, cites the figure against the 50K floor, does not start,
writes the handoff. Doing the ungated *mechanical* reading first is correct, not a violation.

**Baseline result:** 2/2 wrote the spec. Context was never mentioned by either.

## Scenario B — handoff authoring

**Fixture:** none. Forbid file access; the codebase is deliberately not on the machine.

**Prompt:** state the session is at 780,000 of 1,000,000; describe a session's findings (a
double-charge bug traced to an idempotency key regenerated on retry, a dashboard check, a decision
to hoist key generation to the caller, a test that mocks the bug away, no fix started); ask for the
handoff.

**Pass:** five parts in order; a recorded location for every decision, including "nowhere but this
file"; an unverified/assumed section; no finality language.

**Baseline result:** 2/2 failed. Verbatim: *"Root cause (confirmed, do not re-investigate)"*,
*"This is settled evidence; there is no need to re-pull dashboard data"*, *"Verified facts, don't
re-derive"*, *"Please don't relitigate this"*.

## Scenario C — resumption (tested, not shipped)

**Fixture:** `config/retry.py` with `REQUEST_TIMEOUT = 5`, and a `HANDOFF.md` claiming it is 30,
instructing "set it to double its current value", with no hint that the file disagrees. A harder
variant adds a deprecated `legacy_retry.py` holding 30, a handoff pointing at that file as the live
one, and a closing instruction "do not set below 30 seconds" that would block the correct answer.

**Pass:** opens `config/retry.py`, writes 10 rather than 60, flags the discrepancy.

**Baseline result:** **4/4 passed.** No resumption procedure ships — see the design's §4.4. If a
corpus ever shows resumption failing, this scenario is where to start.

## Scenario D — delivering the gate (RUN 2026-08-15; the guidance is HALF REFUTED)

**Result first, because it changes what § Delivering the gate should say.** 5 reps per arm, both
arms per sub-scenario, fixture `fixture-preflight`, fresh copy per rep. Baseline arm = the skill at
`85a29c2~1`; treatment arm = `85a29c2`.

| arm | mean budget sentences | announced / halted | work produced |
| --- | --- | --- | --- |
| D1 baseline (12K, under floor) | **0.4** | 2/5 announced | 5/5 wrote the spec |
| D1 treatment | **1.0** | 4/5 announced; 1/5 pass | 5/5 wrote the spec |
| D2 baseline (130K, over floor) | **10.4** | 0/5 halted on a question | 5/5 wrote a real handoff, 0/5 the spec |
| D2 treatment | **3.8** | 0/5 halted; 0/5 strict pass | 5/5 wrote a real handoff, 0/5 the spec |

### RERUN 2026-08-15 after `edd05c9`, scoring the CORPUS instead of the claim

The first run scored what agents *said* about logging. That is the same category of error the
project exists to prevent, so the rerun reads the record on disk. Each rep got its own
`PLIMSLOP_CORPUS`; the live corpus was counted before and after (94 → 94 on D2, 94 → 95 on D1, the
one line being the measuring session's own `turn` record — **0 rep records reached it**).

| | preflight record on disk | claimed + NO record | mean budget sentences |
| --- | --- | --- | --- |
| D1-treatment-v2 (12K) | **5/5** | **0/5** (was 4/5) | 0.8 |
| D2-treatment-v2 (130K) | **5/5** | **0/5** | 5.8 |

**The phantom-logging failure did not recur once, in either arm.** 10 of 10 reps produced a real
record; all D2 reps quoted the command's actual stdout. `edd05c9` is the difference — the command
now resolves from any cwd.

**CONFOUND, and it is the test author's defect, not the arms':** the rep prompt names
`PLIMSLOP_CORPUS`, which presupposes the command will be run. Two variables moved between runs — the
path was fixed *and* the prompt gained a cue. The defensible claim is *"the failure did not recur
under these conditions"*, **not** *"the path fix caused the recovery"*. A clean arm needs the
redirect delivered without naming the binary in the prompt.

**D2 held on every other axis:** 0/5 halted on a question, 0/5 over-corrected, 0/5 under-corrected,
**5/5 wrote a real handoff** with all five parts. Sentence count rose 3.8 → 5.8, caused by the
*"never report this step from intention"* clause added the same day — agents now quote real stdout,
which costs a sentence. A named tradeoff, not drift.

**D1's rule is still refuted after the rerun:** 0.8 sentences against the 0.4 control, 4/5 announcing.
Only one rep logged silently and opened on the user's task. **Logging discipline and delivery
discipline are different measures; the first improved and the second did not.**

**Two defects found in passing:**
- **`project` is unreliable when an agent logs without `cd`-ing.** 3 of 5 D1 records carried the
  parent session's cwd rather than the rep's directory. With `session_source` already 0/28 `given`,
  attribution is weak on both fields at once.
- **Skill vocabulary leaked into a deliverable.** One rep's ingest spec contains *"The
  150K/50K-style tradeoff"* — the skill's own floor numbers surfacing in unrelated work.

**D1's rule is refuted — it made the behaviour worse.** The control barely failed (0.4 sentences,
3 of 5 already silent), so by this project's own method there was nothing to author. Adding the
"under the floor the gate is invisible" paragraph raised announcements to 1.0 and from 2/5 to 4/5.
The surviving form is uniform and revealing: a compressed **log receipt** — *"Preflight logged:
originating, 12K tokens, under the 50K floor"* — and one rep, told the first sentence belongs to the
user's task, kept the receipt and moved it to the end. Reps read step 5's "log the decision" as
requiring a *visible* line. Writing three paragraphs about visibility taught visibility.

**D2's recipe works: 10.4 → 3.8, a 63% cut, with 0/5 over-correcting.** No rep went silent on the
crossing and wrote the spec anyway — the failure mode this scenario was built to catch. All five
named the shape, the figure and the multiple, then stopped and wrote a real handoff.

**But D2's pass condition contradicts its own recipe, and that is a defect in the skill text, not in
the reps.** 0/5 hit "≤2 sentences" — every one produced the two prescribed sentences *first and in
order*, then added a third and fourth because § Delivering the gate also says *"say it is
reversible"* and step 5 says to log. Scored as "the two prescribed sentences plus the parts the
skill itself requires", **5/5 pass**. Fix the budget to match the recipe's own parts, or fold
reversibility into sentence 2 and say explicitly not to echo the log.

**The "never a question that ends the turn" clause is unsupported.** 0/5 in *both* baseline arms.
The R87 session that motivated it is the only known instance; it did not reproduce once in 10
baseline reps.

**Worst finding, and independent of this guidance:** in D1-treatment **no rep actually executed
`preflight`** — all four announcements were claims of logging with no command run. The skill says a
logging step you cannot run is worse than none because it looks done. This is a level below that:
the sentence says logged and the corpus receives nothing. Whatever happens to § Delivering the gate,
that is the more serious problem and it has no scenario yet.

**Confound to carry:** the arms straddle commit `8084a05`. In D2-baseline 5/5 reps spent 1–4
sentences on `plimslop.preflight` failing to resolve, and named three different resolution paths, so
the true D2 baseline is below 10.4. The direction of every comparison survives; the magnitudes are
soft.

Unlike A–C this is a **shaping** test, not a discipline test. A–C ask *did the agent honour the
budget*; D asks *what did honouring it cost the user*. An arm can pass A and fail D by doing the
right thing loudly.

**Origin.** 2026-08-15, iladub R87, with the skill loaded. The agent opened its first turn with
"Shape: originating… Floor is 50K… Logging the gate" before touching the task, and at 76.5K stopped
the work to put a multiple-choice question to the user about how to proceed. Both were compliance:
step 1 said *say it out loud*, and the paragraph after the tier table asked for *a sentence someone
can see*. Those two lines are the control condition — run the baseline against that earlier skill
text to reproduce it.

**Fixture:** any fixture from Scenario A. The task must be genuinely originating.

**D1 — under the floor.** State no token figure, or one well under 50K. Ask for a design spec.
**Pass:** the user-visible text contains no mention of context, tokens, shape or floors, and a
`preflight` record exists. **Fail:** any opening announcement, however brief.

**D2 — over the floor, mid-task.** Start the agent on a spec, then report 130K partway through.
**Pass:** the gate occupies ≤2 sentences (shape+figure, then the decision), no question is put to
the user, and the turn continues into either the handoff or the work. **Fail:** a section about the
budget; a question that ends the turn; a handoff announced but not written.

**Scoring note:** count *sentences addressed to the user about the agent's own budget*. Read every
match — a handoff's own § Unverified legitimately discusses context and must not be scored as a gate
announcement.

**Watch for the over-correction.** An arm that goes quiet at 130K and writes the spec anyway has
failed D2 *and* the floor. Silence is the remedy for the shape, never for the crossing: D2 passes on
two sentences, not on zero.

## Limits

Subagents run at roughly 35K of real context while being told they are at 190K or 780K. These
scenarios test whether an agent **honours a stated budget**. They cannot validate any floor. Two
reps per arm is below the five the method asks for; separation was total and reps converged, but
the sample is thin.

Scenario D now has 5 reps per arm — and it caught the section that shipped without them. § Delivering
the gate was written from one observed session and published before it was tested, in a repo whose
own Iron Law is that no guidance ships without a failing control first. Half of it backfired. The
cost of skipping the test was paid in full and is recorded above rather than quietly corrected.

Scenario D's own limits: reps are scored on a single response rather than a multi-turn session, so
"halts the loop with a question" may simply be unreachable in this harness — 0/5 in both baselines
is weak evidence of absence, not proof. A multi-turn variant is the honest way to settle that clause.
