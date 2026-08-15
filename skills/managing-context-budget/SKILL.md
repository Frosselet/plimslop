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

1. **Name the shape** — say it out loud, in one line: *originating*, *executing*, or *mechanical*.
2. **Read the figure** — the absolute token count reported for this session. If no figure has been
   reported, you are below every floor; proceed.
3. **Compare to the floor for that shape.**
4. **At or above the floor: do not start.** Write the handoff, and say the work needs a fresh
   session.

| shape | what it is | floor |
| --- | --- | --- |
| **originating** | spec, plan, design, architecture, review, starting a loop — multi-step reasoning producing something others build on | **50K** |
| **executing** | implementing from a plan that already exists in writing | **150K** |
| **mechanical** | reading, searching, answering, a named edit, running tests | ungated |

**These numbers are asserted, not proven.** 50K is anchored on published long-context results
(NoLiMa: 11 of 13 models below half their baseline at 32K; Chroma: decline begins immediately
rather than at a cliff). **150K has no source behind it** — it is an interpolation between a
defensible floor and no floor, and it is the first number here that should be argued with.

Step 1 is doing the real work. A threshold can be crossed silently; a shape stated out loud cannot.
"Originating, 190K, proceeding anyway" is a sentence someone can see.

**Delegating to a subagent is a legitimate remedy, not a loophole.** Subagent context is separate,
so moving a bounded piece of work into one genuinely keeps this session under a floor.

**Compaction does not reset a floor.** It lowers the number without undoing the damage — it is a
lossy summary of this session written by this session. Treat crossing a compaction as a stronger
reason to hand off than crossing a threshold.

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

## Common mistakes

| mistake | what to do instead |
| --- | --- |
| Writing "confirmed", "settled", "verified facts", "do not re-investigate", "don't re-derive" | Say where the evidence lives so it can be reopened. Finality you have not earned is the failure mode this section exists for. |
| Summarising the primaries into the handoff so the next session "won't have to re-read" | Point at them. Saving the next session a file read is not worth handing them a claim they cannot check. |
| Reading the percentage instead of the token count | 19% of 1M is 190K, which is past the originating floor by nearly 4×. |
| Treating a plan you wrote this session as "an existing plan" and claiming *executing* | It is *originating* until it is written down and re-read. Shape follows the artefact, not the intention. |
| Starting the spec because the deadline is today | The deadline is the reason to hand off early, not late. |

## Red flags

- About to write a spec, plan, or design and you have not said the shape out loud
- About to write "already done — do not redo" in a handoff
- Reasoning "I have all the context loaded, so I should be the one to write it" — deep context is
  an argument *for* a handoff, not against one
- A handoff with no "unverified" heading
- "It's only 19%"

## Note on scope

This skill covers the two behaviours that were observed to fail without it. **Resuming** from a
handoff was tested and did not fail: agents reliably opened the primary, caught a handoff that
contradicted it, and escalated rather than resolving it alone. No resumption procedure ships here
for that reason. If your own record later shows resumption failing, that is the point to add one.
