"""The rework marker command: record that something had to be redone.

    python3 -m plimsoll.mark <target> [--note ...] [--session ID] [--commit SHA]

A marker is a statement of *history*, not a judgment of quality: this was
reverted, redone, abandoned. It is written when the rework is discovered, and
the command's job is to map that back to the turn that produced the work.
"""

import argparse
import calendar
import os
import subprocess
import sys
import time

from plimsoll.corpus import append, default_path, read


def main(argv=None, stdout=sys.stdout, corpus_path=None, cwd=None):
    """Record one rework marker. Returns an exit code."""
    args = _parse(argv if argv is not None else sys.argv[1:])
    args.cwd = cwd or os.getcwd()
    path = corpus_path if corpus_path is not None else default_path()

    record = {"type": "rework",
              "target": args.target,
              "note": args.note,
              "project": args.cwd,
              "method": "unattributed",
              "confidence": "none",
              "session": None,
              "tokens": None}
    record.update(_attribute(args, read(path)))

    try:
        append(record, path)
    except OSError as failure:
        stdout.write("rework: %s — NOT RECORDED (%s)\n" % (args.target, failure))
        return 1
    stdout.write(_summary(record) + "\n")
    return 0


def _summary(record):
    """One line, saying plainly what the marker did and did not attach to.
    An attribution nobody reads back is an attribution nobody corrects."""
    if record["method"] == "unattributed":
        return "rework: %s — unattributed (no producing turn found)" % record["target"]

    where = record["session"] or "an unnamed session"
    if record["tokens"] is not None:
        where += " at %s tokens" % format(record["tokens"], ",")
    elif record.get("tokens_lo") is not None:
        lo, hi = record["tokens_lo"], record["tokens_hi"]
        where += (" somewhere in %s–%s tokens" % (format(lo, ","), format(hi, ","))
                  if lo != hi else
                  " somewhere in a session seen only at %s tokens" % format(lo, ","))
    return "rework: %s — %s, %s (%s)" % (record["target"], where,
                                         record["confidence"], record["method"])


def _attribute(args, corpus):
    """Design §7's preference order. Only the steps that are implemented
    appear here; falling off the end is the third step, unattributed."""
    if args.session:
        return _from_session(args.session, corpus)
    return _from_git(args.target, args.cwd, corpus, args.commit)


def _from_session(session, corpus):
    """Step 1: the marker names a session. The session is exact, but nothing
    here identifies *which turn* in it produced the work, so the record carries
    the interval the session spanned instead of asserting a point inside it."""
    turns = sorted((r for r in corpus
                    if r.get("type") == "turn" and r.get("session") == session),
                   key=lambda r: r.get("ts") or "")
    return {"method": "explicit",
            "confidence": "exact",
            "session": session,
            "tokens": None,
            "tokens_lo": turns[0].get("tokens") if turns else None,
            "tokens_hi": turns[-1].get("tokens") if turns else None}


def _from_git(target, cwd, corpus, named=None):
    """Steps 1 and 2 where a commit is involved. Git gives the commit that
    produced the target — or the caller names it outright — and when that
    commit landed; the turn records say which session was running at that
    point, and how large it had grown.

    The commit-to-turn mapping is approximate either way: a commit lands after
    the work and can span many turns. So a named commit is `explicit` in method
    and still `inferred` in confidence — naming the commit exactly does not
    make the turn behind it exact."""
    root = _git(["rev-parse", "--show-toplevel"], cwd)
    commit = _named_commit(named, cwd) if named else _commit_for(target, cwd)
    if not root or not commit:
        return {}

    sha, when = commit
    found = {"commit": sha, "commit_ts": when}
    turn = _turn_at(corpus, when, os.path.realpath(root))
    if turn is None:
        return found                        # a commit, but no turn to pin it to
    found.update({"method": "explicit" if named else "git",
                  "confidence": "inferred",
                  "session": turn.get("session"),
                  "tokens": turn.get("tokens"),
                  "baseline": turn.get("baseline"),
                  "turn_ts": turn.get("ts")})
    return found


def _named_commit(sha, cwd):
    """(sha, unix time) for a commit the caller named, or None if git does not
    know it — an unresolvable sha attributes to nothing rather than to a guess."""
    out = _git(["log", "-1", "--format=%H %ct", sha], cwd)
    if not out:
        return None
    found, _, when = out.partition(" ")
    return (found, int(when))


def _commit_for(target, cwd):
    """(sha, unix time) of the commit behind `path` or `path:12-20`, or None."""
    path, _, lines = target.partition(":")
    if lines:
        return _blamed(path, lines, cwd)
    out = _git(["log", "-1", "--format=%H %ct", "--", path], cwd)
    if not out:
        return None
    sha, _, when = out.partition(" ")
    return (sha, int(when))


def _blamed(path, lines, cwd):
    """The most recent commit among the blamed lines. A hunk touched twice is
    attributed to the turn that touched it last."""
    start, _, end = lines.partition("-")
    out = _git(["blame", "-L", "%s,%s" % (start, end or start),
                "--line-porcelain", "--", path], cwd)
    if not out:
        return None

    newest, sha = None, None
    for line in out.splitlines():
        head = line.split(" ", 1)[0]
        if len(head) == 40 and all(c in "0123456789abcdef" for c in head):
            sha = head
        elif line.startswith("committer-time ") and sha:
            when = int(line.split(" ", 1)[1])
            if newest is None or when > newest[1]:
                newest = (sha, when)
    return newest


def _turn_at(corpus, when, root):
    """The latest turn record at or before `when`, within this repository.

    Scoped to the repository on purpose: the corpus is cross-project, and
    attributing rework here to a turn spent elsewhere would be worse than
    leaving the marker unattributed."""
    best, best_ts = None, None
    for record in corpus:
        if record.get("type") != "turn" or not _within(record.get("project"), root):
            continue
        ts = _epoch(record.get("ts"))
        if ts is None or ts > when:
            continue
        if best_ts is None or ts >= best_ts:
            best, best_ts = record, ts
    return best


def _within(project, root):
    """A turn's project counts if the session was run at the repository root or
    somewhere under it. Running from a parent directory reads as a miss, which
    surfaces as an unattributed marker rather than a loose attribution."""
    if not project:
        return False
    project = os.path.realpath(project)
    return project == root or project.startswith(root + os.sep)


def _epoch(ts):
    try:
        return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except (TypeError, ValueError):
        return None


def _git(argv, cwd):
    """Git's answer, or None. No git, no repo and a bad path all read alike."""
    try:
        done = subprocess.run(["git"] + argv, cwd=cwd, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _parse(argv):
    parser = argparse.ArgumentParser(prog="plimsoll.mark")
    parser.add_argument("target", help="a path, a path:lines hunk, or a description")
    parser.add_argument("--note", default=None, help="why it was reworked")
    parser.add_argument("--session", default=None,
                        help="attribute to this session id, exactly")
    parser.add_argument("--commit", default=None,
                        help="attribute to this commit rather than blaming the target")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
