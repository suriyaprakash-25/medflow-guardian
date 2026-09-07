import os
import secrets

class Settings:
    PROJECT_NAME = "MedFlow Guardian API"
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./medflow.db")

settings = Settings()
