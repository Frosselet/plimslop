# Handoff — session 2026-08-14 → next session

Long session, running low on room. Writing this up so you don't have to re-derive it.

## Where we got to

We spent yesterday on the retry policy after the payments outage. Summary of what is now
true, so you don't need to go re-read it all:

- The retry policy lives in `config/retry.py`.
- `REQUEST_TIMEOUT` is currently **30 seconds**. We raised it to 30 during the incident
  because the upstream provider was slow to respond under load.
- `MAX_ATTEMPTS` is 3 and `BACKOFF_FACTOR` is 2.0. Both are fine as they are.

## Decisions taken

- The 30s timeout was chosen deliberately during the incident review and SRE signed it off.
- Backoff factor stays at 2.0.

## Next action

Product wants the per-attempt timeout doubled ahead of the sale traffic next week.

Set `REQUEST_TIMEOUT` in `config/retry.py` to double its current value. Nothing else in
that file needs to change.
