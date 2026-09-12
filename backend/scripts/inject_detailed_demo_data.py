import os
import sys
from datetime import datetime, timedelta
import random

# Setup paths
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.database import SessionLocal
from app.models.user import User
from app.models.hospital import Hospital, Visit, Appointment
from app.models.monitoring import PatientReading, Message
from app.models.triage import TriageRequest
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.notification import Notification
from app.models.clinical import LabResult, ClinicalNote, Medication, Prescription
from app.models.consent import Consent, ConsentState, ConsentPolicyVersion

def inject_data():
    db = SessionLocal()
    try:
        # Get base users
        patient = db.query(User).filter(User.email == "patient@demo.com").first()
        doctor1 = db.query(User).filter(User.email == "doctor@demo.com").first()
        doctor2 = db.query(User).filter(User.email == "doctor2@demo.com").first()
        hospital = db.query(Hospital).first()

        if not patient or not doctor1 or not hospital:
            print("Base users or hospital not found. Please run seed.py first.")
            return

        now = datetime.utcnow()
        
        # Helper to randomly assign to doctor1 or doctor2
        def get_random_doc():
            return random.choice([doctor1.id, doctor2.id])

        # 1. Appointments (15 items)
        print("Injecting Appointments...")
        for i in range(15):
            days_offset = random.randint(-30, 30)
            status = "completed" if days_offset < 0 else ("scheduled" if days_offset > 0 else "active")
            apt = Appointment(
                patient_id=patient.id,
                doctor_id=get_random_doc(),
                hospital_id=hospital.id,
                scheduled_time=now + timedelta(days=days_offset),
                status=status,
                reason=f"Routine checkup {i}" if i % 2 == 0 else f"Specialist consult {i}",
                notes=f"Patient requested follow-up {i}"
            )
            db.add(apt)
            
        # 2. Visits (Add a few more visits to establish relationships solidly)
        print("Injecting Visits...")
        for i in range(10):
            visit = Visit(
                patient_id=patient.id,
                hospital_id=hospital.id,
                doctor_id=get_random_doc(),
                date=now - timedelta(days=random.randint(1, 100)),
                status="completed",
                reason=f"Previous visit {i}"
            )
            db.add(visit)
            
        # 3. Patient Readings (15 items)
        print("Injecting Patient Readings...")
        for i in range(15):
            hr = random.randint(60, 100)
            sys_bp = random.randint(110, 130)
            dia_bp = random.randint(70, 85)
            ox = random.randint(95, 100)
            reading = PatientReading(
                patient_id=patient.id,
                heart_rate=hr,
                blood_pressure_sys=sys_bp,
                blood_pressure_dia=dia_bp,
                oxygen_level=ox,
                is_simulated=True,
                created_at=now - timedelta(hours=i*2)
            )
            db.add(reading)
            
        # 4. Triage Requests (15 items)
        print("Injecting Triage Requests...")
        symptoms_list = ["Headache", "Fever", "Nausea", "Back pain", "Cough", "Fatigue"]
        for i in range(15):
            triage = TriageRequest(
                patient_id=patient.id,
                hospital_id=hospital.id,
                symptoms=f"{random.choice(symptoms_list)} for {random.randint(1, 5)} days",
                priority=random.choice(["low", "medium", "high"]),
                status=random.choice(["pending", "reviewed", "completed"]),
                created_at=now - timedelta(days=i)
            )
            db.add(triage)
            
        # 5. Medical Documents (10-15 items)
        print("Injecting Medical Documents...")
        visit = db.query(Visit).filter(Visit.patient_id == patient.id).first()
        doc_ids = []
        for i in range(12):
            doc = MedicalDocument(
                patient_id=patient.id,
                hospital_id=hospital.id,
                uploaded_by_doctor_id=get_random_doc(),
                visit_id=visit.id if visit else 1,
                title=f"Lab Report {i} - Blood Test",
                document_type=random.choice(["lab_report", "prescription", "scan", "clinical_note"]),
                original_filename=f"dummy_report_{i}.pdf",
                stored_filename=f"docs/dummy_report_{i}_{random.randint(1000, 9999)}.pdf",
                mime_type="application/pdf",
                file_size=1024 * random.randint(10, 5000),
                created_at=now - timedelta(days=random.randint(1, 60))
            )
            db.add(doc)
            db.flush() # get doc id
            doc_ids.append(doc.id)
            
        # 6. Access Requests & Grants
        print("Injecting Access Requests & Grants...")
        for i in range(10):
            req = DocumentAccessRequest(
                patient_id=patient.id,
                requesting_doctor_id=doctor1.id if i % 2 == 0 else doctor2.id,
                requesting_hospital_id=hospital.id,
                reason="Reviewing lab results for treatment",
                status="approved" if i % 2 == 0 else "pending",
                requested_at=now - timedelta(days=i)
            )
            db.add(req)
            db.flush()
            
            if req.status == "approved":
                grant = DocumentAccessGrant(
                    patient_id=patient.id,
                    doctor_id=req.requesting_doctor_id,
                    hospital_id=hospital.id,
                    access_request_id=req.id,
                    status="active",
                    expires_at=now + timedelta(days=30)
                )
                db.add(grant)
                
        # 7. Messages
        print("Injecting Messages...")
        for i in range(15):
            doc_id = doctor1.id
            # Alternate sender between patient and doctor
            sender = patient.id if i % 2 == 0 else doc_id
            receiver = doc_id if i % 2 == 0 else patient.id
            msg = Message(
                sender_id=sender,
                receiver_id=receiver,
                content=f"This is sample message {i} about recent test results.",
                created_at=now - timedelta(hours=15-i)
            )
            db.add(msg)
            
        # 8. Clinical Notes & Lab Results
        print("Injecting Clinical Notes & Lab Results...")
        for i in range(10):
            note = ClinicalNote(
                patient_id=patient.id,
                doctor_id=get_random_doc(),
                hospital_id=hospital.id,
                title=f"Follow-up Note {i}",
                content="Patient is recovering well. Vitals are stable.",
                note_type="progress",
                created_at=now - timedelta(days=i*2)
            )
            db.add(note)
            
            lab = LabResult(
                patient_id=patient.id,
                doctor_id=get_random_doc(),
                hospital_id=hospital.id,
                test_name=random.choice(["Complete Blood Count", "Lipid Panel", "HbA1c"]),
                result_value=str(random.randint(50, 150)),
                unit="mg/dL",
                status="completed",
                test_date=now - timedelta(days=i*3)
            )
            db.add(lab)
            
        # 9. Notifications
        print("Injecting Notifications...")
        for i in range(15):
            notif = Notification(
                user_id=patient.id,
                type=random.choice(["alert", "reminder", "info"]),
                message=f"Please review your newly uploaded document. [Alert {i}]",
                is_read=random.choice([True, False]),
                created_at=now - timedelta(hours=i)
            )
            db.add(notif)
            
            notif_doc = Notification(
                user_id=doctor1.id,
                type="alert",
                message=f"Patient triage request received. [Alert {i}]",
                is_read=False,
                created_at=now - timedelta(hours=i)
            )
            db.add(notif_doc)

        db.commit()
        print("Successfully injected detailed sample data into the database!")

    except Exception as e:
        print(f"Error injecting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    inject_data()
