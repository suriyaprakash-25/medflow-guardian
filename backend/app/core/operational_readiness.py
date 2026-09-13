"""Production dependency probes used by the readiness endpoint."""

from __future__ import annotations

import socket

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal


def database_ready() -> bool:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return True
    finally:
        db.close()


def clamav_ready() -> bool:
    if not settings.MALWARE_SCANNER_HOST:
        return False
    try:
        with socket.create_connection(
            (settings.MALWARE_SCANNER_HOST, settings.MALWARE_SCANNER_PORT),
            timeout=min(settings.MALWARE_SCANNER_TIMEOUT_SECONDS, 5),
        ) as connection:
            connection.settimeout(5)
            connection.sendall(b"zPING\0")
            return b"PONG" in connection.recv(64)
    except OSError:
        return False


def private_storage_ready() -> bool:
    """Verify the configured Supabase bucket exists and is not public."""
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/bucket/{settings.SUPABASE_BUCKET}"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    }
    try:
        response = httpx.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("id") == settings.SUPABASE_BUCKET and payload.get("public") is False
    except (httpx.HTTPError, ValueError, TypeError):
        return False


def production_dependency_status() -> dict[str, bool]:
    status = {"database": False, "clamav": False, "private_storage": False}
    try:
        status["database"] = database_ready()
    except Exception:
        status["database"] = False
    status["clamav"] = clamav_ready()
    status["private_storage"] = private_storage_ready()
    return status
