import os
import sys
import sqlite3
from sqlalchemy import create_engine, MetaData, inspect
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import datetime

# Setup paths to import from backend
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.config import settings

def migrate_data():
    sqlite_db_path = "medflow.db"
    
    if not os.path.exists(sqlite_db_path):
        print(f"ERROR: Local SQLite database {sqlite_db_path} not found.")
        sys.exit(1)

    postgres_url = settings.SQLALCHEMY_DATABASE_URI
    
    if postgres_url.startswith("sqlite"):
        print("ERROR: DATABASE_URL is still configured for SQLite.")
        print("Please configure a PostgreSQL connection string in .env to run the migration.")
        sys.exit(1)

    print(f"Connecting to PostgreSQL: {postgres_url}")
    pg_engine = create_engine(postgres_url)
    
    try:
        pg_engine.connect()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    # Reflect PostgreSQL schema
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)
    
    # We rely on Alembic having already run to create the schema!
    inspector = inspect(pg_engine)
    pg_tables = inspector.get_table_names()

    if not pg_tables or "users" not in pg_tables:
        print("ERROR: PostgreSQL database schema is empty.")
        print("Please run `alembic upgrade head` on the PostgreSQL database before migrating data.")
        sys.exit(1)

    print("\nConnecting to local SQLite database...")
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Define the tables to migrate, honoring foreign key constraints (parents first)
    # This must match the actual tables in the schema
    tables_to_migrate = [
        "users",
        "hospitals",
        "hospital_staff",
        "practitioner_profiles",
        "visits",
        "triage_requests",
        "vitals_readings",
        "medical_documents",
        "document_access_grants",
        "document_access_grant_documents",
        "audit_logs",
        "notifications"
    ]

    total_migrated = 0

    with pg_engine.begin() as pg_conn:
        # Disable foreign key checks for this transaction (requires superuser, standard in Supabase)
        pg_conn.execute(sa.text("SET session_replication_role = 'replica';"))
        
        try:
            for table_name in tables_to_migrate:
                if table_name not in pg_tables:
                    print(f"WARNING: Table {table_name} not found in PostgreSQL. Skipping.")
                    continue

                print(f"\nMigrating table: {table_name}...")
                
                # Get sqlite data
                try:
                    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                    rows = sqlite_cursor.fetchall()
                except sqlite3.OperationalError as e:
                    print(f"WARNING: Could not read from {table_name} in SQLite: {e}")
                    continue

                if not rows:
                    print(f"Table {table_name} is empty. Skipping.")
                    continue

                # Prepare insert
                pg_table = pg_meta.tables[table_name]
                
                # Map sqlite rows to dicts
                insert_data = []
                for row in rows:
                    row_dict = dict(row)
                    insert_data.append(row_dict)

                try:
                    pg_conn.execute(pg_table.insert(), insert_data)
                    print(f"Successfully migrated {len(insert_data)} rows into {table_name}.")
                    total_migrated += len(insert_data)
                except Exception as e:
                    print(f"ERROR migrating {table_name}: {e}")
                    sys.exit(1)
        finally:
            # Re-enable foreign key checks
            pg_conn.execute(sa.text("SET session_replication_role = 'origin';"))

    print(f"\n--- Migration Complete ---")
    print(f"Total rows migrated: {total_migrated}")

if __name__ == "__main__":
    migrate_data()
