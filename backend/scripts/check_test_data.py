import os, sys
from sqlalchemy import create_engine, text

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)
from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
with engine.connect() as conn:
    res = conn.execute(text("SELECT email FROM users WHERE email LIKE 'test_%@demo.com'")).fetchall()
    print("Users found:", res)
    
    hospitals = conn.execute(text("SELECT name FROM hospitals WHERE name LIKE 'Test Hospital%'")).fetchall()
    print("Hospitals found:", hospitals)
