from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.clinical import ClinicalNote, LabResult, Prescription
from app.models.document import MedicalDocument
from app.models.hospital import Hospital
from app.models.user import User
from app.schemas.consent import FHIRConsentImportResponse
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.consent_context import resolve_active_scoped_consent
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
    to_fhir_organization,
    to_fhir_patient,
    to_fhir_practitioner,
)
from app.services.interoperability.capability import build_capability_statement


router = APIRouter()


@router.get("/interoperability/metadata")
def fhir_capability_statement(request: Request) -> JSONResponse:
    """Return the public, implementation-specific FHIR R4 capability statement."""
    return JSONResponse(
        build_capability_statement(str(request.base_url).rstrip("/")),
        media_type="application/fhir+json",
    )


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
    hospital_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Export an authorized patient record as a scoped FHIR R4 Bundle.

    Patient self-export remains consent-free. For practitioner export, the
    browser supplies only the intended hospital scope and purpose. The backend
    resolves the exact active patient+doctor+hospital consent and then passes it
    into the existing CAE/ConsentService path. No client-supplied consent ID is
    accepted as authorization authority.
    """
    consent = None
    if current_user.role == "doctor":
        if hospital_id is None:
            raise HTTPException(
                status_code=422,
                detail="Practitioner FHIR export requires hospital_id scope",
            )
        consent = resolve_active_scoped_consent(
            db,
            patient_id=patient_id,
            doctor_id=current_user.id,
            hospital_id=hospital_id,
        )
        if consent is None:
            raise HTTPException(
                status_code=403,
                detail="No active consent is scoped to this patient, practitioner, and hospital",
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
        consent_id=consent.id if consent else None,
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

    prescriptions = prescription_query.all()
    labs = lab_query.all()
    notes = note_query.all()
    documents = document_query.all()

    practitioner_ids = {
        item.doctor_id for item in [*prescriptions, *labs, *notes]
    } | {item.uploaded_by_doctor_id for item in documents}
    organization_ids = {
        item.hospital_id for item in [*prescriptions, *labs, *notes, *documents]
    }
    practitioners = db.query(User).filter(
        User.id.in_(practitioner_ids), User.role == "doctor"
    ).all() if practitioner_ids else []
    organizations = db.query(Hospital).filter(
        Hospital.id.in_(organization_ids)
    ).all() if organization_ids else []
    resources.extend(to_fhir_practitioner(item) for item in practitioners)
    resources.extend(to_fhir_organization(item) for item in organizations)

    for prescription in prescriptions:
        resources.append(to_fhir_medication_request(prescription))
    for lab in labs:
        resources.append(to_fhir_observation(lab))
    for note in notes:
        resources.append(to_fhir_document_reference_note(note))
    for document in documents:
        resources.append(to_fhir_document_reference_file(document))

    return JSONResponse(
        to_fhir_bundle(resources),
        media_type="application/fhir+json",
    )
