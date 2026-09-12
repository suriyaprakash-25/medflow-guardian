"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, triage, websockets, monitoring, hospital, document, access, notification, audit, users, appointments, clinical, admin, visits, interoperability, consent
from app.core.logging import log
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

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

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )

from app.core.config import settings

# ---------------------------------------------------------------------------
# CORS — allow the doctor-portal and patient-app dev servers
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# Security Headers Middleware (Phase 10 Hardening)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])
app.include_router(hospital.router, prefix="/api", tags=["hospital"])
app.include_router(document.router, prefix="/api", tags=["document"])
app.include_router(access.router, prefix="/api", tags=["access"])
app.include_router(notification.router, prefix="/api", tags=["notification"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(appointments.router, prefix="/api", tags=["appointments"])
app.include_router(visits.router, prefix="/api", tags=["visits"])
app.include_router(clinical.router, prefix="/api/clinical", tags=["clinical"])
app.include_router(interoperability.router, prefix="/api", tags=["interoperability"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(consent.router, prefix="/api", tags=["consent"])
app.include_router(websockets.router, tags=["websockets"])

@app.get("/health", tags=["health"])
async def health_check():
    """Liveness probe: answers 'Is the application process alive?'"""
    return {"status": "ok"}

@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness probe: answers 'Can this instance serve requests safely?'"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Verify database connectivity
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service unavailable: Database connection failed")
    finally:
        db.close()
