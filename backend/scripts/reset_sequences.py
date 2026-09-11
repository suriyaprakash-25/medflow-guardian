import os
import sys
from sqlalchemy import create_engine, text

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.config import settings

def reset_sequences():
    print("Connecting to Supabase PostgreSQL...")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    with engine.connect() as conn:
        # Get all sequences
        result = conn.execute(text("""
            SELECT c.relname as sequence_name
            FROM pg_class c
            WHERE c.relkind = 'S';
        """))
        sequences = [row[0] for row in result]
        
    for seq in sequences:
        if seq.endswith('_id_seq'):
            table_name = seq[:-7] # remove '_id_seq'
            with engine.begin() as conn:
                try:
                    conn.execute(text(f"""
                        SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM "{table_name}") + 1, 1), false);
                    """))
                    print(f"Reset sequence {seq} for table {table_name}")
                except Exception as e:
                    print(f"Skipped {seq}: {e}")

if __name__ == "__main__":
    reset_sequences()
