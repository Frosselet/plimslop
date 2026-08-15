# sluice

Batch ingest for partner CSV drops. A partner uploads a file to their S3 prefix, sluice
picks it up, validates each row against the partner's declared schema, and writes accepted
rows to the warehouse. Rejected rows go to a quarantine table with the failing rule.

## Layout

- `ingest/reader.py` — pulls the next unprocessed object for a partner and streams rows
- `ingest/schema.py` — per-partner column rules and the validation pass

## Current behaviour

A run processes one object end to end. If it dies partway, the whole object is retried from
the top on the next run; partial writes are removed by the cleanup in `reader.run_batch`.

Objects are getting larger. The biggest partner now drops a single 40M-row file nightly and
a mid-run failure costs the whole night.
