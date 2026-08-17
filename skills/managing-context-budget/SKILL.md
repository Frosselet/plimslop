---
name: managing-context-budget
description: Use when about to originate a spec, plan, design, architecture decision, review, or loop; when a context or token figure has been reported for this session; or when writing a handoff for a fresh session to pick up.
---

# Managing context budget

## Overview

Accuracy degrades with **absolute tokens in the window**, not with the fraction of it used. A
percentage is the wrong unit, and it gets more permissive as windows grow: 40% of a 200K window is
80K, 40% of a 1M window is 400K, and those are not the same claim.

Multi-step reasoning degrades far earlier and harder than factual retrieval. So "I can still recall
the code fine" is not evidence that it is safe to design.

## Pre-flight: before starting work

Do this **before** the work, not as a warning afterwards.

1. **Name the shape** — in one line: *originating*, *executing*, or *mechanical*. How much of this
   reaches the user is § Delivering the gate, and it is usually none of it.
2. **Read the figure** — the absolute token count reported for this session. If no figure has been
   reported, you are below every floor; proceed.
3. **Compare to the floor for that shape.**
4. **At or above the floor: do not start.** Write the handoff, and say the work needs a fresh
   session.
5. **Log the decision** — including when you proceed anyway:

   ```
   plimslop preflight --shape originating --tokens 190000 --decision proceed
   ```

   Declaring `proceed` above the floor is recorded as `overridden`, whatever you called it. That
   is deliberate: the override rate is the only honest measure of whether these floors are usable,
   and a gate whose circumvention nobody can count is a gate that will be circumvented. If the rate
   turns out high, the tiers are wrong — not you.

   If `plimslop` is not on your path, `bin/plimslop` has not been symlinked — README § Installing
   gives the one `ln -s`. From a checkout, `python3 -m plimslop.preflight …` works from the repo root
   and nowhere else. **A logging step you cannot run is worse than none, because it looks done.**

   **And a step you say you ran without running it is worse still.** MEASURED 2026-08-15
   (`TESTS.md` § Scenario D): 4 of 5 agents told the user *"Preflight logged"* having executed
   nothing — every one of them while the command was in fact unresolvable. Run it; don't announce
   it. **Say something only when it FAILED**, because that is the case the user has to fix.

| shape | what it is | floor |
| --- | --- | --- |
| **originating** | spec, plan, design, architecture, review, starting a loop — multi-step reasoning producing something others build on | **50K** |
| **executing** | implementing from a plan that already exists in writing | **150K** |
| **mechanical** | reading, searching, answering, a named edit, running tests | ungated |

**These numbers are asserted, not proven.** 50K is anchored on published long-context results
(NoLiMa: 11 of 13 models below half their baseline at 32K; Chroma: decline begins immediately
rather than at a cliff). **150K has no source behind it** — it is an interpolation between a
defensible floor and no floor, and it is the first number here that should be argued with.

Step 1 is doing the real work. A threshold can be crossed silently; a shape named and logged cannot.
**The record is what makes it visible** — `preflight` writes it whether you proceed or stop, and the
override rate is counted from there, not from anything you say to the user.

**Delegating to a subagent is a legitimate remedy, not a loophole.** Subagent context is separate,
so moving a bounded piece of work into one genuinely keeps this session under a floor.

**The boundary is measurement, not authorship.** Delegate greps, call-site inventories, corpus runs,
cost figures — work whose output is a fact the session can check when it returns. Do **not** delegate
the spec, the plan or the design itself. An agent handed your finished reasoning is a transcriber,
and a transcriber cannot catch a defect in the reasoning it was handed — which is the entire reason
the artefact gets reviewed. Delegating authorship lowers the number without protecting what the floor
protects, and it is harder to spot than an override because nothing gets logged.

**Compaction does not reset a floor.** It lowers the number without undoing the damage — it is a
lossy summary of this session written by this session. Treat crossing a compaction as a stronger
reason to hand off than crossing a threshold.

## Delivering the gate

The gate protects the loop; performing the gate damages it. `stop.py` already applies this in code —
the hook speaks **once per session**, because one that speaks every turn gets switched off, and a
switched-off hook measures nothing. The same holds for prose.

**Under the floor: log it, start the work.** No rule beyond that — a stronger one was written here
and measurably backfired, because guidance about visibility produces visibility (`TESTS.md`
§ Scenario D). Do not re-add it.

**At or over the floor, what the user sees is two parts, in this order:**

1. **The shape and the figure** — "Plan work, and I'm at 2.3× the originating floor."
2. **What you are doing about it** — handing off, or proceeding with the override logged. Where the
   choice is genuinely the user's, fold the recommendation and its reversibility into *this*
   sentence: *"I'm handing off; say the word and I'll write it here with the override logged."*

**Do not narrate the log.** The record on disk is what makes the gate visible — that is the whole
design. Report the command only when it FAILED, which is the one case the user has to act on.

Then continue in the same turn: write the handoff, or do the work.

