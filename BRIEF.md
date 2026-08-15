# BRIEF — read this first

> **THIS FILE IS HISTORY, NOT CURRENT STATE.** It is the originating handoff, preserved as
> written plus the Task 1 findings. Its "nothing is designed yet" framing was true on the
> morning of 2026-08-15 and is false by that evening: there is an approved design, a tested
> skill, and two working hooks. **Read `HANDOFF.md` first for where things actually stand.**

**Status when written: SCAFFOLD ONLY.** Nothing here is designed yet. This file is the handoff
from the session that had the idea (2026-08-15, working in the origin repo), written so a fresh session
can resume without re-deriving anything.

**The name is now `plimsoll`** (`deadweight` was settled first, then superseded the same day — see § Task 1
results). The provisional name `context-discipline` survived as the directory name until it was
renamed on 2026-08-15, and
should be renamed when convenient; nothing depends on it.

---

## What this is meant to become

A small, installable set of three things that keep a coding-agent session honest about its own
context budget:

1. **A gauge** — a right-aligned status-line bar showing context used, so the human can see it.
2. **A hook** — the only part that can actually reach the model, injecting the figure each turn.
3. **A skill** — the procedure: a pre-flight check before starting costly work, a handoff
   protocol, and a resumption protocol.

The gauge and hook already exist in prototype (§ What already exists). **The skill does not, and
it is the actual product** — the gauge is the visible part, the protocol is the valuable part.

## First actions, in order

1. ~~**Naming check, before anything is pushed.**~~ **DONE 2026-08-15** — § Task 1 results.
2. ~~**Prior-art sweep on the gauge specifically.**~~ **DONE 2026-08-15** — § Task 1 results.
   The anticipated outcome is the one that occurred: the gauge should not be published.
3. Only then: brainstorm the skill. ← **next**

---

## Task 1 results (swept 2026-08-15)

### Naming: `context-discipline` fails, and not on collision

| check | result |
| --- | --- |
| PyPI `context-discipline` / `context_discipline` / `contextdiscipline` | all 404 — free |
| GitHub exact repo name | no collision |
| same-domain prior art | **fails** |

PyPI is clear and no repo carries the name, but the criterion this file set — *no same-domain prior
art* — is not met. "Context discipline" is already generic descriptive vocabulary in this exact
domain, appearing in the **descriptions** of unrelated projects: `anothervibecoder-s/claudecode-harness`
(★223, "Context discipline, subagents…"), `Fearvox/multica-ultimate-workbench` (★26),
`kmshihab7878/claude-code-setup` ("context-budget discipline"), `gregorriegler/yak-shaving-kata`
("Kata to practice context discipline"). Nearest named things: `symbolicmatter/llm-context-discipline`
(★0) and `geopolitis/cdad` = "Context-Disciplined Agent Development".

So the name is not taken — it is **unclaimable**. It reads as a category label rather than a product
and will never be findable by search. Rename before pushing.

**Resolved 2026-08-15: the name is `deadweight`.** Free on PyPI; no agent- or context-tooling prior
art. Two caveats accepted knowingly: npm is taken, and the word already reads as *unused-code
detection* in software generally (`aanand/deadweight`, ★1181, marked NOT MAINTAINED;
`rails_deadweight`). That connotation was judged to help rather than hurt, since the design reports
unused MCP servers. `plimsoll` was the runner-up — free everywhere, no prior art, and a closer
metaphor (an absolute load line, several of them for different conditions) — and remains the
fallback if `deadweight` proves confusing.

**Superseded 2026-08-15: the name is `plimsoll`.** The runner-up was promoted on the owner's
call, for the reason recorded above plus one not anticipated here: `deadweight` carries the word
*dead*, which was not wanted. The metaphor also survives the change intact — deadweight tonnage is
precisely what a Plimsoll line measures, so the two names describe the same thing from opposite
ends, the capacity and the mark. `deadweight`'s own sweep result stands unedited above: it was a
sound name, and the decision that replaced it was preference, not a defect found. **The plimsoll
sweep was then run, 2026-08-15, and **`plimsoll` FAILS the same criterion `context-discipline`
failed.**

