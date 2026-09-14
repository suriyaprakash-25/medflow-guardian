from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_authorization_service, get_practitioner_identity
from app.core.database import get_db
from app.models.access import DocumentAccessRequest
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.access import AccessRequestResponse
from app.services.access_lifecycle import materialize_access_request_expiry
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)


router = APIRouter()


@router.post(
    "/access-requests/{request_id}/cancel",
    response_model=AccessRequestResponse,
)
def cancel_access_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    """Cancel a still-pending request owned by the requesting practitioner."""
    req = (
        db.query(DocumentAccessRequest)
        .with_for_update()
        .filter(
            DocumentAccessRequest.id == request_id,
            DocumentAccessRequest.requesting_doctor_id == current_doctor.id,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if materialize_access_request_expiry(req):
        db.add(
            AuditLog(
                actor_id=current_doctor.id,
                actor_role="doctor",
                organization_id=req.requesting_hospital_id,
                patient_id=req.patient_id,
                operation="expire_access",
                resource_type="access_request",
                resource_id=str(req.id),
                decision="DENY",
                denial_reason="request_expired",
            )
        )
        db.commit()
        db.refresh(req)
        raise HTTPException(status_code=409, detail="Access request has expired")

    if req.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Access request is already {req.status}",
        )

    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_doctor,
            operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=db,
            resource=req,
            hospital_id=req.requesting_hospital_id,
            patient_id=req.patient_id,
            requires_consent=False,
        )
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    req.status = "cancelled"
    req.responded_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor_id=current_doctor.id,
            actor_role="doctor",
            organization_id=req.requesting_hospital_id,
            patient_id=req.patient_id,
            operation="cancel_access",
            resource_type="access_request",
            resource_id=str(req.id),
            decision="ALLOW",
        )
    )
    db.commit()
    db.refresh(req)
    return req
