from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.consent import Consent, ConsentStatus, ConsentPolicyVersion, ConsentState
from app.models.access import DocumentAccessGrant
from datetime import datetime, timezone
from app.schemas.consent import (
    ConsentCreate,
    ConsentTransition,
    ConsentPolicyVersionCreate,
    ConsentResponse,
    ConsentStateResponse,
    ConsentPolicyVersionResponse,
)
from app.api.dependencies import get_current_user
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)

router = APIRouter()

CONSENT_MANAGEMENT_PURPOSE = "CONSENT_MANAGEMENT"


def _consent_response(db: Session, consent: Consent) -> dict:
    current_state = (
        db.query(ConsentState)
        .filter(ConsentState.consent_id == consent.id)
        .order_by(ConsentState.created_at.desc(), ConsentState.id.desc())
        .first()
    )
    active_policy = current_state.policy_version if current_state else None
    return {
        "id": consent.id,
        "patient_id": consent.patient_id,
        "hospital_id": consent.hospital_id,
        "doctor_id": consent.doctor_id,
        "status": consent.status,
        "created_at": consent.created_at,
        "updated_at": consent.updated_at,
        "current_state": current_state,
        "active_policy": active_policy,
    }


def _enforce_consent_write(
    *,
    db: Session,
    current_user: User,
    operation: Operation,
    patient_id: int,
    consent: Consent | None = None,
) -> None:
    """Authorize a consent mutation through the central authorization engine.

    Consent writes are patient-owned. Platform or organization administration
    never implies authority to change a patient's consent. This helper keeps the
    API from re-introducing endpoint-local role exceptions such as the legacy
    ``current_user.role == "admin"`` bypass.
    """
    decision = AuthorizationService(db).authorize(
        AuthorizationContext(
            actor=current_user,
            operation=operation,
            resource_type=ResourceType.CONSENT,
            db=db,
            resource=consent,
            hospital_id=consent.hospital_id if consent else None,
            patient_id=patient_id,
            consent_id=consent.id if consent else None,
            purpose=CONSENT_MANAGEMENT_PURPOSE,
        )
    )
    if not decision.allowed:
        detail = decision.detail or (
            decision.reason.value if decision.reason is not None else "Consent mutation is not authorized"
        )
        raise HTTPException(status_code=403, detail=detail)


@router.get("/consents", response_model=list[ConsentResponse])
def list_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _enforce_consent_write(
        db=db,
        current_user=current_user,
        operation=Operation.LIST,
        patient_id=current_user.id,
    )
    consents = (
        db.query(Consent)
        .filter(Consent.patient_id == current_user.id)
        .order_by(Consent.created_at.desc(), Consent.id.desc())
        .all()
    )
    return [_consent_response(db, item) for item in consents]


@router.get("/consents/{consent_id}", response_model=ConsentResponse)
def get_consent(
    consent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = db.query(Consent).filter(Consent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    _enforce_consent_write(
        db=db,
        current_user=current_user,
        operation=Operation.READ,
        patient_id=consent.patient_id,
        consent=consent,
    )
    return _consent_response(db, consent)


@router.post("/consents", response_model=ConsentResponse)
def create_consent(
    consent_in: ConsentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _enforce_consent_write(
        db=db,
        current_user=current_user,
        operation=Operation.CREATE,
        patient_id=current_user.id,
    )

    consent = Consent(
        patient_id=current_user.id,
        hospital_id=consent_in.hospital_id,
        doctor_id=consent_in.doctor_id,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": consent_in.allowed_purposes,
            "allowed_operations": consent_in.allowed_operations,
        },
        status="active",
        valid_from=consent_in.valid_from,
        valid_until=consent_in.valid_until,
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(state)
    db.commit()
    db.refresh(consent)
    return _consent_response(db, consent)


@router.post("/consents/{consent_id}/policy-versions", response_model=ConsentPolicyVersionResponse)
def create_policy_version(
    consent_id: int,
    policy_in: ConsentPolicyVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an immutable policy version and make it authoritative for future decisions."""
    consent = db.query(Consent).filter(Consent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    _enforce_consent_write(
        db=db,
        current_user=current_user,
        operation=Operation.UPDATE,
        patient_id=consent.patient_id,
        consent=consent,
    )

    latest = db.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).order_by(ConsentPolicyVersion.version_number.desc()).first()

    next_version = (latest.version_number + 1) if latest else 1

    # Policy versions are immutable. Retire the previous active version rather than editing it.
    active_versions = db.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id,
        ConsentPolicyVersion.status == "active",
    ).all()
    for version in active_versions:
        version.status = "superseded"

    new_policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=next_version,
        policy_payload={
            "allowed_purposes": policy_in.allowed_purposes,
            "allowed_operations": policy_in.allowed_operations,
        },
        status="active",
        valid_from=policy_in.valid_from,
        valid_until=policy_in.valid_until,
    )
    db.add(new_policy)
    db.flush()

    # A policy change is made authoritative through a new append-only state row.
    # Keep the current consent lifecycle status; do not implicitly reactivate a revoked/suspended consent.
    current_state = db.query(ConsentState).filter(
        ConsentState.consent_id == consent.id
    ).order_by(ConsentState.created_at.desc(), ConsentState.id.desc()).first()
    if not current_state:
        db.rollback()
        raise HTTPException(status_code=500, detail="Consent state history is missing")

    db.add(ConsentState(
        consent_id=consent.id,
        policy_version_id=new_policy.id,
        status=current_state.status,
        reason=policy_in.reason,
    ))
    db.commit()
    db.refresh(new_policy)
    return new_policy


@router.post("/consents/{consent_id}/transition", response_model=ConsentStateResponse)
def transition_consent(
    consent_id: int,
    transition: ConsentTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = db.query(Consent).filter(Consent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    _enforce_consent_write(
        db=db,
        current_user=current_user,
        operation=Operation.UPDATE,
        patient_id=consent.patient_id,
        consent=consent,
    )

    valid_transitions = {
        ConsentStatus.DRAFT.value: [ConsentStatus.ACTIVE.value, ConsentStatus.CANCELLED.value],
        ConsentStatus.ACTIVE.value: [
            ConsentStatus.SUSPENDED.value,
            ConsentStatus.REVOKED.value,
            ConsentStatus.EXPIRED.value,
            ConsentStatus.SUPERSEDED.value,
        ],
        ConsentStatus.SUSPENDED.value: [ConsentStatus.ACTIVE.value, ConsentStatus.REVOKED.value],
    }
    current_status = consent.status
    target_status = transition.target_status

    if target_status not in valid_transitions.get(current_status, []):
        raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to {target_status}")

    policy = db.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id,
        ConsentPolicyVersion.status == "active",
    ).order_by(ConsentPolicyVersion.version_number.desc()).first()
    if not policy:
        raise HTTPException(status_code=500, detail="Active policy version not found")

    consent.status = target_status
    new_state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=target_status,
        reason=transition.reason,
    )
    db.add(new_state)
    if target_status != ConsentStatus.ACTIVE.value:
        db.query(DocumentAccessGrant).filter(
            DocumentAccessGrant.consent_id == consent.id,
            DocumentAccessGrant.status == "active",
        ).update(
            {
                DocumentAccessGrant.status: "revoked",
                DocumentAccessGrant.revoked_at: datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
    db.commit()
    db.refresh(new_state)
    return new_state
