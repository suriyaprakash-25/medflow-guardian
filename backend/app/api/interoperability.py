from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.clinical import ClinicalNote, LabResult, Prescription
from app.models.consent import Consent
from app.models.document import MedicalDocument
from app.models.user import User
from app.schemas.consent import FHIRConsentImportResponse
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.interoperability.fhir_consent import (
    FHIRConsentError,
    FHIRConsentImporter,
    map_fhir_consent,
)
from app.services.interoperability.fhir_serializers import (
    to_fhir_bundle,
    to_fhir_document_reference_file,
    to_fhir_document_reference_note,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_patient,
)


router = APIRouter()


def _denial_detail(decision) -> str:
    if decision.detail:
        return decision.detail
    if decision.reason is not None:
        return decision.reason.value
    return "Authorization denied"


def _import_canonical_fhir_consent(
    *,
    resource: Dict[str, Any],
    source_system: str,
    db: Session,
    current_user: User,
) -> FHIRConsentImportResponse:
    """Authorize and persist one resource through the single R6 import path."""
    try:
        mapped = map_fhir_consent(resource, source_system)
    except FHIRConsentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = AuthorizationService(db).authorize(
        AuthorizationContext(
            actor=current_user,
            operation=Operation.CREATE,
            resource_type=ResourceType.CONSENT,
            db=db,
            patient_id=mapped.patient_id,
        )
    )
    if not decision.allowed:
        # AuthorizationService flushed a DENY audit row into this otherwise
        # read-only transaction. Commit that audit decision; do not roll the
        # session back and erase both the audit evidence and test/request state.
        db.commit()
        raise HTTPException(status_code=403, detail=_denial_detail(decision))

    try:
        result = FHIRConsentImporter(db).import_consent(
            resource,
            source_system,
            current_user,
        )
        db.commit()
        db.refresh(result.consent)
        db.refresh(result.policy)
        db.refresh(result.state)
    except FHIRConsentError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return FHIRConsentImportResponse(
        consent_id=result.consent.id,
        policy_version_id=result.policy.id,
        policy_version_number=result.policy.version_number,
        state_id=result.state.id,
        state_status=result.state.status,
        created=result.created,
        source_system=result.consent.source_system,
        source_resource_id=result.consent.source_resource_id,
        policy_payload=result.policy.policy_payload,
    )


@router.post(
    "/interoperability/consents/import",
    response_model=FHIRConsentImportResponse,
    deprecated=True,
)
def import_fhir_consent_compatibility_alias(
    resource: Dict[str, Any] = Body(...),
    source_system: str = Query(..., min_length=8, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FHIRConsentImportResponse:
    """Deprecated route alias; semantics are identical to the canonical endpoint."""
    return _import_canonical_fhir_consent(
        resource=resource,
        source_system=source_system,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/interoperability/fhir/consents/import",
    response_model=FHIRConsentImportResponse,
)
def import_fhir_consent(
    resource: Dict[str, Any] = Body(...),
    source_system: str = Query(..., min_length=8, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FHIRConsentImportResponse:
    """Import the declared fail-closed FHIR R4 Consent subset."""
    return _import_canonical_fhir_consent(
        resource=resource,
        source_system=source_system,
        db=db,
        current_user=current_user,
    )


@router.get("/interoperability/patients/{patient_id}/export")
def export_patient_fhir_bundle(
    patient_id: int,
    purpose: str = Query(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    ),
    consent_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Export the authorized patient record as a scoped FHIR R4 collection Bundle."""
    consent = None
    if current_user.role == "doctor" and consent_id is not None:
        consent = db.query(Consent).filter(Consent.id == consent_id).first()
        # A practitioner export must have an organization boundary so one
        # authorization decision cannot release records from other hospitals.
        if consent is not None and consent.hospital_id is None:
            raise HTTPException(
                status_code=403,
                detail="Practitioner FHIR export requires organization-scoped consent",
            )

    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.READ,
        resource_type=ResourceType.FHIR_EXPORT,
        db=db,
        patient_id=patient_id,
        hospital_id=consent.hospital_id if consent else None,
        relationship_context=consent,
        purpose=purpose,
        consent_id=consent_id,
    )
    decision = AuthorizationService(db).authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=_denial_detail(decision))

    patient = db.query(User).filter(
        User.id == patient_id,
        User.role == "patient",
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    resources = [to_fhir_patient(patient)]
    hospital_scope = consent.hospital_id if current_user.role == "doctor" and consent else None

    prescription_query = db.query(Prescription).filter(
        Prescription.patient_id == patient_id
    )
    lab_query = db.query(LabResult).filter(LabResult.patient_id == patient_id)
    note_query = db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id)
    document_query = db.query(MedicalDocument).filter(
        MedicalDocument.patient_id == patient_id
    )

    if hospital_scope is not None:
        prescription_query = prescription_query.filter(
            Prescription.hospital_id == hospital_scope
        )
        lab_query = lab_query.filter(LabResult.hospital_id == hospital_scope)
        note_query = note_query.filter(ClinicalNote.hospital_id == hospital_scope)
        document_query = document_query.filter(
            MedicalDocument.hospital_id == hospital_scope
        )

    for prescription in prescription_query.all():
        resources.append(to_fhir_medication_request(prescription))
    for lab in lab_query.all():
        resources.append(to_fhir_observation(lab))
    for note in note_query.all():
        resources.append(to_fhir_document_reference_note(note))
    for document in document_query.all():
        resources.append(to_fhir_document_reference_file(document))

    return to_fhir_bundle(resources)
