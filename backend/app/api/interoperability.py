from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict

from app.core.database import get_db
from app.models.user import User
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType
from app.schemas.consent import FHIRConsentImportResponse
from app.services.interoperability.fhir_consent import (
    FHIRConsentError,
    FHIRConsentImporter,
    map_fhir_consent,
)

from app.services.interoperability.fhir_serializers import (
    to_fhir_patient,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_document_reference_note,
    to_fhir_document_reference_file,
    to_fhir_bundle
)

router = APIRouter()


@router.post("/interoperability/fhir/consents/import", response_model=FHIRConsentImportResponse)
def import_fhir_consent(
    resource: Dict[str, Any] = Body(...),
    source_system: str = Query(..., min_length=8, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FHIRConsentImportResponse:
    """Import a supported FHIR R4 Consent into the central consent model."""
    try:
        mapped = map_fhir_consent(resource, source_system)
    except FHIRConsentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = AuthorizationService(db).authorize(AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.CONSENT,
        db=db,
        patient_id=mapped.patient_id,
    ))
    if not decision.allowed:
        db.rollback()
        raise HTTPException(status_code=403, detail=decision.detail)

    try:
        result = FHIRConsentImporter(db).import_consent(resource, source_system, current_user)
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

@router.get("/interoperability/patients/{patient_id}/export")
def export_patient_fhir_bundle(
    patient_id: int,
    purpose: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Exports a patient's complete clinical record as a FHIR R4 Bundle.
    Protected by the Central Authorization Engine.
    """
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.READ,
        resource_type=ResourceType.FHIR_EXPORT,
        db=db,
        patient_id=patient_id,
        purpose=purpose
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    # 1. Get Patient
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    resources = []
    
    # Add Patient Resource
    resources.append(to_fhir_patient(patient))

    # 2. Get Prescriptions
    prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient_id).all()
    for p in prescriptions:
        resources.append(to_fhir_medication_request(p))

    # 3. Get Lab Results
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    for lab in labs:
        resources.append(to_fhir_observation(lab))

    # 4. Get Clinical Notes
    notes = db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id).all()
    for note in notes:
        resources.append(to_fhir_document_reference_note(note))

    # 5. Get Medical Documents
    docs = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id).all()
    for doc in docs:
        resources.append(to_fhir_document_reference_file(doc))

    bundle = to_fhir_bundle(resources)
    return bundle
