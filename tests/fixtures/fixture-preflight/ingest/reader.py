"""Object pickup and row streaming for a partner batch."""

from ingest.schema import validate_row

BATCH_SIZE = 5000


def next_object(partner_id: str):
    """The oldest unprocessed object for this partner, or None."""
    raise NotImplementedError("wired to the S3 listing in production")


def stream_rows(obj):
    """Yield decoded rows from the object, one at a time."""
    raise NotImplementedError


def run_batch(partner_id: str) -> dict:
    """Process one object end to end.

    On any exception the caller removes everything written for this object and the
    whole thing is retried from the top on the next run. There is no resume point.
    """
    obj = next_object(partner_id)
    if obj is None:
        return {"status": "idle"}

    accepted, rejected = [], []
    for row in stream_rows(obj):
        problem = validate_row(partner_id, row)
        if problem:
            rejected.append((row, problem))
        else:
            accepted.append(row)
        if len(accepted) >= BATCH_SIZE:
            _write_accepted(partner_id, accepted)
            accepted = []

    if accepted:
        _write_accepted(partner_id, accepted)
    _write_quarantine(partner_id, rejected)
    return {"status": "done", "rejected": len(rejected)}


def _write_accepted(partner_id: str, rows: list) -> None:
    raise NotImplementedError


def _write_quarantine(partner_id: str, rows: list) -> None:
    raise NotImplementedError
