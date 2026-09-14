import os
from pathlib import Path
from urllib.parse import urlparse

# Backend tests exercise PostgreSQL-specific behavior (RLS, constraints, locking,
# migrations). Never inherit a developer/production DATABASE_URL implicitly.
# CI may keep supplying DATABASE_URL because it provisions a dedicated local DB.
_DEFAULT_LOCAL_TEST_DATABASE_URL = (
    "postgresql://medflow:password@127.0.0.1:55432/medflow_test"
)
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_test_database_url() -> str:
    is_ci = _is_truthy("CI") or _is_truthy("GITHUB_ACTIONS")
    explicit_test_url = os.getenv("TEST_DATABASE_URL", "").strip()
    ci_database_url = os.getenv("DATABASE_URL", "").strip() if is_ci else ""
    database_url = explicit_test_url or ci_database_url or _DEFAULT_LOCAL_TEST_DATABASE_URL
    parsed = urlparse(database_url)

    if parsed.scheme not in {"postgresql", "postgresql+psycopg2"}:
        raise RuntimeError(
            "Backend tests require PostgreSQL. Set TEST_DATABASE_URL to a dedicated "
            "test PostgreSQL database."
        )

    database_name = parsed.path.lstrip("/").split("?", 1)[0]
    # CI also validates a freshly restored clone named medflow_restore. It is local,
    # disposable, and created inside the workflow, so allow that exact name only in CI.
    is_known_ci_restore = is_ci and database_name == "medflow_restore"
    if (
        "test" not in database_name.lower()
        and not is_known_ci_restore
        and not _is_truthy("ALLOW_UNSAFE_TEST_DATABASE")
    ):
        raise RuntimeError(
            "Refusing to run tests against a database whose name does not contain "
            "'test'. Set TEST_DATABASE_URL to a dedicated test database."
        )

    if parsed.hostname not in _LOCAL_HOSTS and not _is_truthy(
        "ALLOW_REMOTE_TEST_DATABASE"
    ):
        raise RuntimeError(
            "Refusing to run the test suite against a remote PostgreSQL host. "
            "Use a local test database or explicitly set ALLOW_REMOTE_TEST_DATABASE=true."
        )

    return database_url


# Configure test-only behavior before importing any application modules. The
# application settings object and SQLAlchemy engine are constructed at import time.
os.environ["ENV"] = "test"
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = _resolve_test_database_url()
os.environ.setdefault("SUPABASE_URL", "http://127.0.0.1:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from app.core.database import SessionLocal, engine, get_db
from app.main import app

_BACKEND_ROOT = Path(__file__).resolve().parent


@pytest.fixture(scope="session", autouse=True)
def configure_postgres():
    """Fail fast on DB connectivity and keep the test schema at migration head."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise RuntimeError(
            "Cannot connect to the dedicated MedFlow test PostgreSQL database. "
            "Start it with `docker compose -f docker-compose.test.yml up -d --wait` "
            "or set TEST_DATABASE_URL to another dedicated test database."
        ) from exc

    alembic_config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    yield

    # Ensure no test process leaves pooled/zombie database connections behind.
    engine.dispose()


@pytest.fixture(scope="function")
def db_session():
    """Run each DB test inside an outer transaction that is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    session.begin_nested()

    # Application code may commit the SAVEPOINT. Recreate it while preserving the
    # outer test transaction so database state cannot leak into the next test.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, nested_transaction):
        parent = nested_transaction._parent
        if nested_transaction.nested and parent is not None and not parent.nested:
            session.begin_nested()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
