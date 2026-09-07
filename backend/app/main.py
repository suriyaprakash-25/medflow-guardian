"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, triage, websockets, monitoring, hospital, document, access, notification, audit

# ---------------------------------------------------------------------------
# Startup: create tables + seed demo users
# ---------------------------------------------------------------------------
def _seed_db():
    """Create all tables and insert demo users if they don't already exist."""
    from app.core.database import SessionLocal, engine, Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    from app.models.user import User
    from app.models.hospital import Hospital, HospitalStaff, Visit
    from app.core.security import get_password_hash

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

    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_db()
    yield


app = FastAPI(
    title="MedFlow Guardian API",
    description="Backend API for the MedFlow Guardian healthcare platform.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the doctor-portal and patient-app dev servers
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])
app.include_router(hospital.router, prefix="/api", tags=["hospital"])
app.include_router(document.router, prefix="/api", tags=["document"])
app.include_router(access.router, prefix="/api", tags=["access"])
app.include_router(notification.router, prefix="/api", tags=["notification"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(websockets.router, tags=["websockets"])

@app.get("/health", tags=["health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "ok"}
