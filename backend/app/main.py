"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, triage, websockets, monitoring

# ---------------------------------------------------------------------------
# Startup: create tables + seed demo users
# ---------------------------------------------------------------------------
def _seed_db():
    """Create all tables and insert demo users if they don't already exist."""
    from app.core.database import SessionLocal, engine, Base
    # Import all models so Base knows about them
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    from app.models.user import User
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "patient@demo.com").first():
            db.add(User(
                email="patient@demo.com",
                hashed_password=get_password_hash("password"),
                role="patient",
                full_name="Demo Patient",
                is_active=True,
            ))
        if not db.query(User).filter(User.email == "doctor@demo.com").first():
            db.add(User(
                email="doctor@demo.com",
                hashed_password=get_password_hash("password"),
                role="doctor",
                full_name="Demo Doctor",
                is_active=True,
            ))
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
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])
app.include_router(websockets.router, tags=["websockets"])

@app.get("/health", tags=["health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "ok"}
