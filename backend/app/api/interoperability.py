from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.models.user import User
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.models.consent import Consent, ConsentState, ConsentPolicyVersion
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType

from app.services.interoperability.fhir_serializers import (
    to_fhir_patient,
    to_fhir_practitioner,
    to_fhir_organization,
    to_fhir_consent,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_document_reference_note,
    to_fhir_document_reference_file,
    to_fhir_bundle,
)

router = APIRouter()


@router.get("/interoperability/patients/{patient_id}/export")
def export_patient_fhir_bundle(
    patient_id: int,
    purpose: str = Query(..., min_length=1),
    consent_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    resources = [to_fhir_patient(patient)]
    doctor_ids = set()
    hospital_ids = set()

    prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient_id).all()
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    notes = db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id).all()
    documents = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id).all()

    for prescription in prescriptions:
        resources.append(to_fhir_medication_request(prescription))
        doctor_ids.add(prescription.doctor_id)
        hospital_ids.add(prescription.hospital_id)
    for lab in labs:
        resources.append(to_fhir_observation(lab))
        doctor_ids.add(lab.doctor_id)
        hospital_ids.add(lab.hospital_id)
    for note in notes:
        resources.append(to_fhir_document_reference_note(note))
        doctor_ids.add(note.doctor_id)
        hospital_ids.add(note.hospital_id)
    for doc in documents:
        resources.append(to_fhir_document_reference_file(doc))
        doctor_ids.add(doc.uploaded_by_doctor_id)
        hospital_ids.add(doc.hospital_id)

    # Add referenced practitioners and organizations so the exported Bundle is
    # self-describing rather than leaving dangling Practitioner/Organization refs.
    if doctor_ids:
        for doctor in db.query(User).filter(User.id.in_(doctor_ids), User.role == "doctor").all():
            resources.append(to_fhir_practitioner(doctor))
    if hospital_ids:
        for hospital in db.query(__import__("app.models.hospital", fromlist=["Hospital"]).Hospital).filter(
            __import__("app.models.hospital", fromlist=["Hospital"]).Hospital.id.in_(hospital_ids)
        ).all():
            resources.append(to_fhir_organization(hospital))

    # For provider disclosure, expose the exact authoritative consent state and
    # immutable policy version that the CAE evaluated. This is interoperability
    # metadata, not a second authorization path.
    if current_user.role == "doctor" and consent_id is not None:
        consent = db.query(Consent).filter(Consent.id == consent_id).first()
        state = db.query(ConsentState).filter(ConsentState.id == ctx.consent_state_id).first() if ctx.consent_state_id else None
        policy = db.query(ConsentPolicyVersion).filter(ConsentPolicyVersion.id == state.policy_version_id).first() if state else None
        if consent and state and policy:
            resources.append(to_fhir_consent(consent, state, policy))
            if consent.doctor_id:
                doctor = db.query(User).filter(User.id == consent.doctor_id, User.role == "doctor").first()
                if doctor and doctor.id not in doctor_ids:
                    resources.append(to_fhir_practitioner(doctor))
            if consent.hospital_id:
                from app.models.hospital import Hospital
                hospital = db.query(Hospital).filter(Hospital.id == consent.hospital_id).first()
                if hospital and hospital.id not in hospital_ids:
                    resources.append(to_fhir_organization(hospital))

    return to_fhir_bundle(resources)
