> **UNREVIEWED — NOT APPROVED, NOT A DECISION.**
>
> Produced by subagents running a test scenario that had already been established as invalid.
> Two of them wrote this same file concurrently, racing each other, and amended the approved
> design document until that was reverted. Nothing here has been checked.
>
> It is kept because two ideas in it look worth stealing: reframing the reader's refusal rule
> from sample size to interval width, and the argument that no trend should ever be fitted.
> Verify anything you take. See `HANDOFF.md` §4.

# plimsoll — the reader, in detail

*Expansion of §7 of [`2026-08-15-context-budget-skill-design.md`](2026-08-15-context-budget-skill-design.md).
That section settles what the reader is; this one settles what it does.*

**Date:** 2026-08-15
**Status:** detailed design, **not yet approved**. Written to unblock implementation.
**Scope:** the reader only — the three views, attribution resolution, the refusal rule, and
`session_summary` rollups. The marker command, the two hooks and the skill are designed in the
parent document and are referred to here, not redesigned.

**Four things in here change the parent's §7** and need sign-off before implementation starts. They
are listed in §9 with the section that argues each one. Everything else expands §7 without moving
it.

**Everything numeric in this document is graded.** Where a number is *proposed* it is a default a
user can change, and the observation that would settle it is stated. Nothing here is *promoted*.
Shipping an ungrounded constant inside the tool built to stop people shipping ungrounded constants
would be the project's worst possible failure, and the reader is where that temptation is
strongest — it is the part that draws the graph.

---

## 1. Command surface

One binary, `plimsoll`, with the reader occupying three subcommands and the §7 marker command a
fourth:

```
plimsoll curve     [strata and filter options]
plimsoll baseline  [filter options]
plimsoll tiers     [filter options]
plimsoll rework    <target> [--session|--commit|--note]   # §7 marker, designed elsewhere
```

**Decision: one binary, not two.** The marker writes to the corpus that the reader reads, both
resolve attribution against the same git logic (§4), and a user who has installed one has installed
the other. Two commands would duplicate the attribution code, and duplicated logic that drifts from
its source is the failure mode this whole project is about.

### 1.1 Global options

| option | default | note |
| --- | --- | --- |
| `--project <path>` \| `--project all` | `all` | see below |
| `--since <ISO date>` / `--until <ISO date>` | whole corpus | |
| `--last <n>` | — | last *n* sessions, ordered by end time |
| `--json` | off | machine-readable; **carries the refusal, see §5.6** |
| `--include-low` | off | admits `low`-confidence attributions to rate arithmetic (§4.5) |
| `--width <cols>` | `$COLUMNS`, else 80 | clamped to 60–120 |
| `--no-color` | auto | off when not a tty, or when `NO_COLOR` is set |
| `--rebuild` | off | re-derive every `session_summary` (§6.6) |
| `--corpus <dir>` | `~/.claude/plimsoll` | testing hook |

**`--project` defaults to `all`, deliberately.** The corpus is cross-project by design (§3 of the
parent) precisely so *n* accumulates. Defaulting to the current project would silently narrow every
view to the thinnest possible slice and make the refusal rule fire constantly for reasons that have
nothing to do with the evidence. The default is the wide slice; narrowing is an explicit act, and
the header always states which slice is in force.

### 1.2 Exit codes, and how far §8 binds the reader

§8 of the parent — *the tool is never the reason a session fails* — is written for the hooks, which
run inside someone's turn. **The reader is a user-invoked CLI and is not bound by it in the same
way**, because a reader that silently returns nothing when its arguments are wrong is a reader that
lies about an empty corpus.

| code | when |
| --- | --- |
| 0 | rendered successfully — **including when every cell refuses.** A refusal is an answer, not a failure |
| 2 | usage error: unknown subcommand, unparseable date, unreadable `--corpus` |
| 1 | unexpected internal error, one line to stderr, no traceback |

What the reader *does* inherit is the spirit: **bad data degrades the answer, it never prevents
one.** A corrupt corpus line, an unreadable transcript, a busy lock — each is skipped, counted, and
reported in the header (§3.1). The distinction is that the reader fails loudly on *its own*
misuse and silently on *the corpus's* defects, and the two are never confused.

### 1.3 Output medium

Plain text on a monospaced terminal. No plotting library, no image output, no HTML. Colour is used
only to mark refusal and warning states and never carries information on its own — the same view
piped to a file must say the same things.

---

## 2. Data the reader consumes

| source | written by | read for |
| --- | --- | --- |
| `turns-YYYY-MM.jsonl` | `UserPromptSubmit` hook | tokens-at-turn, baseline, model, window, compaction flag |
| `preflight-YYYY-MM.jsonl` | skill | declared shape, decision, overrides |
| `rework.jsonl` | marker command, and reader re-resolutions (§4.6) | rework markers and their attribution |
| `summaries.jsonl` | **the reader itself** (§6) | producing turns, tool/server usage, files written |
| `~/.claude/projects/*/*.jsonl` | Claude Code | source for `session_summary` derivation only |
| `~/.claude/settings.json`, `~/.claude.json`, `<project>/.mcp.json` | the user | the declared MCP roster (§3.2) |
| the git repository | the user | attribution (§4) |

Monthly rotation on `turns-` and `preflight-` files answers §8's "rotation should be documented".
`rework.jsonl` and `summaries.jsonl` are low-volume and unrotated. The reader globs and merges;
a missing month is not an error.

