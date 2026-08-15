#!/usr/bin/env python3
"""Status-line context gauge — a right-aligned bar showing how much of the context
window this session has used.

The convention it serves (the origin repo CLAUDE.md, R76): accuracy degrades well before the
window is full, so a loop runs in a fresh session. Blue below the handoff mark, amber
between handoff and stop, red past the stop mark — at which point you clear the
context or start a fresh session rather than pressing on.

Reads the status-line payload as JSON on stdin and reports

    context = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

taken from the LAST usage record in the session transcript. That is the real
per-turn figure the API reports, not a proxy.

THRESHOLDS ARE NOT DEFINED HERE WHEN A PROJECT DEFINES THEM. If the current project
ships `scripts/context_budget.py` (the origin repo does, wired as a UserPromptSubmit hook),
its HANDOFF_PCT / STOP_PCT / WINDOW are imported so the gauge and the hook can never
drift apart. Elsewhere the defaults below apply.

Never raises and never blocks: any failure prints nothing and exits 0. A status line
that breaks the TUI is worse than no status line.
"""
from __future__ import annotations

import json
import os
import sys

HANDOFF_PCT = 30          # amber: write the handoff while still accurate
STOP_PCT = 40             # red: finish the step and start a fresh session
WINDOW = int(os.environ.get("CLAUDE_CONTEXT_WINDOW", "1000000"))

CELLS = 20                # bar width; each cell is 100/CELLS percent
TAIL_BYTES = 512 * 1024   # how much of the transcript tail to scan for the last usage

# A BLUE -> AMBER -> RED ramp, not green -> amber -> red. Chosen for the daltonized
# theme: green and red are the pair red-green colour vision deficiency collapses, and
# amber sits between them, so the classic traffic-light ramp is its worst case. Blue is
# carried by a channel CVD leaves intact, and the red is deliberately the pink-leaning
# 197 rather than a pure 31 — retaining some blue keeps it separable from the amber.
BLUE, AMBER, RED = "\033[38;5;39m", "\033[38;5;214m", "\033[38;5;197m"
DIM, RESET = "\033[2m", "\033[0m"


def _project_thresholds() -> None:
    """Adopt the current project's budget constants when it defines them."""
    global HANDOFF_PCT, STOP_PCT, WINDOW
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if not root:
        return
    path = os.path.join(root, "scripts")
    if not os.path.exists(os.path.join(path, "context_budget.py")):
        return
    sys.path.insert(0, path)
    try:
        import context_budget as cb
    except Exception:
        return
    HANDOFF_PCT = getattr(cb, "HANDOFF_PCT", HANDOFF_PCT)
    STOP_PCT = getattr(cb, "STOP_PCT", STOP_PCT)
    WINDOW = getattr(cb, "WINDOW", WINDOW)


def last_usage(path: str):
    """The most recent usage record in the transcript, or None.

    Scans only the tail: a status line re-runs constantly and transcripts reach many
    megabytes, so a full scan per repaint is not affordable. Falls back to a full
    scan when the tail holds no usage record (a very long single turn).
    """
    try:
        size = os.path.getsize(path)
        with open(path, "r", errors="replace") as fh:
            if size > TAIL_BYTES:
                fh.seek(size - TAIL_BYTES)
                fh.readline()             # discard the partial first line
            lines = fh.readlines()
        found = _scan(lines)
        if found is None and size > TAIL_BYTES:
            with open(path, "r", errors="replace") as fh:
                found = _scan(fh)
        return found
    except OSError:
        return None


def _scan(lines):
    found = None
    for line in lines:
        if '"usage"' not in line:
            continue
        try:
            msg = json.loads(line).get("message") or {}
        except (ValueError, AttributeError):
            continue
        u = msg.get("usage")
        if isinstance(u, dict):
            found = u
    return found


def terminal_width() -> int:
    """MEASURED against Claude Code 2.1.226: the status-line command runs with no tty
    on any descriptor (isatty(1) and isatty(2) are both False) but WITH COLUMNS set to
    the real terminal width. So COLUMNS is the authoritative source here and is checked
    first; the tty probes remain for other harnesses. Never clamp upward — claiming 80
    on a 60-column terminal makes the line wrap, which is worse than being left of the
    right edge.
    """
    try:
        w = int(os.environ.get("COLUMNS", "0"))
        if w > 0:
            return w
    except ValueError:
        pass
    for fd in (2, 1, 0):
        try:
            w = os.get_terminal_size(fd).columns
            if w > 0:
                return w
        except OSError:
            continue
    return 80


