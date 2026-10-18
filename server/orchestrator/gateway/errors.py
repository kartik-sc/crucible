"""Gateway error taxonomy.

The retry/rotate decision is driven entirely by these types:
  - RetryableError  -> cool the key, try the next one (429 / 5xx / timeout)
  - KeyAuthError    -> likely a bad key; long-cool it and try the next
  - NonRetryableError -> a request/model bug; fail fast, do NOT rotate
  - GatewayExhausted / AllKeysCoolingError -> pool-level failures
"""
from __future__ import annotations


class GatewayError(Exception):
    """Base class for every gateway error."""


class ConfigError(GatewayError):
    """Missing/invalid configuration (e.g. an empty key pool)."""


class RetryableError(GatewayError):
    """Transient provider failure. Rotate to the next key and retry.

    retry_after is the provider-suggested cool-down in seconds (0 if unknown).
    """

    def __init__(self, message: str, retry_after: float = 0.0, status: int | None = None):
        super().__init__(message)
        self.retry_after = max(0.0, float(retry_after))
        self.status = status


class KeyAuthError(RetryableError):
    """401/403 on a single key. Treated as retryable (try the next key) but
    long-cooled, so one mistyped key does not sink a call while real keys exist.
    If every key auth-fails, GatewayExhausted surfaces this as the last error.
    """


class NonRetryableError(GatewayError):
    """A bug, not a limit: 400/404/422, malformed/blocked response, bad model id.
    The same request will fail on every key, so we fail fast instead of burning
    the pool.
    """

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class AllKeysCoolingError(GatewayError):
    """Every key in the pool is currently cooling down."""

    def __init__(self, wait: float):
        super().__init__(f"all keys cooling; soonest available in {wait:.2f}s")
        self.wait = wait


class GatewayExhausted(GatewayError):
    """Retry budget spent without a successful call."""

    def __init__(self, role: str, attempts: int, last_error: Exception | None):
        super().__init__(f"gateway exhausted for role={role} after {attempts} attempts: {last_error}")
        self.role = role
        self.attempts = attempts
        self.last_error = last_error