**Config files are opened read-only and never written.** §6's hard non-goal — *the tool reports, it
never applies* — is enforced structurally: the reader opens `settings.json` with mode `r` and has
no code path that writes anywhere except the corpus directory.

### 2.1 Transcript fields the derivation depends on

Verified against real transcripts on this machine (Claude Code 2.1.x, 2026-08-15):

| field | use |
| --- | --- |
| `type: "assistant"` + `message.content[].type == "tool_use"` + `.name` | tool and server usage (§3.2) |
| `isSidechain` | separates subagent activity from main-chain (§6.4) |
| `sessionId`, `timestamp`, `cwd`, `gitBranch`, `version` | session identity and slicing |
| `message.usage.{input,cache_read_input,cache_creation_input}_tokens` | the token figure, summed as the hook sums it |
| `type: "system"`, `subtype: "compact_boundary"`, `compactMetadata` | **compaction, exactly** — see below |
| `toolUseResult` | whether a Write/Edit actually succeeded (§6.3) |

**Finding worth carrying back into the parent document.** §10 specifies a test for "post-compaction
flag set when totals drop discontinuously" — a heuristic. Transcripts carry an explicit
`compact_boundary` system record whose `compactMetadata` gives `trigger` (`auto`/`manual`),
`preTokens`, `postTokens` and `cumulativeDroppedTokens`. The reader uses the explicit record and
treats discontinuity detection only as a fallback for transcripts that lack one. This makes §8's
"post-compaction turns are flagged" exact rather than inferred, and it gives the corpus the size of
what was dropped for free.

MCP tool names follow `mcp__<server>__<tool>`; the server is the middle segment. Plugin-provided
servers appear as `mcp__plugin_<plugin>_<server>__<tool>` and are attributed to the plugin.

---

## 3. The three views

Every view opens with the same header, so no rendered output is ever ambiguous about which slice of
which corpus produced it.

### 3.1 Header

```
plimsoll <view> · <one-line description>
corpus  ~/.claude/plimsoll  ·  all projects  ·  2026-06-30 → 2026-08-15
        41 sessions · 3,812 turns · 604 producing turns · 27 rework markers
        2 sessions unsummarised (unreadable transcript) · 1 corpus line skipped
```

The fourth line appears only when something was skipped, and it never suppresses the view. A tool
that silently drops the data it could not read reports a cleaner corpus than it has.

### 3.2 `plimsoll baseline`

The §6 report: items (a) and (b), with (c) explicitly absent rather than estimated.

```
plimsoll baseline · what is in the window before you type
corpus  ~/.claude/plimsoll  ·  all projects  ·  2026-06-30 → 2026-08-15
        41 sessions · 3,812 turns · 604 producing turns · 27 rework markers

  BASELINE TOKENS PER SESSION
    median    38,400          p90       52,100
    min       21,900          max       61,300          most recent  44,700

    at or above the 50,000 originating floor in 11 of 41 sessions (27%)

  ⚠ UNSATISFIABLE GATE
    In 11 sessions the baseline alone met or exceeded the 50,000 originating
    floor. In those sessions originating work is refused from turn one.
    Per §9 enforcement degrades to `warn` there — the floor is not silently
    blocking you, and this line is why.
    Reduce the baseline, or revise the tier. plimsoll will do neither.

  DECLARED, AND USED
    roster from settings.json, ~/.claude.json and .mcp.json · usage from
    transcripts over 41 sessions

    server                       tools   invocations   last invoked
    ─────────────────────────────────────────────────────────────────
    claude-in-chrome                31             0   never
    plugin_playwright_playwright    24             0   never
    claude_ai_Gmail                  2             0   never
    ide                              2            14   2026-08-11
    ─────────────────────────────────────────────────────────────────
    3 of 4 declared servers were never invoked in 41 sessions.

    Read this as what you paid for and did not use. It is not a
    recommendation: plimsoll cannot know what you need, and it will not
    change your configuration.

  PER-SOURCE TOKEN ATTRIBUTION
    Not implemented (§6c, fast follow). Total baseline is measured; its
    breakdown is not. No estimate is shown in preference to a wrong one.
```

Notes on the derivation:

- **The roster cannot come from transcripts.** A server that was never invoked leaves no trace in
  one. The declared roster is read from config; usage is counted from transcripts; the interesting
  set is roster-minus-used. Both halves are stated in the output because they have different
  provenance and different reliability.
- **`tools` is the declared schema count, not the resident count.** Where tool definitions are
  deferred behind a search mechanism, the schemas are not all in the window at once, and the column
  overstates the weight. The reader prints a one-line caveat when it detects deferred-tool records
  (`ToolSearch` invocations) in the slice. Getting this wrong would inflate exactly the number the
  view exists to make actionable.
- **Below `n_min` sessions the "never invoked" claim is suppressed**, and the table prints raw
  counts with `n=6 sessions — too few to call anything unused`. §6's second non-goal — *no
  recommendation without evidence behind it* — binds this view as much as the curve.
- Baseline per session is the `baseline_tokens` field of the session's first turn record. Sessions
  with no turn record (installed mid-session) are excluded and counted in the header.

### 3.3 `plimsoll curve`

Rework against tokens-at-production, stratified by shape and baseline band. This is the view the
refusal rule exists for, and most of the time it will refuse.

