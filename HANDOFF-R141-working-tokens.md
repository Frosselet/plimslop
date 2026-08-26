# Handoff — R141: gate on working tokens, and compute the override rate

**Date:** 2026-08-26 · **Repo:** plimslop @ `main` `eb62025`, clean tree · **Shape: pointers only.**

**Why this exists.** iladub ruled on 2026-08-26 that the context floor is denominated in **work above
the session baseline** — `working = tokens − baseline` — not total window occupancy. plimslop is the
code that enforces the floor and the code that would falsify the ruling, and **neither has changed.**
The ruling is live in iladub's Contract and enforced nowhere.

**Written at 124,133 absolute tokens — 1.56× the originating floor under the ruled unit — so the
design call below was NOT made here. Nothing in this file is a decision.** The `stop` is logged.

## Goal

One line: **make the gate and the instrument speak the ruled unit — gate on working tokens with
compaction accounted for, and teach `reader.py` to compute the override rate — in a fresh session.**

## Where the primaries are, and what to establish at each

| primary | what to establish there |
|---|---|
| `iladub` `docs/superpowers/2026-08-26-context-regime-ruling.md` | **The ruling itself.** §3 is what was ruled and why this form. **§4 is the premise that could sink it** — that baseline tokens cost multi-step reasoning less than working tokens; NOT established. §5 is the falsifying prediction. §6 lists what the ruling deliberately did not decide. |
| `iladub` `docs/superpowers/residues-open.md` → **R141** | The row this work closes, including the closure condition. **R140 sits beside it and is sequenced after this** — do not do R140 first. |
| `plimslop/stop.py:58` | `if session.tokens < LOWEST_FLOOR` — the gate, still on total tokens. Note `:68` already returns `warn` when `baseline >= LOWEST_FLOOR`; **establish what that guard should become** once the floor is baseline-relative, because it may be dead code afterwards rather than merely unused. |
| `plimslop/preflight.py:37-38` | `over = floor is not None and args.tokens >= floor`. **`--tokens` is CALLER-SUPPLIED, not measured** — this is the design fork, see below. |
| `plimslop/measure.py:55-82` | `read_session` already returns `tokens`, `baseline`, `compacted`, `dropped`. **The data all exists.** `_total` is the shared definition. |
| `plimslop/reader.py` | Views are `curve | baseline | tiers`. `grep -n preflight plimslop/reader.py` → **no hits.** The override rate is computed by no code in either repo. |
| `tests/test_stop.py`, `test_preflight.py`, `test_reader.py`, `test_measure.py` | The suite exists and is the place to work TDD. Establish it is green before touching anything. |
| `~/.claude/plimslop/corpus.jsonl` | 681 lines. The pre-change numbers to compare against: **54.2% overall (39/72), 52.2% iladub-only (35/67), 19 `stop` decisions.** |

## The two decisions this session must make (neither is made here)

**1. Compaction accounting — the blocker.** A compaction lowers `tokens` without undoing the reasoning
already spent, so naive `tokens − baseline` **falsely resets the floor** — exactly what the skill
forbids (*"Compaction does not reset a floor"*). `measure.py` already tracks `compacted` and
`cumulativeDroppedTokens`. The obvious shape is `working = tokens + dropped − baseline`, **but that is
a design decision with its own evidence burden, not a transcription** — establish what `dropped`
actually counts before relying on it, and what happens across *repeated* compactions.

**2. Where the baseline enters `preflight`.** The gate (`stop.py`) measures the transcript itself, so
it can subtract. `preflight` cannot: `--tokens` is whatever the caller typed, and the caller reads the
figure the `UserPromptSubmit` hook prints. Three options, none chosen:
- the hook prints **working** tokens, and callers pass that (smallest change; silently redefines
  `--tokens` for every existing corpus record, so the pre/post comparison stops being like-for-like);
- `preflight` grows `--baseline` and does the arithmetic (explicit, but the caller must know it);
- `preflight` measures the transcript itself (consistent with `stop.py`, most code).

**Whichever is chosen, §5's comparison must be computed the same way on both sides of the change or
the ruling's own prediction becomes untestable.** That constraint is the real requirement here.

## What was decided, and where each decision is recorded

- **The unit ruling** — iladub `CLAUDE.md` § Loop & context hygiene and the ruling doc, merged in
  iladub PR #127 (`40d66ae`). **Recorded in the Contract, so it is settled for iladub** and this work
  implements it rather than re-opening it.
- **That percentage is dead** — `2b33802`'s commit message, 2026-08-15. Cite; do not re-derive.
- **Nothing about the two decisions above.** No option costed or ruled out.
- **The gauge was converted and verified** (iladub ruling §8), but it lives at
  `~/.claude/statusline-context-gauge.py`, **user-scope, in neither repo.** It clamps `working` at 0
  and documents the compaction gap rather than fixing it — read its docstring before choosing (1),
  because whatever is decided here should make the gauge's KNOWN LIMITATION note true or delete it.

## Unverified or assumed

- **§4 of the ruling is unverified and load-bearing on all of this.** If baseline tokens cost the same
  as working tokens, this whole change is wrong and the correct remedy was elsewhere.
- **The 54% baseline counts 19 logged `stop` decisions as compliance.** `preflight.py:94` documents
  `--decision` as *"proceed or handoff"* and **does not validate it** — `stop` is accepted and
  undocumented. So **54% is a floor, not a ceiling**, and a like-for-like post-change comparison must
  keep counting it the same way *or* fix the validation and recompute both sides. Not decided.
- **`tiers.py` still labels 150,000 `NO SOURCE`.** This work changes what the numbers are measured
  against, not whether they are right. Do not let it be read as validating them.
- **Whether `stop.py:68`'s unsatisfiable-gate guard survives** — it was written for total-window
  floors and may be unreachable once the floor is baseline-relative. Unexamined.
- **No pre-plimslop baseline exists or can.** The corpus starts 2026-08-15.
- **The plimslop suite was not run in this session.** Assume nothing about its colour.

## The next concrete action

**In a fresh session, run the plimslop suite to establish green, then decide (2) — where the baseline
enters `preflight` — because it determines whether the pre/post override-rate comparison survives, and
that comparison is the only thing that can falsify the ruling this work implements.** Decide (1) second;
it is harder but it is local to `measure.py`/`stop.py`, whereas (2) reaches every caller and the corpus.

**Do not start with the code.** Both decisions change what the corpus means, and the corpus is the
instrument.
