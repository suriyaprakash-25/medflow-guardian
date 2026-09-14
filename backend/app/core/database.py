import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Production uses PostgreSQL statement timeouts. A file-backed SQLite engine is
# allowed only by Settings in explicit test processes, enabling deterministic
# browser workflows when an external Supabase environment is unavailable.
_is_sqlite = settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite")
_is_test_process = os.getenv("TESTING", "").strip().lower() == "true"

if _is_sqlite:
    _connect_args = {"check_same_thread": False}
else:
    # A finite connect timeout prevents an unreachable PostgreSQL/Supabase host
    # from stalling every test for the driver's much longer default timeout.
    _connect_args = {
        "options": "-c statement_timeout=30000",
        "connect_timeout": 5 if _is_test_process else 10,
    }

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=NullPool,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
