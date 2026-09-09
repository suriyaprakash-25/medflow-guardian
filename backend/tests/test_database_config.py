import os
from unittest import mock
import pytest
from sqlalchemy import create_engine
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

def test_sqlite_engine_config():
    with mock.patch("app.core.config.settings.SQLALCHEMY_DATABASE_URI", "sqlite:///./medflow.db"):
        with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
            import importlib
            import app.core.database
            importlib.reload(app.core.database)
            
            mock_create_engine.assert_any_call(
                "sqlite:///./medflow.db",
                connect_args={"check_same_thread": False}
            )

def test_postgres_engine_config():
    with mock.patch("app.core.config.settings.SQLALCHEMY_DATABASE_URI", "postgresql://user:pass@localhost/db"):
        with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
            import importlib
            import app.core.database
            importlib.reload(app.core.database)
            
            mock_create_engine.assert_any_call(
                "postgresql://user:pass@localhost/db",
                connect_args={}
            )
