from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentState, ConsentStatus


def resolve_active_scoped_consent(
    db: Session,
    *,
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
) -> Optional[Consent]:
    """Resolve one authoritative, explicitly scoped consent for clinical access.

    R5 deliberately does not infer authority from a client supplied consent ID and
    does not widen an unscoped consent (doctor_id/hospital_id = NULL) into an
    organization-specific clinical authorization. Only consents explicitly bound
    to this patient, practitioner, and hospital are eligible.

    If multiple exact-scope consent records exist, the newest record whose latest
    append-only state is ACTIVE is selected deterministically. ConsentService still
    evaluates the authoritative state, policy purpose, and operation before access
    is released, so this helper is context resolution rather than a parallel PDP.
    """
    candidates = (
        db.query(Consent)
        .filter(
            Consent.patient_id == patient_id,
            Consent.doctor_id == doctor_id,
            Consent.hospital_id == hospital_id,
            Consent.status == ConsentStatus.ACTIVE.value,
        )
        .order_by(Consent.created_at.desc(), Consent.id.desc())
        .all()
    )

    for consent in candidates:
        latest_state = (
            db.query(ConsentState)
            .filter(ConsentState.consent_id == consent.id)
            .order_by(ConsentState.created_at.desc(), ConsentState.id.desc())
            .first()
        )
        if latest_state and latest_state.status == ConsentStatus.ACTIVE.value:
            return consent

    return None
