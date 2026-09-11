import pytest
from unittest import mock

def test_postgres_engine_config():
    with mock.patch("app.core.config.settings.SQLALCHEMY_DATABASE_URI", "postgresql://user:pass@localhost/db"):
        with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
            import importlib
            import app.core.database
            importlib.reload(app.core.database)
            
            mock_create_engine.assert_any_call(
                "postgresql://user:pass@localhost/db",
                pool_size=10,
                max_overflow=5,
                pool_pre_ping=True,
                pool_recycle=1800,
                connect_args={"options": "-c statement_timeout=30000"}
            )