```
plimsoll curve · rework against tokens-at-production
corpus  ~/.claude/plimsoll  ·  all projects  ·  2026-06-30 → 2026-08-15
        41 sessions · 3,812 turns · 604 producing turns · 27 rework markers

  ATTRIBUTION   exact 6 · high 9 · medium 5 · low 4 · unattributed 3
                low-confidence points are excluded from rates (--include-low)
                unattributed fraction 3/27 = 11%

  ORIGINATING · baseline band 20–40K

    tokens-at-production   producing   reworked   observed
    ──────────────────────────────────────────────────────────────────
        0 –  25K                  41          2   4.9%  [1.4 – 16.1]
       25K –  50K                 33          3   9.1%  [3.2 – 23.6]
       50K –  75K                 18          2   n=18 — below n_min=20
       75K – 100K                  9          2   n=9 — this shows nothing
      100K +                       4          1   n=4 — this shows nothing

    NO COMPARISON DRAWN. 2 buckets are precise enough to describe, and
    their intervals overlap (§5.3). No trend is fitted at any n.
    Brackets are Wilson 95% intervals on the bucket proportion. They
    describe what was observed in this corpus. They are not an estimate
    of your rework rate.

  ORIGINATING · baseline band 40–60K            5 producing turns — omitted
  EXECUTING   · baseline band 20–40K           88 producing turns
  ...

  27 markers · 3 unattributed
    no-turn-records 2 · ambiguous-session 1
```

Once two buckets in a stratum are precise enough to describe *and* their intervals are disjoint, the
same stratum renders marks and an ordering:

```
  ORIGINATING · baseline band 20–40K

    tokens-at-production   producing   reworked   observed
    ──────────────────────────────────────────────────────────────────
        0 –  25K                 210         14   6.7%  [4.0 – 10.9]
                                                  ██████│
       25K –  50K                163         17   10.4% [6.6 – 16.0]
                                                  █████████│
       50K –  75K                141         26   18.4% [12.9 – 25.7]
                                                  ████████████████│
       75K – 100K                104         27   26.0% [18.4 – 35.3]
                                                  ███████████████████████│
      100K +                      38          9   23.7% [13.0 – 39.2]
                                                  ±0.26 — described, not
                                                  compared (interval overlaps)
    ──────────────────────────────────────────────────────────────────
                              0%      10%      20%      30%      40%

    OBSERVED, NOT EXPLAINED. Rework was more frequent above 50K than
    below it in this corpus (0–25K 6.7% [4.0–10.9] vs 75–100K 26.0%
    [18.4–35.3]; intervals disjoint). plimsoll does not claim the
    tokens caused it. Late work in a session is also harder work, and
    that confound is not removable by stratification (§8).
```

Rules that govern this rendering:

- **The bar is the point estimate; the `│` is the upper interval bound.** Nothing is drawn for a
  bucket that refuses.
- **Comparative language appears only between buckets whose Wilson intervals are disjoint**, and
  only in the fixed template shown above. There is one sentence template for a comparison and one
  for its absence; neither can be reached by any other code path. §8's "never claims causality" is
  enforced by there being no string in the binary that could express it.
- **No trend is fitted, at any *n*.** See §5.3 — this is one of the four changes to the parent.
- **Buckets are 25K wide** — *proposed*, display-only. No decision anywhere reads the bucket
  width; it is changed with `--bucket`. It is 25K because it is half the originating floor, so the
  floor always lands on a bucket edge.
- **Baseline bands are `<20K`, `20–40K`, `40–60K`, `≥60K`** — *proposed*, display-only, chosen to
  bracket the 50K floor. Per §5 of the parent, "rework at 120K with a 20K baseline" and the same at
  90K baseline are different experiments, and merging them would manufacture another ungrounded
  constant. Bands may be flattened with `--no-strata`, which prints a warning that it has been done.
- **Strata below `n_min` producing turns collapse to one line** rather than printing five refusals
  each. The count is still shown; the data is not hidden, only folded.
- **`--shape` and `--band` select a single stratum.**

#### The denominator, which is the most arguable choice here

Rework *count* against tokens is meaningless — more turns happen at some token levels than others,
and the distribution of turns over tokens is itself strongly non-uniform. The view needs a rate,
and a rate needs an exposure denominator. §7 of the parent does not name one.

**Decision: the denominator is producing turns.** A *producing turn* is a turn in which at least
one `Write`, `Edit` or `NotebookEdit` call succeeded against a file inside the project. This is
derivable from transcripts, rolled up per session (§6.3), and it is the population that rework
markers are drawn from — a turn that only read files cannot generate a rework marker, so counting
it as exposure would dilute the rate in a token-dependent way.

Rejected alternatives, recorded because the choice will be revisited:

- **All turns.** Available and simple, but mechanical turns are neither uniformly distributed over
  tokens nor capable of producing rework. The rate would be a mixture of two things.
- **Preflight records.** The right conceptual unit — one per decision to begin work — but far too
  sparse to be a denominator, and only present for gated shapes.

The count of all turns is still printed in the header, so the reader can see how much of the
session the denominator represents.

### 3.4 `plimsoll tiers`

Current floors, their grades, and whether the corpus supports, contradicts, or cannot yet speak to
each. This view is where the project's own claims get audited.

