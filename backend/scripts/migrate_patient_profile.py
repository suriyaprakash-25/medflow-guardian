import sqlite3
import os
import sys

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'medflow.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column_name, column_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
        print(f"Added {column_name} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column_name} already exists in {table}")
        else:
            print(f"Error adding {column_name} to {table}: {e}")

add_column('users', 'phone_number', 'VARCHAR')
add_column('patient_profiles', 'date_of_birth', 'VARCHAR')
add_column('patient_profiles', 'address', 'VARCHAR')
add_column('patient_profiles', 'emergency_contact_name', 'VARCHAR')
add_column('patient_profiles', 'emergency_contact_phone', 'VARCHAR')
add_column('patient_profiles', 'blood_type', 'VARCHAR')
add_column('patient_profiles', 'allergies', 'VARCHAR')

conn.commit()
conn.close()
print("Migration completed successfully.")
