import os
import sys
from sqlalchemy import create_engine, MetaData

# Setup paths
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.core.config import settings

def drop_all():
    url = settings.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to: {url}")
    engine = create_engine(url)
    
    meta = MetaData()
    meta.reflect(bind=engine)
    
    # Drop all tables, including alembic_version
    with engine.begin() as conn:
        for table in reversed(meta.sorted_tables):
            print(f"Dropping table {table.name}...")
            conn.execute(table.delete()) # wait, we want to DROP table, not delete data
            
        meta.drop_all(bind=engine)
        print("All tables dropped.")

if __name__ == "__main__":
    drop_all()
