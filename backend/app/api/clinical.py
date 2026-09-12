from typing import List, Optional, Type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.clinical import ClinicalNote, LabResult, Prescription
from app.models.user import User
from app.schemas.clinical import (
    ClinicalNoteCreate,
    ClinicalNoteResponse,
    LabResultCreate,
    LabResultResponse,
    PrescriptionCreate,
    PrescriptionResponse,
)
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.consent_context import resolve_active_scoped_consent

router = APIRouter()


def _authorize_clinical_access(
    *,
    db: Session,
    current_user: User,
    patient_id: int,
    hospital_id: Optional[int],
    purpose: Optional[str],
    operation: Operation,
) -> None:
    """Build the trusted clinical authorization context server-side.

    Patients may read their own records without a third-party consent context.
    Practitioner access is purpose-bound and must resolve an ACTIVE consent that
    is explicitly scoped to the exact patient, practitioner, and hospital. The
    client never chooses the consent ID that reaches the CAE.
    """
    consent_id = None

    if current_user.role == "doctor":
        if hospital_id is None:
            raise HTTPException(
                status_code=400,
                detail="hospital_id is required for practitioner clinical access",
            )
        if purpose is None or not purpose.strip():
            raise HTTPException(
                status_code=403,
                detail="PURPOSE_REQUIRED: practitioner clinical access requires an explicit purpose",
            )

        consent = resolve_active_scoped_consent(
            db,
            patient_id=patient_id,
            doctor_id=current_user.id,
            hospital_id=hospital_id,
        )
        consent_id = consent.id if consent else None

    ctx = AuthorizationContext(
        actor=current_user,
        operation=operation,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient_id,
        hospital_id=hospital_id,
        purpose=purpose,
        consent_id=consent_id,
    )
    decision = AuthorizationService(db).authorize(ctx)
    if not decision.allowed:
        raise HTTPException(
            status_code=403,
            detail=decision.detail or str(decision.reason),
        )


def _scoped_patient_records_query(
    *,
    db: Session,
    model: Type,
    patient_id: int,
    current_user: User,
    hospital_id: Optional[int],
):
    query = db.query(model).filter(model.patient_id == patient_id)

    # A practitioner authorization is hospital-specific. Never authorize one
    # hospital and then return records belonging to every hospital.
    if current_user.role == "doctor":
        query = query.filter(model.hospital_id == hospital_id)
    elif hospital_id is not None:
        query = query.filter(model.hospital_id == hospital_id)

    return query


# -- Prescriptions --


@router.post("/prescriptions", response_model=PrescriptionResponse)
def create_prescription(
    prescription: PrescriptionCreate,
    purpose: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=prescription.patient_id,
        hospital_id=prescription.hospital_id,
        purpose=purpose,
        operation=Operation.CREATE,
    )

    db_prescription = Prescription(
        patient_id=prescription.patient_id,
        doctor_id=current_user.id,
        medication_id=prescription.medication_id,
        hospital_id=prescription.hospital_id,
        dosage=prescription.dosage,
        frequency=prescription.frequency,
        start_date=prescription.start_date,
        end_date=prescription.end_date,
        notes=prescription.notes,
    )
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription


@router.get("/prescriptions/patient/{patient_id}", response_model=List[PrescriptionResponse])
def get_patient_prescriptions(
    patient_id: int,
    purpose: Optional[str] = Query(None),
    hospital_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=patient_id,
        hospital_id=hospital_id,
        purpose=purpose,
        operation=Operation.LIST,
    )

    return _scoped_patient_records_query(
        db=db,
        model=Prescription,
        patient_id=patient_id,
        current_user=current_user,
        hospital_id=hospital_id,
    ).all()


# -- Lab Results --


@router.post("/labs", response_model=LabResultResponse)
def create_lab_result(
    lab: LabResultCreate,
    purpose: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=lab.patient_id,
        hospital_id=lab.hospital_id,
        purpose=purpose,
        operation=Operation.CREATE,
    )

    db_lab = LabResult(
        patient_id=lab.patient_id,
        doctor_id=current_user.id,
        hospital_id=lab.hospital_id,
        test_name=lab.test_name,
        result_value=lab.result_value,
        unit=lab.unit,
        reference_range=lab.reference_range,
        test_date=lab.test_date,
        notes=lab.notes,
    )
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab


@router.get("/labs/patient/{patient_id}", response_model=List[LabResultResponse])
def get_patient_labs(
    patient_id: int,
    purpose: Optional[str] = Query(None),
    hospital_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=patient_id,
        hospital_id=hospital_id,
        purpose=purpose,
        operation=Operation.LIST,
    )

    return _scoped_patient_records_query(
        db=db,
        model=LabResult,
        patient_id=patient_id,
        current_user=current_user,
        hospital_id=hospital_id,
    ).all()


# -- Clinical Notes --


@router.post("/notes", response_model=ClinicalNoteResponse)
def create_clinical_note(
    note: ClinicalNoteCreate,
    purpose: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=note.patient_id,
        hospital_id=note.hospital_id,
        purpose=purpose,
        operation=Operation.CREATE,
    )

    db_note = ClinicalNote(
        patient_id=note.patient_id,
        doctor_id=current_user.id,
        hospital_id=note.hospital_id,
        title=note.title,
        content=note.content,
        note_type=note.note_type,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


@router.get("/notes/patient/{patient_id}", response_model=List[ClinicalNoteResponse])
def get_patient_notes(
    patient_id: int,
    purpose: Optional[str] = Query(None),
    hospital_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize_clinical_access(
        db=db,
        current_user=current_user,
        patient_id=patient_id,
        hospital_id=hospital_id,
        purpose=purpose,
        operation=Operation.LIST,
    )

    return _scoped_patient_records_query(
        db=db,
        model=ClinicalNote,
        patient_id=patient_id,
        current_user=current_user,
        hospital_id=hospital_id,
    ).all()
