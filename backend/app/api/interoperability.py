from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict

from app.core.database import get_db
from app.models.user import User
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.models.consent import Consent
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType
from app.schemas.consent import FHIRConsentImportResponse
from app.services.interoperability.fhir_consent import (
    FHIRConsentError,
    FHIRConsentImporter,
    map_fhir_consent,
)
from app.services.interoperability.fhir_consent_import import (
    FHIRConsentImportError,
    import_fhir_consent as import_strict_fhir_consent,
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


def _extract_import_patient_id(resource: Dict[str, Any]) -> int:
    """Extract the subject identifier needed for pre-persistence authorization."""
    if not isinstance(resource, dict) or resource.get("resourceType") != "Consent":
        raise FHIRConsentImportError("resourceType must be 'Consent'")
    patient = resource.get("patient")
    if not isinstance(patient, dict):
        raise FHIRConsentImportError("Consent.patient must be a FHIR Reference object")
    reference = patient.get("reference")
    if not isinstance(reference, str) or not reference.startswith("Patient/"):
        raise FHIRConsentImportError("Consent.patient.reference must use Patient/<internal-id>")
    parts = reference.split("/")
    if len(parts) != 2:
        raise FHIRConsentImportError("Consent.patient.reference must use Patient/<internal-id>")
    try:
        return int(parts[1])
    except ValueError as exc:
        raise FHIRConsentImportError(
            "Consent.patient.reference must contain a numeric MedFlow identifier"
        ) from exc


@router.post("/interoperability/consents/import", status_code=201)
def import_strict_patient_fhir_consent(
    resource: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compatibility endpoint for the fail-closed FHIR R4 import profile."""
    try:
        patient_id = _extract_import_patient_id(resource)
    except FHIRConsentImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = AuthorizationService(db).authorize(AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.CONSENT,
        db=db,
        patient_id=patient_id,
        purpose="CONSENT_MANAGEMENT",
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    try:
        imported = import_strict_fhir_consent(db, resource)
        db.commit()
        db.refresh(imported.consent)
        db.refresh(imported.policy_version)
        db.refresh(imported.state)
    except FHIRConsentImportError as exc:
        # Validation and scope checks complete before the strict importer adds
        # rows, so no transaction rollback is needed for this expected 422.
        # This also preserves any outer transaction owned by a caller/test.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "consent_id": imported.consent.id,
        "policy_version_id": imported.policy_version.id,
        "state_id": imported.state.id,
        "status": imported.state.status,
        "source_resource_id": imported.source_resource_id,
        "allowed_purposes": imported.policy_version.policy_payload.get("allowed_purposes", []),
        "allowed_operations": imported.policy_version.policy_payload.get("allowed_operations", []),
    }


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
    purpose: str = Query(..., min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$"),
    consent_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Exports a patient's complete clinical record as a FHIR R4 Bundle.
    Protected by the Central Authorization Engine.
    """
    consent = None
    if current_user.role == "doctor" and consent_id is not None:
        consent = db.query(Consent).filter(Consent.id == consent_id).first()

    auth_svc = AuthorizationService(db)
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
