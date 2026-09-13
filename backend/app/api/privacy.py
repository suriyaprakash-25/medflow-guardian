from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.privacy import PrivacyLegalHold, PrivacyRequest
from app.models.user import User
from app.schemas.privacy import (
    LegalHoldCreate,
    PrivacyRequestCreate,
    PrivacyRequestDecision,
    PrivacyRequestResponse,
)
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.privacy import PrivacyExecutionError, execute_approved_deletion


router = APIRouter()


def _authorize(
    db: Session,
    actor: User,
    operation: Operation,
    resource_type: ResourceType,
    patient_id: int | None = None,
) -> None:
    decision = AuthorizationService(db).authorize(
        AuthorizationContext(
            actor=actor,
            operation=operation,
            resource_type=resource_type,
            db=db,
            patient_id=patient_id,
            requires_consent=False,
        )
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or "Not authorized")


@router.post("/privacy/requests", response_model=PrivacyRequestResponse, status_code=201)
def create_privacy_request(
    payload: PrivacyRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.CREATE, ResourceType.PRIVACY_REQUEST, current_user.id)
    duplicate = db.query(PrivacyRequest).filter(
        PrivacyRequest.patient_id == current_user.id,
        PrivacyRequest.request_type == payload.request_type,
        PrivacyRequest.status.in_(["pending", "approved"]),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An active request of this type already exists")
    request = PrivacyRequest(
        patient_id=current_user.id,
        request_type=payload.request_type,
        reason=payload.reason,
        status="pending",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/privacy/requests", response_model=list[PrivacyRequestResponse])
def list_own_privacy_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.LIST, ResourceType.PRIVACY_REQUEST, current_user.id)
    return db.query(PrivacyRequest).filter(
        PrivacyRequest.patient_id == current_user.id
    ).order_by(PrivacyRequest.requested_at.desc()).all()


@router.get("/admin/privacy/requests", response_model=list[PrivacyRequestResponse])
def list_privacy_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.LIST, ResourceType.PRIVACY_REQUEST)
    query = db.query(PrivacyRequest)
    if status:
        if status not in {"pending", "approved", "rejected", "completed"}:
            raise HTTPException(status_code=400, detail="Invalid privacy request status")
        query = query.filter(PrivacyRequest.status == status)
    return query.order_by(PrivacyRequest.requested_at.asc()).all()


@router.post("/admin/privacy/requests/{request_id}/decision", response_model=PrivacyRequestResponse)
def decide_privacy_request(
    request_id: int,
    payload: PrivacyRequestDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.UPDATE, ResourceType.PRIVACY_REQUEST)
    request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).with_for_update().first()
    if not request:
        raise HTTPException(status_code=404, detail="Privacy request not found")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Privacy request has already been reviewed")
    request.status = payload.decision
    request.review_notes = payload.review_notes
    request.reviewed_by_id = current_user.id
    request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request


@router.post("/admin/privacy/requests/{request_id}/execute", response_model=PrivacyRequestResponse)
def execute_privacy_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.UPDATE, ResourceType.PRIVACY_REQUEST)
    try:
        request = execute_approved_deletion(db, request_id)
        db.commit()
        db.refresh(request)
        return request
    except PrivacyExecutionError as exc:
        # All expected conflicts are validated before the service mutates data.
        # Commit the authorization decision while leaving protected data intact.
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/admin/privacy/legal-holds", status_code=201)
def place_legal_hold(
    payload: LegalHoldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.CREATE, ResourceType.LEGAL_HOLD)
    patient = db.query(User).filter(User.id == payload.patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = db.query(PrivacyLegalHold).filter(
        PrivacyLegalHold.patient_id == payload.patient_id,
        PrivacyLegalHold.active.is_(True),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="An active legal hold already exists")
    hold = PrivacyLegalHold(
        patient_id=payload.patient_id,
        reason=payload.reason,
        placed_by_id=current_user.id,
        active=True,
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return {"id": hold.id, "patient_id": hold.patient_id, "active": hold.active}


@router.post("/admin/privacy/legal-holds/{hold_id}/release")
def release_legal_hold(
    hold_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _authorize(db, current_user, Operation.UPDATE, ResourceType.LEGAL_HOLD)
    hold = db.query(PrivacyLegalHold).filter(PrivacyLegalHold.id == hold_id).with_for_update().first()
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    if not hold.active:
        raise HTTPException(status_code=409, detail="Legal hold is already released")
    hold.active = False
    hold.released_by_id = current_user.id
    hold.released_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": hold.id, "patient_id": hold.patient_id, "active": hold.active}
