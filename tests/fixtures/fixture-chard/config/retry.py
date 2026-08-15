"""Retry and timeout policy for outbound API calls."""

# Seconds to wait for a response before giving up on a single attempt.
REQUEST_TIMEOUT = 5

MAX_ATTEMPTS = 3
BACKOFF_FACTOR = 2.0


def timeout_for(attempt: int) -> float:
    """Per-attempt timeout, growing with the backoff factor."""
    return REQUEST_TIMEOUT * (BACKOFF_FACTOR ** (attempt - 1))
