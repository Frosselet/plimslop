# Pressure scenarios for `managing-context-budget`

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

## Limits

Subagents run at roughly 35K of real context while being told they are at 190K or 780K. These
scenarios test whether an agent **honours a stated budget**. They cannot validate any floor. Two
reps per arm is below the five the method asks for; separation was total and reps converged, but
the sample is thin.
