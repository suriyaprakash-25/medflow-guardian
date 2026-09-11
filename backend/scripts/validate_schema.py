import os
import sys
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.config import settings
from app.models import Base

def validate_schema():
    print(f"DATABASE_URL configured: {'Yes' if settings.SQLALCHEMY_DATABASE_URI else 'No'}")
    
    if not settings.SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
        print("ERROR: Not a PostgreSQL URL!")
        sys.exit(1)

    print("Connecting to Supabase PostgreSQL...")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    # Reflect actual db schema
    db_meta = MetaData()
    db_meta.reflect(bind=engine)
    
    # Get model metadata
    model_meta = Base.metadata
    
    model_tables = set(model_meta.tables.keys())
    db_tables = set(db_meta.tables.keys())
    
    print("\n--- SCHEMA VALIDATION ---")
    
    # We ignore alembic_version
    if 'alembic_version' in db_tables:
        db_tables.remove('alembic_version')
        
    missing_in_db = model_tables - db_tables
    extra_in_db = db_tables - model_tables
    
    if missing_in_db:
        print(f"FAIL: Missing tables in DB: {missing_in_db}")
    else:
        print("PASS: All model tables exist in PostgreSQL DB.")
        
    if extra_in_db:
        print(f"INFO: Extra tables in DB: {extra_in_db}")
        
    # Check columns
    for table_name in model_tables:
        if table_name not in db_tables:
            continue
        
        m_table = model_meta.tables[table_name]
        d_table = db_meta.tables[table_name]
        
        m_cols = set(m_table.columns.keys())
        d_cols = set(d_table.columns.keys())
        
        if m_cols != d_cols:
            print(f"FAIL: Column mismatch in {table_name}")
            print(f"  Model cols: {m_cols}")
            print(f"  DB cols: {d_cols}")
        else:
            # check constraints/indexes
            print(f"PASS: {table_name} columns match exactly.")

if __name__ == "__main__":
    validate_schema()
