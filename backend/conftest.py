import pytest
from sqlalchemy import event
from app.core.database import SessionLocal, engine
from app.main import app
from app.core.database import get_db

import os
os.environ["TESTING"] = "True"

@pytest.fixture(scope="session", autouse=True)
def configure_postgres():
    # Make sure we're using PostgreSQL
    assert str(engine.url).startswith("postgresql"), "Tests must run against PostgreSQL!"
    yield
    # Safely close all connections at the end of the test session
    # This prevents Supabase pool exhaustion and zombie connections
    engine.dispose()

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh sqlalchemy session for each test that operates in a
    transaction that is rolled back at the end of the test.
    """
    connection = engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()
    
    # Bind session to the connection
    session = SessionLocal(bind=connection)
    
    # Start a nested transaction (SAVEPOINT)
    session.begin_nested()
    
    # If the application code calls session.commit, it will commit the nested
    # transaction but not the outer transaction. Then we restart a new nested
    # transaction for any subsequent operations in the same test.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
            
    # Override FastAPI dependency to use this session
    def override_get_db():
        yield session
        
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    app.dependency_overrides.clear()
    session.close()
    transaction.rollback()
    connection.close()
