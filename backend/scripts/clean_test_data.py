import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)
from app.core.config import settings

from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.triage import TriageRequest
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.user import User, PractitionerProfile, PatientProfile
from app.models.audit import AuditLog

def clean_test_data():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        test_user_ids = [u.id for u in db.query(User).filter(User.email.like('test_%@demo.com')).all()]
        test_hospitals_ids = [h.id for h in db.query(Hospital).filter(Hospital.name.like('Test Hospital%')).all()]
        
        if test_user_ids or test_hospitals_ids:
            # Audit Logs
            db.query(AuditLog).delete(synchronize_session=False)
            
            # Grants
            if test_user_ids:
                db.query(DocumentAccessGrant).filter(DocumentAccessGrant.doctor_id.in_(test_user_ids)).delete(synchronize_session=False)
            if test_hospitals_ids:
                db.query(DocumentAccessGrant).filter(DocumentAccessGrant.hospital_id.in_(test_hospitals_ids)).delete(synchronize_session=False)
            
            # Requests
            if test_user_ids:
                db.query(DocumentAccessRequest).filter(DocumentAccessRequest.patient_id.in_(test_user_ids)).delete(synchronize_session=False)
            
            # Documents
            if test_user_ids:
                db.query(MedicalDocument).filter(MedicalDocument.patient_id.in_(test_user_ids)).delete(synchronize_session=False)
            if test_hospitals_ids:
                db.query(MedicalDocument).filter(MedicalDocument.hospital_id.in_(test_hospitals_ids)).delete(synchronize_session=False)
            
            # Profiles
            if test_user_ids:
                db.query(PractitionerProfile).filter(PractitionerProfile.user_id.in_(test_user_ids)).delete(synchronize_session=False)
                db.query(PatientProfile).filter(PatientProfile.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            
            # Triage and Visits
            if test_hospitals_ids:
                db.query(TriageRequest).filter(TriageRequest.hospital_id.in_(test_hospitals_ids)).delete(synchronize_session=False)
                db.query(Visit).filter(Visit.hospital_id.in_(test_hospitals_ids)).delete(synchronize_session=False)
            if test_user_ids:
                db.query(TriageRequest).filter(TriageRequest.patient_id.in_(test_user_ids)).delete(synchronize_session=False)
                db.query(Visit).filter(Visit.patient_id.in_(test_user_ids)).delete(synchronize_session=False)
                db.query(Visit).filter(Visit.doctor_id.in_(test_user_ids)).delete(synchronize_session=False)
            
            # Staff
            if test_user_ids:
                db.query(HospitalStaff).filter(HospitalStaff.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            if test_hospitals_ids:
                db.query(HospitalStaff).filter(HospitalStaff.hospital_id.in_(test_hospitals_ids)).delete(synchronize_session=False)
            
            # Parent Objects
            if test_user_ids:
                db.query(User).filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
            if test_hospitals_ids:
                db.query(Hospital).filter(Hospital.id.in_(test_hospitals_ids)).delete(synchronize_session=False)
            
            db.commit()
            print("Successfully cleaned.")
        else:
            print("Nothing to clean.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_test_data()
