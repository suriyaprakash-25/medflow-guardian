from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.clinical import Prescription, Medication, LabResult, ClinicalNote
from app.models.user import User
from app.schemas.clinical import PrescriptionCreate, PrescriptionResponse, LabResultCreate, LabResultResponse, ClinicalNoteCreate, ClinicalNoteResponse
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType

router = APIRouter()

# -- Prescriptions --

@router.post("/prescriptions", response_model=PrescriptionResponse)
def create_prescription(
    prescription: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=prescription.patient_id,
        hospital_id=prescription.hospital_id,
        purpose="TREATMENT"
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    db_prescription = Prescription(
        patient_id=prescription.patient_id,
        doctor_id=current_user.id,
        medication_id=prescription.medication_id,
        hospital_id=prescription.hospital_id,
        dosage=prescription.dosage,
        frequency=prescription.frequency,
        start_date=prescription.start_date,
        end_date=prescription.end_date,
        notes=prescription.notes
    )
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription

@router.get("/prescriptions/patient/{patient_id}", response_model=List[PrescriptionResponse])
def get_patient_prescriptions(
    patient_id: int,
    enforcement_state_id: Optional[int] = Query(None),
    purpose: Optional[str] = Query("TREATMENT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient_id,
        purpose=purpose,
        enforcement_state_id=enforcement_state_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
            
    return db.query(Prescription).filter(Prescription.patient_id == patient_id).all()

# -- Lab Results --

@router.post("/labs", response_model=LabResultResponse)
def create_lab_result(
    lab: LabResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=lab.patient_id,
        hospital_id=lab.hospital_id,
        purpose="TREATMENT"
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    db_lab = LabResult(
        patient_id=lab.patient_id,
        doctor_id=current_user.id,
        hospital_id=lab.hospital_id,
        test_name=lab.test_name,
        result_value=lab.result_value,
        unit=lab.unit,
        reference_range=lab.reference_range,
        test_date=lab.test_date,
        notes=lab.notes
    )
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab

@router.get("/labs/patient/{patient_id}", response_model=List[LabResultResponse])
def get_patient_labs(
    patient_id: int,
    enforcement_state_id: Optional[int] = Query(None),
    purpose: Optional[str] = Query("TREATMENT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient_id,
        purpose=purpose,
        enforcement_state_id=enforcement_state_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
            
    return db.query(LabResult).filter(LabResult.patient_id == patient_id).all()

# -- Clinical Notes --

@router.post("/notes", response_model=ClinicalNoteResponse)
def create_clinical_note(
    note: ClinicalNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=note.patient_id,
        hospital_id=note.hospital_id,
        purpose="TREATMENT"
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    db_note = ClinicalNote(
        patient_id=note.patient_id,
        doctor_id=current_user.id,
        hospital_id=note.hospital_id,
        title=note.title,
        content=note.content,
        note_type=note.note_type
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@router.get("/notes/patient/{patient_id}", response_model=List[ClinicalNoteResponse])
def get_patient_notes(
    patient_id: int,
    enforcement_state_id: Optional[int] = Query(None),
    purpose: Optional[str] = Query("TREATMENT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient_id,
        purpose=purpose,
        enforcement_state_id=enforcement_state_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
            
    return db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id).all()
