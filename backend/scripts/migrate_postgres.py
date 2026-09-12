import os
import sys

# Add the parent directory to sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

def add_column(conn, table, column_name, column_type):
    try:
        # Check if column exists in PostgreSQL
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=:table AND column_name=:column_name
        """)
        result = conn.execute(check_query, {"table": table, "column_name": column_name}).fetchone()
        
        if result:
            print(f"Column {column_name} already exists in {table}")
        else:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
            print(f"Added {column_name} to {table}")
    except Exception as e:
        print(f"Error adding {column_name} to {table}: {e}")

def run_migration():
    with engine.connect() as conn:
        add_column(conn, 'users', 'phone_number', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'date_of_birth', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'address', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'emergency_contact_name', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'emergency_contact_phone', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'blood_type', 'VARCHAR')
        add_column(conn, 'patient_profiles', 'allergies', 'VARCHAR')
        conn.commit()

if __name__ == "__main__":
    run_migration()
    print("PostgreSQL migration completed successfully.")
