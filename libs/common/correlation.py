"""Correlation ID tracking for all services.

Every incoming request gets a correlation_id (UUID v4). It is stored in a
ContextVar so every log line, DB row and outbound HTTP call in the same
request can include it. This is how we trace a single transfer end-to-end.
"""
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware


correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Return the correlation_id for the current request context."""
    return correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation_id for the current request context."""
    correlation_id_var.set(cid)


def _parse_or_generate(header_value: str | None) -> str:
    """Use the header if it is a valid UUID, else generate a fresh UUID v4."""
    if header_value:
        try:
            return str(uuid.UUID(header_value))
        except (ValueError, AttributeError):
            pass
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Read X-Correlation-ID, validate or generate, store, and echo back."""

    async def dispatch(self, request, call_next):
        cid = _parse_or_generate(request.headers.get("X-Correlation-ID"))
        correlation_id_var.set(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response