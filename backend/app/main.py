"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import (
    access,
    admin,
    appointments,
    audit,
    auth,
    clinical,
    consent,
    document,
    hospital,
    interoperability,
    monitoring,
    notification,
    triage,
    users,
    visits,
    websockets,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


# Interactive OpenAPI surfaces are useful in development but expose the full
# endpoint/schema inventory in production. Keep them out of the public runtime.
_docs_enabled = settings.ENV != "production"

app = FastAPI(
    title="MedFlow Guardian API",
    description="Backend API for the MedFlow Guardian healthcare platform.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    # Do not disclose route-specific limiter internals to unauthenticated clients.
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


# Credentialed browser traffic is constrained to the HTTP verbs and headers
# actually used by the three MedFlow portals. Wildcard origins remain forbidden
# by Settings._parse_cors_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):  # noqa: ARG001
    """Apply defense-in-depth headers to every backend response.

    The backend returns PHI-bearing API responses and protected document bytes,
    so intermediaries and browsers must not cache them. Interactive docs are
    disabled in production, allowing the production CSP to be API-only.
    """
    response = await call_next(request)

    if settings.ENV == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'"
        )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # Modern browsers ignore this legacy filter; explicitly disabling it avoids
    # historical XSS-auditor behavior that can introduce side channels.
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
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
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        log.exception("Readiness database connectivity check failed")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Database connection failed",
        )
    finally:
        db.close()
