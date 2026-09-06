import os

class Settings:
    PROJECT_NAME = "MedFlow Guardian API"
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret_hackathon_key_change_in_prod")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./medflow.db")

settings = Settings()
