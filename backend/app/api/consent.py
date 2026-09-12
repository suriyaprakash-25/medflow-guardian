from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.consent import Consent, ConsentStatus, ConsentPolicyVersion, ConsentState
from app.schemas.consent import ConsentCreate, ConsentTransition, ConsentResponse, ConsentStateResponse
from app.api.dependencies import get_current_user

router = APIRouter()

@router.post("/consents", response_model=ConsentResponse)
def create_consent(
    consent_in: ConsentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can create consents")

    # 1. Create Consent Entity
    consent = Consent(
        patient_id=current_user.id,
        hospital_id=consent_in.hospital_id,
        doctor_id=consent_in.doctor_id,
        status=ConsentStatus.ACTIVE.value
    )
    db.add(consent)
    db.flush()

    # 2. Create Policy Version
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": consent_in.allowed_purposes,
            "allowed_operations": consent_in.allowed_operations
        },
        status="active"
    )
    db.add(policy)
    db.flush()

    # 3. Create Authoritative State History
    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=ConsentStatus.ACTIVE.value
    )
    db.add(state)
    db.commit()
    db.refresh(consent)
    
    return consent

@router.post("/consents/{consent_id}/transition", response_model=ConsentStateResponse)
def transition_consent(
    consent_id: int,
    transition: ConsentTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve consent
    consent = db.query(Consent).filter(Consent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
        
    if consent.patient_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to modify this consent")

    valid_transitions = {
        ConsentStatus.DRAFT.value: [ConsentStatus.ACTIVE.value, ConsentStatus.CANCELLED.value],
        ConsentStatus.ACTIVE.value: [ConsentStatus.SUSPENDED.value, ConsentStatus.REVOKED.value, ConsentStatus.EXPIRED.value, ConsentStatus.SUPERSEDED.value],
        ConsentStatus.SUSPENDED.value: [ConsentStatus.ACTIVE.value, ConsentStatus.REVOKED.value]
    }
    
    current_status = consent.status
    target_status = transition.target_status

    if target_status not in valid_transitions.get(current_status, []):
        raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to {target_status}")

    # Get active policy version
    policy = db.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id,
        ConsentPolicyVersion.status == "active"
    ).order_by(ConsentPolicyVersion.version_number.desc()).first()

    if not policy:
        raise HTTPException(status_code=500, detail="Active policy version not found")

    # Update Consent Entity
    consent.status = target_status
    
    # Append to State History
    new_state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=target_status
    )
    db.add(new_state)
    db.commit()
    db.refresh(new_state)

    return new_state
