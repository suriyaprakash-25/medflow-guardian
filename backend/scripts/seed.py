import os
import sys
from sqlalchemy import inspect
from alembic.config import Config
from alembic import command

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.core.security import get_password_hash

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    
    inspector = inspect(engine)
    has_users = inspector.has_table("users")
    has_alembic = inspector.has_table("alembic_version")
    
    if has_users and not has_alembic:
        print("Legacy database detected. Stamping schema to head.")
        command.stamp(alembic_cfg, "head")
        
    print("Running migrations...")
    command.upgrade(alembic_cfg, "head")

def seed_data():
    print("Seeding database...")
    db = SessionLocal()
    try:
        # 1. Create Patient
        patient = db.query(User).filter(User.email == "patient@demo.com").first()
        if not patient:
            patient = User(
                email="patient@demo.com",
                hashed_password=get_password_hash("password"),
                role="patient",
                full_name="Demo Patient",
                is_active=True,
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # 2. Create Doctors
        doctor1 = db.query(User).filter(User.email == "doctor@demo.com").first()
        if not doctor1:
            doctor1 = User(
                email="doctor@demo.com",
                hashed_password=get_password_hash("password"),
                role="doctor",
                full_name="Demo Doctor 1",
                is_active=True,
            )
            db.add(doctor1)
            
        doctor2 = db.query(User).filter(User.email == "doctor2@demo.com").first()
        if not doctor2:
            doctor2 = User(
                email="doctor2@demo.com",
                hashed_password=get_password_hash("password"),
                role="doctor",
                full_name="Demo Doctor 2",
                is_active=True,
            )
            db.add(doctor2)
            db.commit()
            db.refresh(doctor1)
            db.refresh(doctor2)

        # Create Admin
        admin1 = db.query(User).filter(User.email == "admin@demo.com").first()
        if not admin1:
            admin1 = User(
                email="admin@demo.com",
                hashed_password=get_password_hash("password"),
                role="admin",
                full_name="Hospital Administrator",
                is_active=True,
            )
            db.add(admin1)
            db.commit()
            db.refresh(admin1)

        # 3. Create Hospitals
        h1 = db.query(Hospital).filter(Hospital.name == "City General Hospital").first()
        if not h1:
            h1 = Hospital(name="City General Hospital", address="123 Health Ave")
            db.add(h1)
        h2 = db.query(Hospital).filter(Hospital.name == "Westside Clinic").first()
        if not h2:
            h2 = Hospital(name="Westside Clinic", address="456 West Blvd")
            db.add(h2)
            db.commit()
            db.refresh(h1)
            db.refresh(h2)

        # 4. Create Hospital Staff
        if not db.query(HospitalStaff).filter(HospitalStaff.user_id == doctor1.id).first():
            db.add(HospitalStaff(user_id=doctor1.id, hospital_id=h1.id, role="doctor"))
        if not db.query(HospitalStaff).filter(HospitalStaff.user_id == doctor2.id).first():
            db.add(HospitalStaff(user_id=doctor2.id, hospital_id=h2.id, role="doctor"))
        if not db.query(HospitalStaff).filter(HospitalStaff.user_id == admin1.id).first():
            db.add(HospitalStaff(user_id=admin1.id, hospital_id=h1.id, role="admin"))
        db.commit()

        # 5. Create Visits
        if not db.query(Visit).first():
            db.add(Visit(patient_id=patient.id, hospital_id=h1.id, doctor_id=doctor1.id, status="completed", reason="Annual Checkup"))
            db.add(Visit(patient_id=patient.id, hospital_id=h2.id, doctor_id=doctor2.id, status="active", reason="Specialist Consult"))
            db.commit()
            
        print("Database seeded successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    run_migrations()
    seed_data()
