"""Create deterministic test-only data for the authenticated P0 browser run."""

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models import Hospital, HospitalStaff, MedicalDocument, User, Visit
from app.services.storage import storage_service


def seed() -> None:
    if engine.url.drivername != "sqlite":
        raise RuntimeError("P0 E2E seed is restricted to an explicit SQLite test database")
    if "p0-e2e" not in str(engine.url.database):
        raise RuntimeError("P0 E2E database filename must contain 'p0-e2e'")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        patient = User(
            email="patient@demo.com",
            hashed_password=get_password_hash("password"),
            role="patient",
            full_name="P0 Patient",
            is_active=True,
        )
        doctor = User(
            email="doctor@demo.com",
            hashed_password=get_password_hash("password"),
            role="doctor",
            full_name="P0 Doctor",
            is_active=True,
        )
        hospital = Hospital(name="P0 Validation Hospital", address="Test environment")
        db.add_all([patient, doctor, hospital])
        db.flush()
        db.add(HospitalStaff(user_id=doctor.id, hospital_id=hospital.id, role="doctor"))
        visit = Visit(
            patient_id=patient.id,
            doctor_id=doctor.id,
            hospital_id=hospital.id,
            status="completed",
            reason="P0 browser validation",
        )
        db.add(visit)
        db.flush()

        object_key = f"patient/{patient.id}/p0-validation.txt"
        local_path = storage_service._local_path(object_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        payload = b"MedFlow P0 protected document validation\n"
        local_path.write_bytes(payload)
        db.add(
            MedicalDocument(
                patient_id=patient.id,
                hospital_id=hospital.id,
                uploaded_by_doctor_id=doctor.id,
                visit_id=visit.id,
                document_type="lab report",
                title="P0 Validation Document",
                description="Deterministic browser workflow fixture",
                original_filename="p0-validation.txt",
                stored_filename=object_key,
                mime_type="text/plain",
                file_size=len(payload),
                scan_status="clean",
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