**Weaker than the rest of this section, and kept at that grade:** don't end the turn on a question
about how to proceed. One real session did (2026-08-15, iladub R87); 0 of 10 pressure reps did
without being told, and those reps cannot show a multi-turn halt (`TESTS.md` § Scenario D).

**The budget is these two parts — never a sentence count.** A count was tried, could not fit the
parts this section itself requires, and failed 5 of 5 agents who had done exactly the right thing.

**Anticipate rather than announce.** Most floor crossings are spent on reading order, which is yours
to manage before it becomes anyone's decision:

- Decide the hard thing first, while fresh, before you have read everything.
- Delegate **measurement** early — subagent context is separate. Never authorship.
- Write the handoff at 30%, while still accurate. An umbrella that exists before the rain makes
  stopping a step rather than a crisis.

## Handoff: what the document IS

A handoff is a **set of pointers**. It says where to look and what was decided; it does not restate
what is in the primaries.

Write these parts, in this order:

1. **Goal** — one line.
2. **Where the primaries are** — paths, commits, files, dashboards. For each: what to establish there.
3. **What was decided, and where that decision is recorded.** If the answer is "nowhere but this
   file", write that. It marks the decision as reversible rather than settled.
4. **Unverified or assumed** — under its own heading. Everything not demonstrated goes here,
   including anything reached late in the session.
5. **The next concrete action** — one action.

**Required in every handoff:** part 3 states a location for each decision, and part 4 exists even
when empty. A handoff without them is a condensed secondary source, which is the artefact that gets
consumed as fact one session later.

## When work has to be redone

The floors above are asserted, not proven, and the only thing that can ever argue with them is a
record of what actually got reworked. When you find work that had to be redone — reverted, rewritten,
abandoned — mark it **at the moment you discover it**, not when it was produced:

```
plimslop mark path/to/file.py --note "rewritten from scratch"
plimslop mark "the approach I abandoned"                   # no artefact is fine
```

It maps the target back to the turn that produced it via `git blame` and the turn log. This is a
statement of **history**, not a judgment of quality: you are recording that something was redone,
not deciding whether it was any good. Markers it cannot attribute are still recorded.

Same path caveat as step 5 above.

## Common mistakes

| mistake | what to do instead |
| --- | --- |
| Writing "confirmed", "settled", "verified facts", "do not re-investigate", "don't re-derive" | Say where the evidence lives so it can be reopened. Finality you have not earned is the failure mode this section exists for. |
| Summarising the primaries into the handoff so the next session "won't have to re-read" | Point at them. Saving the next session a file read is not worth handing them a claim they cannot check. |
| Reading the percentage instead of the token count | 19% of 1M is 190K, which is past the originating floor by nearly 4×. |
| Treating a plan you wrote this session as "an existing plan" and claiming *executing* | It is *originating* until it is written down and re-read. Shape follows the artefact, not the intention. |
| Starting the spec because the deadline is today | The deadline is the reason to hand off early, not late. |
| Opening the turn by naming the shape and the figure when nothing binds | Log it and start the work. Under the floor the gate is invisible. |
| Delegating the spec or plan itself so the session stays under a floor | Delegate measurement; author the artefact yourself. A transcriber cannot catch a defect in reasoning it was handed. |

## Red flags

- About to write a spec, plan, or design and you have not said the shape out loud
- About to write "already done — do not redo" in a handoff
- Reasoning "I have all the context loaded, so I should be the one to write it" — deep context is
  an argument *for* a handoff, not against one
- A handoff with no "unverified" heading
- "It's only 19%"
- A paragraph about your own token count in a turn where the user asked for work

## Note on scope

This skill covers the two behaviours that were observed to fail without it. **Resuming** from a
handoff was tested and did not fail: agents reliably opened the primary, caught a handoff that
contradicted it, and escalated rather than resolving it alone. No resumption procedure ships here
for that reason. If your own record later shows resumption failing, that is the point to add one.

**§ Delivering the gate rests on a different kind of evidence from the rest.** It began with a
failure observed **with** this skill loaded — one real session (2026-08-15, iladub R87), not a
pressure scenario. The agent complied with every rule above and still damaged the loop: it announced
the shape before doing any work, then halted mid-task to ask permission to continue. It was not
misreading; step 1 and the paragraph after the tier table told it to *"say it out loud"* and produce
*"a sentence someone can see"*. That is a **wrong-shape** failure rather than a discipline failure,
so the remedy is written as a recipe — stating what the output IS — and not as a prohibition, which
the superpowers:writing-skills guidance reports measurably backfiring on this class.

**It has since been run**, and half of what shipped did not survive (`TESTS.md` § Scenario D, 5 reps
× 4 arms, plus a rerun scoring the corpus rather than the claim). The over-floor recipe held: 10.4 →
3.8 sentences, 0/5 over-correcting, 5/5 writing a real handoff. Two rules did not, and both are now
gone: an under-floor silence rule that raised announcements against its own control, and a
≤2-sentence budget that contradicted the parts this section itself requires. The one clause still
resting on the original n=1 is the question prohibition, marked as such where it appears.
