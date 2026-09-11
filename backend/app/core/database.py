from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Production connection pooling settings for PostgreSQL/Supabase
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,      # Tests connections before handing them out (fixes pooler drops)
    pool_recycle=1800,       # Recycles connections older than 30 minutes
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
