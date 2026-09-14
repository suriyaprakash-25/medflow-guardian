from __future__ import annotations

from datetime import datetime, timezone

from app.core.time import as_utc
from app.models.access import DocumentAccessRequest


def access_request_is_expired(
    request: DocumentAccessRequest,
    *,
    now: datetime | None = None,
) -> bool:
    """Return the authoritative time-based expiry state for a pending request."""
    if request.status != "pending" or request.expires_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    return as_utc(request.expires_at) <= as_utc(current)


def materialize_access_request_expiry(
    request: DocumentAccessRequest,
    *,
    now: datetime | None = None,
) -> bool:
    """Transition an overdue pending request to the terminal expired state."""
    current = now or datetime.now(timezone.utc)
    if not access_request_is_expired(request, now=current):
        return False
    request.status = "expired"
    request.responded_at = current
    return True
