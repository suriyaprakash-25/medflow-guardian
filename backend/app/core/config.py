import os
import secrets
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")


def _parse_cors_origins(raw_values: list[str]) -> list[str]:
    """Normalize and validate explicit browser origins.

    Credentialed CORS cannot safely use a wildcard. Production deployment must
    therefore provide concrete HTTP(S) origins for every MedFlow frontend.
    """
    origins: list[str] = []
    for raw in raw_values:
        for value in raw.split(","):
            origin = value.strip().rstrip("/")
            if not origin:
                continue
            if origin == "*":
                raise ValueError("Wildcard CORS origins are not allowed")
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {origin}")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError(f"CORS origin must not contain a path/query/fragment: {origin}")
            if origin not in origins:
                origins.append(origin)
    return origins


class Settings:
    PROJECT_NAME = "MedFlow Guardian API"
    ENV = ENV
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived token

    # Production secrets must be stable and explicitly provisioned.
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if ENV == "production":
            raise ValueError("CRITICAL: SECRET_KEY environment variable is missing in production!")
        SECRET_KEY = secrets.token_urlsafe(32)

    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    if not ENCRYPTION_KEY:
        if ENV == "production":
            raise ValueError("CRITICAL: ENCRYPTION_KEY environment variable is missing in production!")
        from cryptography.fernet import Fernet
        ENCRYPTION_KEY = Fernet.generate_key().decode()

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
        print("CRITICAL CONFIGURATION ERROR: A valid PostgreSQL DATABASE_URL is required.")
        print("SQLite is strictly prohibited in the production architecture.")
        sys.exit(1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # CORS Configuration. Render injects the three service URLs individually;
    # operators can also provide FRONTEND_CORS_ORIGINS for custom domains.
    _cors_inputs = [
        os.getenv("FRONTEND_CORS_ORIGINS", ""),
        os.getenv("PATIENT_APP_ORIGIN", ""),
        os.getenv("DOCTOR_PORTAL_ORIGIN", ""),
        os.getenv("ADMIN_PORTAL_ORIGIN", ""),
    ]
    if ENV != "production" and not any(value.strip() for value in _cors_inputs):
        _cors_inputs = [
            "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
            "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
        ]
    FRONTEND_CORS_ORIGINS = _parse_cors_origins(_cors_inputs)
    if ENV == "production" and not FRONTEND_CORS_ORIGINS:
        raise ValueError(
            "CRITICAL: production requires at least one explicit frontend CORS origin"
        )

    # The Render-generated frontend and API hostnames are cross-origin and may
    # also be cross-site. Production therefore uses a Secure SameSite=None
    # refresh cookie, while cookie-authenticated endpoints separately validate
    # the browser Origin against the exact CORS allowlist.
    REFRESH_COOKIE_SAMESITE = os.getenv(
        "REFRESH_COOKIE_SAMESITE",
        "none" if ENV == "production" else "lax",
    ).strip().lower()
    if REFRESH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        raise ValueError(
            "REFRESH_COOKIE_SAMESITE must be one of: lax, strict, none"
        )
    REFRESH_COOKIE_SECURE = ENV == "production"
    if ENV == "production" and REFRESH_COOKIE_SAMESITE == "none" and not REFRESH_COOKIE_SECURE:
        raise ValueError("SameSite=None refresh cookies must be Secure in production")

    # Proxy / rate-limit identity. Forwarded headers are ignored unless the
    # immediate peer belongs to one of these explicitly configured networks.
    TRUSTED_PROXY_CIDRS_RAW = os.getenv("TRUSTED_PROXY_CIDRS", "")
    TRUSTED_PROXY_CIDRS = [
        cidr.strip()
        for cidr in TRUSTED_PROXY_CIDRS_RAW.split(",")
        if cidr.strip()
    ]

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    if not SUPABASE_URL:
        print("CRITICAL CONFIGURATION ERROR: SUPABASE_URL is required.")
        sys.exit(1)

    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not SUPABASE_KEY:
        print("CRITICAL CONFIGURATION ERROR: SUPABASE_SERVICE_ROLE_KEY is required.")
        sys.exit(1)

    SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "medical-documents")

    # R7 Malware Scanning. Production must have a real scanner configured.
    # Test/development environments may leave the scanner unset; documents then
    # remain non-releasable and are marked scan_error rather than auto-cleaned.
    MALWARE_SCANNER_HOST = os.getenv("CLAMAV_HOST")
    MALWARE_SCANNER_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
    MALWARE_SCANNER_TIMEOUT_SECONDS = float(
        os.getenv("CLAMAV_TIMEOUT_SECONDS", "15")
    )
    MALWARE_SCANNER_MAX_BYTES = int(
        os.getenv("CLAMAV_MAX_BYTES", str(10 * 1024 * 1024))
    )

    if ENV == "production" and not MALWARE_SCANNER_HOST:
        raise ValueError(
            "CRITICAL: CLAMAV_HOST is required in production; uploads must not be auto-cleared without a real malware scanner."
        )


settings = Settings()