```
plimsoll tiers · floors, grades, and what the corpus says
corpus  ~/.claude/plimsoll  ·  all projects  ·  2026-06-30 → 2026-08-15
        41 sessions · 3,812 turns · 604 producing turns · 27 rework markers

  ORIGINATING                                 floor  50,000 tokens
    grade         asserted, literature-anchored (NoLiMa; Chroma; ~50K)
    enforcement   block · degraded to warn in 11 of 41 sessions
                  (baseline ≥ floor, §9)
    corpus        CANNOT YET SPEAK
                  below floor   n=74   6.8%  [3.0 – 14.8]   ±0.12
                  above floor   n=31   16.1% [7.1 – 32.6]   ±0.26
                  The above-floor interval is wider than max_width, and
                  the two intervals overlap. The observed direction is
                  consistent with the floor. That is not support.
    demoted by    both arms precise enough to describe, within a baseline
                  band, with the above-floor rework rate not exceeding the
                  below-floor rate by 1.5× — that is, the upper bound on
                  the difference falling below that effect. Then 50,000 is
                  not doing work and should fall.
    preflight     31 recorded · 9 overridden (29%)

  EXECUTING                                   floor  150,000 tokens
    grade         asserted, WEAKEST — extrapolated, no direct support.
                  This should be the first tier the corpus argues with.
    enforcement   warn
    corpus        CANNOT YET SPEAK
                  below floor   n=402  4.2%  [2.6 – 6.7]    ±0.04
                  above floor   n=11   n=11 — this shows nothing
    demoted by    as above, at 150,000.
    preflight     58 recorded · 31 overridden (53%)
                  ⚠ Above 50%. On §7's own reading the tier is wrong,
                    not the user.

  MECHANICAL                                  ungated
    grade         asserted from "retrieval survives longer"
    enforcement   off
    corpus        NOT APPLICABLE — no floor to support or contradict.
                  Observed rework among mechanical producing turns is
                  reported in `curve` for completeness. plimsoll does
                  not propose a floor where none exists; moving floors
                  from corpus evidence is §12, deferred.
    preflight     0 recorded — mechanical work is ungated, so the skill
                  logs no decision.
```

The verdict is mechanical, computed per tier from two arms — producing turns below the floor and at
or above it — within a baseline band, with bands combined only if every band individually qualifies:

| verdict | rule |
| --- | --- |
| `CANNOT YET SPEAK` | either arm refuses under §5.3, **or** intervals overlap and the difference is not bounded. The default, and the honest state for a long time |
| `SUPPORTS` | both arms describe, Wilson intervals disjoint, above-floor rate higher |
| `CONTRADICTS` | both arms describe **and** the upper confidence bound on the difference falls below `min_effect` — i.e. an equivalence result, not merely a null one |
| `INVERTED` | both arms describe, intervals disjoint, above-floor rate **lower**. Reported plainly; almost certainly a confound, and the output says so |

**`CONTRADICTS` requires an equivalence bound, not a failure to find a difference.** "We looked and
saw nothing" is what a thin corpus always says, and treating it as evidence against the floor would
let the tool demote its own best-supported number by being underpowered. This is the same error, in
the opposite direction, that produced the prior rule.

The `demoted by` line is §10's falsifiability requirement made visible: each floor ships with the
observation that would demote it, printed next to the floor itself. A tier that cannot fill this
line is a preference, not an assertion, and must be labelled one.

---

## 4. Attribution resolution

Input is a rework marker; output is a resolved record carrying `session`, `turn`, `tokens`,
`method`, `confidence` and — if unresolved — a `reason`.

**Resolution runs at marker time, and its result is stored in the record.** §7 of the parent says
the record carries the attribution but does not say when it is computed; git history is stable, so
resolving once at marker time is cheaper than resolving on every read. The reader re-resolves only
the unattributed and `low`-confidence markers, per §4.6. This is one of the four changes in §9.

### 4.1 Step 0 — normalise the target

1. If the target is a path, resolve it against the repository containing the current working
   directory; record the repo root and the path relative to it.
2. Determine whether the path is tracked *now* and whether it was tracked at the marker timestamp.
   An untracked file has no git history and skips to step 3.
3. Accept `path:LINE` and `path:START-END` forms; a line range enables the `git blame` path in 4.3.
4. A 7–40 character hex string that resolves via `git rev-parse` is treated as a commit, not a path.
5. Anything else — a free-text description, a deleted file, a path outside any repository — skips
   to step 3 with reason `target-unresolvable`.

### 4.2 Step 1 — explicit

The marker names a session or a commit. Highest precedence; nothing below is consulted.

**Marker names a session** (`--session <id>`):

- If a target file is known, take that session's producing turns that wrote the file, and use the
  last one. `method: explicit-session`, `confidence: exact`.
- If no target file is known, use the session's producing-turn token span and its midpoint.
  `method: explicit-session`, `confidence: medium`, `tokens_span` recorded.
- If the session has no turn records, fall through to step 3, reason `no-turn-records`.

**Marker names a commit** (`--commit <sha>`): enter at step 2b with `method: explicit-commit`. The
commit is not guessed, so the mapping is one step shorter, but commit→turn remains inferential and
the confidence ceiling is `high`, never `exact`.

### 4.3 Step 2 — git-derived

The workhorse. Three sub-steps, each of which can degrade confidence or bail out.

**2a — target → commit.**

- With a line range: `git blame -L <a>,<b> --porcelain -- <path>` as of the marker's timestamp; take
  the most recent commit among the blamed lines.
- Without a line range: `git log --follow --format=%H%x09%cI -- <path>`; take the most recent commit
  at or before the marker's timestamp.
- No commit found → step 3, reason `no-commit-found`.
- The commit is a merge (a second parent exists), or its author is not the corpus owner → **step
  3**, reason `not-own-work`. Attributing someone else's commit to your own session is worse than
  not attributing it.

**2b — commit → session.**

Candidate sessions are those with turn records in the window `(commit_time − lookback,
commit_time]`, where **lookback defaults to 24 hours** (*proposed*; `--lookback`). The window is
one-sided because work precedes its commit; a turn after the commit did not produce it.

