from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.hospital import Hospital, Visit, HospitalStaff
from app.models.user import User
from app.models.document import MedicalDocument
from app.schemas.hospital import Hospital as HospitalSchema, VisitWithDetails
from app.api.dependencies import get_current_user, get_current_patient, get_current_doctor

router = APIRouter()

@router.get("/hospitals", response_model=List[HospitalSchema])
def list_hospitals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Hospital).filter(Hospital.is_active == True).all()

@router.get("/hospitals/{hospital_id}", response_model=HospitalSchema)
def get_hospital(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital

@router.get("/visits/patient", response_model=List[VisitWithDetails])
def get_patient_visits(db: Session = Depends(get_db), current_patient: User = Depends(get_current_patient)):
    visits = db.query(Visit).filter(Visit.patient_id == current_patient.id).all()
    return visits

@router.get("/visits/doctor", response_model=List[VisitWithDetails])
def get_doctor_visits(db: Session = Depends(get_db), current_doctor: User = Depends(get_current_doctor)):
    # Doctor can only see visits for hospitals they are affiliated with
    affiliations = db.query(HospitalStaff).filter(HospitalStaff.user_id == current_doctor.id).all()
    hospital_ids = [aff.hospital_id for aff in affiliations]
    
    if not hospital_ids:
        return []

    visits = db.query(Visit).filter(Visit.hospital_id.in_(hospital_ids)).all()
    return visits

@router.get("/admin/dashboard")
def get_admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get hospital affiliation
    affiliation = db.query(HospitalStaff).filter(HospitalStaff.user_id == current_user.id, HospitalStaff.role == "admin").first()
    if not affiliation:
        raise HTTPException(status_code=403, detail="No admin hospital affiliation found")

    hospital_id = affiliation.hospital_id

    # Get doctors at this hospital
    doctor_affiliations = db.query(HospitalStaff).filter(HospitalStaff.hospital_id == hospital_id, HospitalStaff.role == "doctor").all()
    doctor_ids = [aff.user_id for aff in doctor_affiliations]
    doctors = db.query(User).filter(User.id.in_(doctor_ids)).all()

    # Get visits
    visits = db.query(Visit).filter(Visit.hospital_id == hospital_id).all()

    # Get documents uploaded by this hospital (or during visits here)
    documents = db.query(MedicalDocument).filter(MedicalDocument.hospital_id == hospital_id).all()

    return {
        "hospital_id": hospital_id,
        "doctors": [{"id": d.id, "email": d.email, "full_name": d.full_name} for d in doctors],
        "visits": visits,
        "documents": documents
    }
