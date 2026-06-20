"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MedFlow Guardian API",
    description="Backend API for the MedFlow Guardian healthcare platform.",
    version="0.1.0",
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


@app.get("/health", tags=["health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "ok"}