- Exactly one candidate → proceed.
- Several candidates → narrow to those whose `session_summary.files_written` contains the target
  path. This is why §6.5 carries that set: without it, attribution stops working the moment
  transcripts rotate, which is the failure the summaries exist to prevent.
  - Narrowing leaves exactly one → proceed, confidence ceiling `high`.
  - Narrowing leaves several → take the latest, confidence `low`, reason noted as
    `ambiguous-session`.
  - Narrowing leaves none → step 3, reason `ambiguous-session`.
- No candidates at all → step 3, reason `no-turn-records` (work predating installation).

**2c — session → turn.**

Among that session's producing turns that wrote the target file, take the last one at or before the
commit time. Its `total_tokens` is **tokens-at-production**, and its `baseline_tokens` fixes the
stratum.

- Exactly one such turn → `confidence: high`.
- Several → record the full span in `tokens_span`, use the last for arithmetic,
  `confidence: medium`.
- None (the file appears in the commit but in no recorded producing turn — an external edit, a
  `git mv`, a generated file) → use the session's producing-turn span midpoint,
  `confidence: low`.

### 4.4 Step 3 — unattributed

Recorded, never dropped, with one of these reasons:

| reason | means |
| --- | --- |
| `no-turn-records` | no session overlaps — usually work predating installation |
| `untracked-file` | target has no git history |
| `no-commit-found` | tracked, but nothing touched it before the marker |
| `ambiguous-session` | several sessions plausible, none distinguishable |
| `not-own-work` | merge commit, or another author |
| `target-unresolvable` | free text, deleted path, or outside a repository |

**The reason codes are the point.** "17 unattributed" says the corpus is weak; "17 unattributed, 14
of them `no-turn-records`" says the corpus is merely *young* and will fix itself, while "14 of them
`ambiguous-session`" says the *method* is failing and the lookback or the narrowing needs work.
Both views print the breakdown.

### 4.5 Confidence, and what each level is allowed to do

| confidence | assigned when | in rate arithmetic | rendered as |
| --- | --- | --- | --- |
| `exact` | explicit session **and** a known producing turn for the file | yes | filled mark |
| `high` | single session, single producing turn, commit within lookback | yes | filled mark |
| `medium` | single session, several producing turns — a span | yes, at the last turn | hollow mark with span whiskers |
| `low` | ambiguous session, commit older than lookback, or no producing turn for the file | **no**, unless `--include-low` | hollow mark, greyed |

Two honesty requirements from §7, made operational:

- **Git attribution is approximate and says so.** Commits happen after the work, sometimes long
  after, and one commit can span many turns. `method` and `confidence` are on every record, the
  curve renders inferred points differently from exact ones, and a span is drawn as a span rather
  than collapsed to a point.
- **`--include-low` changes the printed `n`, visibly.** When it is set, the header says
  `low-confidence points INCLUDED (--include-low)` and every affected `n` is annotated. A flag that
  quietly improves your numbers is a flag that will be left on.

### 4.6 Re-resolution

Attribution can improve after the fact: turn records accumulate, a longer lookback becomes
justified, a summary gets built for a session that had none. A marker resolved badly on a young
corpus should not poison it permanently.

On each run the reader re-resolves markers whose current state is `unattributed` or `low`, and, when
the result improves, **appends a new `rework` record carrying `supersedes: <uuid>`**. Nothing is
mutated; the corpus stays append-only; readers take the latest record per marker chain. Records that
resolve to the same result are not re-appended.

Re-resolution never downgrades. If a marker was `high` and now resolves worse — because a repository
was rewritten or moved — the original stands and the run counts a `resolution-conflict` in the
header. A tool that quietly rewrites its own history in response to a rebase is not an evidence
corpus.

---

## 5. The refusal rule

§7 of the parent calls this *the most important behaviour in the project*. Getting it right turns
out to depend on a choice of **unit**, which is the same place the prior rule went wrong.

### 5.1 The unit is interval width, not sample size

§7 says *"below a stated n"*, and §11 leaves that *n* unchosen. **A raw sample size is the wrong
unit for this**, for a reason this project should recognise immediately: it is a proxy for the thing
actually being asked about, and the error in the proxy varies with conditions. `n=40` with 2 rework
events and `n=40` with 20 tell you very different amounts about the underlying rate — the first is
consistent with anything from 1% to 17%, the second with 35% to 65%. A rule denominated in *n*
treats them as equally speakable.

**plimsoll is the tool whose whole thesis is that everyone denominates context budgets in
percentage when the defensible unit is absolute tokens.** Shipping a refusal rule denominated in
sample size, when the defensible unit is precision, would reproduce that exact error inside the
mechanism built to prevent it.

**Decision: a cell may speak when the Wilson 95% interval on its proportion is narrower than
`max_width`.** That is a direct statement of how much is known, it adapts to the base rate for free,
and it degrades gracefully instead of snapping at a threshold. Wilson rather than normal-approximation
because it is well-behaved at small *n* and at proportions near 0, which is where this corpus will
live for a long time, and because it needs no dependency beyond `math`.

### 5.2 The zero-event backstop

Interval width alone has one degenerate case, and it will not be rare here: a cell with **no rework
events at all** produces a one-sided interval that narrows much faster than a two-sided one. At
`max_width` 0.35 the arithmetic is:

