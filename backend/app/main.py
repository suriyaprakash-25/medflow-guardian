"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, triage, websockets, monitoring, hospital, document, access, notification, audit, users

# ---------------------------------------------------------------------------
# Startup: create tables + seed demo users
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(users.router, prefix="/api/users", tags=["users"])
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
