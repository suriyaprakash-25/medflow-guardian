from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.models.user import User
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType

from app.services.interoperability.fhir_serializers import (
    to_fhir_patient,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_document_reference_note,
    to_fhir_document_reference_file,
    to_fhir_bundle
)

router = APIRouter()


@router.get("/interoperability/patients/{patient_id}/export")
def export_patient_fhir_bundle(
    patient_id: int,
    purpose: str = Query(..., min_length=1),
    consent_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Export a patient's clinical record as a FHIR R4 Bundle.

    Self-export is authorized by the CAE without provider consent. Provider
    export must carry an explicit consent_id; there is deliberately no fallback
    to visit/relationship access because FHIR export is a bulk disclosure.
    """
    if current_user.role == "doctor" and consent_id is None:
        raise HTTPException(status_code=403, detail="Provider FHIR export requires explicit consent_id")

    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.READ,
        resource_type=ResourceType.FHIR_EXPORT,
        db=db,
        patient_id=patient_id,
        relationship_context=consent_id,
        purpose=purpose,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    patient = db.query(User).filter(
        User.id == patient_id,
        User.role == "patient"
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    resources = [to_fhir_patient(patient)]

    for prescription in db.query(Prescription).filter(Prescription.patient_id == patient_id).all():
        resources.append(to_fhir_medication_request(prescription))

    for lab in db.query(LabResult).filter(LabResult.patient_id == patient_id).all():
        resources.append(to_fhir_observation(lab))

    for note in db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id).all():
        resources.append(to_fhir_document_reference_note(note))

    for doc in db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id).all():
        resources.append(to_fhir_document_reference_file(doc))

    return to_fhir_bundle(resources)