| n, with 0 events | Wilson 95% interval | width | speakable on width alone? |
| --- | --- | --- | --- |
| 6 | [0, 0.390] | 0.390 | no |
| 7 | [0, 0.354] | 0.354 | no |
| **8** | **[0, 0.324]** | **0.324** | **yes — and it should not be** |
| 20 | [0, 0.161] | 0.161 | yes |

Eight producing turns with nothing reworked would otherwise license a printed rate. That is exactly
the "confident curve through four points" §7 warns about, arriving through the back door.

**A minimum absolute *n* is therefore retained as a backstop, not as the primary criterion.** Both
conditions must hold. The backstop does one narrow job — guarding the zero-event case — and the
width criterion does the actual work. For orientation: at the widest point (p̂ ≈ 0.5) `max_width`
0.35 binds at about 28 producing turns, so the backstop of 20 is not what is limiting in the normal
case.

### 5.3 Three tiers of speech

| corpus state | what the reader may do |
| --- | --- |
| **REFUSE** — `n < n_min` **or** interval wider than `max_width` | raw counts only. No rate, no interval, no mark. The cell reads `n=9 — this shows nothing` |
| **DESCRIBE** — both conditions met | print the observed proportion with its interval, labelled as a description of what happened in this corpus. No comparison with any other cell |
| **COMPARE** — two cells both DESCRIBE **and** their intervals are disjoint | state the ordering between them, in the fixed template of §3.3 |

Both conditions are evaluated **per cell**, never per corpus. A corpus of 400 producing turns with 3
in the `originating × baseline ≥60K` cell must refuse that cell. Refusal is a property of the claim
being made, not of the file on disk, and the most tempting bad claim is the one made from a
well-populated corpus about a sparse stratum of it.

**No trend is ever fitted.** There is no regression, no smoothing, no line of best fit, and no
extrapolation beyond the observed buckets — not at any *n*. The reader renders per-bucket rates with
their intervals and, where intervals are disjoint, states an ordering. Fitting a curve through five
bucket points and showing a user their personal "context curve" is the single most persuasive and
least defensible thing this tool could do, and the persuasiveness is precisely why it is out. §7's
phrase "draw the curve" is honoured as *plot the observed points*, never *fit a function through
them*. This is one of the four changes in §9.

### 5.4 The defaults, and why they are not promoted

| parameter | default | grade | flag |
| --- | --- | --- | --- |
| `max_width` | 0.35 | **proposed** | `--max-width` |
| `n_min` (backstop) | 20 | **proposed** | `--n-min` |
| `min_effect` (for `CONTRADICTS`) | 1.5× relative | **proposed** | `--min-effect` |

Settable in `~/.claude/plimsoll/config.toml`. Tightening is always permitted. **Loosening either
prints a warning into the rendered output**, so a screenshot of a permissive run is
self-incriminating:

```
  ⚠ max_width loosened to 0.60 (default 0.35). Rates this imprecise are
    shown at your instruction and should not be quoted.
```

The self-criticism printed by `plimsoll tiers --explain-n`:

> `max_width` = 0.35 is a **weak** bar. An interval 0.35 wide is one like 5%–40%: it says the rate
> is known to within a factor of several, not that it is known. In the worst case (p̂ ≈ 0.5) it
> binds at about 28 producing turns; against a 10% base rate it binds nearer 50. For comparison,
> distinguishing a 10% rework rate from a 20% one at conventional power needs roughly 200 per arm —
> far more than this bar demands. It is set here because a corpus that never speaks is a corpus
> nobody maintains, and because an *ordering* survives imprecision that a *rate* does not. That is
> the whole of the justification, and it is not much of one.

Shipping that paragraph in the tool's own output is the point. This design does not close §11's open
question by fiat; it ships a default that argues against itself and records what would settle it.

**What would promote `max_width`:** a corpus where the between-bucket ordering is stable under
bootstrap resampling at the chosen width, across at least two independent users. Until then it stays
*proposed*, and the reader keeps printing the paragraph above.

### 5.5 What refusal looks like

Refusal is never an error, never an empty screen, and never silent. The cell keeps its row, keeps
its counts, and loses only the claim:

```
       50K –  75K                 18          2   n=18 — below n_min=20
       75K – 100K                  9          2   n=9 — this shows nothing
      100K +                      31          3   ±0.41 too wide — no rate
```

`n=3 — this shows nothing` is the parent document's own wording and is kept verbatim for cells
below half of `n_min`, because it is blunter than the arithmetic version and bluntness is the
feature. The stratum footer then states what was withheld and why:

```
    NO COMPARISON DRAWN. 1 of 5 buckets is precise enough to describe,
    and a comparison needs two (§5.3). No trend is fitted at any n.
```

### 5.6 Refusal in `--json`

The refusal must survive the machine-readable path, or the first script anyone writes will plot the
thin data anyway.

```json
{
  "view": "curve",
  "stratum": {"shape": "originating", "baseline_band": "20-40K"},
  "criteria": {"max_width": 0.35, "n_min": 20, "method": "wilson95"},
  "buckets": [
    {"lo": 0, "hi": 25000, "producing": 41, "reworked": 2,
     "speech": "describe", "rate": 0.0488, "ci": [0.0136, 0.1614],
     "ci_width": 0.1478},
    {"lo": 75000, "hi": 100000, "producing": 9, "reworked": 2,
     "speech": "refuse", "refusal": "n=9 — this shows nothing",
     "rate": null, "ci": null, "ci_width": null}
  ],
  "comparisons": [],
  "comparison_refusal": "only 1 bucket is precise enough to describe",
  "trend": null,
  "trend_note": "plimsoll never fits a trend"
}
```

