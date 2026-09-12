from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

from sqlalchemy.pool import NullPool

# Production connection pooling settings for PostgreSQL/Supabase
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=NullPool,
    connect_args={
        "options": "-c statement_timeout=30000" # 30s timeout to prevent leaked long-running transactions
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