def git_branch(cwd: str) -> str | None:
    """Read .git/HEAD directly — no subprocess, because this runs on every repaint."""
    d = os.path.abspath(cwd or ".")
    while True:
        head = os.path.join(d, ".git", "HEAD")
        if os.path.exists(head):
            try:
                with open(head, errors="replace") as fh:
                    ref = fh.read().strip()
            except OSError:
                return None
            return ref.rsplit("/", 1)[-1] if ref.startswith("ref:") else ref[:7]
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def zone_colour(pct: float) -> str:
    """The ramp, defined ONCE — the bar and the percentage must never disagree."""
    return BLUE if pct < HANDOFF_PCT else (AMBER if pct < STOP_PCT else RED)


def gauge(pct: float) -> tuple[str, int]:
    """The coloured bar plus its VISIBLE width (ANSI escapes excluded)."""
    colour = zone_colour(pct)
    filled = min(CELLS, int(pct / 100 * CELLS + 0.5))
    mark = int(STOP_PCT / 100 * CELLS + 0.5)          # the budget line, drawn in the bar
    body = ""
    for i in range(CELLS):
        if i < filled:
            body += "█"
        elif i == mark:
            body += "┊"                                # where you are meant to stop
        else:
            body += "░"
    bar = f"{colour}{body}{RESET}"
    return bar, CELLS


def human(n: int) -> str:
    return f"{n / 1_000_000:.1f}M" if n >= 1_000_000 else f"{round(n / 1000)}k"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    _project_thresholds()

    # PRIMARY: the harness reports the live figure in the payload (measured against
    # Claude Code 2.1.226 — `context_window.total_input_tokens` equals the sum of
    # current_usage's input + cache_read + cache_creation, i.e. the same definition
    # context_budget.py derives from the transcript). No file read at all.
    cw = payload.get("context_window") or {}
    used = cw.get("total_input_tokens")
    window = cw.get("context_window_size") or WINDOW

    # FALLBACK: older harnesses that send no context_window block.
    if not isinstance(used, int):
        path = payload.get("transcript_path") or ""
        u = (last_usage(path) or {}) if path and os.path.exists(path) else {}
        used = (u.get("input_tokens", 0)
                + u.get("cache_read_input_tokens", 0)
                + u.get("cache_creation_input_tokens", 0))
        window = WINDOW

    pct = 100.0 * used / window if window else 0.0

    colour = zone_colour(pct)
    width = terminal_width()

    # LEFT — model and branch, so enabling this gauge does not cost the context the
    # default status line was providing.
    model = ((payload.get("model") or {}).get("display_name") or "").strip()
    cwd = ((payload.get("workspace") or {}).get("current_dir")
           or payload.get("cwd") or os.getcwd())
    branch = git_branch(cwd)
    left_plain = " ".join(x for x in (model, f"({branch})" if branch else "") if x)
    left = f"{DIM}{left_plain}{RESET}" if left_plain else ""

    # RIGHT — the gauge itself.
    bar, bar_w = gauge(pct)
    counts = f" {human(used)}/{human(window)}"
    # REDUNDANT ENCODING, not decoration: the theme in use is daltonized, so the
    # green/amber/red ramp cannot be the only carrier of the state. The percentage,
    # the in-bar stop mark and this word each say it independently.
    state = "" if pct < HANDOFF_PCT else (" handoff" if pct < STOP_PCT else " STOP")
    pct_txt = f"{pct:.0f}%{state}"
    right = f"{DIM}ctx{RESET} {bar} {colour}{pct_txt}{RESET}{DIM}{counts}{RESET}"
    right_w = 4 + bar_w + 1 + len(pct_txt) + len(counts)

    # Degrade on narrow terminals rather than wrapping — a wrapped status line
    # pushes the prompt around on every repaint.
    if width < right_w + len(left_plain) + 2:
        right = f"{DIM}ctx{RESET} {bar} {colour}{pct_txt}{RESET}"
        right_w = 4 + bar_w + 1 + len(pct_txt)
        left, left_plain = "", ""
    if width < right_w + 2:
        right = f"{colour}ctx {pct_txt}{RESET}"
        right_w = 4 + len(pct_txt)

    pad = max(1, width - right_w - len(left_plain) - 1)
    sys.stdout.write(f"{left}{' ' * pad}{right}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)          # never break the TUI