`rate`, `ci` and `ci_width` are **`null`, not omitted and not computed**, wherever `speech` is
`refuse`. A consumer that wants the number must compute it from `producing` and `reworked` itself —
a deliberate speed bump rather than a barrier, so that plotting thin data is a decision rather than
an accident. `trend` is present and permanently `null`, so a consumer expecting one gets an explicit
answer rather than a missing key it might paper over.

---

## 6. `session_summary` rollups

§7 settles the requirement: tool-invocation statistics are derived rather than logged per turn, and
the reader writes a rolled-up record so the figures survive transcript rotation. This section
settles the mechanics.

### 6.1 The reader writes. This is a deliberate wart.

A command named "reader" that appends to the corpus is a smell, and it is accepted for one reason:
the alternative is duplicating tool statistics into every turn record, which would multiply corpus
size by the tool-call rate to carry data that is derivable. The write is bounded and the bound is
part of the design:

**The reader may append `session_summary` records and superseding `rework` records (§4.6). It may
append nothing else, and it may modify or delete nothing at all.** It never writes `turn` or
`preflight` records — those have owners, and a reader that could forge them would make the corpus
unable to distinguish what was measured from what was reconstructed.

### 6.2 When summaries are written

On every reader invocation, before rendering, so that a view never reflects a corpus staler than the
transcripts on disk.

For each session with turn records in the selected slice:

1. **Skip** if a `final: true` summary exists whose `source_digest` matches the transcript's current
   `(path, size, mtime_ns, last_uuid)`.
2. **Skip and keep** if the transcript is gone. An existing summary stands; a session that has
   rotated away is not recomputed from nothing, and its summary is the only surviving record of it.
   This is the entire reason the mechanism exists.
3. Otherwise derive a summary and append it.

**The live session is summarised too, with `final: false`.** Excluding it would make the most recent
work invisible in every view, which is when people look. It is marked non-final and superseded on a
later run.

**Supersession, not mutation.** A later `session_summary` for the same `session_id` supersedes
earlier ones; readers keep the highest `generation` per session. The file stays append-only, which
keeps the corpus's central property — nothing already written is ever untrue, only outdated.

Closedness test for `final`: the session is not the reader's own, and the transcript's newest record
is older than **30 minutes** (*proposed*, `--final-after`). A resumed session simply produces a new
generation.

### 6.3 What is derived

Per session, in one pass over the transcript:

| field | derived from |
| --- | --- |
| `turns` | count of main-chain `user` prompts |
| `producing_turns` | turns with ≥1 successful `Write`/`Edit`/`NotebookEdit` (success read from `toolUseResult`, not from the call) |
| `producing_histogram` | producing turns bucketed by tokens-at-turn — **the curve's denominator after rotation** |
| `files_written` | set of repo-relative paths successfully written — **required by attribution 2b** |
| `tools` | `{name: count}` over `tool_use` blocks |
| `servers` | `{server: count}`, from the `mcp__<server>__` prefix |
| `subagent_tools` | the same, over `isSidechain` records, kept separate |
| `compactions` | one entry per `compact_boundary`: `trigger`, `pre_tokens`, `post_tokens`, `dropped` |
| `baseline_tokens`, `peak_tokens`, `final_tokens` | turn records, cross-checked against transcript usage |
| `models`, `windows` | every distinct value seen — §8's model-switching case |
| `ts_start`, `ts_end`, `project`, `git_branch`, `cc_version` | first/last records |

`producing_histogram` and `files_written` are the two fields load-bearing for other parts of this
design; the rest are reporting.

### 6.4 Subagent activity is counted separately

Subagent context is separate (§4.5 of the parent), so a subagent's tool calls do not sit in the main
session's window. Folding them into `tools` would overstate main-session weight and would make
delegation — the one remedy the skill actually endorses — look like consumption. They are recorded
under `subagent_tools`, reported in `baseline` as a separate line, and excluded from producing-turn
counts: a subagent's edits are attributed to the main-chain turn that dispatched it, because that is
the turn whose context conditions produced the decision.

### 6.5 Record shape

```json
{
  "type": "session_summary",
  "schema_version": 1,
  "generation": 2,
  "final": true,
  "session_id": "0e2c1279-a768-48fb-93e6-811af62673d4",
  "project": "<origin>",
  "git_branch": "main",
  "ts_start": "2026-08-14T09:12:03Z",
  "ts_end": "2026-08-14T17:48:51Z",
  "ts_written": "2026-08-15T08:02:11Z",
  "models": ["claude-opus-5[1m]"],
  "windows": [1000000],
  "cc_version": "2.1.226",
  "turns": 217,
  "producing_turns": 44,
  "producing_histogram": {"0-25000": 3, "25000-50000": 9, "50000-75000": 12,
                          "75000-100000": 11, "100000+": 9},
  "files_written": ["docs/superpowers/specs/foo.md", "scripts/context_budget.py"],
  "baseline_tokens": 38412,
  "peak_tokens": 1000114,
  "final_tokens": 26659,
  "tools": {"Bash": 409, "Edit": 90, "Agent": 62, "Read": 25},
  "servers": {"ide": 14},
  "subagent_tools": {"Read": 88, "Grep": 41},
  "compactions": [{"trigger": "auto", "pre_tokens": 1000114,
                   "post_tokens": 26659, "dropped": 973455,
                   "ts": "2026-08-14T16:31:20Z"}],
  "source_digest": {"path": ".../0e2c1279.jsonl", "size": 48211944,
                    "mtime_ns": 1755244131000000000,
                    "last_uuid": "1f4038c6-e3f4-41c7-9065-d58a75a28aae"},
  "derivation_errors": 0
}
```