| check | result |
| --- | --- |
| PyPI `plimsoll` | 404 — free |
| npm `plimsoll` | **taken** — dormant Sails.js Postgres adapter, last published 2020 |
| GitHub exact repo name | **20+ repos**, none with traction (max ★10) |
| same-domain prior art | **fails, worse than `deadweight` did** |

The runner-up note said "free everywhere, no prior art". That was wrong on both counts. Four repos
named exactly `plimsoll` are LLM/agent tooling, all created within the last ten weeks:

- `CryptoJym/plimsoll` (2026-06-10) — *"The load line for your AI spend — local-first telemetry for
  Claude Code & Codex that joins token usage to shipped outcomes. Open core, privacy-first."*
  **That is this product's pitch, metaphor and all.**
- `Raghu23-dev/plimsoll` (2026-08-06) — *"Load and capacity harness for LLM agent services. Finds
  the safe load line."*
- `theo-ai-lab/plimsoll` (2026-06-01), `boaglio/plimsoll` — *"Non Official Claude Usage GUI"*
- adjacent: `mtnygard/plimsoll` — capacity analysis for software systems

So the load-line metaphor is **already generic vocabulary for AI capacity tooling**, reached for
independently by several people in the same quarter. That is precisely why `context-discipline`
was rejected: not taken, but unclaimable. `deadweight`'s own sweep, by contrast, found no agent- or
context-tooling prior art at all.

Nothing here blocks the name — no competitor has traction. It is a findability judgment, and it is
now an informed one. **`deadweight` remains the only name in this project that has passed the
criterion.**

### The gauge: do not publish it

Unambiguous. 736 GitHub repos match "claude code statusline context". The field:

- `jarrodwatts/claude-hud` — **★27,401** — context usage, active tools, running agents, todos
- `henchmarketing-rgb/headroom` — ★68 — *"Know your headroom. Context window usage bar for Claude
  Code."* Same product, same framing
- `stephenleo/cship` ★414, `leeguooooo/claude-code-usage-bar` ★349,
  `ilia-pluzhnikov/claude-code-statusline` ★104, and ~20 more at ★13–50, all shipping context bar +
  rate limits + git state

The prototype's measured findings (`COLUMNS` authoritative; preferring
`context_window.total_input_tokens`) are implementation details, not differentiation — several of
these read the same payload. Keep the gauge as a personal script; point users at claude-hud or
headroom.

### The protocol: explored, but not landed

The whole cohort sits at ★0–3.

- **`vsrox-cliqq/context-governor`** (★3) — closest to the entire product. Measures every tool call,
  **ends the session at 60% of the window**, boots the next from a structured handoff ledger
- **`reganomika/HighWater`** (★2) — `Stop` hook forcing a task-boundary checkpoint at **55% / 88%**,
  per-model; recalibrates the hard mark downward the first time it witnesses a real auto-compaction
- **`silvesterdivas/context-engineer`** (★0) — Budget Zones skill (GREEN/YELLOW/ORANGE/RED),
  Degradation Detection skill, Fresh Context Pattern (TASK.md + PROGRESS.md handoff)
- `Artim-Nayas/token-manager` (★1) "tiered behavioral guidance"; `leaflessbranch/cc-pacekeeper` (★1)
  self-pacing, thresholds, resumable checkpoints

**Every one of them ships a percentage constant.** § The load-bearing finding is therefore not
the origin repo's local error — it is the field's shared error. On a 1M window HighWater's 55% is 550K
tokens; NoLiMa found 11 of 13 models below half their baseline at **32K**. Chroma's 18-model study
found steady decline from the start rather than a cliff, which undercuts the threshold framing
everyone is using, including R76's.

### What the sweep leaves unoccupied

1. **Absolute-token denomination.** Nobody found does this.
2. **Measure-your-own-curve.** HighWater's auto-compaction recalibration is the cohort's only
   adaptive mechanism, and it calibrates to a *harness event*, not to work quality. No one logs
   tokens-at-turn against outcome markers.
3. **Staleness as a separate mechanism** (§ Three mechanisms). Every tool found treats "context is
   big" as the only failure mode, so all prescribe a fresh session — which does nothing for a stale
   fact consumed as truth.

### Carried into the scope decision

