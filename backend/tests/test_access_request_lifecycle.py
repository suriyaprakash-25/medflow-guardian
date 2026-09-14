from datetime import datetime, timedelta, timezone

from app.models.access import DocumentAccessRequest
from app.schemas.access import AccessRequestResponse
from app.services.access_lifecycle import (
    access_request_is_expired,
    materialize_access_request_expiry,
)
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)


def _request(expires_at, status="pending"):
    return DocumentAccessRequest(
        id=1,
        patient_id=10,
        requesting_doctor_id=20,
        requesting_hospital_id=30,
        reason="Treatment",
        status=status,
        requested_at=datetime.now(timezone.utc) - timedelta(hours=2),
        expires_at=expires_at,
    )


def test_expired_request_materializes_terminal_state():
    now = datetime.now(timezone.utc)
    request = _request(now - timedelta(seconds=1))
    assert access_request_is_expired(request, now=now) is True
    assert materialize_access_request_expiry(request, now=now) is True
    assert request.status == "expired"
    assert request.responded_at == now


def test_future_request_remains_pending():
    now = datetime.now(timezone.utc)
    request = _request(now + timedelta(hours=1))
    assert access_request_is_expired(request, now=now) is False
    assert materialize_access_request_expiry(request, now=now) is False
    assert request.status == "pending"


def test_authorization_denies_approval_after_expiry():
    request = _request(datetime.now(timezone.utc) - timedelta(minutes=1))
    context = AuthorizationContext(
        actor=type("Actor", (), {"id": 10, "role": "patient", "is_active": True})(),
        operation=Operation.GRANT_ACCESS,
        resource_type=ResourceType.ACCESS_REQUEST,
        db=None,
        resource=request,
        patient_id=10,
        hospital_id=30,
    )
    decision = AuthorizationService(None)._authorize_access_request(context)
    assert decision.allowed is False
    assert decision.detail == "Access request has expired"


def test_response_exposes_effective_expired_status_without_client_authority():
    now = datetime.now(timezone.utc)
    response = AccessRequestResponse(
        id=1,
        patient_id=10,
        requesting_doctor_id=20,
        requesting_hospital_id=30,
        reason="Treatment",
        status="pending",
        requested_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
        requested_documents=[],
    )
    assert response.status == "expired"