`files_written` is capped at 500 entries; beyond that the field records `truncated: true` and
attribution treats a miss as inconclusive rather than as a negative. Silently truncating a set that
another algorithm tests membership against would turn a size limit into a wrong answer.

### 6.6 Cost, concurrency, and failure

**Cost.** The first run parses every transcript in the slice — minutes on a large history, and the
reader prints a progress line to stderr when it exceeds two seconds. Subsequent runs parse only
sessions whose digest changed, which is normally one. `--rebuild` forces full re-derivation and
appends a new generation for every session; it never deletes the old ones.

**Concurrency.** Two readers can run at once. Summary writing takes an exclusive `flock` on
`~/.claude/plimsoll/.lock` with a **2-second timeout**; on timeout the reader **skips writing and
renders from what already exists**, noting `summaries not updated (corpus busy)` in the header.
Records exceed the atomic-append size, so `O_APPEND` alone is not sufficient and the lock is not
optional. Rendering never takes the lock — reads are always available.

**Failure.** Any error deriving one session — unreadable transcript, malformed JSON, permission
denied — is caught, counted, and skipped. The session is reported in the header as unsummarised,
and the run continues. A partially derived summary is never written: a summary is built entirely in
memory and appended in one call, or not at all.

---

## 7. Verification

Extends §10 of the parent. The failure paths matter most; so does the refusal.

**Refusal — §10 says this deserves a test of its own, and it needs several:**

- a cell at `n_min − 1` prints the refusal string and no rate, in text and in JSON
- **a cell with 0 events at n=8 refuses** — the §5.2 degeneracy, the sharpest single test here
- a cell whose interval is wider than `max_width` refuses even when `n` is large
- two cells that both describe but whose intervals **overlap** produce no comparative sentence
- a corpus large overall but sparse in one stratum refuses **that stratum only**
- `--max-width` loosened past the default emits the warning line into the rendered output
- `--json` emits `rate: null` and `ci: null` for refused cells, never a computed value
- **no code path produces a fitted trend**, at any *n*, in any view or output format
- Wilson bounds are clamped to [0, 1] and are correct at x=0 and x=n

**Attribution:**

- explicit session with a matching producing turn → `exact`
- explicit commit → `high`, never `exact`
- git-derived, single session, single producing turn → `high`
- git-derived, single session, several producing turns → `medium` with a populated `tokens_span`
- merge commit and foreign-author commit → unattributed with `not-own-work`
- commit older than lookback → `low`
- ambiguity resolved by `files_written` → `high`; unresolved → `low` with `ambiguous-session`
- **re-resolution appends a superseding record and never downgrades**
- unattributed markers appear in every view's counts and are never dropped

**Summaries:**

- unchanged digest → no new record appended
- changed transcript → new generation, old generation retained, latest wins
- missing transcript with an existing summary → summary stands, no error
- live session → `final: false`; after `--final-after` → `final: true` at a new generation
- compaction derived from `compact_boundary`, and from a discontinuity when the record is absent
- `isSidechain` tool calls land in `subagent_tools` and not in `tools`
- lock held by another process → renders anyway, header states summaries were not updated
- malformed transcript line → counted in `derivation_errors`, session still summarised
- `files_written` past the cap → `truncated: true`, and 2b treats a miss as inconclusive

**Baseline view:**

- a server in the roster but absent from every transcript → `never`, but only above `n_min` sessions
- below `n_min` sessions → raw counts and the `too few to call anything unused` line
- baseline ≥ floor in any session → the unsatisfiable-gate block renders
- **no code path in the binary opens a config file for writing** — §6's hard non-goal, tested

---

## 8. Open, and deliberately not closed here

- **`max_width` and `n_min` remain *proposed*.** §11 of the parent lists the stated *n* as unchosen;
  this design reframes the unit (§5.1) but does not close the value by fiat. The promotion criterion
  is in §5.4.
- **The producing-turn denominator (§3.3) is the most consequential choice in this document** and
  the one most likely to be wrong. It should be reviewed before implementation, not after data
  accumulates against it.
- **The 24-hour lookback** is a guess. The corpus can settle it: the distribution of
  producing-turn-to-commit intervals is derivable from data the reader already holds, and a later
  version should report it rather than assume it.
- **Bucket width and baseline bands are display parameters.** If any decision anywhere ever starts
  reading them, they have become constants and need grades.
- **`--fail-on-thin` for CI use** is not designed. It is plausible and it is not v1.

## 9. The four changes to §7 that need sign-off

| change | from | to | argued in |
| --- | --- | --- | --- |
| **where attribution is resolved and stored** | §7 says the record carries it, not when it is computed | resolved at marker time and stored; the reader re-resolves only weak records, appending supersessions | §4, §4.6 |
| **what a rework rate is denominated in** | §7 names no denominator | producing turns — turns with a successful write to a project file | §3.3 |
| **whether a trend is ever fitted** | §7 says the reader "declines to plot a trend" below *n*, implying it plots one above | **never**, at any *n*. Observed points and orderings only | §5.3 |
| **whether §8's silent-failure rule binds the reader** | §8 is stated as absolute | it binds the *hooks* absolutely; the reader fails loudly on its own misuse and silently on corpus defects | §1.2 |

A fifth item is a finding rather than a change: §10's post-compaction test should reference the
explicit `compact_boundary` transcript record rather than discontinuity detection (§2.1).