`context-governor` and `HighWater` are close enough that this repo must state plainly what it does
that they do not, or it is a sixth entrant to a category with no winner. The ★0–3 ceiling across the
whole protocol cohort is its own signal — either the idea does not get adoption, or nobody has
cracked packaging it. That bears on "disseminate", not on the one-user MVP.

Sweep method: PyPI JSON API; `gh api search/repositories` on five queries; two web searches. Star
counts are as of 2026-08-15.

## What already exists, and exactly where

| thing | path | notes |
| --- | --- | --- |
| the gauge (live copy) | `~/.claude/statusline-context-gauge.py` | wired via `statusLine` in `~/.claude/settings.json` |
| the gauge (repo copy) | *removed 2026-08-15* | deleted before publication, per the sweep. Only the live copy remains, so there is no longer a fork |
| the hook | `<origin>/scripts/context_budget.py` | `UserPromptSubmit` hook in the origin repo's `.claude/settings.json` |

`<origin>` = `<origin>`.

Both read the same figure: `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.
The gauge prefers the status-line payload's `context_window.total_input_tokens` (present in Claude
Code 2.1.226; verified to equal that sum) and falls back to scanning the transcript tail. It
imports `HANDOFF_PCT` / `STOP_PCT` / `WINDOW` from `context_budget.py` when `CLAUDE_PROJECT_DIR`
points at the origin repo, so the two cannot drift there.

Measured while building the gauge, worth not rediscovering:
- The status-line command runs with **no tty on any descriptor** but **with `COLUMNS` set** to the
  real width. `COLUMNS` is authoritative; check it first.
- The payload carries `context_window`, `cost`, `rate_limits`, `effort`, `model`, `workspace.repo`
  and more — a lot is available for free without reading any file.

## The load-bearing finding: the 40% rule is denominated in the wrong unit

the origin repo's `CLAUDE.md` records R76: *never work past 40% of the context window*, with 30% as the
handoff mark. **Do not ship that number.** What was found on 2026-08-15:

**Its evidence is weak.** One session (2026-08-09), uncontrolled, self-assessed, confounded — late
sessions also hold the harder residual work. A real signal, but not evidence for a threshold at 40%.

**Its unit is wrong, and the error grows with window size.** The literature anchors degradation to
*absolute* token counts, not to a fraction of the window (a commonly cited figure: serious loss at
~50K tokens inside a 200K window). So a percentage rule becomes monotonically more permissive as
windows grow:

| window | R76's 40% line | absolute tokens |
| --- | --- | --- |
| 200k | 40% | 80k |
| **1M (the setup R76 was written on)** | **40%** | **400k** |

The 2026-08-09 observation that "the later 71% of the session produced five blocked specs" is fully
consistent with degradation having begun *hundreds of thousands of tokens earlier*, with 40% merely
being where it became noticeable enough to name. **The rule is probably far too loose, not too
strict.**

Corollary for this repo's design: **denominate the budget in absolute tokens; show the percentage
only as display.**

## Three mechanisms — and only two are about length

1. **Attention dilution** — more candidate material, more chance of attending to the wrong thing.
2. **Positional burial** — the U-shaped "lost in the middle" effect; a fact established mid-session
   is weaker than one at either end.
3. **Staleness — NOT a context-length effect at all.** This one dominates the real recorded
   incidents in the origin repo: a residue index line consumed as fact (twice, R87 and R88), a code comment
   saying "widened on this branch only" that had long since shipped, and — found the same day — a
   residue row whose own closing *instruction* was wrong. A fresh session does not fix any of
   these; **opening the primary source does.** Keep this separate in the design or the skill will
   prescribe the wrong remedy.

Also load-bearing: **multi-step reasoning degrades much earlier and harder than factual
retrieval.** Writing a spec or a plan is multi-step reasoning, which is why "the model can still
recall things fine" is not evidence that it is safe to design.

## The design principle that follows

Do not ship a constant. Ship the discipline, and **make the tool collect the evidence**: the hook
already measures every turn, so log tokens-at-turn against outcome markers and let a user see their
own curve. That converts an ungrounded constant into something promotable on evidence — which is
the origin repo's own assert / propose / promote epistemics applied to its own tooling, and the honest
answer to "is 40% right?": *measure it, don't inherit it.*

## Process decision (settled — do not re-litigate)

**Brainstorm yes. Spec no. Plan no.** the origin repo's spec→plan ceremony is calibrated to product code with
SHACL membranes, derivation queries and falsifiable oracles, where five defects were once found in a
plan's own text. A skill is markdown with no membrane and no oracle; the ceremony would be form
without cause. Use `superpowers:writing-skills` when authoring.

A short brainstorm still earns its keep — the open questions below are real.

## Open design questions

- **Is the pre-flight check even buildable as conceived?** Estimating "how much context will this
  task consume" before running it invites a tuned constant, which the origin repo's §8 gate treats as prima
  facie evidence that a decision belongs elsewhere. The honest form may be far simpler — a rule
  about *task shape* ("a loop, a spec or a plan starts below N tokens, full stop") rather than a
  cost model. **Attack this premise before designing around it.**
- Trigger: model-invoked by description, or the hook injecting a pointer to the skill?
- Scope: personal (`~/.claude/skills/`) or project skill? The gauge went user-scope so it survives
  branch switches; the same argument probably applies.
- Should `context_budget.py`'s injected prose be replaced by a pointer at the skill?
- Licensing: not decided. the origin repo uses Apache-2.0 for code and CC-BY-4.0 for vocabulary/spec; this
  repo is separate and the choice is open.

## Scope discipline

MVP is gauge + hook + skill working for **one user** — though § Task 1 results puts the *published*
composition back in play (gauge almost certainly out; hook's injection mechanism is also largely
commodity in that cohort). Scope not yet re-decided.

"Disseminate it" is a separate decision that
should follow the prior-art sweep *and* enough collected turn-by-turn data to say something honest
about where the line sits. Publishing the discipline is defensible today; publishing a threshold
is not.

## Note on continuity

Auto-memory is **per project directory**. The notes from the originating session live under
`~/.claude/projects/<origin>/memory/` and **will not load in this repo.**
This file is deliberately self-contained for that reason. The note on the origin side is
`context-discipline-skill-idea.md`.

Unrelated and still queued on the origin side: the **R87 plan** (spec written and committed on a
branch there). Unaffected by this work, and named here only so it is not lost.

## Sources (single search, 2026-08-15 — NOT a literature review; vet before citing publicly)

- Context Rot: Why Long-Context LLMs Degrade — https://www.tmls.nyc/research/context-rot-mechanistic
- Context Length Alone Hurts LLM Performance Despite Perfect Retrieval (EMNLP Findings 2025) —
  https://aclanthology.org/2025.findings-emnlp.1264.pdf
- Positional Failures in Long-Context LLMs — https://arxiv.org/pdf/2605.23170
- Context Discipline and Performance Correlation — https://arxiv.org/html/2601.11564v1
- Context Rot, RAG, and Long Context — https://glasp.co/articles/context-rot-rag-long-context-hybrid

Added by the 2026-08-15 sweep (same caveat — vet before citing publicly):

- Context Rot: Why LLMs Degrade as Context Grows — https://www.morphllm.com/context-rot
- Context Engineering: Why More Tokens Makes Agents Worse — https://www.morphllm.com/context-engineering
- The Context Rot Problem: Why AI Coding Agents Get Worse As They Work —
  https://empromptu.ai/resources/context-rot-progressive-prompt-ephemerality
- Evaluating Context Compression for AI Agents (Factory.ai) — https://factory.ai/news/evaluating-compression
- 1M Tokens Won't Save Your Engineering Standards — https://straion.com/blog/1m-tokens-wont-save-your-engineering-standards/
- Claude Code Context Window / context management (claudefa.st) —
  https://claudefa.st/blog/guide/mechanics/context-management
- `skillListingBudgetFraction` computed against a fixed ~200K baseline, not the real window
  (anthropics/claude-code#57941) — https://github.com/anthropics/claude-code/issues/57941
  *Relevant: the harness itself makes the percentage-vs-absolute error this repo is about.*

Prior art referenced in § Task 1 results:

- https://github.com/jarrodwatts/claude-hud · https://github.com/henchmarketing-rgb/headroom
- https://github.com/vsrox-cliqq/context-governor · https://github.com/reganomika/HighWater
- https://github.com/silvesterdivas/context-engineer
