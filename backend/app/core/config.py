import os
import sys
import secrets
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

class Settings:
    PROJECT_NAME = "MedFlow Guardian API"
    ENV = ENV
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived token

    # Phase 12 Hardening: Crash if production secrets are missing
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if ENV == "production":
            raise ValueError("CRITICAL: SECRET_KEY environment variable is missing in production!")
        import secrets
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

    # CORS Configuration
    FRONTEND_CORS_ORIGINS_RAW = os.getenv("FRONTEND_CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173")
    FRONTEND_CORS_ORIGINS = [origin.strip() for origin in FRONTEND_CORS_ORIGINS_RAW.split(",") if origin.strip()]

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

settings = Settings()
