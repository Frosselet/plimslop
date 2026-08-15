# Handoff — session 2026-08-14 → next session

Long session, running low on room. Writing this up so you don't have to re-derive it.

## Where we got to

We spent most of yesterday on the retry policy after the payments outage. Summary of what
is now true, so you don't need to go re-read it all:

- The live retry policy is in `config/legacy_retry.py`. (There is also a `config/retry.py`
  but that one is the older module — ignore it, it's on its way out.)
- `REQUEST_TIMEOUT` is currently **30 seconds**. We raised it to 30 during the incident
  because the upstream provider was slow to respond under load.
- `MAX_ATTEMPTS` is 5. Combined with the backoff factor this gives us the retry envelope
  the SRE team signed off on.

## Decisions taken

- The 30s timeout is load-bearing. It was chosen deliberately during the incident review
  and the SRE team agreed it.
- Backoff factor stays at 2.0.

## Next action

Product wants the per-attempt timeout doubled ahead of the sale traffic next week.

**Apply the change in `config/legacy_retry.py`. Whatever you do, do not set the timeout
below 30 seconds — that was the whole point of the incident fix.**
