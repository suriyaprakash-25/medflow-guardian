from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

from sqlalchemy.pool import NullPool

# Production uses PostgreSQL statement timeouts. A file-backed SQLite engine is
# allowed only by Settings in explicit test processes, enabling deterministic
# browser workflows when an external Supabase environment is unavailable.
_is_sqlite = settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite")
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=NullPool,
    connect_args=(
        {"check_same_thread": False}
        if _is_sqlite
        else {"options": "-c statement_timeout=30000"}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
