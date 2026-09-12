import pytest
from unittest import mock
from sqlalchemy.pool import NullPool

def test_postgres_engine_config():
    import importlib
    import app.core.database

    with mock.patch("app.core.config.settings.SQLALCHEMY_DATABASE_URI", "postgresql://user:pass@localhost/db"):
        with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
            importlib.reload(app.core.database)
            
            mock_create_engine.assert_any_call(
                "postgresql://user:pass@localhost/db",
                poolclass=NullPool,
                connect_args={"options": "-c statement_timeout=30000"}
            )

    # Do not leak the mocked engine into tests collected after this one.
    importlib.reload(app.core.database)
