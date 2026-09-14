"""
MedFlow Guardian — FastAPI Backend
===================================
Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
import re
import secrets
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
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
    privacy,
    triage,
    users,
    visits,
    websockets,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import log
from app.core.observability import (
    monotonic_time,
    observe_http_request,
    render_prometheus,
    set_readiness,
)
from app.core.request_context import bind_request_context, reset_request_context


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


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
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Correlation-ID",
    ],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)

app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def observe_request(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id
        if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid.uuid4())
    )
    supplied_correlation_id = request.headers.get("X-Correlation-ID", "")
    correlation_id = (
        supplied_correlation_id
        if _REQUEST_ID_PATTERN.fullmatch(supplied_correlation_id)
        else request_id
    )
    context_tokens = bind_request_context(request_id, correlation_id)
    started = monotonic_time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        duration = monotonic_time() - started
        observe_http_request(
            method=request.method,
            route=route,
            status_code=status_code,
            duration_seconds=duration,
        )
        log.exception(
            "Unhandled request failure",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "route": route,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )
        raise
    finally:
        reset_request_context(context_tokens)

    route = getattr(request.scope.get("route"), "path", "unmatched")
    duration = monotonic_time() - started
    if route != "/internal/metrics":
        observe_http_request(
            method=request.method,
            route=route,
            status_code=status_code,
            duration_seconds=duration,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    log_method = log.warning if status_code >= 500 else log.info
    log_method(
        "HTTP request completed",
        extra={
            "event": "http_request",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "route": route,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 3),
        },
    )
    return response


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
app.include_router(privacy.router, prefix="/api", tags=["privacy"])
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
    try:
        from app.core.operational_readiness import (
            database_ready,
            production_dependency_status,
        )

        if settings.ENV == "production":
            dependency_status = production_dependency_status()
            if not all(dependency_status.values()):
                failed = sorted(
                    name for name, ready in dependency_status.items() if not ready
                )
                log.error(
                    "Production dependency readiness failed",
                    extra={"event": "readiness_failed", "components": failed},
                )
                raise RuntimeError("Production dependency unavailable")
        elif not database_ready():
            raise RuntimeError("Database unavailable")
        set_readiness(True)
        return {"status": "ready"}
    except Exception:
        set_readiness(False)
        log.exception("Readiness database connectivity check failed")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: dependency readiness failed",
        )


@app.get("/internal/metrics", include_in_schema=False)
async def metrics(request: Request):
    """Protected Prometheus scrape endpoint; never contains request payloads."""
    configured = settings.OBSERVABILITY_TOKEN
    authorization = request.headers.get("Authorization", "")
    supplied = authorization[7:] if authorization.startswith("Bearer ") else ""
    if not configured or not secrets.compare_digest(supplied, configured):
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse(
        render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
