"""MedFlow authorization facade.

The previously verified collocated Model-A engine is preserved byte-for-byte in
``authorization_core.py``.  This facade adds only lifecycle guards that depend
on schema introduced after that engine was frozen.
"""

from datetime import datetime, timezone

from app.models.access import DocumentAccessRequest
from app.services.access_lifecycle import access_request_is_expired
from app.services.authorization_core import *  # noqa: F401,F403
from app.services.authorization_core import AuthorizationService as CoreAuthorizationService


class AuthorizationService(CoreAuthorizationService):
    """Current authorization engine with additive access-request expiry guard."""

    def _authorize_access_request(self, ctx):
        req = (
            ctx.resource
            if isinstance(ctx.resource, DocumentAccessRequest)
            else None
        )
        if (
            req is not None
            and ctx.operation in (Operation.GRANT_ACCESS, Operation.DELETE)
            and access_request_is_expired(req, now=datetime.now(timezone.utc))
        ):
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                "Access request has expired",
            )
        return super()._authorize_access_request(ctx)
